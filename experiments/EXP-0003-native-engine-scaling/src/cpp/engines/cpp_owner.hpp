#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../queues/binary_heap.hpp"
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>
#include <barrier>
#include <algorithm>
#include <limits>

namespace sc {

class CppOwnerEngine {
public:
    explicit CppOwnerEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers = 4
    ) : config_(config), graph_(graph), num_workers_(std::max(1, num_workers)) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t max_events = 10000000ULL
    ) {
        (void)max_events;
        auto start_wall = std::chrono::high_resolution_clock::now();
        int32_t N = config_.num_nodes;
        int32_t W = num_workers_;
        int32_t nodes_per_worker = (N + W - 1) / W;

        auto get_partition = [&](int32_t node) noexcept -> int32_t {
            int32_t p = node / nodes_per_worker;
            return (p < W) ? p : (W - 1);
        };

        // Compute exact conservative lookahead from minimum cross-region edge delay
        double min_cross_delay = std::numeric_limits<double>::infinity();
        bool has_cross_edges = false;

        for (int32_t u = 0; u < N; ++u) {
            int32_t part_u = get_partition(u);
            const int32_t* tgts = nullptr;
            const float* w = nullptr;
            const float* d = nullptr;
            uint32_t cnt = 0;
            graph_.get_outgoing(u, tgts, w, d, cnt);

            for (uint32_t i = 0; i < cnt; ++i) {
                int32_t v = tgts[i];
                int32_t part_v = get_partition(v);
                if (part_u != part_v) {
                    has_cross_edges = true;
                    if (d[i] < min_cross_delay) {
                        min_cross_delay = d[i];
                    }
                }
            }
        }

        double epoch_delta = config_.min_delay;
        if (has_cross_edges) {
            epoch_delta = (min_cross_delay > 0.0) ? min_cross_delay : 0.001;
        } else {
            // Completely independent partitions: safe lookahead is the entire simulation horizon
            epoch_delta = t_max + 1.0;
        }

        // Per-worker event queues
        std::vector<BinaryHeapQueue> local_queues;
        local_queues.reserve(W);
        for (int32_t w = 0; w < W; ++w) {
            local_queues.emplace_back(std::max(size_t{16384}, external_events.size() * 2 / W + 1024));
        }

        uint64_t seq_counter = 0;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                int32_t p = get_partition(ee.target);
                local_queues[p].push(Event{
                    ee.timestamp,
                    seq_counter++,
                    ee.source,
                    ee.target,
                    ee.amplitude,
                    ee.kind
                });
            }
        }

        // Cross-worker mailboxes: outgoing[from_w][to_w]
        std::vector<std::vector<std::vector<Event>>> mailboxes(W, std::vector<std::vector<Event>>(W));

        // State: partitioned by node ownership, each worker accesses its own nodes exclusively
        SubstrateStatePacked state(config_);

        std::atomic<uint64_t> total_processed{0};
        std::atomic<uint64_t> total_edges{0};
        std::atomic<uint64_t> cross_region_count{0};
        std::atomic<uint64_t> causal_stalls{0};

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(W);
        std::vector<uint64_t> per_worker_seq(W, 0);
        for (int32_t w = 0; w < W; ++w) {
            per_worker_seq[w] = static_cast<uint64_t>(w) << 48;
        }

        std::barrier sync_barrier(W);
        std::vector<std::thread> workers;
        workers.reserve(W);

        for (int32_t w = 0; w < W; ++w) {
            workers.emplace_back([&, w]() {
                auto& my_queue = local_queues[w];
                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;

                double epoch_limit = epoch_delta;

                while (epoch_limit - epoch_delta <= t_max) {
                    while (!my_queue.empty()) {
                        if (my_queue.peek().timestamp >= epoch_limit) {
                            break;
                        }

                        Event ev = my_queue.pop();
                        total_processed.fetch_add(1, std::memory_order_relaxed);

                        if (ev.timestamp > t_max) continue;

                        bool fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
                        if (fired) {
                            per_worker_spikes[w].push_back({ev.timestamp, ev.target});

                            graph_.get_outgoing(ev.target, targets, weights, delays, count);
                            total_edges.fetch_add(count, std::memory_order_relaxed);

                            for (uint32_t i = 0; i < count; ++i) {
                                double arr_t = ev.timestamp + static_cast<double>(delays[i]);
                                if (arr_t <= t_max) {
                                    int32_t dest = targets[i];
                                    int32_t dest_part = get_partition(dest);
                                    Event child{
                                        arr_t,
                                        per_worker_seq[w]++,
                                        ev.target,
                                        dest,
                                        weights[i],
                                        static_cast<int32_t>(EventKind::SPIKE)
                                    };

                                    if (dest_part == w) {
                                        my_queue.push(child);
                                    } else {
                                        mailboxes[w][dest_part].push_back(child);
                                        cross_region_count.fetch_add(1, std::memory_order_relaxed);
                                    }
                                }
                            }
                        }
                    }

                    causal_stalls.fetch_add(1, std::memory_order_relaxed);
                    sync_barrier.arrive_and_wait();

                    for (int32_t from_w = 0; from_w < W; ++from_w) {
                        if (from_w != w) {
                            auto& incoming = mailboxes[from_w][w];
                            for (const auto& ev : incoming) {
                                my_queue.push(ev);
                            }
                            incoming.clear();
                        }
                    }

                    sync_barrier.arrive_and_wait();
                    epoch_limit += epoch_delta;
                }
            });
        }

        for (auto& t : workers) {
            if (t.joinable()) t.join();
        }

        state.advance_all_potentials(t_max);

        auto end_wall = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> diff = end_wall - start_wall;

        SimulationResult res;
        res.scheduler_name = "cpp_owner_workers_" + std::to_string(W);
        res.wall_time_sec = diff.count();
        res.total_events_processed = total_processed.load();
        res.total_edges_traversed = total_edges.load();
        res.total_spikes = state.total_spikes;
        size_t peak_q = 0;
        for (const auto& q : local_queues) {
            if (q.peak_size() > peak_q) peak_q = q.peak_size();
        }
        res.peak_queue_size = peak_q * W;
        res.final_time = t_max;
        res.final_potentials.assign(state.potentials, state.potentials + config_.num_nodes);

        for (auto& spks : per_worker_spikes) {
            res.spike_records.insert(res.spike_records.end(), spks.begin(), spks.end());
        }
        std::sort(res.spike_records.begin(), res.spike_records.end(), [](const SpikeRecord& a, const SpikeRecord& b) {
            if (std::abs(a.timestamp - b.timestamp) > 1e-6) return a.timestamp < b.timestamp;
            return a.node < b.node;
        });

        res.state_digest = compute_state_digest(res.spike_records, res.final_potentials);
        res.injected_active_fraction = static_cast<double>(external_events.size()) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.propagated_active_fraction = static_cast<double>(state.total_spikes) /
            (config_.num_nodes * std::max(t_max, 1e-5));
        res.cross_region_events = cross_region_count.load();
        res.causal_stalls = causal_stalls.load();
        res.rss_bytes = get_actual_peak_rss_bytes();
        res.estimated_memory_bytes = state.memory_bytes() + graph_.memory_bytes() + peak_q * W * sizeof(Event);

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
};

} // namespace sc
