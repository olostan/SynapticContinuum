#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include <vector>
#include <cmath>
#include <chrono>
#include <unordered_map>

namespace sc {

class CppDenseSyncEngine {
public:
    explicit CppDenseSyncEngine(const SubstrateConfig& config, const NeuralGraphCSR& graph, double dt = 0.1)
        : config_(config), graph_(graph), dt_(dt) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t /*max_events*/ = 10000000ULL
    ) {
        auto start_wall = std::chrono::high_resolution_clock::now();
        int32_t N = config_.num_nodes;
        double dt = dt_;
        size_t num_steps = static_cast<size_t>(std::ceil(t_max / dt));
        float decay_factor = std::exp(static_cast<float>(-dt / config_.tau_m));

        std::vector<float> potentials(N, 0.0f);
        std::vector<double> refractory_until(N, -1e9);
        std::vector<SpikeRecord> spike_records;

        uint64_t total_spikes = 0;
        uint64_t edges_traversed = 0;
        uint64_t events_processed = 0;

        // Group external events by step
        std::unordered_map<size_t, std::vector<std::pair<int32_t, float>>> ext_by_step;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                size_t step = static_cast<size_t>(ee.timestamp / dt);
                if (step <= num_steps) {
                    ext_by_step[step].push_back({ee.target, ee.amplitude});
                }
            }
        }

        size_t max_delay_steps = static_cast<size_t>(std::ceil(config_.max_delay / dt)) + 4;
        std::vector<std::vector<float>> delay_ring(max_delay_steps, std::vector<float>(N, 0.0f));

        const int32_t* targets = nullptr;
        const float* weights = nullptr;
        const float* delays = nullptr;
        uint32_t count = 0;

        for (size_t step = 0; step < num_steps; ++step) {
            double current_t = step * dt;
            size_t ring_idx = step % max_delay_steps;
            float* syn_inputs = delay_ring[ring_idx].data();

            // 1. Vectorized passive decay
            for (int32_t i = 0; i < N; ++i) {
                potentials[i] *= decay_factor;
            }

            // 2. Add external inputs
            auto it = ext_by_step.find(step);
            if (it != ext_by_step.end()) {
                for (const auto& in : it->second) {
                    events_processed++;
                    if (current_t >= refractory_until[in.first]) {
                        potentials[in.first] += in.second;
                    }
                }
            }

            // 3. Add synaptic inputs
            for (int32_t i = 0; i < N; ++i) {
                if (syn_inputs[i] != 0.0f) {
                    events_processed++;
                    if (current_t >= refractory_until[i]) {
                        potentials[i] += syn_inputs[i];
                    }
                    syn_inputs[i] = 0.0f; // reset ring slot
                }
            }

            // 4. Threshold check
            for (int32_t i = 0; i < N; ++i) {
                if (current_t < refractory_until[i]) {
                    potentials[i] = config_.v_reset;
                    continue;
                }

                if (potentials[i] >= config_.threshold) {
                    total_spikes++;
                    potentials[i] = config_.v_reset;
                    refractory_until[i] = current_t + config_.refractory_period;
                    spike_records.push_back({current_t, i});

                    graph_.get_outgoing(i, targets, weights, delays, count);
                    edges_traversed += count;

                    for (uint32_t e = 0; e < count; ++e) {
                        int32_t target_node = targets[e];
                        float w = weights[e];
                        float d = delays[e];
                        size_t d_steps = std::max(size_t{1}, static_cast<size_t>(std::round(d / dt)));
                        size_t target_step = step + d_steps;
                        if (target_step < num_steps) {
                            size_t target_ring_idx = target_step % max_delay_steps;
                            delay_ring[target_ring_idx][target_node] += w;
                        }
                    }
                }
            }
        }

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = "cpp_dense_sync_dt_" + std::to_string(dt_);
        res.wall_time_sec = diff.count();
        res.total_events_processed = events_processed;
        res.total_edges_traversed = edges_traversed;
        res.total_spikes = total_spikes;
        res.peak_queue_size = max_delay_steps * N;
        res.final_time = t_max;
        res.final_potentials = std::move(potentials);
        res.spike_records = std::move(spike_records);
        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (N * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(total_spikes) /
            (N * std::max(t_max, 1e-5));
        res.rss_bytes = sizeof(float) * N * (max_delay_steps + 1) + graph_.memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    double dt_;
};

class CppSparseSyncEngine {
public:
    explicit CppSparseSyncEngine(const SubstrateConfig& config, const NeuralGraphCSR& graph, double dt = 0.1)
        : config_(config), graph_(graph), dt_(dt) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t /*max_events*/ = 10000000ULL
    ) {
        auto start_wall = std::chrono::high_resolution_clock::now();
        int32_t N = config_.num_nodes;
        double dt = dt_;
        size_t num_steps = static_cast<size_t>(std::ceil(t_max / dt));

        std::vector<float> potentials(N, 0.0f);
        std::vector<double> last_updated(N, 0.0);
        std::vector<double> refractory_until(N, -1e9);
        std::vector<SpikeRecord> spike_records;

        uint64_t total_spikes = 0;
        uint64_t edges_traversed = 0;
        uint64_t events_processed = 0;

        std::unordered_map<size_t, std::vector<std::pair<int32_t, float>>> ext_by_step;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                size_t step = static_cast<size_t>(ee.timestamp / dt);
                if (step <= num_steps) {
                    ext_by_step[step].push_back({ee.target, ee.amplitude});
                }
            }
        }

        size_t max_delay_steps = static_cast<size_t>(std::ceil(config_.max_delay / dt)) + 4;
        std::vector<std::vector<std::pair<int32_t, float>>> delay_ring(max_delay_steps);

        const int32_t* targets = nullptr;
        const float* weights = nullptr;
        const float* delays = nullptr;
        uint32_t count = 0;

        std::vector<int32_t> touched_nodes;
        touched_nodes.reserve(N);
        std::vector<bool> in_touched(N, false);

        for (size_t step = 0; step < num_steps; ++step) {
            double current_t = step * dt;
            size_t ring_idx = step % max_delay_steps;
            auto& syn_events = delay_ring[ring_idx];

            touched_nodes.clear();

            // External inputs
            auto it = ext_by_step.find(step);
            if (it != ext_by_step.end()) {
                for (const auto& in : it->second) {
                    events_processed++;
                    int32_t node = in.first;
                    double dt_node = current_t - last_updated[node];
                    if (dt_node > 0.0) {
                        potentials[node] *= std::exp(static_cast<float>(-dt_node / config_.tau_m));
                        last_updated[node] = current_t;
                    }
                    if (current_t >= refractory_until[node]) {
                        potentials[node] += in.second;
                    }
                    if (!in_touched[node]) {
                        in_touched[node] = true;
                        touched_nodes.push_back(node);
                    }
                }
            }

            // Synaptic inputs
            for (const auto& syn : syn_events) {
                events_processed++;
                int32_t node = syn.first;
                double dt_node = current_t - last_updated[node];
                if (dt_node > 0.0) {
                    potentials[node] *= std::exp(static_cast<float>(-dt_node / config_.tau_m));
                    last_updated[node] = current_t;
                }
                if (current_t >= refractory_until[node]) {
                    potentials[node] += syn.second;
                }
                if (!in_touched[node]) {
                    in_touched[node] = true;
                    touched_nodes.push_back(node);
                }
            }
            syn_events.clear();

            // Check only touched nodes
            for (int32_t node : touched_nodes) {
                in_touched[node] = false;
                if (current_t < refractory_until[node]) {
                    potentials[node] = config_.v_reset;
                    continue;
                }

                if (potentials[node] >= config_.threshold) {
                    total_spikes++;
                    potentials[node] = config_.v_reset;
                    refractory_until[node] = current_t + config_.refractory_period;
                    spike_records.push_back({current_t, node});

                    graph_.get_outgoing(node, targets, weights, delays, count);
                    edges_traversed += count;

                    for (uint32_t e = 0; e < count; ++e) {
                        int32_t target_node = targets[e];
                        float w = weights[e];
                        float d = delays[e];
                        size_t d_steps = std::max(size_t{1}, static_cast<size_t>(std::round(d / dt)));
                        size_t target_step = step + d_steps;
                        if (target_step < num_steps) {
                            size_t target_ring_idx = target_step % max_delay_steps;
                            delay_ring[target_ring_idx].push_back({target_node, w});
                        }
                    }
                }
            }
        }

        // Advance all to t_max
        for (int32_t i = 0; i < N; ++i) {
            double dt_node = t_max - last_updated[i];
            if (dt_node > 0.0) {
                potentials[i] *= std::exp(static_cast<float>(-dt_node / config_.tau_m));
                last_updated[i] = t_max;
            }
        }

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = "cpp_sparse_sync_dt_" + std::to_string(dt_);
        res.wall_time_sec = diff.count();
        res.total_events_processed = events_processed;
        res.total_edges_traversed = edges_traversed;
        res.total_spikes = total_spikes;
        res.peak_queue_size = max_delay_steps * 1000;
        res.final_time = t_max;
        res.final_potentials = std::move(potentials);
        res.spike_records = std::move(spike_records);
        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (N * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(total_spikes) /
            (N * std::max(t_max, 1e-5));
        res.rss_bytes = sizeof(float) * N * 3 + graph_.memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    double dt_;
};

} // namespace sc
