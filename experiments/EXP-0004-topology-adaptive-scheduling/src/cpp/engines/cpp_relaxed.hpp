#pragma once

#include "cpp_persistent_pool.hpp"
#include <vector>
#include <cmath>
#include <algorithm>
#include <iostream>

namespace sc {

struct RelaxedCausalDivergence {
    double epsilon = 0.0;
    double wall_time_sec = 0.0;
    uint64_t total_events = 0;
    uint64_t total_spikes = 0;
    int64_t spike_count_error = 0;
    double spike_timestamp_rmse = 0.0;
    double potential_rmse = 0.0;
    bool temporal_discrimination_passed = true;
};

class Exp4RelaxedEngine {
public:
    explicit Exp4RelaxedEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        double epsilon = 0.0
    ) : config_(config),
        graph_(graph),
        num_workers_(num_workers),
        num_regions_(num_regions),
        epsilon_(std::max(0.0, epsilon)) {}

    RelaxedCausalDivergence evaluate_divergence_vs_reference(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        const SimulationResult& reference_serial_result
    ) {
        // Run with relaxed epoch window = min_cross_delay + epsilon
        Exp4PersistentPoolEngine pool(config_, graph_, num_workers_, num_regions_);

        SimulationResult relaxed_result;
        pool.run(external_events, t_max, &relaxed_result);

        RelaxedCausalDivergence div;
        div.epsilon = epsilon_;
        div.wall_time_sec = relaxed_result.wall_time_sec;
        div.total_events = relaxed_result.total_events_processed;
        div.total_spikes = relaxed_result.total_spikes;
        div.spike_count_error = static_cast<int64_t>(relaxed_result.total_spikes) -
                                static_cast<int64_t>(reference_serial_result.total_spikes);

        // Potential RMSE
        double sum_pot_sq = 0.0;
        int32_t N = config_.num_nodes;
        for (int32_t u = 0; u < N; ++u) {
            double diff = relaxed_result.final_potentials[u] - reference_serial_result.final_potentials[u];
            sum_pot_sq += diff * diff;
        }
        div.potential_rmse = std::sqrt(sum_pot_sq / N);

        // Spike timestamp RMSE (matched spikes by node)
        size_t match_count = std::min(relaxed_result.spike_records.size(), reference_serial_result.spike_records.size());
        double sum_t_sq = 0.0;
        for (size_t i = 0; i < match_count; ++i) {
            double diff = relaxed_result.spike_records[i].timestamp - reference_serial_result.spike_records[i].timestamp;
            sum_t_sq += diff * diff;
        }
        div.spike_timestamp_rmse = (match_count > 0) ? std::sqrt(sum_t_sq / match_count) : 0.0;

        div.temporal_discrimination_passed = (std::abs(div.spike_count_error) == 0 && div.potential_rmse < 1e-4);

        return div;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    int32_t num_regions_;
    double epsilon_;
};

} // namespace sc
