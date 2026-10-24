#include "../core/types.hpp"
#include "../core/prng.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../engines/cpp_packed.hpp"
#include "../engines/cpp_sync.hpp"

#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <fstream>
#include <sstream>

namespace sc {

struct WorkloadFidelityResult {
    int32_t N;
    double active_fraction;
    double t_event_ms;
    double t_sync_dt01_ms;
    double t_sync_dt001_ms;
    double ratio_dt01;  // t_sync / t_event
    double ratio_dt001; // t_sync / t_event
    uint64_t spikes_event;
    uint64_t spikes_dt01;
    uint64_t spikes_dt001;
    double rmse_pot_dt01;
    double rmse_pot_dt001;
    double mean_t_err_dt01;
    double mean_t_err_dt001;
};

// Compute mean timestamp error between exact spike times and sync spike times
double compute_mean_timestamp_error(
    const std::vector<SpikeRecord>& exact_spikes,
    const std::vector<SpikeRecord>& sync_spikes,
    int32_t num_nodes
) {
    std::vector<std::vector<double>> exact_per_node(num_nodes);
    std::vector<std::vector<double>> sync_per_node(num_nodes);

    for (const auto& spk : exact_spikes) {
        if (spk.node >= 0 && spk.node < num_nodes) {
            exact_per_node[spk.node].push_back(spk.timestamp);
        }
    }
    for (const auto& spk : sync_spikes) {
        if (spk.node >= 0 && spk.node < num_nodes) {
            sync_per_node[spk.node].push_back(spk.timestamp);
        }
    }

    double total_err = 0.0;
    size_t count = 0;

    for (int32_t i = 0; i < num_nodes; ++i) {
        size_t n = std::min(exact_per_node[i].size(), sync_per_node[i].size());
        for (size_t k = 0; k < n; ++k) {
            total_err += std::abs(exact_per_node[i][k] - sync_per_node[i][k]);
            count++;
        }
    }

    return count > 0 ? (total_err / count) : 0.0;
}

} // namespace sc

int main(int argc, char* argv[]) {
    std::string out_path = "runs/matched_fidelity_metrics.json";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--out" && i + 1 < argc) {
            out_path = argv[++i];
        }
    }

    std::cout << "========================================================================\n"
              << "Running EXP-0003 Comprehensive Matched-Fidelity & Crossover Benchmark\n"
              << "========================================================================\n" << std::endl;

    std::vector<int32_t> sizes = {128, 1024, 10000};
    std::vector<double> fractions = {0.001, 0.01, 0.05, 0.10, 0.20, 0.50, 1.00};
    int32_t degree = 16;
    double t_max = 10.0;
    uint64_t seed = 42;
    int32_t reps = 3;

    std::vector<sc::WorkloadFidelityResult> results;

    for (int32_t N : sizes) {
        std::cout << ">>> Profiling N = " << N << " (D = " << degree << ") across active fractions...\n";
        auto graph = sc::GraphFactory::create_random(N, degree, seed);

        sc::SubstrateConfig config;
        config.num_nodes = N;
        config.mean_out_degree = degree;
        config.threshold = 1.0f;
        config.refractory_period = 1.0f;
        config.tau_m = 5.0f;

        for (double f : fractions) {
            auto events = sc::EventGenerator::generate(N, f, 1.0, t_max, seed);

            // 1. Exact Event-Driven (cpp_packed)
            sc::CppPackedEngine event_eng(config, graph);
            std::vector<double> event_times;
            sc::SimulationResult res_event;
            for (int r = 0; r < reps; ++r) {
                res_event = event_eng.run(events, t_max);
                event_times.push_back(res_event.wall_time_sec * 1000.0);
            }
            std::sort(event_times.begin(), event_times.end());
            double t_event = event_times[reps / 2];

            // 2. Dense Sync dt = 0.10
            sc::CppDenseSyncEngine sync01_eng(config, graph, 0.10);
            std::vector<double> sync01_times;
            sc::SimulationResult res_sync01;
            for (int r = 0; r < reps; ++r) {
                res_sync01 = sync01_eng.run(events, t_max);
                sync01_times.push_back(res_sync01.wall_time_sec * 1000.0);
            }
            std::sort(sync01_times.begin(), sync01_times.end());
            double t_sync01 = sync01_times[reps / 2];

            // 3. Dense Sync dt = 0.01
            sc::CppDenseSyncEngine sync001_eng(config, graph, 0.01);
            std::vector<double> sync001_times;
            sc::SimulationResult res_sync001;
            for (int r = 0; r < reps; ++r) {
                res_sync001 = sync001_eng.run(events, t_max);
                sync001_times.push_back(res_sync001.wall_time_sec * 1000.0);
            }
            std::sort(sync001_times.begin(), sync001_times.end());
            double t_sync001 = sync001_times[reps / 2];

            // Accuracy metrics
            double ssq_err_01 = 0.0;
            double ssq_err_001 = 0.0;
            for (int32_t i = 0; i < N; ++i) {
                double d01 = res_sync01.final_potentials[i] - res_event.final_potentials[i];
                ssq_err_01 += d01 * d01;
                double d001 = res_sync001.final_potentials[i] - res_event.final_potentials[i];
                ssq_err_001 += d001 * d001;
            }
            double rmse_01 = std::sqrt(ssq_err_01 / N);
            double rmse_001 = std::sqrt(ssq_err_001 / N);

            double mean_t_err_01 = sc::compute_mean_timestamp_error(res_event.spike_records, res_sync01.spike_records, N);
            double mean_t_err_001 = sc::compute_mean_timestamp_error(res_event.spike_records, res_sync001.spike_records, N);

            sc::WorkloadFidelityResult wres{
                N, f,
                t_event, t_sync01, t_sync001,
                t_sync01 / t_event, t_sync001 / t_event,
                res_event.total_spikes, res_sync01.total_spikes, res_sync001.total_spikes,
                rmse_01, rmse_001,
                mean_t_err_01, mean_t_err_001
            };
            results.push_back(wres);

            std::cout << "  f = " << std::fixed << std::setprecision(3) << f
                      << " | Event: " << std::setprecision(3) << t_event << " ms"
                      << " | Sync(0.1): " << t_sync01 << " ms (RMSE=" << std::setprecision(4) << rmse_01 << ")"
                      << " | Sync(0.01): " << t_sync001 << " ms (RMSE=" << rmse_001 << ")\n";
        }
    }

    // Print Full Markdown Table
    std::cout << "\n========================================================================\n"
              << "### Measured Matched-Fidelity & Crossover Table\n"
              << "========================================================================\n\n";

    std::cout << "| $N$ | Active Fraction ($f$) | Event Sim Time | Sync ($\\\\Delta t = 0.1$) Time | Sync ($\\\\Delta t = 0.01$) Time | RMSE ($\\\\Delta t = 0.1$) | RMSE ($\\\\Delta t = 0.01$) | Spike Error ($\\\\Delta t = 0.1$) | Spike Error ($\\\\Delta t = 0.01$) | Timestamp Err ($\\\\Delta t = 0.1$) | Timestamp Err ($\\\\Delta t = 0.01$) | Regime Favored ($\\\\Delta t = 0.01$) |\n";
    std::cout << "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n";

    for (const auto& r : results) {
        std::string regime = (r.t_event_ms < r.t_sync_dt001_ms) ? "**EVENT**" : "**SYNC**";
        int64_t diff_spk_01 = std::abs(static_cast<int64_t>(r.spikes_dt01) - static_cast<int64_t>(r.spikes_event));
        int64_t diff_spk_001 = std::abs(static_cast<int64_t>(r.spikes_dt001) - static_cast<int64_t>(r.spikes_event));

        std::cout << "| " << r.N
                  << " | " << std::fixed << std::setprecision(3) << r.active_fraction
                  << " | " << std::setprecision(3) << r.t_event_ms << " ms"
                  << " | " << std::setprecision(3) << r.t_sync_dt01_ms << " ms"
                  << " | " << std::setprecision(3) << r.t_sync_dt001_ms << " ms"
                  << " | " << std::setprecision(4) << r.rmse_pot_dt01
                  << " | " << std::setprecision(4) << r.rmse_pot_dt001
                  << " | " << diff_spk_01
                  << " | " << diff_spk_001
                  << " | " << std::setprecision(4) << r.mean_t_err_dt01 << " ms"
                  << " | " << std::setprecision(4) << r.mean_t_err_dt001 << " ms"
                  << " | " << regime << " |\n";
    }

    // Save JSON metrics
    std::ofstream jout(out_path);
    if (jout) {
        jout << "[\n";
        for (size_t i = 0; i < results.size(); ++i) {
            const auto& r = results[i];
            jout << "  {\n"
                 << "    \"N\": " << r.N << ",\n"
                 << "    \"active_fraction\": " << r.active_fraction << ",\n"
                 << "    \"t_event_ms\": " << r.t_event_ms << ",\n"
                 << "    \"t_sync_dt01_ms\": " << r.t_sync_dt01_ms << ",\n"
                 << "    \"t_sync_dt001_ms\": " << r.t_sync_dt001_ms << ",\n"
                 << "    \"rmse_pot_dt01\": " << r.rmse_pot_dt01 << ",\n"
                 << "    \"rmse_pot_dt001\": " << r.rmse_pot_dt001 << ",\n"
                 << "    \"spikes_event\": " << r.spikes_event << ",\n"
                 << "    \"spikes_dt01\": " << r.spikes_dt01 << ",\n"
                 << "    \"spikes_dt001\": " << r.spikes_dt001 << ",\n"
                 << "    \"mean_t_err_dt01\": " << r.mean_t_err_dt01 << ",\n"
                 << "    \"mean_t_err_dt001\": " << r.mean_t_err_dt001 << "\n"
                 << "  }" << (i + 1 < results.size() ? ",\n" : "\n");
        }
        jout << "]\n";
    }

    return 0;
}
