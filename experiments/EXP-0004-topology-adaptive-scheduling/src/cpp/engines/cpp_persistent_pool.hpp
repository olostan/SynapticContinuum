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
#include <condition_variable>
#include <mutex>
#include <cmath>

namespace sc {

class Exp4PersistentPoolEngine {
public:
    explicit Exp4PersistentPoolEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        const std::vector<int32_t>& node_to_region = {}
    ) : config_(config),
        graph_(graph),
        num_workers_(std::max(1, num_workers)),
        num_regions_(std::max(num_workers_, num_regions)),
        node_to_region_(node_to_region),
        stop_workers_(false),
        epoch_barrier_(num_workers_ + 1), // Workers + Coordinator
        migration_barrier_(num_workers_ + 1),
        drain_barrier_(num_workers_ + 1)
    {
        if (node_to_region_.empty()) {
            node_to_region_.resize(config_.num_nodes);
            int32_t nodes_per_reg = (config_.num_nodes + num_regions_ - 1) / num_regions_;
            for (int32_t u = 0; u < config_.num_nodes; ++u) {
                int32_t r = u / nodes_per_reg;
                node_to_region_[u] = (r < num_regions_) ? r : (num_regions_ - 1);
            }
        }

        // Default region ownership: block distribution across workers
        region_owner_.resize(num_regions_);
        int32_t reg_per_w = (num_regions_ + num_workers_ - 1) / num_workers_;
        for (int32_t r = 0; r < num_regions_; ++r) {
            int32_t w = r / reg_per_w;
            region_owner_[r] = (w < num_workers_) ? w : (num_workers_ - 1);
        }

        start_persistent_workers();
    }

    ~Exp4PersistentPoolEngine() {
        stop_persistent_workers();
    }

    void set_region_ownership(const std::vector<int32_t>& region_owner) {
        if (region_owner.size() == static_cast<size_t>(num_regions_)) {
            region_owner_ = region_owner;
        }
    }

    const std::vector<int32_t>& get_region_ownership() const noexcept {
        return region_owner_;
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

        // Compute conservative lookahead
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
                throw std::invalid_argument(
                    "Exp4PersistentPoolEngine causality precondition violation: Cross-worker edge delay <= 0.0. "
                    "Rejecting graph per conservative PDES contract."
                );
            }
            epoch_delta = min_cross_delay;
        } else {
            epoch_delta = t_max + 1.0;
        }

        // Initialize per-worker queues
        worker_queues_.clear();
        worker_queues_.reserve(W);
        for (int32_t w = 0; w < W; ++w) {
            worker_queues_.emplace_back(std::max(size_t{16384}, external_events.size() * 2 / W + 1024));
        }

        uint64_t seq = 0;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                int32_t r = node_to_region_[ee.target];
                int32_t w = region_owner_[r];
                worker_queues_[w].push(Event{
                    ee.timestamp,
                    seq++,
                    ee.source,
                    ee.target,
                    ee.amplitude,
                    ee.kind
                });
            }
        }

        // Initialize cross-worker mailboxes: outgoing[from_w][to_w]
        mailboxes_.assign(W, std::vector<std::vector<Event>>(W));

        int64_t num_epochs = (epoch_delta > 0.0) ? static_cast<int64_t>(std::ceil(t_max / epoch_delta)) : 1;
        if (num_epochs <= 0) num_epochs = 1;
        current_num_epochs_ = num_epochs;

        // Shared simulation context
        current_state_ = std::make_unique<SubstrateStatePacked>(config_);
        current_t_max_ = t_max;
        current_epoch_delta_ = epoch_delta;
        total_processed_.store(0, std::memory_order_relaxed);
        total_edges_.store(0, std::memory_order_relaxed);
        cross_worker_events_.store(0, std::memory_order_relaxed);

        per_worker_spikes_.assign(W, {});
        worker_active_sec_.assign(W, 0.0);
        worker_barrier1_sec_.assign(W, 0.0);
        worker_mailbox_sec_.assign(W, 0.0);
        worker_barrier2_sec_.assign(W, 0.0);
        worker_events_.assign(W, 0);
        region_events_.assign(R, 0);

        // Notify persistent workers to begin
        auto t_start_sim = std::chrono::high_resolution_clock::now();

        {
            std::unique_lock<std::mutex> lock(job_mutex_);
            job_done_count_ = 0;
            current_job_id_++;
            job_cv_.notify_all();
        }

        // Coordinator loop: participate in epoch barriers
        for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
            double epoch_limit = (epoch + 1) * epoch_delta;

            // Wait for workers to finish epoch events
            epoch_barrier_.arrive_and_wait();

            // Coordinator migration phase: all workers are parked at migration_barrier_
            on_epoch_boundary(epoch_limit);

            // Release workers to proceed with mailbox draining
            migration_barrier_.arrive_and_wait();

            // Wait for workers to finish mailbox drain
            drain_barrier_.arrive_and_wait();
        }

        // Wait for workers to complete the simulation
        {
            std::unique_lock<std::mutex> lock(job_mutex_);
            done_cv_.wait(lock, [&]() { return job_done_count_ == W; });
        }

        auto t_end_sim = std::chrono::high_resolution_clock::now();

        current_state_->advance_all_potentials(t_max);
        auto t_end_total = std::chrono::high_resolution_clock::now();

        double wall_sim_sec = std::chrono::duration<double>(t_end_sim - t_start_sim).count();
        double wall_total_sec = std::chrono::duration<double>(t_end_total - t_start_total).count();
        double spawn_overhead_sec = wall_total_sec - wall_sim_sec;

        // Collect spikes and compute digest
        std::vector<SpikeRecord> all_spikes;
        for (auto& spks : per_worker_spikes_) {
            all_spikes.insert(all_spikes.end(), spks.begin(), spks.end());
        }
        std::sort(all_spikes.begin(), all_spikes.end(), [](const SpikeRecord& a, const SpikeRecord& b) {
            if (std::abs(a.timestamp - b.timestamp) > 1e-6) return a.timestamp < b.timestamp;
            return a.node < b.node;
        });

        std::vector<float> final_pots(current_state_->potentials, current_state_->potentials + N);
        uint64_t digest = compute_state_digest(all_spikes, final_pots);

        uint64_t max_ev = 0;
        uint64_t sum_ev = 0;
        for (uint64_t ev : worker_events_) {
            sum_ev += ev;
            if (ev > max_ev) max_ev = ev;
        }
        double mean_ev = (W > 0) ? (static_cast<double>(sum_ev) / W) : 1.0;
        double imbalance = (mean_ev > 0) ? (static_cast<double>(max_ev) / mean_ev) : 1.0;

        Exp4ProfilingStats stats;
        stats.scheduler_name = "cpp_persistent_pool_W" + std::to_string(W) + "_R" + std::to_string(R);
        stats.num_workers = W;
        stats.num_regions = R;
        stats.wall_time_sim_sec = wall_sim_sec;
        stats.wall_time_total_sec = wall_total_sec;
        stats.total_events_processed = total_processed_.load();
        stats.total_edges_traversed = total_edges_.load();
        stats.total_spikes = all_spikes.size();
        stats.cross_region_events = cross_worker_events_.load();
        stats.total_migrations = total_migrations_recorded_;
        stats.migration_pause_sec = migration_pause_recorded_sec_;
        stats.backlog_imbalance_ratio = imbalance;
        stats.peak_rss_bytes = get_actual_peak_rss_bytes();
        stats.state_digest = digest;
        stats.worker_active_sec = worker_active_sec_;
        stats.worker_barrier1_sec = worker_barrier1_sec_;
        stats.worker_mailbox_sec = worker_mailbox_sec_;
        stats.worker_barrier2_sec = worker_barrier2_sec_;
        stats.worker_events_processed = worker_events_;
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

protected:
    virtual void on_epoch_boundary(double current_epoch_limit) {
        (void)current_epoch_limit;
    }

    void start_persistent_workers() {
        worker_threads_.reserve(num_workers_);
        for (int32_t w = 0; w < num_workers_; ++w) {
            worker_threads_.emplace_back([this, w]() {
                worker_loop(w);
            });
        }
    }

    void stop_persistent_workers() {
        {
            std::unique_lock<std::mutex> lock(job_mutex_);
            stop_workers_ = true;
            job_cv_.notify_all();
        }
        for (auto& t : worker_threads_) {
            if (t.joinable()) t.join();
        }
        worker_threads_.clear();
    }

    void worker_loop(int32_t w) {
        const int32_t* targets = nullptr;
        const float* weights = nullptr;
        const float* delays = nullptr;
        uint32_t count = 0;

        uint64_t my_seq = static_cast<uint64_t>(w) << 48;
        uint64_t last_job_id = 0;

        while (true) {
            // Wait for new simulation job
            {
                std::unique_lock<std::mutex> lock(job_mutex_);
                job_cv_.wait(lock, [this, last_job_id]() {
                    return current_job_id_ > last_job_id || stop_workers_;
                });
                if (stop_workers_) return;
                last_job_id = current_job_id_;
            }

            double t_max = current_t_max_;
            double epoch_delta = current_epoch_delta_;
            int64_t num_epochs = current_num_epochs_;

            uint64_t my_processed = 0;
            auto& my_queue = worker_queues_[w];

            for (int64_t epoch = 0; epoch < num_epochs; ++epoch) {
                double epoch_limit = (epoch + 1) * epoch_delta;
                auto t_act_start = std::chrono::high_resolution_clock::now();

                while (!my_queue.empty()) {
                    if (my_queue.peek().timestamp >= epoch_limit) break;

                    Event ev = my_queue.pop();
                    my_processed++;
                    if (ev.timestamp > t_max) continue;

                    int32_t reg = node_to_region_[ev.target];
                    region_events_[reg]++;

                    bool fired = current_state_->receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
                    if (fired) {
                        per_worker_spikes_[w].push_back({ev.timestamp, ev.target});
                        graph_.get_outgoing(ev.target, targets, weights, delays, count);
                        total_edges_.fetch_add(count, std::memory_order_relaxed);

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
                                    // Intra-worker fast path: direct delivery into local queue!
                                    my_queue.push(child);
                                } else {
                                    // Inter-worker delivery via mailbox
                                    mailboxes_[w][dest_owner].push_back(child);
                                    cross_worker_events_.fetch_add(1, std::memory_order_relaxed);
                                }
                            }
                        }
                    }
                }

                auto t_act_end = std::chrono::high_resolution_clock::now();
                worker_active_sec_[w] += std::chrono::duration<double>(t_act_end - t_act_start).count();
                worker_events_[w] = my_processed;

                // Barrier 1: Arrive and wait for all workers + coordinator
                auto t_b1_start = std::chrono::high_resolution_clock::now();
                epoch_barrier_.arrive_and_wait();
                auto t_b1_end = std::chrono::high_resolution_clock::now();
                worker_barrier1_sec_[w] += std::chrono::duration<double>(t_b1_end - t_b1_start).count();

                // Barrier 1.5 (Migration Barrier): Park until coordinator finishes migration phase
                migration_barrier_.arrive_and_wait();

                // Mailbox transfer: pull incoming events from other workers
                auto t_mb_start = std::chrono::high_resolution_clock::now();
                for (int32_t from_w = 0; from_w < num_workers_; ++from_w) {
                    if (from_w != w) {
                        auto& incoming = mailboxes_[from_w][w];
                        for (const auto& ev : incoming) {
                            my_queue.push(ev);
                        }
                        incoming.clear();
                    }
                }
                auto t_mb_end = std::chrono::high_resolution_clock::now();
                worker_mailbox_sec_[w] += std::chrono::duration<double>(t_mb_end - t_mb_start).count();

                // Barrier 2: Arrive and wait for all workers + coordinator
                auto t_b2_start = std::chrono::high_resolution_clock::now();
                drain_barrier_.arrive_and_wait();
                auto t_b2_end = std::chrono::high_resolution_clock::now();
                worker_barrier2_sec_[w] += std::chrono::duration<double>(t_b2_end - t_b2_start).count();
            }

            worker_events_[w] = my_processed;
            total_processed_.fetch_add(my_processed, std::memory_order_relaxed);

            // Notify coordinator that worker is done
            {
                std::unique_lock<std::mutex> lock(job_mutex_);
                job_done_count_++;
                if (job_done_count_ == num_workers_) {
                    done_cv_.notify_one();
                }
            }
        }
    }

    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
    int32_t num_regions_;
    std::vector<int32_t> node_to_region_;
    std::vector<int32_t> region_owner_;

    std::vector<BinaryHeapQueue> worker_queues_;
    std::vector<std::vector<std::vector<Event>>> mailboxes_;

    std::unique_ptr<SubstrateStatePacked> current_state_;
    double current_t_max_ = 0.0;
    double current_epoch_delta_ = 0.0;
    int64_t current_num_epochs_ = 0;

    std::atomic<uint64_t> total_processed_{0};
    std::atomic<uint64_t> total_edges_{0};
    std::atomic<uint64_t> cross_worker_events_{0};

    std::vector<std::vector<SpikeRecord>> per_worker_spikes_;
    std::vector<double> worker_active_sec_;
    std::vector<double> worker_barrier1_sec_;
    std::vector<double> worker_mailbox_sec_;
    std::vector<double> worker_barrier2_sec_;
    std::vector<uint64_t> worker_events_;
    std::vector<uint64_t> region_events_;

    uint64_t total_migrations_recorded_ = 0;
    double migration_pause_recorded_sec_ = 0.0;

    // Thread pool synchronization
    std::vector<std::thread> worker_threads_;
    std::mutex job_mutex_;
    std::condition_variable job_cv_;
    std::condition_variable done_cv_;
    bool stop_workers_;
    uint64_t current_job_id_ = 0;
    int32_t job_done_count_ = 0;

    std::barrier<> epoch_barrier_;
    std::barrier<> migration_barrier_;
    std::barrier<> drain_barrier_;
};

} // namespace sc
