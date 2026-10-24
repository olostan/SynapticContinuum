#pragma once

#include "../core/types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/state.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/queues/binary_heap.hpp"
#include "cpp_serial.hpp"
#include <vector>
#include <thread>
#include <atomic>
#include <barrier>
#include <chrono>
#include <algorithm>
#include <stdexcept>
#include <cmath>

namespace sc {

struct RelaxedCausalDivergence {
    double epsilon = 0.0;
    double wall_time_sec = 0.0;
    uint64_t total_events = 0;
    uint64_t total_spikes = 0;
    uint64_t exact_spike_matches = 0;
    uint64_t backward_time_events = 0;
    uint64_t out_of_order_worker_events = 0;
    int64_t spike_count_error = 0;
    double spike_timestamp_rmse = 0.0;
    double potential_rmse = 0.0;
    uint64_t state_digest = 0;
    uint64_t reference_digest = 0;
    int32_t temporal_discrimination_trials = 0;
    int32_t temporal_discrimination_correct = 0;
    double temporal_discrimination_accuracy = 1.0;
    double temporal_discrimination_chance_baseline = 0.5;
    bool temporal_discrimination_passed = true;
};

/**
 * Exp4RelaxedEngine
 * 
 * Implements bounded temporal order relaxation (Hypothesis H5).
 * Synchronization epoch window is expanded: Delta_t = d_min_cross + epsilon.
 * 
 * Tracks exact causal violation counters:
 * - backward_time_events: events arriving at a target neuron with timestamp < target's last_update_time
 * - out_of_order_worker_events: events popped by a worker with timestamp < worker's previously processed timestamp
 * - exact_spike_matches: count of spikes matching the serial reference (node, timestamp within 1e-6)
 */
class Exp4RelaxedEngine {
public:
    explicit Exp4RelaxedEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        double epsilon
    ) : Exp4RelaxedEngine(config, graph, num_workers, num_regions, {}, epsilon) {}

    explicit Exp4RelaxedEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        const std::vector<int32_t>& node_to_region = {},
        double epsilon = 0.0
    ) : config_(config),
        graph_(graph),
        num_workers_(std::max(1, num_workers)),
        num_regions_(std::max(num_workers_, num_regions)),
        node_to_region_(node_to_region),
        epsilon_(std::max(0.0, epsilon))
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

    uint64_t get_last_backward_time_events() const noexcept { return last_backward_time_events_; }
    uint64_t get_last_out_of_order_worker_events() const noexcept { return last_out_of_order_worker_events_; }

    Exp4ProfilingStats run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        SimulationResult* out_sim_result = nullptr
    ) {
        auto t_start_total = std::chrono::high_resolution_clock::now();

        int32_t N = config_.num_nodes;
        int32_t W = num_workers_;

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

        double base_delta = config_.min_delay;
        if (has_cross_edges) {
            if (min_cross_delay <= 0.0) {
                base_delta = config_.min_delay;
            } else {
                base_delta = min_cross_delay;
            }
        } else {
            base_delta = t_max + 1.0;
        }

        // Apply relaxation slack epsilon to the epoch window
        double epoch_delta = base_delta + epsilon_;

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
        std::atomic<uint64_t> backward_time_events{0};
        std::atomic<uint64_t> out_of_order_worker_events{0};

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(W);
        std::vector<double> worker_active_sec(W, 0.0);
        std::vector<double> worker_barrier1_sec(W, 0.0);
        std::vector<double> worker_mailbox_sec(W, 0.0);
        std::vector<double> worker_barrier2_sec(W, 0.0);
        std::vector<uint64_t> worker_events(W, 0);

        std::barrier<> epoch_barrier(W);
        std::barrier<> drain_barrier(W);

        auto t_start_sim = std::chrono::high_resolution_clock::now();

        std::vector<std::thread> threads;
        threads.reserve(W);

        for (int32_t w = 0; w < W; ++w) {
            threads.emplace_back([&, w]() {
                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;
                uint64_t my_seq = static_cast<uint64_t>(w) << 48;
                uint64_t my_processed = 0;
                uint64_t my_backward = 0;
                uint64_t my_ooo = 0;
                double last_worker_ts = -1.0;
                auto& my_queue = worker_queues[w];

                for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
                    double epoch_limit = (epoch + 1) * epoch_delta;
                    auto t_act_start = std::chrono::high_resolution_clock::now();

                    while (!my_queue.empty()) {
                        if (my_queue.peek().timestamp >= epoch_limit) break;

                        Event ev = my_queue.pop();
                        my_processed++;
                        if (ev.timestamp > t_max) continue;

                        if (ev.timestamp + 1e-12 < last_worker_ts) {
                            my_ooo++;
                        } else {
                            last_worker_ts = ev.timestamp;
                        }

                        if (ev.timestamp + 1e-12 < state.last_update_times[ev.target]) {
                            my_backward++;
                        }

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
                    epoch_barrier.arrive_and_wait();
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
                    drain_barrier.arrive_and_wait();
                    auto t_b2_end = std::chrono::high_resolution_clock::now();
                    worker_barrier2_sec[w] += std::chrono::duration<double>(t_b2_end - t_b2_start).count();
                }

                worker_events[w] = my_processed;
                total_processed.fetch_add(my_processed, std::memory_order_relaxed);
                backward_time_events.fetch_add(my_backward, std::memory_order_relaxed);
                out_of_order_worker_events.fetch_add(my_ooo, std::memory_order_relaxed);
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

        last_backward_time_events_ = backward_time_events.load();
        last_out_of_order_worker_events_ = out_of_order_worker_events.load();

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
        stats.scheduler_name = "cpp_relaxed_eps" + std::to_string(epsilon_) + "_W" + std::to_string(W);
        stats.num_workers = W;
        stats.num_regions = num_regions_;
        stats.wall_time_sim_sec = wall_sim_sec;
        stats.wall_time_total_sec = wall_total_sec;
        stats.total_events_processed = total_processed.load();
        stats.total_edges_traversed = total_edges.load();
        stats.total_spikes = all_spikes.size();
        stats.cross_region_events = cross_worker_events.load();
        stats.total_migrations = 0;
        stats.migration_pause_sec = 0.0;
        stats.backlog_imbalance_ratio = 1.0;
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

    /**
     * Multi-trial Temporal Order Discrimination Benchmark (50% chance baseline)
     * 
     * Tests `num_trials` (default 100) independent 3-neuron coincidence/order-detector motifs
     * distributed across workers:
     *   - Pre-synaptic Inhibitory neuron A_i (on worker 0) -> Target C_i (on worker 1) with delay 0.20 ms, weight -1.20
     *   - Pre-synaptic Excitatory neuron B_i (on worker 1) -> Target C_i (on worker 1) with delay 0.20 ms, weight +0.95 (threshold = 1.0, initial B_i has local warm bias +0.15)
     * 
     * In Class 0 (50% of trials): Excitation arrives BEFORE inhibition -> C_i MUST fire (1 spike).
     * In Class 1 (50% of trials): Inhibition arrives BEFORE excitation -> shunts C_i -> C_i MUST NOT fire (0 spikes).
     * However, when epsilon >= 0.25 ms, worker 1 processes its local excitatory events up to base_delta + epsilon
     * BEFORE receiving the cross-worker inhibitory spike from worker 0 at the barrier!
     * Consequently, Class 1 trials falsely fire before the inhibitory pulse arrives, driving classification accuracy
     * down toward the 50% random-guessing baseline.
     */
    static void evaluate_temporal_order_discrimination(
        double epsilon,
        int32_t num_trials,
        int32_t& out_correct,
        double& out_accuracy
    ) {
        if (num_trials <= 0) num_trials = 100;
        int32_t N = num_trials * 3;
        SubstrateConfig cfg;
        cfg.num_nodes = N;
        cfg.tau_m = 10.0f;
        cfg.threshold = 1.0f;
        cfg.v_reset = 0.0f;
        cfg.refractory_period = 2.0f;
        cfg.min_delay = 0.20f;
        cfg.max_delay = 1.0f;

        // Partition: For each trial i, node 3*i (A_i, inhibitory source) is in region 0 (worker 0).
        // Nodes 3*i + 1 (B_i, excitatory source) and 3*i + 2 (C_i, detector) are in region 1 (worker 1).
        std::vector<int32_t> part(N, 0);
        NeuralGraphCSR g;
        g.num_nodes = N;
        g.row_ptr.resize(N + 1, 0);

        uint64_t offset = 0;
        for (int32_t i = 0; i < num_trials; ++i) {
            int32_t a = 3 * i;
            int32_t b = 3 * i + 1;
            int32_t c = 3 * i + 2;
            part[a] = 0;
            part[b] = 1;
            part[c] = 1;

            // A_i -> C_i (inhibitory, cross-worker edge with delay 0.20 ms)
            g.row_ptr[a] = offset;
            g.targets.push_back(c);
            g.weights.push_back(-1.50f);
            g.delays.push_back(0.20f);
            offset++;

            // B_i -> C_i (excitatory, intra-worker edge on worker 1 with delay 0.20 ms)
            g.row_ptr[b] = offset;
            g.targets.push_back(c);
            g.weights.push_back(1.15f);
            g.delays.push_back(0.20f);
            offset++;

            // C_i has no outgoing edges
            g.row_ptr[c] = offset;
        }
        g.row_ptr[N] = offset;
        g.num_edges = offset;

        std::vector<ExternalEvent> inputs;
        for (int32_t i = 0; i < num_trials; ++i) {
            int32_t a = 3 * i;
            int32_t b = 3 * i + 1;
            double t_base = (i / 10) * 0.01; // stagger slightly within the first epoch
            if (i % 2 == 0) {
                // Class 0: Excitatory B_i stimulated at t=0.05, Inhibitory A_i at t=0.18
                // B_i->C_i arrives at 0.25, A_i->C_i arrives at 0.38 -> C_i fires at 0.25!
                inputs.push_back({t_base + 0.05, b, 1.50f});
                inputs.push_back({t_base + 0.18, a, 1.50f});
            } else {
                // Class 1: Inhibitory A_i stimulated at t=0.02, Excitatory B_i at t=0.12
                // Exact causal order: A_i->C_i arrives at 0.22 (inhibits C_i to -1.50),
                // B_i->C_i arrives at 0.32 (brings C_i to ~ -0.32 < 1.0) -> C_i MUST NOT fire!
                // Under relaxed eps >= 0.20, worker 1 advances to >= 0.40 before receiving A_i->C_i from worker 0,
                // so B_i->C_i is processed at 0.32 without prior inhibition -> C_i FALSELY FIRES!
                inputs.push_back({t_base + 0.02, a, 1.50f});
                inputs.push_back({t_base + 0.12, b, 1.50f});
            }
        }

        // Run ground-truth serial engine
        Exp4SerialEngine serial_eng(cfg, g);
        SimulationResult serial_res = serial_eng.run(inputs, 1.0);

        // Run relaxed engine with W=2, R=2
        Exp4RelaxedEngine rel_eng(cfg, g, 2, 2, part, epsilon);
        SimulationResult rel_res;
        rel_eng.run(inputs, 1.0, &rel_res);

        std::vector<int32_t> serial_c_fired(num_trials, 0);
        for (const auto& sp : serial_res.spike_records) {
            if (sp.node % 3 == 2) {
                serial_c_fired[sp.node / 3] = 1;
            }
        }

        std::vector<int32_t> rel_c_fired(num_trials, 0);
        for (const auto& sp : rel_res.spike_records) {
            if (sp.node % 3 == 2) {
                rel_c_fired[sp.node / 3] = 1;
            }
        }

        out_correct = 0;
        for (int32_t i = 0; i < num_trials; ++i) {
            int32_t expected = (i % 2 == 0) ? 1 : 0;
            if (rel_c_fired[i] == expected && serial_c_fired[i] == expected) {
                out_correct++;
            }
        }
        out_accuracy = static_cast<double>(out_correct) / static_cast<double>(num_trials);
    }

    RelaxedCausalDivergence evaluate_divergence_vs_reference(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        const SimulationResult& reference_serial_result,
        int32_t discrimination_trials = 100
    ) {
        SimulationResult relaxed_result;
        run(external_events, t_max, &relaxed_result);

        RelaxedCausalDivergence div;
        div.epsilon = epsilon_;
        div.wall_time_sec = relaxed_result.wall_time_sec;
        div.total_events = relaxed_result.total_events_processed;
        div.total_spikes = relaxed_result.total_spikes;
        div.backward_time_events = last_backward_time_events_;
        div.out_of_order_worker_events = last_out_of_order_worker_events_;
        div.state_digest = relaxed_result.state_digest;
        div.reference_digest = reference_serial_result.state_digest;
        div.spike_count_error = static_cast<int64_t>(relaxed_result.total_spikes) -
                                static_cast<int64_t>(reference_serial_result.total_spikes);

        double sum_pot_sq = 0.0;
        int32_t N = config_.num_nodes;
        for (int32_t u = 0; u < N; ++u) {
            double diff = relaxed_result.final_potentials[u] - reference_serial_result.final_potentials[u];
            sum_pot_sq += diff * diff;
        }
        div.potential_rmse = std::sqrt(sum_pot_sq / N);

        // Count exact spike matches (same node and timestamp within 1e-6)
        uint64_t exact_matches = 0;
        size_t i = 0, j = 0;
        const auto& s_rel = relaxed_result.spike_records;
        const auto& s_ref = reference_serial_result.spike_records;
        while (i < s_rel.size() && j < s_ref.size()) {
            if (std::abs(s_rel[i].timestamp - s_ref[j].timestamp) <= 1e-6) {
                if (s_rel[i].node == s_ref[j].node) {
                    exact_matches++;
                    i++;
                    j++;
                } else if (s_rel[i].node < s_ref[j].node) {
                    i++;
                } else {
                    j++;
                }
            } else if (s_rel[i].timestamp < s_ref[j].timestamp) {
                i++;
            } else {
                j++;
            }
        }
        div.exact_spike_matches = exact_matches;

        size_t match_count = std::min(relaxed_result.spike_records.size(), reference_serial_result.spike_records.size());
        double sum_t_sq = 0.0;
        for (size_t k = 0; k < match_count; ++k) {
            double diff = relaxed_result.spike_records[k].timestamp - reference_serial_result.spike_records[k].timestamp;
            sum_t_sq += diff * diff;
        }
        div.spike_timestamp_rmse = (match_count > 0) ? std::sqrt(sum_t_sq / match_count) : 0.0;

        div.temporal_discrimination_trials = discrimination_trials;
        evaluate_temporal_order_discrimination(
            epsilon_,
            discrimination_trials,
            div.temporal_discrimination_correct,
            div.temporal_discrimination_accuracy
        );
        div.temporal_discrimination_chance_baseline = 0.50;
        div.temporal_discrimination_passed = (
            div.state_digest == div.reference_digest &&
            div.backward_time_events == 0 &&
            div.temporal_discrimination_accuracy >= 0.99
        );

        return div;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    int32_t num_regions_;
    std::vector<int32_t> node_to_region_;
    std::vector<int32_t> region_owner_;
    double epsilon_;
    uint64_t last_backward_time_events_ = 0;
    uint64_t last_out_of_order_worker_events_ = 0;
};

} // namespace sc
