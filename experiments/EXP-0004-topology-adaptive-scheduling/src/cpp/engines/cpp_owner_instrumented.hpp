#pragma once

#include "../core/types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/state.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/queues/binary_heap.hpp"
#include <vector>
#include <thread>
#include <atomic>
#include <barrier>
#include <chrono>
#include <algorithm>
#include <stdexcept>
#include <cmath>

namespace sc {

class Exp4OwnerInstrumentedEngine {
public:
    explicit Exp4OwnerInstrumentedEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        const std::vector<int32_t>& partition_map = {}
    ) : config_(config), graph_(graph), num_workers_(std::max(1, num_workers)), partition_map_(partition_map) {
        if (partition_map_.empty()) {
            partition_map_.resize(config_.num_nodes);
            int32_t nodes_per_worker = (config_.num_nodes + num_workers_ - 1) / num_workers_;
            for (int32_t u = 0; u < config_.num_nodes; ++u) {
                int32_t p = u / nodes_per_worker;
                partition_map_[u] = (p < num_workers_) ? p : (num_workers_ - 1);
            }
        }
    }

    Exp4ProfilingStats run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        SimulationResult* out_sim_result = nullptr
    ) {
        auto t_start_total = std::chrono::high_resolution_clock::now();

        int32_t N = config_.num_nodes;
        int32_t W = num_workers_;

        auto get_partition = [&](int32_t node) noexcept -> int32_t {
            int32_t p = partition_map_[node];
            return (p >= 0) ? (p % W) : 0;
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
            if (min_cross_delay <= 0.0) {
                throw std::invalid_argument(
                    "Exp4OwnerInstrumentedEngine causality precondition violation: Graph contains cross-region edge(s) "
                    "with non-positive delay (min_cross_delay = " + std::to_string(min_cross_delay) +
                    " <= 0.0). Conservative PDES lookahead requires strictly positive cross-region "
                    "delays (d_min > 0.0) to prevent causal arrival inversions and deadlock."
                );
            }
            epoch_delta = min_cross_delay;
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

        // State partitioned across workers
        SubstrateStatePacked state(config_);

        std::atomic<uint64_t> total_processed{0};
        std::atomic<uint64_t> total_edges{0};
        std::atomic<uint64_t> cross_region_count{0};

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(W);
        std::vector<uint64_t> per_worker_seq(W, 0);
        for (int32_t w = 0; w < W; ++w) {
            per_worker_seq[w] = static_cast<uint64_t>(w) << 48;
        }

        // Telemetry structures
        std::vector<double> worker_active_sec(W, 0.0);
        std::vector<double> worker_barrier1_sec(W, 0.0);
        std::vector<double> worker_mailbox_sec(W, 0.0);
        std::vector<double> worker_barrier2_sec(W, 0.0);
        std::vector<uint64_t> worker_events(W, 0);

        std::barrier sync_barrier(W);

        auto t_start_threads = std::chrono::high_resolution_clock::now();
        std::vector<std::thread> workers;
        workers.reserve(W);

        int64_t num_epochs = (epoch_delta > 0.0) ? static_cast<int64_t>(std::ceil(t_max / epoch_delta)) : 1;
        if (num_epochs <= 0) num_epochs = 1;

        for (int32_t w = 0; w < W; ++w) {
            workers.emplace_back([&, w]() {
                auto& my_queue = local_queues[w];
                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;

                uint64_t my_processed = 0;

                for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
                    double epoch_limit = (epoch + 1) * epoch_delta;
                    auto t_active_start = std::chrono::high_resolution_clock::now();

                    while (!my_queue.empty()) {
                        if (my_queue.peek().timestamp >= epoch_limit) {
                            break;
                        }

                        Event ev = my_queue.pop();
                        my_processed++;

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

                    auto t_active_end = std::chrono::high_resolution_clock::now();
                    worker_active_sec[w] += std::chrono::duration<double>(t_active_end - t_active_start).count();

                    // Barrier 1: Wait for all workers to finish epoch events
                    auto t_b1_start = std::chrono::high_resolution_clock::now();
                    sync_barrier.arrive_and_wait();
                    auto t_b1_end = std::chrono::high_resolution_clock::now();
                    worker_barrier1_sec[w] += std::chrono::duration<double>(t_b1_end - t_b1_start).count();

                    // Mailbox transfer
                    auto t_mb_start = std::chrono::high_resolution_clock::now();
                    for (int32_t from_w = 0; from_w < W; ++from_w) {
                        if (from_w != w) {
                            auto& incoming = mailboxes[from_w][w];
                            for (const auto& ev : incoming) {
                                my_queue.push(ev);
                            }
                            incoming.clear();
                        }
                    }
                    auto t_mb_end = std::chrono::high_resolution_clock::now();
                    worker_mailbox_sec[w] += std::chrono::duration<double>(t_mb_end - t_mb_start).count();

                    // Barrier 2: Wait for mailbox draining before starting next epoch
                    auto t_b2_start = std::chrono::high_resolution_clock::now();
                    sync_barrier.arrive_and_wait();
                    auto t_b2_end = std::chrono::high_resolution_clock::now();
                    worker_barrier2_sec[w] += std::chrono::duration<double>(t_b2_end - t_b2_start).count();
                }

                worker_events[w] = my_processed;
                total_processed.fetch_add(my_processed, std::memory_order_relaxed);
            });
        }

        for (auto& t : workers) {
            if (t.joinable()) t.join();
        }
        auto t_end_threads = std::chrono::high_resolution_clock::now();

        state.advance_all_potentials(t_max);
        auto t_end_total = std::chrono::high_resolution_clock::now();

        double wall_sim_sec = std::chrono::duration<double>(t_end_threads - t_start_threads).count();
        double wall_total_sec = std::chrono::duration<double>(t_end_total - t_start_total).count();
        double spawn_overhead_sec = wall_total_sec - wall_sim_sec;

        // Collect spikes and compute digest
        std::vector<SpikeRecord> all_spikes;
        for (auto& spks : per_worker_spikes) {
            all_spikes.insert(all_spikes.end(), spks.begin(), spks.end());
        }
        std::sort(all_spikes.begin(), all_spikes.end(), [](const SpikeRecord& a, const SpikeRecord& b) {
            if (std::abs(a.timestamp - b.timestamp) > 1e-6) return a.timestamp < b.timestamp;
            return a.node < b.node;
        });

        std::vector<float> final_pots(state.potentials, state.potentials + N);
        uint64_t digest = compute_state_digest(all_spikes, final_pots);

        // Compute backlog imbalance: max / mean
        uint64_t max_ev = 0;
        uint64_t sum_ev = 0;
        for (uint64_t ev : worker_events) {
            sum_ev += ev;
            if (ev > max_ev) max_ev = ev;
        }
        double mean_ev = (W > 0) ? (static_cast<double>(sum_ev) / W) : 1.0;
        double imbalance = (mean_ev > 0) ? (static_cast<double>(max_ev) / mean_ev) : 1.0;

        Exp4ProfilingStats stats;
        stats.scheduler_name = "cpp_owner_instrumented_W" + std::to_string(W);
        stats.num_workers = W;
        stats.num_regions = W;
        stats.wall_time_sim_sec = wall_sim_sec;
        stats.wall_time_total_sec = wall_total_sec;
        stats.total_events_processed = total_processed.load();
        stats.total_edges_traversed = total_edges.load();
        stats.total_spikes = all_spikes.size();
        stats.cross_region_events = cross_region_count.load();
        stats.total_migrations = 0;
        stats.migration_pause_sec = 0.0;
        stats.backlog_imbalance_ratio = imbalance;
        stats.peak_rss_bytes = get_actual_peak_rss_bytes();
        stats.state_digest = digest;
        stats.worker_active_sec = worker_active_sec;
        stats.worker_barrier1_sec = worker_barrier1_sec;
        stats.worker_mailbox_sec = worker_mailbox_sec;
        stats.worker_barrier2_sec = worker_barrier2_sec;
        stats.worker_events_processed = worker_events;
        stats.thread_spawn_join_overhead_sec = spawn_overhead_sec;

        if (out_sim_result) {
            out_sim_result->scheduler_name = stats.scheduler_name;
            out_sim_result->wall_time_sec = wall_sim_sec;
            out_sim_result->total_events_processed = stats.total_events_processed;
            out_sim_result->total_edges_traversed = stats.total_edges_traversed;
            out_sim_result->total_spikes = stats.total_spikes;
            out_sim_result->final_time = t_max;
            out_sim_result->final_potentials = std::move(final_pots);
            out_sim_result->spike_records = std::move(all_spikes);
            out_sim_result->state_digest = digest;
            out_sim_result->rss_bytes = stats.peak_rss_bytes;
            out_sim_result->cross_region_events = stats.cross_region_events;
        }

        return stats;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    std::vector<int32_t> partition_map_;
};

} // namespace sc
