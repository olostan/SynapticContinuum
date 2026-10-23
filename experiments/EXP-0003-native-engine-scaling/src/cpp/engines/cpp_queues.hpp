#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../queues/queue_interface.hpp"
#include "../queues/binary_heap.hpp"
#include "../queues/dary_heap.hpp"
#include "../queues/bucket_queue.hpp"
#include <memory>
#include <chrono>

namespace sc {

enum class QueueType : int32_t {
    BINARY_HEAP = 0,
    DARY_HEAP_4 = 1,
    BUCKET_QUEUE = 2
};

class CppQueuesEngine {
public:
    explicit CppQueuesEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        QueueType queue_type = QueueType::BINARY_HEAP
    ) : config_(config), graph_(graph), queue_type_(queue_type) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t max_events = 10000000ULL
    ) {
        std::unique_ptr<IEventQueue> queue;
        std::string q_name;

        switch (queue_type_) {
            case QueueType::DARY_HEAP_4:
                queue = std::make_unique<DaryHeapQueue<4>>(std::max(size_t{65536}, external_events.size() * 2));
                q_name = "cpp_queue_dary4";
                break;
            case QueueType::BUCKET_QUEUE:
                queue = std::make_unique<BucketEventQueue>(config_.min_delay, 64);
                q_name = "cpp_queue_bucket";
                break;
            case QueueType::BINARY_HEAP:
            default:
                queue = std::make_unique<BinaryHeapQueue>(std::max(size_t{65536}, external_events.size() * 2));
                q_name = "cpp_queue_binary";
                break;
        }

        auto start_wall = std::chrono::high_resolution_clock::now();
        SubstrateStatePacked state(config_);
        uint64_t seq_counter = 0;

        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                queue->push(Event{
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

        while (!queue->empty()) {
            if (events_processed >= max_events) {
                capacity_exceeded = true;
                break;
            }

            Event ev = queue->pop();
            events_processed++;

            if (ev.timestamp > t_max) {
                break;
            }

            bool fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
            if (fired) {
                spike_records.push_back({ev.timestamp, ev.target});

                graph_.get_outgoing(ev.target, targets, weights, delays, count);
                edges_traversed += count;

                for (uint32_t i = 0; i < count; ++i) {
                    double arrival_t = ev.timestamp + static_cast<double>(delays[i]);
                    if (arrival_t <= t_max) {
                        queue->push(Event{
                            arrival_t,
                            seq_counter++,
                            ev.target,
                            targets[i],
                            weights[i],
                            static_cast<int32_t>(EventKind::SPIKE)
                        });
                    }
                }
            }
        }

        state.advance_all_potentials(t_max);

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = q_name;
        res.wall_time_sec = diff.count();
        res.total_events_processed = events_processed;
        res.total_edges_traversed = edges_traversed;
        res.total_spikes = state.total_spikes;
        res.peak_queue_size = queue->peak_size();
        res.final_time = t_max;
        res.final_potentials.assign(state.potentials, state.potentials + config_.num_nodes);
        res.spike_records = std::move(spike_records);
        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(state.total_spikes) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.max_queue_exceeded = capacity_exceeded;
        res.rss_bytes = state.memory_bytes() + graph_.memory_bytes() + queue->memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    QueueType queue_type_;
};

} // namespace sc
