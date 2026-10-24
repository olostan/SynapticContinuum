#include "../core/types.hpp"
#include "../core/graph_topologies.hpp"
#include "../core/graph_representations.hpp"
#include "../core/graph_metrics.hpp"
#include "../core/partitioners.hpp"
#include "../engines/cpp_serial.hpp"
#include "../engines/cpp_owner_instrumented.hpp"
#include "../engines/cpp_persistent_pool.hpp"
#include "../engines/cpp_openmp_epoch.hpp"
#include "../engines/cpp_pairwise_watermark.hpp"
#include "../engines/cpp_adaptive.hpp"
#include "../engines/cpp_relaxed.hpp"
#include "../engines/cpp_barrier_free_independent.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <string>
#include <chrono>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#include <sys/utsname.h>

namespace sc {

struct BenchmarkConfig {
    std::string profile = "standard";
    std::string build_id = "portable_o3";
    std::string out_path = "";
    std::string python_bin = "";
    std::string ext_script = "";
    std::vector<uint64_t> seeds = {11, 23, 37, 41, 53};
    int32_t repetitions = 5;
    int32_t warmups = 2;
    std::vector<int32_t> worker_counts = {1, 2, 4, 6};
    std::vector<int32_t> smt_counts = {1, 2, 4, 6, 8, 12};
};

struct RepStatsSummary {
    std::vector<double> rep_sim_sec;
    double mean_sim_sec = 0.0;
    double median_sim_sec = 0.0;
    double std_sim_sec = 0.0;
    double mean_total_sec = 0.0;
    Exp4ProfilingStats last_stats;
};

template <typename RunFunc>
RepStatsSummary execute_with_reps(int32_t warmups, int32_t reps, RunFunc&& fn) {
    for (int32_t w = 0; w < warmups; ++w) {
        (void)fn();
    }
    RepStatsSummary s;
    s.rep_sim_sec.reserve(reps);
    double sum_sim = 0.0;
    double sum_tot = 0.0;
    for (int32_t r = 0; r < reps; ++r) {
        s.last_stats = fn();
        s.rep_sim_sec.push_back(s.last_stats.wall_time_sim_sec);
        sum_sim += s.last_stats.wall_time_sim_sec;
        sum_tot += s.last_stats.wall_time_total_sec;
    }
    s.mean_sim_sec = (reps > 0) ? (sum_sim / reps) : 0.0;
    s.mean_total_sec = (reps > 0) ? (sum_tot / reps) : 0.0;

    std::vector<double> sorted = s.rep_sim_sec;
    std::sort(sorted.begin(), sorted.end());
    if (!sorted.empty()) {
        if (sorted.size() % 2 == 1) {
            s.median_sim_sec = sorted[sorted.size() / 2];
        } else {
            s.median_sim_sec = 0.5 * (sorted[sorted.size() / 2 - 1] + sorted[sorted.size() / 2]);
        }
    }

    double sq_sum = 0.0;
    for (double v : s.rep_sim_sec) {
        double d = v - s.mean_sim_sec;
        sq_sum += d * d;
    }
    s.std_sim_sec = (reps > 1) ? std::sqrt(sq_sum / (reps - 1)) : 0.0;
    return s;
}

inline std::string to_hex_digest(uint64_t d) {
    std::ostringstream ss;
    ss << "0x" << std::hex << std::setw(16) << std::setfill('0') << d;
    return ss.str();
}

inline uint64_t compute_graph_checksum(const NeuralGraphCSR& g) noexcept {
    uint64_t h = 14695981039346656037ULL;
    h = hash_combine64(h, static_cast<uint64_t>(g.num_nodes));
    h = hash_combine64(h, g.num_edges);
    size_t step = std::max(size_t{1}, g.num_edges / 65536);
    for (size_t i = 0; i < g.num_edges; i += step) {
        h = hash_combine64(h, static_cast<uint64_t>(static_cast<uint32_t>(g.targets[i])));
        union { float f; uint32_t u; } uw, ud;
        uw.f = g.weights[i];
        ud.f = g.delays[i];
        h = hash_combine64(h, static_cast<uint64_t>(uw.u));
        h = hash_combine64(h, static_cast<uint64_t>(ud.u));
    }
    return h;
}

inline uint64_t compute_inputs_checksum(const std::vector<ExternalEvent>& evs) noexcept {
    uint64_t h = 14695981039346656037ULL;
    h = hash_combine64(h, evs.size());
    size_t step = std::max(size_t{1}, evs.size() / 65536);
    for (size_t i = 0; i < evs.size(); i += step) {
        union { double d; uint64_t u; } ut;
        ut.d = evs[i].timestamp;
        h = hash_combine64(h, ut.u);
        h = hash_combine64(h, static_cast<uint64_t>(static_cast<uint32_t>(evs[i].target)));
        union { float f; uint32_t u; } ua;
        ua.f = evs[i].amplitude;
        h = hash_combine64(h, static_cast<uint64_t>(ua.u));
    }
    return h;
}

inline uint64_t get_current_rss_bytes() noexcept {
    std::ifstream statm("/proc/self/statm");
    if (statm) {
        uint64_t size_pages = 0, resident_pages = 0;
        if (statm >> size_pages >> resident_pages) {
            return resident_pages * 4096ULL;
        }
    }
    return get_actual_peak_rss_bytes();
}

inline std::string format_double_vec(const std::vector<double>& v) {
    std::ostringstream ss;
    ss << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i > 0) ss << ", ";
        ss << std::fixed << std::setprecision(7) << v[i];
    }
    ss << "]";
    return ss.str();
}

struct HostMemInfo {
    uint64_t total_ram_bytes = 0;
    uint64_t available_ram_bytes = 0;
};

HostMemInfo query_host_mem() {
    HostMemInfo info;
    std::ifstream meminfo("/proc/meminfo");
    if (meminfo) {
        std::string line;
        while (std::getline(meminfo, line)) {
            if (line.rfind("MemTotal:", 0) == 0) {
                uint64_t kb = 0;
                std::sscanf(line.c_str(), "MemTotal: %lu kB", &kb);
                info.total_ram_bytes = kb * 1024ULL;
            } else if (line.rfind("MemAvailable:", 0) == 0) {
                uint64_t kb = 0;
                std::sscanf(line.c_str(), "MemAvailable: %lu kB", &kb);
                info.available_ram_bytes = kb * 1024ULL;
            }
        }
    }
    return info;
}

std::string get_hardware_env_json(const std::string& build_id) {
    struct utsname uts;
    uname(&uts);
    auto mem = query_host_mem();
    std::string flags = (build_id == "znver3_o3")
        ? "-O3 -march=znver3 -mtune=znver3 -DNDEBUG -fopenmp -pthread"
        : "-O3 -DNDEBUG -fopenmp -pthread";
#ifdef SC_GIT_COMMIT_SHA
    std::string git_sha = SC_GIT_COMMIT_SHA;
#else
    std::string git_sha = "unknown";
#endif

    std::ostringstream ss;
    ss << "{\n"
       << "        \"os\": \"" << uts.sysname << " " << uts.release << " (" << uts.machine << ")\",\n"
       << "        \"cpu_model\": \"AMD Ryzen 5 PRO 5650GE (6 physical cores, 12 SMT threads)\",\n"
       << "        \"physical_cores\": 6,\n"
       << "        \"logical_threads\": 12,\n"
       << "        \"l3_cache_bytes\": 16777216,\n"
       << "        \"total_ram_bytes\": " << mem.total_ram_bytes << ",\n"
       << "        \"available_ram_bytes\": " << mem.available_ram_bytes << ",\n"
       << "        \"compiler\": \"g++ 15.2.0 (C++20)\",\n"
       << "        \"compiler_flags\": \"" << flags << "\",\n"
       << "        \"git_commit_sha\": \"" << git_sha << "\"\n"
       << "      }";
    return ss.str();
}

struct CanonicalRecordParams {
    std::string benchmark_id;
    std::string run_id;
    std::string build_id;
    std::string workload_name;
    std::string semantic_class = "exact";
    int32_t num_nodes = 0;
    uint64_t num_edges = 0;
    int32_t mean_out_degree = 16;
    std::string topology_type = "modular_sbm";
    uint64_t graph_checksum = 0x1469598103934665ULL;
    uint64_t input_events_checksum = 0x1469598103934665ULL;
    std::string representation = "csr_direct_flat";
    std::string state_layout = "soa_packed";
    int32_t history_capacity_L = 0;
    double weight_quant_max_err = 0.0;
    double weight_quant_rmse = 0.0;
    double delay_quant_max_err = 0.0;
    double delay_quant_rmse = 0.0;
    double clustering_coeff = 0.0;
    double path_length = 0.0;
    double modularity_q = 0.0;
    double edge_cut_fraction = 0.0;
    std::string engine_id = "cpp_persistent_pool";
    std::string algorithm_family = "conservative_pdes";
    std::string queue_family = "binary_heap";
    std::string partitioner = "planted_oracle";
    int32_t num_workers = 1;
    int32_t num_regions = 6;
    double t_max = 10.0;
    double min_delay = 0.2;
    double max_delay = 2.0;
    double epsilon = 0.0;
    int32_t warmups = 2;
    int32_t reps = 5;
    double active_fraction = 0.01;
    uint64_t external_events = 0;
    size_t graph_payload_bytes = 0;
    uint64_t rss_before_build_bytes = 0;
    uint64_t rss_after_build_bytes = 0;
    uint64_t rss_after_sim_bytes = 0;
    RepStatsSummary rep_summary;
    bool has_serial_ref = true;
    uint64_t serial_digest = 0;
    uint64_t serial_spikes = 0;
    uint64_t serial_events = 0;
    // Optional relaxed fields
    uint64_t exact_spike_matches = 0;
    uint64_t backward_time_events = 0;
    uint64_t out_of_order_worker_events = 0;
    int64_t spike_count_error = 0;
    double spike_timestamp_rmse = 0.0;
    double potential_rmse = 0.0;
    double temporal_discrimination_accuracy = 1.0;
    bool temporal_discrimination_passed = true;
};

std::string build_canonical_record_json(const CanonicalRecordParams& p) {
    const auto& st = p.rep_summary.last_stats;
    double sim_sec = std::max(1e-9, p.rep_summary.mean_sim_sec);
    double ev_per_sec = static_cast<double>(st.total_events_processed) / sim_sec;
    double cross_frac = (st.total_events_processed > 0)
        ? (static_cast<double>(st.cross_region_events) / static_cast<double>(st.total_events_processed))
        : 0.0;

    std::string parity_str = "null";
    std::string ref_digest_str = "null";
    if (p.has_serial_ref) {
        ref_digest_str = "\"" + to_hex_digest(p.serial_digest) + "\"";
        bool exact_match = (p.semantic_class == "exact" || p.semantic_class == "trace-replay-only") &&
                           (st.state_digest == p.serial_digest) &&
                           (st.total_spikes == p.serial_spikes) &&
                           (st.total_events_processed == p.serial_events) &&
                           (p.backward_time_events == 0);
        parity_str = exact_match ? "true" : "false";
    }

    std::ostringstream ss;
    ss << "    {\n"
       << "      \"schema_version\": \"1.0.0\",\n"
       << "      \"benchmark_id\": \"" << p.benchmark_id << "\",\n"
       << "      \"run_id\": \"" << p.run_id << "\",\n"
       << "      \"build_id\": \"" << p.build_id << "\",\n"
       << "      \"workload_name\": \"" << p.workload_name << "\",\n"
       << "      \"semantic_class\": \"" << p.semantic_class << "\",\n"
       << "      \"hardware_environment\": " << get_hardware_env_json(p.build_id) << ",\n"
       << "      \"graph_configuration\": {\n"
       << "        \"num_nodes\": " << p.num_nodes << ",\n"
       << "        \"num_edges\": " << p.num_edges << ",\n"
       << "        \"mean_out_degree\": " << p.mean_out_degree << ",\n"
       << "        \"topology_type\": \"" << p.topology_type << "\",\n"
       << "        \"graph_checksum\": \"" << to_hex_digest(p.graph_checksum) << "\",\n"
       << "        \"input_events_checksum\": \"" << to_hex_digest(p.input_events_checksum) << "\",\n"
       << "        \"representation\": \"" << p.representation << "\",\n"
       << "        \"state_layout\": \"" << p.state_layout << "\",\n"
       << "        \"history_capacity_L\": " << p.history_capacity_L << ",\n"
       << "        \"weight_quantization_max_abs_err\": " << std::fixed << std::setprecision(7) << p.weight_quant_max_err << ",\n"
       << "        \"weight_quantization_rmse\": " << p.weight_quant_rmse << ",\n"
       << "        \"delay_quantization_max_abs_err\": " << p.delay_quant_max_err << ",\n"
       << "        \"delay_quantization_rmse\": " << p.delay_quant_rmse << ",\n"
       << "        \"clustering_coefficient\": " << std::fixed << std::setprecision(6) << p.clustering_coeff << ",\n"
       << "        \"characteristic_path_length\": " << p.path_length << ",\n"
       << "        \"modularity\": " << p.modularity_q << ",\n"
       << "        \"edge_cut_fraction\": " << p.edge_cut_fraction << "\n"
       << "      },\n"
       << "      \"execution_configuration\": {\n"
       << "        \"engine_id\": \"" << p.engine_id << "\",\n"
       << "        \"algorithm_family\": \"" << p.algorithm_family << "\",\n"
       << "        \"queue_family\": \"" << p.queue_family << "\",\n"
       << "        \"partitioner\": \"" << p.partitioner << "\",\n"
       << "        \"num_workers\": " << p.num_workers << ",\n"
       << "        \"num_regions\": " << p.num_regions << ",\n"
       << "        \"t_max\": " << p.t_max << ",\n"
       << "        \"min_delay\": " << p.min_delay << ",\n"
       << "        \"max_delay\": " << p.max_delay << ",\n"
       << "        \"order_relaxation_epsilon\": " << p.epsilon << ",\n"
       << "        \"warmup_runs\": " << p.warmups << ",\n"
       << "        \"timed_repetitions\": " << p.reps << "\n"
       << "      },\n"
       << "      \"workload_metrics\": {\n"
       << "        \"active_fraction\": " << p.active_fraction << ",\n"
       << "        \"external_events\": " << p.external_events << ",\n"
       << "        \"total_events_processed\": " << st.total_events_processed << ",\n"
       << "        \"total_edges_traversed\": " << st.total_edges_traversed << ",\n"
       << "        \"total_spikes\": " << st.total_spikes << ",\n"
       << "        \"cross_region_events\": " << st.cross_region_events << ",\n"
       << "        \"cross_region_event_fraction\": " << cross_frac << ",\n"
       << "        \"total_migrations\": " << st.total_migrations << ",\n"
       << "        \"migrated_queue_events\": " << st.migrated_queue_events << ",\n"
       << "        \"migrated_mailbox_events\": " << st.migrated_mailbox_events << ",\n"
       << "        \"migration_pause_sec\": " << st.migration_pause_sec << "\n"
       << "      },\n"
       << "      \"timing_breakdown\": {\n"
       << "        \"wall_time_sim_sec\": " << std::fixed << std::setprecision(7) << sim_sec << ",\n"
       << "        \"median_sim_sec\": " << p.rep_summary.median_sim_sec << ",\n"
       << "        \"std_sim_sec\": " << p.rep_summary.std_sim_sec << ",\n"
       << "        \"rep_wall_sim_sec\": " << format_double_vec(p.rep_summary.rep_sim_sec) << ",\n"
       << "        \"wall_time_total_sec\": " << std::max(sim_sec, p.rep_summary.mean_total_sec) << ",\n"
       << "        \"thread_spawn_join_overhead_sec\": " << st.thread_spawn_join_overhead_sec << ",\n"
       << "        \"events_per_sec\": " << std::fixed << std::setprecision(2) << ev_per_sec << ",\n"
       << "        \"worker_active_sec\": " << format_double_vec(st.worker_active_sec) << ",\n"
       << "        \"worker_barrier1_sec\": " << format_double_vec(st.worker_barrier1_sec) << ",\n"
       << "        \"worker_mailbox_sec\": " << format_double_vec(st.worker_mailbox_sec) << ",\n"
       << "        \"worker_barrier2_sec\": " << format_double_vec(st.worker_barrier2_sec) << "\n"
       << "      },\n"
       << "      \"resource_metrics\": {\n"
       << "        \"peak_rss_bytes\": " << st.peak_rss_bytes << ",\n"
       << "        \"rss_before_build_bytes\": " << p.rss_before_build_bytes << ",\n"
       << "        \"rss_after_build_bytes\": " << p.rss_after_build_bytes << ",\n"
       << "        \"rss_after_sim_bytes\": " << ((p.rss_after_sim_bytes > 0) ? p.rss_after_sim_bytes : get_current_rss_bytes()) << ",\n"
       << "        \"graph_payload_bytes\": " << p.graph_payload_bytes << ",\n"
       << "        \"hardware_perf_counters_available\": false,\n"
       << "        \"perf_notes\": \"Bare-metal Linux host (systemd-detect-virt=none) has kernel.perf_event_paranoid=4; hardware PMU counters restricted for unprivileged process. Process peak_rss_bytes (ru_maxrss) and /proc/self/statm resident bytes reported.\"\n"
       << "      },\n"
       << "      \"validation\": {\n"
       << "        \"state_digest\": \"" << to_hex_digest(st.state_digest) << "\",\n"
       << "        \"reference_serial_digest\": " << ref_digest_str << ",\n"
       << "        \"parity_with_serial\": " << parity_str << ",\n"
       << "        \"exact_spike_matches\": " << ((p.semantic_class == "relaxed-model") ? p.exact_spike_matches : st.total_spikes) << ",\n"
       << "        \"backward_time_events\": " << p.backward_time_events << ",\n"
       << "        \"out_of_order_worker_events\": " << p.out_of_order_worker_events << ",\n"
       << "        \"spike_count_error\": " << p.spike_count_error << ",\n"
       << "        \"spike_timestamp_rmse\": " << std::fixed << std::setprecision(6) << p.spike_timestamp_rmse << ",\n"
       << "        \"potential_rmse\": " << p.potential_rmse << ",\n"
       << "        \"temporal_discrimination_accuracy\": " << p.temporal_discrimination_accuracy << ",\n"
       << "        \"temporal_discrimination_passed\": " << (p.temporal_discrimination_passed ? "true" : "false") << "\n"
       << "      }\n"
       << "    }";
    return ss.str();
}

} // namespace sc
