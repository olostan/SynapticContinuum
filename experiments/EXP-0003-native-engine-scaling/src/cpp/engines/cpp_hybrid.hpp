#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../queues/binary_heap.hpp"
#include <vector>
#include <chrono>

namespace sc {

class CppHybridEngine {
public:
    explicit CppHybridEngine(const SubstrateConfig& config, const NeuralGraphCSR& graph)
        : config_(config), graph_(graph) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t max_events = 10000000ULL
    ) {
        auto start_wall = std::chrono::high_resolution_clock::now();
        SubstrateStatePacked state(config_);

        BinaryHeapQueue queue(std::max(size_t{65536}, external_events.size() * 2));
        uint64_t seq_counter = 0;

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

        std::vector<SpikeRecord> spike_records;
        uint64_t events_processed = 0;
        uint64_t edges_traversed = 0;
        bool capacity_exceeded = false;

        const int32_t* targets = nullptr;
        const float* weights = nullptr;
        const float* delays = nullptr;
        uint32_t count = 0;

        std::vector<Event> batch_events;
        batch_events.reserve(16);

        while (!queue.empty()) {
            if (events_processed >= max_events) {
                capacity_exceeded = true;
                break;
            }

            Event ev = queue.pop();
            events_processed++;

            if (ev.timestamp > t_max) {
                break;
            }

            batch_events.clear();
            batch_events.push_back(ev);

            // Pop all simultaneous events targeting the same node at the exact same timestamp
            while (!queue.empty()) {
                const Event& next_ev = queue.peek();
                if (next_ev.timestamp == ev.timestamp && next_ev.target == ev.target) {
                    batch_events.push_back(queue.pop());
                    events_processed++;
                } else {
                    break;
                }
            }

            // Process each impulse sequentially to preserve strict LIF semantics:
            // - If first impulse crosses threshold, neuron resets and enters refractory
            // - Subsequent impulses at same timestamp are correctly clamped by refractory state
            for (const auto& item : batch_events) {
                bool fired = state.receive_impulse(item.target, item.timestamp, item.amplitude, item.kind);
                if (fired) {
                    spike_records.push_back({item.timestamp, item.target});

                    graph_.get_outgoing(item.target, targets, weights, delays, count);
                    edges_traversed += count;

                    for (uint32_t i = 0; i < count; ++i) {
                        double arrival_t = item.timestamp + static_cast<double>(delays[i]);
                        if (arrival_t <= t_max) {
                            queue.push(Event{
                                arrival_t,
                                seq_counter++,
                                item.target,
                                targets[i],
                                weights[i],
                                static_cast<int32_t>(EventKind::SPIKE)
                            });
                        }
                    }
                }
            }
        }

        state.advance_all_potentials(t_max);

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = "cpp_hybrid";
        res.wall_time_sec = diff.count();
        res.total_events_processed = events_processed;
        res.total_edges_traversed = edges_traversed;
        res.total_spikes = state.total_spikes;
        res.peak_queue_size = queue.peak_size();
        res.final_time = t_max;
        res.final_potentials.assign(state.potentials, state.potentials + config_.num_nodes);
        res.spike_records = std::move(spike_records);
        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(state.total_spikes) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.max_queue_exceeded = capacity_exceeded;
        res.rss_bytes = get_actual_peak_rss_bytes();
        res.estimated_memory_bytes = state.memory_bytes() + graph_.memory_bytes() + queue.memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
};

} // namespace sc
