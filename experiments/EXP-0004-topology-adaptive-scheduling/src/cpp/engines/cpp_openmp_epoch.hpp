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
#ifdef _OPENMP
#include <omp.h>
#endif

namespace sc {

/**
 * Exp4OpenMPEngine
 * 
 * D4 Parallel Scheduler Baseline: OpenMP Persistent Team + `#pragma omp barrier` Epoch Engine.
 * Compares standard OpenMP runtime barrier synchronization (`libgomp` spin-wait barrier)
 * against our `std::thread` + `std::barrier` persistent pool (`Exp4PersistentPoolEngine`).
 */
class Exp4OpenMPEngine {
public:
    explicit Exp4OpenMPEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        const std::vector<int32_t>& node_to_region = {}
    ) : config_(config),
        graph_(graph),
        num_workers_(std::max(1, num_workers)),
        num_regions_(std::max(num_workers_, num_regions)),
        node_to_region_(node_to_region)
    {
        if (node_to_region_.empty()) {
            node_to_region_.resize(config_.num_nodes);
            int32_t nodes_per_reg = (config_.num_nodes + num_regions_ - 1) / num_regions_;
            for (int32_t u = 0; u < config_.num_nodes; ++u) {
                int32_t r = u / nodes_per_reg;
                node_to_region_[u] = (r < num_regions_) ? r : (num_regions_ - 1);
            }
        }

        region_owner_.resize(num_regions_);
        int32_t reg_per_w = (num_regions_ + num_workers_ - 1) / num_workers_;
        for (int32_t r = 0; r < num_regions_; ++r) {
            int32_t w = r / reg_per_w;
            region_owner_[r] = (w < num_workers_) ? w : (num_workers_ - 1);
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
        int32_t R = num_regions_;

        double min_cross_delay = std::numeric_limits<double>::infinity();
        bool has_cross_edges = false;

        for (int32_t u = 0; u < N; ++u) {
            int32_t reg_u = node_to_region_[u];
            int32_t owner_u = region_owner_[reg_u];
            const int32_t* tgts = nullptr;
            const float* w = nullptr;
            const float* d = nullptr;
            uint32_t cnt = 0;
            graph_.get_outgoing(u, tgts, w, d, cnt);

            for (uint32_t i = 0; i < cnt; ++i) {
                int32_t v = tgts[i];
                int32_t reg_v = node_to_region_[v];
                int32_t owner_v = region_owner_[reg_v];
                if (owner_u != owner_v) {
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
                throw std::invalid_argument("Exp4OpenMPEngine: Cross-worker edge delay <= 0.0.");
            }
            epoch_delta = min_cross_delay;
        } else {
            epoch_delta = t_max + 1.0;
        }

        std::vector<BinaryHeapQueue> worker_queues;
        worker_queues.reserve(W);
        for (int32_t w = 0; w < W; ++w) {
            worker_queues.emplace_back(std::max(size_t{16384}, external_events.size() * 2 / W + 1024));
        }

        uint64_t seq = 0;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                int32_t r = node_to_region_[ee.target];
                int32_t w = region_owner_[r];
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

        std::vector<std::vector<std::vector<Event>>> mailboxes(W, std::vector<std::vector<Event>>(W));
        int64_t num_epochs = (epoch_delta > 0.0) ? static_cast<int64_t>(std::ceil(t_max / epoch_delta)) : 1;
        if (num_epochs <= 0) num_epochs = 1;

        SubstrateStatePacked state(config_);
        std::atomic<uint64_t> total_processed{0};
        std::atomic<uint64_t> total_edges{0};
        std::atomic<uint64_t> cross_worker_events{0};

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(W);
        std::vector<double> worker_active_sec(W, 0.0);
        std::vector<double> worker_barrier1_sec(W, 0.0);
        std::vector<double> worker_mailbox_sec(W, 0.0);
        std::vector<double> worker_barrier2_sec(W, 0.0);
        std::vector<uint64_t> worker_events(W, 0);

        auto t_start_sim = std::chrono::high_resolution_clock::now();

        #ifdef _OPENMP
        #pragma omp parallel num_threads(W)
        {
            int32_t w = omp_get_thread_num();
            if (w < W) {
                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;

                uint64_t my_seq = static_cast<uint64_t>(w) << 48;
                uint64_t my_processed = 0;
                auto& my_queue = worker_queues[w];

                for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
                    double epoch_limit = (epoch + 1) * epoch_delta;
                    auto t_act_start = std::chrono::high_resolution_clock::now();

                    while (!my_queue.empty()) {
                        if (my_queue.peek().timestamp >= epoch_limit) break;

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
                                    int32_t dest_reg = node_to_region_[dest];
                                    int32_t dest_owner = region_owner_[dest_reg];

                                    Event child{
                                        arr_t,
                                        my_seq++,
                                        ev.target,
                                        dest,
                                        weights[i],
                                        static_cast<int32_t>(EventKind::SPIKE)
                                    };

                                    if (dest_owner == w) {
                                        my_queue.push(child);
                                    } else {
                                        mailboxes[w][dest_owner].push_back(child);
                                        cross_worker_events.fetch_add(1, std::memory_order_relaxed);
                                    }
                                }
                            }
                        }
                    }

                    auto t_act_end = std::chrono::high_resolution_clock::now();
                    worker_active_sec[w] += std::chrono::duration<double>(t_act_end - t_act_start).count();

                    auto t_b1_start = std::chrono::high_resolution_clock::now();
                    #pragma omp barrier
                    auto t_b1_end = std::chrono::high_resolution_clock::now();
                    worker_barrier1_sec[w] += std::chrono::duration<double>(t_b1_end - t_b1_start).count();

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

                    auto t_b2_start = std::chrono::high_resolution_clock::now();
                    #pragma omp barrier
                    auto t_b2_end = std::chrono::high_resolution_clock::now();
                    worker_barrier2_sec[w] += std::chrono::duration<double>(t_b2_end - t_b2_start).count();
                }

                worker_events[w] = my_processed;
                total_processed.fetch_add(my_processed, std::memory_order_relaxed);
            }
        }
        #else
        std::barrier<> fallback_b1(W);
        std::barrier<> fallback_b2(W);
        std::vector<std::thread> fallback_threads;
        fallback_threads.reserve(W);
        for (int32_t w = 0; w < W; ++w) {
            fallback_threads.emplace_back([&, w]() {
                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;
                uint64_t my_seq = static_cast<uint64_t>(w) << 48;
                uint64_t my_processed = 0;
                auto& my_queue = worker_queues[w];

                for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
                    double epoch_limit = (epoch + 1) * epoch_delta;
                    auto t_act_start = std::chrono::high_resolution_clock::now();

                    while (!my_queue.empty()) {
                        if (my_queue.peek().timestamp >= epoch_limit) break;
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
                                    int32_t dest_reg = node_to_region_[dest];
                                    int32_t dest_owner = region_owner_[dest_reg];
                                    Event child{arr_t, my_seq++, ev.target, dest, weights[i], static_cast<int32_t>(EventKind::SPIKE)};
                                    if (dest_owner == w) {
                                        my_queue.push(child);
                                    } else {
                                        mailboxes[w][dest_owner].push_back(child);
                                        cross_worker_events.fetch_add(1, std::memory_order_relaxed);
                                    }
                                }
                            }
                        }
                    }
                    auto t_act_end = std::chrono::high_resolution_clock::now();
                    worker_active_sec[w] += std::chrono::duration<double>(t_act_end - t_act_start).count();

                    auto t_b1_start = std::chrono::high_resolution_clock::now();
                    fallback_b1.arrive_and_wait();
                    auto t_b1_end = std::chrono::high_resolution_clock::now();
                    worker_barrier1_sec[w] += std::chrono::duration<double>(t_b1_end - t_b1_start).count();

                    auto t_mb_start = std::chrono::high_resolution_clock::now();
                    for (int32_t from_w = 0; from_w < W; ++from_w) {
                        if (from_w != w) {
                            auto& incoming = mailboxes[from_w][w];
                            for (const auto& ev : incoming) my_queue.push(ev);
                            incoming.clear();
                        }
                    }
                    auto t_mb_end = std::chrono::high_resolution_clock::now();
                    worker_mailbox_sec[w] += std::chrono::duration<double>(t_mb_end - t_mb_start).count();

                    auto t_b2_start = std::chrono::high_resolution_clock::now();
                    fallback_b2.arrive_and_wait();
                    auto t_b2_end = std::chrono::high_resolution_clock::now();
                    worker_barrier2_sec[w] += std::chrono::duration<double>(t_b2_end - t_b2_start).count();
                }
                worker_events[w] = my_processed;
                total_processed.fetch_add(my_processed, std::memory_order_relaxed);
            });
        }
        for (auto& t : fallback_threads) t.join();
        #endif

        auto t_end_sim = std::chrono::high_resolution_clock::now();
        state.advance_all_potentials(t_max);
        auto t_end_total = std::chrono::high_resolution_clock::now();

        double wall_sim_sec = std::chrono::duration<double>(t_end_sim - t_start_sim).count();
        double wall_total_sec = std::chrono::duration<double>(t_end_total - t_start_total).count();

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

        uint64_t max_ev = 0, sum_ev = 0;
        for (uint64_t ev : worker_events) {
            sum_ev += ev;
            if (ev > max_ev) max_ev = ev;
        }
        double mean_ev = (W > 0) ? (static_cast<double>(sum_ev) / W) : 1.0;
        double imbalance = (mean_ev > 0) ? (static_cast<double>(max_ev) / mean_ev) : 1.0;

        Exp4ProfilingStats stats;
        stats.scheduler_name = "cpp_openmp_epoch_W" + std::to_string(W) + "_R" + std::to_string(R);
        stats.num_workers = W;
        stats.num_regions = R;
        stats.wall_time_sim_sec = wall_sim_sec;
        stats.wall_time_total_sec = wall_total_sec;
        stats.total_events_processed = total_processed.load();
        stats.total_edges_traversed = total_edges.load();
        stats.total_spikes = all_spikes.size();
        stats.cross_region_events = cross_worker_events.load();
        stats.backlog_imbalance_ratio = imbalance;
        stats.peak_rss_bytes = get_actual_peak_rss_bytes();
        stats.state_digest = digest;
        stats.worker_active_sec = worker_active_sec;
        stats.worker_barrier1_sec = worker_barrier1_sec;
        stats.worker_mailbox_sec = worker_mailbox_sec;
        stats.worker_barrier2_sec = worker_barrier2_sec;
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
            out_sim_result->cross_region_events = stats.cross_region_events;
        }

        return stats;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    int32_t num_regions_;
    std::vector<int32_t> node_to_region_;
    std::vector<int32_t> region_owner_;
};

} // namespace sc
