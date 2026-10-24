#pragma once

#include "../core/types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/state.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/queues/binary_heap.hpp"
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>
#include <algorithm>
#include <stdexcept>
#include <cmath>

namespace sc {

/**
 * Exp4BarrierFreeIndependentEngine
 * 
 * Genuine barrier-free independent worker loop control for disconnected modules (c=0.0).
 * Workers process disjoint partitions of the neural graph with zero global barriers,
 * zero inter-thread synchronization, and zero mailbox overhead.
 * 
 * Used as the physical multi-core scaling ceiling control.
 */
class Exp4BarrierFreeIndependentEngine {
public:
    explicit Exp4BarrierFreeIndependentEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        const std::vector<int32_t>& node_to_worker
    ) : config_(config),
        graph_(graph),
        num_workers_(std::max(1, num_workers)),
        node_to_worker_(node_to_worker)
    {
        if (node_to_worker_.empty()) {
            node_to_worker_.resize(config_.num_nodes);
            int32_t nodes_per_w = (config_.num_nodes + num_workers_ - 1) / num_workers_;
            for (int32_t u = 0; u < config_.num_nodes; ++u) {
                int32_t w = u / nodes_per_w;
                node_to_worker_[u] = (w < num_workers_) ? w : (num_workers_ - 1);
            }
        }

        // Verify that there are strictly ZERO cross-worker edges
        for (int32_t u = 0; u < config_.num_nodes; ++u) {
            int32_t w_u = node_to_worker_[u];
            const int32_t* tgts = nullptr;
            const float* w = nullptr;
            const float* d = nullptr;
            uint32_t cnt = 0;
            graph_.get_outgoing(u, tgts, w, d, cnt);
            for (uint32_t i = 0; i < cnt; ++i) {
                int32_t v = tgts[i];
                int32_t w_v = node_to_worker_[v];
                if (w_u != w_v) {
                    throw std::invalid_argument(
                        "Exp4BarrierFreeIndependentEngine requires strictly disconnected components across workers. "
                        "Found edge (" + std::to_string(u) + " -> " + std::to_string(v) + ") crossing workers."
                    );
                }
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

        // Separate queues for each worker
        std::vector<BinaryHeapQueue> worker_queues;
        worker_queues.reserve(W);
        for (int32_t w = 0; w < W; ++w) {
            worker_queues.emplace_back(std::max(size_t{16384}, external_events.size() * 2 / W + 1024));
        }

        uint64_t seq = 0;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                int32_t w = node_to_worker_[ee.target];
                worker_queues[w].push(Event{
                    ee.timestamp,
                    seq++,
                    ee.source,
                    ee.target,
                    ee.amplitude,
                    ee.kind
                });
            }
        }

        SubstrateStatePacked state(config_);

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(W);
        std::vector<double> worker_active_sec(W, 0.0);
        std::vector<uint64_t> worker_events(W, 0);
        std::atomic<uint64_t> total_edges{0};
        std::atomic<uint64_t> total_processed{0};

        auto t_start_sim = std::chrono::high_resolution_clock::now();

        // Spawn workers with ZERO barriers
        std::vector<std::thread> threads;
        threads.reserve(W);

        for (int32_t w = 0; w < W; ++w) {
            threads.emplace_back([&, w]() {
                auto t_act_start = std::chrono::high_resolution_clock::now();
                auto& my_queue = worker_queues[w];
                uint64_t my_seq = static_cast<uint64_t>(w) << 48;
                uint64_t my_processed = 0;

                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;

                while (!my_queue.empty()) {
                    Event ev = my_queue.pop();
                    if (ev.timestamp > t_max) continue;
                    my_processed++;

                    bool fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
                    if (fired) {
                        per_worker_spikes[w].push_back({ev.timestamp, ev.target});
                        graph_.get_outgoing(ev.target, targets, weights, delays, count);
                        total_edges.fetch_add(count, std::memory_order_relaxed);

                        for (uint32_t i = 0; i < count; ++i) {
                            double arr_t = ev.timestamp + static_cast<double>(delays[i]);
                            if (arr_t <= t_max) {
                                my_queue.push(Event{
                                    arr_t,
                                    my_seq++,
                                    ev.target,
                                    targets[i],
                                    weights[i],
                                    static_cast<int32_t>(EventKind::SPIKE)
                                });
                            }
                        }
                    }
                }

                auto t_act_end = std::chrono::high_resolution_clock::now();
                worker_active_sec[w] = std::chrono::duration<double>(t_act_end - t_act_start).count();
                worker_events[w] = my_processed;
                total_processed.fetch_add(my_processed, std::memory_order_relaxed);
            });
        }

        for (auto& t : threads) {
            t.join();
        }

        auto t_end_sim = std::chrono::high_resolution_clock::now();

        state.advance_all_potentials(t_max);
        auto t_end_total = std::chrono::high_resolution_clock::now();

        double wall_sim_sec = std::chrono::duration<double>(t_end_sim - t_start_sim).count();
        double wall_total_sec = std::chrono::duration<double>(t_end_total - t_start_total).count();

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

        Exp4ProfilingStats stats;
        stats.scheduler_name = "cpp_barrier_free_independent_W" + std::to_string(W);
        stats.num_workers = W;
        stats.num_regions = W;
        stats.wall_time_sim_sec = wall_sim_sec;
        stats.wall_time_total_sec = wall_total_sec;
        stats.total_events_processed = total_processed.load();
        stats.total_edges_traversed = total_edges.load();
        stats.total_spikes = all_spikes.size();
        stats.cross_region_events = 0;
        stats.total_migrations = 0;
        stats.migration_pause_sec = 0.0;
        stats.backlog_imbalance_ratio = 1.0;
        stats.peak_rss_bytes = get_actual_peak_rss_bytes();
        stats.state_digest = digest;
        stats.worker_active_sec = worker_active_sec;
        stats.worker_barrier1_sec.assign(W, 0.0);
        stats.worker_mailbox_sec.assign(W, 0.0);
        stats.worker_barrier2_sec.assign(W, 0.0);
        stats.worker_events_processed = worker_events;
        stats.thread_spawn_join_overhead_sec = wall_total_sec - wall_sim_sec;

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
            out_sim_result->cross_region_events = 0;
        }

        return stats;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    std::vector<int32_t> node_to_worker_;
};

} // namespace sc
