#include "../core/types.hpp"
#include "../core/graph_topologies.hpp"
#include "../core/graph_metrics.hpp"
#include "../core/partitioners.hpp"
#include "../engines/cpp_serial.hpp"
#include "../engines/cpp_owner_instrumented.hpp"
#include "../engines/cpp_persistent_pool.hpp"
#include "../engines/cpp_adaptive.hpp"
#include "../engines/cpp_relaxed.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <string>
#include <chrono>
#include <sys/utsname.h>

namespace sc {

struct BenchmarkConfig {
    std::string profile = "standard";
    std::string out_path = "";
    std::vector<uint64_t> seeds = {11, 23, 37, 41, 53};
    int32_t repetitions = 5;
    int32_t warmups = 2;
    std::vector<int32_t> worker_counts = {1, 2, 4, 6};
    std::vector<int32_t> smt_counts = {1, 2, 4, 6, 8, 12};
    std::vector<int32_t> region_counts = {6, 24, 96};
};

std::string get_host_json() {
    struct utsname uts;
    uname(&uts);
    std::ostringstream ss;
    ss << "{\n"
       << "    \"sysname\": \"" << uts.sysname << "\",\n"
       << "    \"nodename\": \"" << uts.nodename << "\",\n"
       << "    \"release\": \"" << uts.release << "\",\n"
       << "    \"machine\": \"" << uts.machine << "\",\n"
       << "    \"cpu\": \"AMD Ryzen 5 PRO 5650GE (6 physical cores, 12 SMT threads)\",\n"
       << "    \"compiler\": \"g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0, C++20\"\n"
       << "  }";
    return ss.str();
}

} // namespace sc

int main(int argc, char** argv) {
    sc::BenchmarkConfig bcfg;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--profile" && i + 1 < argc) {
            bcfg.profile = argv[++i];
        } else if (arg == "--out" && i + 1 < argc) {
            bcfg.out_path = argv[++i];
        }
    }

    if (bcfg.profile == "smoke") {
        bcfg.seeds = {11, 23};
        bcfg.repetitions = 2;
        bcfg.warmups = 1;
        bcfg.worker_counts = {1, 2, 4, 6};
        bcfg.smt_counts = {1, 2, 4, 6};
    } else if (bcfg.profile == "extended") {
        bcfg.seeds = {11, 23, 37, 41, 53};
        bcfg.repetitions = 5;
        bcfg.warmups = 2;
        bcfg.worker_counts = {1, 2, 4, 6};
        bcfg.smt_counts = {1, 2, 4, 6, 8, 12};
        bcfg.region_counts = {6, 24, 96, 384};
    } else {
        // standard
        bcfg.seeds = {11, 23, 37, 41, 53};
        bcfg.repetitions = 5;
        bcfg.warmups = 2;
        bcfg.worker_counts = {1, 2, 4, 6};
        bcfg.smt_counts = {1, 2, 4, 6, 8, 12};
    }

    std::cout << "========================================================\n"
              << " SynapticContinuum EXP-0004 Benchmark Execution\n"
              << " Profile: " << bcfg.profile << "\n"
              << " Seeds: " << bcfg.seeds.size() << " | Repetitions: " << bcfg.repetitions << "\n"
              << "========================================================\n" << std::endl;

    std::ostringstream json_out;
    json_out << "{\n"
             << "  \"experiment\": \"EXP-0004\",\n"
             << "  \"profile\": \"" << bcfg.profile << "\",\n"
             << "  \"host\": " << sc::get_host_json() << ",\n";

    // -------------------------------------------------------------
    // STAGE 0 & PHASE A: Six Disconnected Regions Control vs Random Graph
    // -------------------------------------------------------------
    std::cout << "[Stage 0 & Phase A] Six Disconnected Regions Control vs Random Graph..." << std::endl;
    json_out << "  \"stage0_disconnected_control\": [\n";

    int32_t N_phaseA = (bcfg.profile == "smoke") ? 1024 : 10000;
    int32_t D_phaseA = 16;
    double t_max_phaseA = (bcfg.profile == "smoke") ? 5.0 : 10.0;

    bool first_disc = true;
    for (uint64_t seed : bcfg.seeds) {
        auto g_disc = sc::Exp4GraphGenerators::create_disconnected_modules(N_phaseA, D_phaseA, 6, seed);
        auto g_rand = sc::Exp4GraphGenerators::create_uniform_random(N_phaseA, D_phaseA, seed);

        sc::SubstrateConfig cfg;
        cfg.num_nodes = N_phaseA;
        cfg.mean_out_degree = D_phaseA;

        // Balanced stimulus across all 6 regions
        std::vector<sc::ExternalEvent> inputs;
        int32_t input_events_count = (bcfg.profile == "smoke") ? 50 : 200;
        for (int32_t m = 0; m < 6; ++m) {
            int32_t start_n = m * (N_phaseA / 6);
            for (int32_t s = 0; s < input_events_count; ++s) {
                inputs.push_back({0.05 * s, start_n + (s % 30), 1.5f});
            }
        }

        // Benchmark Disconnected Modules across W
        double t_disc_w1 = 0.0;
        for (int32_t W : bcfg.worker_counts) {
            sc::Exp4PersistentPoolEngine pool(cfg, g_disc.graph, W, 6, g_disc.planted_labels);
            for (int w = 0; w < bcfg.warmups; ++w) pool.run(inputs, t_max_phaseA);

            double total_sim_time = 0.0;
            sc::Exp4ProfilingStats last_stats;
            for (int r = 0; r < bcfg.repetitions; ++r) {
                last_stats = pool.run(inputs, t_max_phaseA);
                total_sim_time += last_stats.wall_time_sim_sec;
            }
            double mean_sim_time = total_sim_time / bcfg.repetitions;
            if (W == 1) t_disc_w1 = mean_sim_time;
            double speedup = (t_disc_w1 > 0) ? (t_disc_w1 / mean_sim_time) : 1.0;

            if (!first_disc) json_out << ",\n";
            first_disc = false;

            json_out << "    {\n"
                     << "      \"type\": \"disconnected_6_modules\",\n"
                     << "      \"N\": " << N_phaseA << ",\n"
                     << "      \"W\": " << W << ",\n"
                     << "      \"seed\": " << seed << ",\n"
                     << "      \"mean_sim_sec\": " << mean_sim_time << ",\n"
                     << "      \"self_speedup\": " << speedup << ",\n"
                     << "      \"events\": " << last_stats.total_events_processed << ",\n"
                     << "      \"spikes\": " << last_stats.total_spikes << ",\n"
                     << "      \"cross_events\": " << last_stats.cross_region_events << ",\n"
                     << "      \"peak_rss_mb\": " << (last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                     << "    }";

            std::cout << "  [Disconnected 6-Mod | Seed " << seed << "] W=" << W << " | Sim: "
                      << std::fixed << std::setprecision(3) << (mean_sim_time * 1000.0)
                      << " ms | Speedup: " << speedup << "x | Spikes: " << last_stats.total_spikes << std::endl;
        }

        // Benchmark Random Graph across W
        double t_rand_w1 = 0.0;
        for (int32_t W : bcfg.worker_counts) {
            auto part_contig = sc::Exp4Partitioners::partition_contiguous(N_phaseA, W);
            sc::Exp4PersistentPoolEngine pool(cfg, g_rand, W, W, part_contig);
            for (int w = 0; w < bcfg.warmups; ++w) pool.run(inputs, t_max_phaseA);

            double total_sim_time = 0.0;
            sc::Exp4ProfilingStats last_stats;
            for (int r = 0; r < bcfg.repetitions; ++r) {
                last_stats = pool.run(inputs, t_max_phaseA);
                total_sim_time += last_stats.wall_time_sim_sec;
            }
            double mean_sim_time = total_sim_time / bcfg.repetitions;
            if (W == 1) t_rand_w1 = mean_sim_time;
            double speedup = (t_rand_w1 > 0) ? (t_rand_w1 / mean_sim_time) : 1.0;

            json_out << ",\n    {\n"
                     << "      \"type\": \"random_graph\",\n"
                     << "      \"N\": " << N_phaseA << ",\n"
                     << "      \"W\": " << W << ",\n"
                     << "      \"seed\": " << seed << ",\n"
                     << "      \"mean_sim_sec\": " << mean_sim_time << ",\n"
                     << "      \"self_speedup\": " << speedup << ",\n"
                     << "      \"events\": " << last_stats.total_events_processed << ",\n"
                     << "      \"spikes\": " << last_stats.total_spikes << ",\n"
                     << "      \"cross_events\": " << last_stats.cross_region_events << ",\n"
                     << "      \"peak_rss_mb\": " << (last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                     << "    }";

            std::cout << "  [Random Graph       | Seed " << seed << "] W=" << W << " | Sim: "
                      << std::fixed << std::setprecision(3) << (mean_sim_time * 1000.0)
                      << " ms | Speedup: " << speedup << "x | CrossEvents: " << last_stats.cross_region_events << std::endl;
        }
    }
    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 1: Controlled Topology Generators, Metrics & Trace Replay
    // -------------------------------------------------------------
    std::cout << "\n[Stage 1] Controlled Topology Sweep & Graph Metrics..." << std::endl;
    json_out << "  \"stage1_topology_sweep\": [\n";

    int32_t N_topo = (bcfg.profile == "smoke") ? 1024 : 10000;
    int32_t D_topo = 16;
    uint64_t seed_topo = bcfg.seeds[0];
    sc::SubstrateConfig cfg_topo;
    cfg_topo.num_nodes = N_topo;
    cfg_topo.mean_out_degree = D_topo;

    bool first_topo = true;

    auto record_topo_bench = [&](
        const std::string& name,
        const sc::NeuralGraphCSR& g,
        const std::vector<int32_t>& part,
        const std::string& extra_param
    ) {
        auto m = sc::Exp4GraphMetricsCalculator::compute_all_metrics(g, part, 300, 100, seed_topo);

        // Run simulation with W=1 and W=6
        std::vector<sc::ExternalEvent> inputs;
        for (int32_t s = 0; s < 100; ++s) {
            inputs.push_back({0.05 * s, (s * 37) % N_topo, 1.5f});
        }

        sc::Exp4PersistentPoolEngine pool_w1(cfg_topo, g, 1, 6, part);
        auto stats_w1 = pool_w1.run(inputs, 5.0);

        sc::Exp4PersistentPoolEngine pool_w6(cfg_topo, g, 6, 6, part);
        auto stats_w6 = pool_w6.run(inputs, 5.0);

        double speedup = (stats_w6.wall_time_sim_sec > 0)
            ? (stats_w1.wall_time_sim_sec / stats_w6.wall_time_sim_sec) : 1.0;

        if (!first_topo) json_out << ",\n";
        first_topo = false;

        json_out << "    {\n"
                 << "      \"name\": \"" << name << "\",\n"
                 << "      \"parameter\": \"" << extra_param << "\",\n"
                 << "      \"N\": " << N_topo << ",\n"
                 << "      \"D\": " << D_topo << ",\n"
                 << "      \"clustering_coeff\": " << m.clustering_coefficient << ",\n"
                 << "      \"path_length\": " << m.characteristic_path_length << ",\n"
                 << "      \"modularity_q\": " << m.modularity_q << ",\n"
                 << "      \"edge_cut\": " << m.edge_cut_fraction << ",\n"
                 << "      \"total_spikes\": " << stats_w6.total_spikes << ",\n"
                 << "      \"cross_events_w6\": " << stats_w6.cross_region_events << ",\n"
                 << "      \"speedup_w6\": " << speedup << "\n"
                 << "    }";

        std::cout << "  [Topo: " << std::setw(25) << std::left << name
                  << " | " << std::setw(12) << extra_param << "] C=" << std::fixed << std::setprecision(4)
                  << m.clustering_coefficient << " | L=" << m.characteristic_path_length
                  << " | Q=" << m.modularity_q << " | Cut=" << m.edge_cut_fraction
                  << " | Spikes=" << stats_w6.total_spikes << " | W6_Speedup=" << speedup << "x" << std::endl;
    };

    // 1. Watts-Strogatz rewiring sweep
    for (float p : {0.0f, 0.01f, 0.10f, 0.50f, 1.00f}) {
        auto g_ws = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N_topo, D_topo, p, seed_topo);
        auto part = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
        record_topo_bench("watts_strogatz", g_ws, part, "p=" + std::to_string(p));
    }

    // 2. Modular SBM cross-module sweep
    for (float c : {0.0f, 0.01f, 0.10f, 0.50f, 1.00f}) {
        auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, c, seed_topo);
        record_topo_bench("modular_sbm", g_mod.graph, g_mod.planted_labels, "c=" + std::to_string(c));
    }

    // 3. Hierarchical modular
    auto g_hier = sc::Exp4GraphGenerators::create_hierarchical_modular(N_topo, D_topo, 2, 3, seed_topo);
    record_topo_bench("hierarchical_modular", g_hier.graph, g_hier.planted_labels, "2x3=6");

    // 4. Degree-preserving rewired control
    auto g_mod_base = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, 0.10f, seed_topo);
    auto g_deg_rewired = sc::Exp4GraphGenerators::create_degree_preserving_rewired(g_mod_base.graph, N_topo * D_topo * 5, seed_topo);
    record_topo_bench("degree_preserving_rewired", g_deg_rewired, g_mod_base.planted_labels, "swaps=5E");

    // 5. Node-ID permuted control
    auto g_permuted = sc::Exp4GraphGenerators::create_node_id_permuted(g_mod_base.graph, seed_topo);
    auto part_contig_perm = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
    record_topo_bench("node_id_permuted", g_permuted, part_contig_perm, "shuffled_ids");

    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 1B: Trace Replay Microbenchmark (Isolating Dispatch from Dynamics)
    // -------------------------------------------------------------
    std::cout << "\n[Stage 1B] Trace Replay Microbenchmark (Matched-Work Dispatch)..." << std::endl;
    json_out << "  \"stage1b_trace_replay\": [\n";

    // Generate reference trace of 2,000 spikes using serial engine
    std::vector<sc::ExternalEvent> trace_stimuli;
    for (int32_t s = 0; s < 150; ++s) {
        trace_stimuli.push_back({0.02 * s, (s * 41) % N_topo, 1.8f});
    }
    sc::Exp4SerialEngine trace_ref_serial(cfg_topo, g_mod_base.graph);
    std::vector<sc::TraceEvent> recorded_trace;
    trace_ref_serial.run(trace_stimuli, 5.0, true, &recorded_trace);

    // Convert recorded trace to external injection sequence
    std::vector<sc::ExternalEvent> replay_inputs;
    replay_inputs.reserve(recorded_trace.size());
    for (const auto& te : recorded_trace) {
        replay_inputs.push_back({te.timestamp, te.target, te.amplitude, te.source, te.kind});
    }

    std::cout << "  Recorded trace events: " << replay_inputs.size() << std::endl;

    bool first_tr = true;
    for (int32_t W : bcfg.worker_counts) {
        sc::Exp4PersistentPoolEngine pool_tr(cfg_topo, g_mod_base.graph, W, 6, g_mod_base.planted_labels);
        auto stats_tr = pool_tr.run(replay_inputs, 5.0);

        if (!first_tr) json_out << ",\n";
        first_tr = false;

        json_out << "    {\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"trace_events\": " << replay_inputs.size() << ",\n"
                 << "      \"wall_sim_sec\": " << stats_tr.wall_time_sim_sec << ",\n"
                 << "      \"events_per_sec\": " << (stats_tr.total_events_processed / stats_tr.wall_time_sim_sec) << "\n"
                 << "    }";

        std::cout << "  [Trace Replay] W=" << W << " | Sim: "
                  << std::fixed << std::setprecision(3) << (stats_tr.wall_time_sim_sec * 1000.0)
                  << " ms | Throughput: "
                  << std::fixed << std::setprecision(1) << (stats_tr.total_events_processed / stats_tr.wall_time_sim_sec)
                  << " events/sec" << std::endl;
    }
    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 2: Partitioning Strategies Comparison
    // -------------------------------------------------------------
    std::cout << "\n[Stage 2] Partitioning Strategies Comparison..." << std::endl;
    json_out << "  \"stage2_partition_strategies\": [\n";

    auto g_eval = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, 0.10f, seed_topo);

    // Warmup activity generation for activity-aware partitioning
    std::vector<sc::ExternalEvent> warmup_inputs;
    for (int32_t s = 0; s < 100; ++s) {
        warmup_inputs.push_back({0.05 * s, (s * 17) % N_topo, 1.5f});
    }
    sc::Exp4SerialEngine serial_warmup(cfg_topo, g_eval.graph);
    std::vector<sc::TraceEvent> warmup_trace;
    serial_warmup.run(warmup_inputs, 3.0, true, &warmup_trace);

    // Extract pairwise warmup traffic
    std::vector<sc::Exp4Partitioners::PairwiseEventRecord> warmup_comm;
    for (const auto& te : warmup_trace) {
        if (te.source >= 0) {
            warmup_comm.push_back({te.source, te.target, 1});
        }
    }

    // Partition candidates
    auto part_contig = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
    auto part_hash = sc::Exp4Partitioners::partition_random_hash(N_topo, 6, seed_topo);
    auto part_oracle = sc::Exp4Partitioners::partition_planted_oracle(N_topo, 6, g_eval.planted_labels);
    auto part_mincut = sc::Exp4Partitioners::partition_greedy_mincut(g_eval.graph, 6, 10);
    auto part_activity = sc::Exp4Partitioners::partition_activity_aware(N_topo, 6, warmup_comm, 10);

    std::vector<std::pair<std::string, std::vector<int32_t>>> partition_list = {
        {"contiguous", part_contig},
        {"random_hash", part_hash},
        {"planted_oracle", part_oracle},
        {"greedy_mincut", part_mincut},
        {"activity_aware", part_activity}
    };

    // Held-out test activity
    std::vector<sc::ExternalEvent> heldout_inputs;
    for (int32_t s = 0; s < 150; ++s) {
        heldout_inputs.push_back({0.05 * s, (s * 31) % N_topo, 1.5f});
    }

    bool first_part = true;
    for (const auto& pentry : partition_list) {
        const auto& pname = pentry.first;
        const auto& pmap = pentry.second;

        double edge_cut = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_eval.graph, pmap);
        double modularity = sc::Exp4GraphMetricsCalculator::compute_modularity(g_eval.graph, pmap);

        // Run on W=6
        sc::Exp4PersistentPoolEngine pool(cfg_topo, g_eval.graph, 6, 6, pmap);
        auto stats = pool.run(heldout_inputs, 6.0);

        double active_event_cut = (stats.total_events_processed > 0)
            ? (static_cast<double>(stats.cross_region_events) / stats.total_events_processed) : 0.0;

        if (!first_part) json_out << ",\n";
        first_part = false;

        json_out << "    {\n"
                 << "      \"partitioner\": \"" << pname << "\",\n"
                 << "      \"edge_cut\": " << edge_cut << "\n,"
                 << "      \"modularity_q\": " << modularity << ",\n"
                 << "      \"cross_events\": " << stats.cross_region_events << ",\n"
                 << "      \"active_event_cut\": " << active_event_cut << ",\n"
                 << "      \"wall_sim_sec\": " << stats.wall_time_sim_sec << ",\n"
                 << "      \"backlog_imbalance\": " << stats.backlog_imbalance_ratio << "\n"
                 << "    }";

        std::cout << "  [Partition: " << std::setw(16) << std::left << pname
                  << "] EdgeCut=" << std::fixed << std::setprecision(4) << edge_cut
                  << " | EventCut=" << active_event_cut
                  << " | CrossEvents=" << stats.cross_region_events
                  << " | Sim: " << (stats.wall_time_sim_sec * 1000.0) << " ms"
                  << " | Imbalance: " << stats.backlog_imbalance_ratio << std::endl;
    }
    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 3: Advanced Schedulers & Full Scaling Comparison
    // -------------------------------------------------------------
    std::cout << "\n[Stage 3] Advanced Schedulers & Scaling Comparison across W (Physical + SMT)..." << std::endl;
    json_out << "  \"stage3_schedulers\": [\n";

    bool first_sched = true;
    for (int32_t W : bcfg.smt_counts) {
        // 1. Static Owner (with barriers, thread per run)
        sc::Exp4OwnerInstrumentedEngine owner(cfg_topo, g_eval.graph, W, part_oracle);
        auto stats_owner = owner.run(heldout_inputs, 6.0);

        // 2. Persistent Pool (thread pool reused, R=24 logical regions)
        auto node_to_reg24 = sc::Exp4Partitioners::partition_contiguous(N_topo, 24);
        sc::Exp4PersistentPoolEngine pool24(cfg_topo, g_eval.graph, W, 24, node_to_reg24);
        auto stats_pool24 = pool24.run(heldout_inputs, 6.0);

        // 3. Dynamic Adaptive Scheduler (with region migration)
        sc::Exp4AdaptiveEngine adaptive(cfg_topo, g_eval.graph, W, 24, node_to_reg24, 1.30, 2);
        auto stats_adapt = adaptive.run_adaptive(heldout_inputs, 6.0);

        if (!first_sched) json_out << ",\n";
        first_sched = false;

        json_out << "    {\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"owner_barrier_sec\": " << stats_owner.wall_time_sim_sec << ",\n"
                 << "      \"owner_spawn_overhead_sec\": " << stats_owner.thread_spawn_join_overhead_sec << ",\n"
                 << "      \"persistent_pool_sec\": " << stats_pool24.wall_time_sim_sec << ",\n"
                 << "      \"adaptive_scheduler_sec\": " << stats_adapt.wall_time_sim_sec << ",\n"
                 << "      \"migrations_count\": " << stats_adapt.total_migrations << ",\n"
                 << "      \"migration_pause_sec\": " << stats_adapt.migration_pause_sec << "\n"
                 << "    }";

        std::cout << "  [W=" << std::setw(2) << W << "] OwnerBarrier: " << std::fixed << std::setprecision(3)
                  << (stats_owner.wall_time_sim_sec * 1000.0) << " ms (spawn: "
                  << (stats_owner.thread_spawn_join_overhead_sec * 1000.0) << " ms)"
                  << " | PersistentPool: " << (stats_pool24.wall_time_sim_sec * 1000.0) << " ms"
                  << " | Adaptive: " << (stats_adapt.wall_time_sim_sec * 1000.0) << " ms (mig: "
                  << stats_adapt.total_migrations << ")" << std::endl;
    }
    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 3B: High-Scale Benchmark (N = 100,000 Neurons)
    // -------------------------------------------------------------
    std::cout << "\n[Stage 3B] High-Scale Scaling Benchmark (N = 100,000 Neurons)..." << std::endl;
    json_out << "  \"stage3b_high_scale_100k\": [\n";

    int32_t N_100k = (bcfg.profile == "smoke") ? 20000 : 100000;
    sc::SubstrateConfig cfg_100k;
    cfg_100k.num_nodes = N_100k;
    cfg_100k.mean_out_degree = 16;

    auto g_100k_disc = sc::Exp4GraphGenerators::create_disconnected_modules(N_100k, 16, 6, seed_topo);
    std::vector<sc::ExternalEvent> inputs_100k;
    for (int32_t m = 0; m < 6; ++m) {
        int32_t start_n = m * (N_100k / 6);
        for (int32_t s = 0; s < 500; ++s) {
            inputs_100k.push_back({0.02 * s, start_n + (s % 100), 1.5f});
        }
    }

    double t_100k_w1 = 0.0;
    bool first_100k = true;
    for (int32_t W : bcfg.worker_counts) {
        sc::Exp4PersistentPoolEngine pool_100k(cfg_100k, g_100k_disc.graph, W, 6, g_100k_disc.planted_labels);
        auto stats_100k = pool_100k.run(inputs_100k, 10.0);
        if (W == 1) t_100k_w1 = stats_100k.wall_time_sim_sec;
        double speedup = (t_100k_w1 > 0) ? (t_100k_w1 / stats_100k.wall_time_sim_sec) : 1.0;

        if (!first_100k) json_out << ",\n";
        first_100k = false;

        json_out << "    {\n"
                 << "      \"N\": " << N_100k << ",\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"wall_sim_sec\": " << stats_100k.wall_time_sim_sec << ",\n"
                 << "      \"self_speedup\": " << speedup << ",\n"
                 << "      \"events\": " << stats_100k.total_events_processed << ",\n"
                 << "      \"spikes\": " << stats_100k.total_spikes << ",\n"
                 << "      \"peak_rss_mb\": " << (stats_100k.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                 << "    }";

        std::cout << "  [100k Scale] W=" << W << " | Sim: "
                  << std::fixed << std::setprecision(3) << (stats_100k.wall_time_sim_sec * 1000.0)
                  << " ms | Speedup: " << speedup << "x | RSS: "
                  << (stats_100k.peak_rss_bytes / (1024.0 * 1024.0)) << " MB" << std::endl;
    }
    json_out << "\n  ],\n";

    // -------------------------------------------------------------
    // STAGE 4: Order Relaxation as Alternative Dynamic Model
    // -------------------------------------------------------------
    std::cout << "\n[Stage 4] Order Relaxation as Alternative Neural Model..." << std::endl;
    json_out << "  \"stage4_relaxed_ordering\": [\n";

    // Reference exact serial run
    sc::Exp4SerialEngine exact_serial(cfg_topo, g_eval.graph);
    auto exact_ref = exact_serial.run(heldout_inputs, 6.0);

    bool first_rel = true;
    for (double eps : {0.0, 0.001, 0.010, 0.100}) {
        sc::Exp4RelaxedEngine relaxed(cfg_topo, g_eval.graph, 6, 24, eps);
        auto div = relaxed.evaluate_divergence_vs_reference(heldout_inputs, 6.0, exact_ref);

        if (!first_rel) json_out << ",\n";
        first_rel = false;

        json_out << "    {\n"
                 << "      \"epsilon\": " << eps << ",\n"
                 << "      \"wall_sim_sec\": " << div.wall_time_sec << ",\n"
                 << "      \"spike_count_error\": " << div.spike_count_error << ",\n"
                 << "      \"spike_timestamp_rmse\": " << div.spike_timestamp_rmse << ",\n"
                 << "      \"potential_rmse\": " << div.potential_rmse << ",\n"
                 << "      \"temporal_discrimination_passed\": " << (div.temporal_discrimination_passed ? "true" : "false") << "\n"
                 << "    }";

        std::cout << "  [Epsilon: " << std::fixed << std::setprecision(3) << eps << "] Sim: "
                  << (div.wall_time_sec * 1000.0) << " ms | SpikeErr: " << div.spike_count_error
                  << " | TimestampRMSE: " << div.spike_timestamp_rmse
                  << " | PotentialRMSE: " << div.potential_rmse << std::endl;
    }
    json_out << "\n  ]\n";

    json_out << "}\n";

    // Write output JSON
    std::string final_json = json_out.str();
    if (!bcfg.out_path.empty()) {
        std::ofstream f(bcfg.out_path);
        if (f) {
            f << final_json;
            std::cout << "\nMetrics written to: " << bcfg.out_path << std::endl;
        } else {
            std::cerr << "Failed to open output file: " << bcfg.out_path << std::endl;
        }
    }

    std::cout << "\nEXP-0004 benchmark execution completed successfully." << std::endl;
    return 0;
}
