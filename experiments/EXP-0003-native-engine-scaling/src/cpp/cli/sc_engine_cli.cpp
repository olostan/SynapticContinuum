#include "../core/types.hpp"
#include "../core/prng.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../engines/cpp_literal.hpp"
#include "../engines/cpp_packed.hpp"
#include "../engines/cpp_queues.hpp"
#include "../engines/cpp_sync.hpp"
#include "../engines/cpp_locked.hpp"
#include "../engines/cpp_owner.hpp"
#include "../engines/cpp_hybrid.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <iomanip>

namespace {

void print_json_result(const sc::SimulationResult& res, std::ostream& out) {
    out << "{\n"
        << "  \"scheduler_name\": \"" << res.scheduler_name << "\",\n"
        << "  \"wall_time_sec\": " << std::setprecision(8) << res.wall_time_sec << ",\n"
        << "  \"total_events_processed\": " << res.total_events_processed << ",\n"
        << "  \"total_edges_traversed\": " << res.total_edges_traversed << ",\n"
        << "  \"total_spikes\": " << res.total_spikes << ",\n"
        << "  \"peak_queue_size\": " << res.peak_queue_size << ",\n"
        << "  \"final_time\": " << res.final_time << ",\n"
        << "  \"state_digest\": " << res.state_digest << ",\n"
        << "  \"injected_active_fraction\": " << res.injected_active_fraction << ",\n"
        << "  \"propagated_active_fraction\": " << res.propagated_active_fraction << ",\n"
        << "  \"max_queue_exceeded\": " << (res.max_queue_exceeded ? "true" : "false") << ",\n"
        << "  \"lock_waits\": " << res.lock_waits << ",\n"
        << "  \"causal_stalls\": " << res.causal_stalls << ",\n"
        << "  \"cross_region_events\": " << res.cross_region_events << ",\n"
        << "  \"rss_bytes\": " << res.rss_bytes << "\n"
        << "}\n";
}

} // namespace

int main(int argc, char* argv[]) {
    std::string engine = "packed";
    int32_t num_nodes = 1024;
    int32_t degree = 16;
    uint64_t seed = 42;
    double active_fraction = 0.10;
    double rate = 1.0;
    double t_max = 10.0;
    double dt = 0.1;
    int32_t workers = 4;
    std::string topology = "random";
    std::string timing = "poisson";
    int32_t history_L = 0;
    int32_t trace_B = 0;
    std::string graph_file = "";
    std::string events_file = "";
    std::string out_json = "";
    int32_t reps = 1;
    int32_t warmups = 0;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--engine" && i + 1 < argc) engine = argv[++i];
        else if (arg == "--nodes" && i + 1 < argc) num_nodes = std::stoi(argv[++i]);
        else if (arg == "--degree" && i + 1 < argc) degree = std::stoi(argv[++i]);
        else if (arg == "--seed" && i + 1 < argc) seed = std::stoull(argv[++i]);
        else if (arg == "--active-fraction" && i + 1 < argc) active_fraction = std::stod(argv[++i]);
        else if (arg == "--rate" && i + 1 < argc) rate = std::stod(argv[++i]);
        else if (arg == "--t-max" && i + 1 < argc) t_max = std::stod(argv[++i]);
        else if (arg == "--dt" && i + 1 < argc) dt = std::stod(argv[++i]);
        else if (arg == "--workers" && i + 1 < argc) workers = std::stoi(argv[++i]);
        else if (arg == "--topology" && i + 1 < argc) topology = argv[++i];
        else if (arg == "--timing" && i + 1 < argc) timing = argv[++i];
        else if (arg == "--history" && i + 1 < argc) history_L = std::stoi(argv[++i]);
        else if (arg == "--trace-bank" && i + 1 < argc) trace_B = std::stoi(argv[++i]);
        else if (arg == "--graph-file" && i + 1 < argc) graph_file = argv[++i];
        else if (arg == "--events-file" && i + 1 < argc) events_file = argv[++i];
        else if (arg == "--out-json" && i + 1 < argc) out_json = argv[++i];
        else if (arg == "--reps" && i + 1 < argc) reps = std::stoi(argv[++i]);
        else if (arg == "--warmups" && i + 1 < argc) warmups = std::stoi(argv[++i]);
    }

    sc::SubstrateConfig config;
    config.num_nodes = num_nodes;
    config.mean_out_degree = degree;
    config.history_capacity_L = history_L;
    config.trace_bases_B = trace_B;

    // Load or generate graph
    sc::NeuralGraphCSR graph_csr;
    if (!graph_file.empty()) {
        graph_csr = sc::NeuralGraphCSR::load_binary(graph_file);
        config.num_nodes = graph_csr.num_nodes;
    } else {
        if (topology == "modular") {
            graph_csr = sc::GraphFactory::create_modular(num_nodes, degree, seed, 4, 0.80f);
        } else {
            graph_csr = sc::GraphFactory::create_random(num_nodes, degree, seed);
        }
    }

    // Load or generate external events
    std::vector<sc::ExternalEvent> external_events;
    if (!events_file.empty()) {
        external_events = sc::EventGenerator::load_binary(events_file);
    } else {
        external_events = sc::EventGenerator::generate(config.num_nodes, active_fraction, rate, t_max, seed, timing);
    }

    sc::SimulationResult final_res;
    std::vector<double> rep_times;

    int total_runs = warmups + std::max(1, reps);
    for (int r = 0; r < total_runs; ++r) {
        sc::SimulationResult res;

        if (engine == "literal") {
            sc::NeuralGraphLiteral lit_graph = sc::NeuralGraphLiteral::from_csr(graph_csr);
            sc::CppLiteralEngine eng(config, lit_graph);
            res = eng.run(external_events, t_max);
        } else if (engine == "packed") {
            sc::CppPackedEngine eng(config, graph_csr);
            res = eng.run(external_events, t_max);
        } else if (engine == "queue_binary") {
            sc::CppQueuesEngine eng(config, graph_csr, sc::QueueType::BINARY_HEAP);
            res = eng.run(external_events, t_max);
        } else if (engine == "queue_dary4") {
            sc::CppQueuesEngine eng(config, graph_csr, sc::QueueType::DARY_HEAP_4);
            res = eng.run(external_events, t_max);
        } else if (engine == "queue_bucket") {
            sc::CppQueuesEngine eng(config, graph_csr, sc::QueueType::BUCKET_QUEUE);
            res = eng.run(external_events, t_max);
        } else if (engine == "dense_sync") {
            sc::CppDenseSyncEngine eng(config, graph_csr, dt);
            res = eng.run(external_events, t_max);
        } else if (engine == "sparse_sync") {
            sc::CppSparseSyncEngine eng(config, graph_csr, dt);
            res = eng.run(external_events, t_max);
        } else if (engine == "locked") {
            sc::CppLockedEngine eng(config, graph_csr, workers);
            res = eng.run(external_events, t_max);
        } else if (engine == "owner") {
            sc::CppOwnerEngine eng(config, graph_csr, workers);
            res = eng.run(external_events, t_max);
        } else if (engine == "hybrid") {
            sc::CppHybridEngine eng(config, graph_csr);
            res = eng.run(external_events, t_max);
        } else {
            std::cerr << "Unknown engine: " << engine << std::endl;
            return 1;
        }

        if (r >= warmups) {
            rep_times.push_back(res.wall_time_sec);
            final_res = std::move(res);
        }
    }

    // Set median wall time if multiple repetitions
    if (!rep_times.empty()) {
        std::sort(rep_times.begin(), rep_times.end());
        final_res.wall_time_sec = rep_times[rep_times.size() / 2];
    }

    if (!out_json.empty()) {
        std::ofstream fout(out_json);
        if (fout) {
            print_json_result(final_res, fout);
        } else {
            std::cerr << "Failed to write output to: " << out_json << std::endl;
        }
    } else {
        print_json_result(final_res, std::cout);
    }

    return 0;
}
