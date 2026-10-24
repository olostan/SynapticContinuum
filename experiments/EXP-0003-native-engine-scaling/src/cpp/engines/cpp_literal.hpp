#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include <queue>
#include <chrono>

namespace sc {

class CppLiteralEngine {
public:
    explicit CppLiteralEngine(const SubstrateConfig& config, const NeuralGraphLiteral& graph)
        : config_(config), graph_(graph) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t max_events = 10000000ULL
    ) {
        auto start_wall = std::chrono::high_resolution_clock::now();
        SubstrateStateLiteral state(config_);

        std::priority_queue<Event, std::vector<Event>, std::greater<Event>> queue;
        uint64_t seq_counter = 0;
        size_t peak_queue = 0;

        // Push external events
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                queue.push(Event{
                    ee.timestamp,
                    seq_counter++,
                    ee.source,
                    ee.target,
                    ee.amplitude,
                    ee.kind
                });
            }
        }
        peak_queue = queue.size();

        std::vector<SpikeRecord> spike_records;
        uint64_t events_processed = 0;
        uint64_t edges_traversed = 0;
        bool capacity_exceeded = false;

        while (!queue.empty()) {
            if (events_processed >= max_events) {
                capacity_exceeded = true;
                break;
            }

            Event ev = queue.top();
            queue.pop();
            events_processed++;

            if (ev.timestamp > t_max) {
                break;
            }

            bool fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
            if (fired) {
                spike_records.push_back({ev.timestamp, ev.target});

                const auto& targets = graph_.adj_targets[ev.target];
                const auto& weights = graph_.adj_weights[ev.target];
                const auto& delays = graph_.adj_delays[ev.target];
                size_t num_targets = targets.size();
                edges_traversed += num_targets;

                for (size_t i = 0; i < num_targets; ++i) {
                    double arrival_t = ev.timestamp + static_cast<double>(delays[i]);
                    if (arrival_t <= t_max) {
                        queue.push(Event{
                            arrival_t,
                            seq_counter++,
                            ev.target,
                            targets[i],
                            weights[i],
                            static_cast<int32_t>(EventKind::SPIKE)
                        });
                    }
                }
                if (queue.size() > peak_queue) {
                    peak_queue = queue.size();
                }
            }
        }

        // Advance all potentials to t_max for exact final state
        state.advance_all_potentials(t_max);

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = "cpp_literal";
        res.wall_time_sec = diff.count();
        res.total_events_processed = events_processed;
        res.total_edges_traversed = edges_traversed;
        res.total_spikes = state.total_spikes;
        res.peak_queue_size = peak_queue;
        res.final_time = t_max;
        res.final_potentials = state.potentials;
        res.spike_records = std::move(spike_records);
        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(state.total_spikes) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.max_queue_exceeded = capacity_exceeded;
        res.rss_bytes = get_actual_peak_rss_bytes();
        res.estimated_memory_bytes = state.memory_bytes() + graph_.memory_bytes() + peak_queue * sizeof(Event);

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphLiteral graph_;
};

} // namespace sc
