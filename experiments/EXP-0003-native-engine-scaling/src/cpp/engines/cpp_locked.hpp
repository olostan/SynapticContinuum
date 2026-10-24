#pragma once

#include "../core/types.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../queues/binary_heap.hpp"
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <chrono>
#include <limits>
#include <algorithm>

namespace sc {

class CppLockedEngine {
public:
    explicit CppLockedEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers = 4
    ) : config_(config), graph_(graph), num_workers_(std::max(1, num_workers)) {}

    SimulationResult run(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        uint64_t max_events = 10000000ULL
    ) {
        auto start_wall = std::chrono::high_resolution_clock::now();
        SubstrateStatePacked state(config_);

        BinaryHeapQueue shared_queue(std::max(size_t{65536}, external_events.size() * 2));
        std::mutex queue_mutex;
        std::condition_variable cv_work;

        uint64_t seq_counter = 0;
        for (const auto& ee : external_events) {
            if (ee.timestamp <= t_max) {
                shared_queue.push(Event{
                    ee.timestamp,
                    seq_counter++,
                    ee.source,
                    ee.target,
                    ee.amplitude,
                    ee.kind
                });
            }
        }

        // Determine conservative minimum edge delay in the graph
        double min_graph_delay = config_.min_delay;
        for (size_t i = 0; i < graph_.delays.size(); ++i) {
            if (graph_.delays[i] < min_graph_delay) {
                min_graph_delay = graph_.delays[i];
            }
        }
        if (min_graph_delay <= 0.0) min_graph_delay = 0.001; // Conservative positive lower bound

        // Track in-flight timestamps per worker for conservative safe horizon
        std::vector<double> in_flight_t(num_workers_, std::numeric_limits<double>::infinity());
        std::vector<int32_t> in_flight_target(num_workers_, -1);

        // Per-node lock to guarantee serialized state updates
        constexpr size_t NUM_SHARDS = 256;
        std::vector<std::mutex> node_locks(NUM_SHARDS);

        std::atomic<uint64_t> total_processed{0};
        std::atomic<uint64_t> total_edges{0};
        std::atomic<uint64_t> lock_waits{0};
        std::atomic<bool> done{false};
        std::atomic<int32_t> active_workers{0};

        std::vector<std::vector<SpikeRecord>> per_worker_spikes(num_workers_);
        std::vector<std::thread> workers;
        workers.reserve(num_workers_);

        auto compute_safe_horizon = [&]() -> double {
            double min_inflight = std::numeric_limits<double>::infinity();
            for (int32_t w = 0; w < num_workers_; ++w) {
                if (in_flight_t[w] < min_inflight) {
                    min_inflight = in_flight_t[w];
                }
            }
            if (min_inflight == std::numeric_limits<double>::infinity()) {
                return std::numeric_limits<double>::infinity();
            }
            return min_inflight + min_graph_delay;
        };

        for (int32_t w = 0; w < num_workers_; ++w) {
            workers.emplace_back([&, w]() {
                std::vector<Event> local_children;
                local_children.reserve(64);

                const int32_t* targets = nullptr;
                const float* weights = nullptr;
                const float* delays = nullptr;
                uint32_t count = 0;

                while (true) {
                    Event ev;
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex);
                        while (true) {
                            if (done.load(std::memory_order_relaxed)) {
                                return;
                            }

                            if (shared_queue.empty()) {
                                if (active_workers.load(std::memory_order_relaxed) == 0) {
                                    done.store(true, std::memory_order_release);
                                    cv_work.notify_all();
                                    return;
                                }
                                lock_waits.fetch_add(1, std::memory_order_relaxed);
                                cv_work.wait(lock);
                                continue;
                            }

                            // Causally sound safe horizon check:
                            // An event with timestamp t can only be popped if t <= min(in_flight) + min_delay,
                            // AND no in-flight worker is currently updating the same target node!
                            double safe_horizon = compute_safe_horizon();
                            const Event& peek_ev = shared_queue.peek();

                            if (peek_ev.timestamp > safe_horizon) {
                                // Must wait for earlier in-flight workers to commit their events
                                lock_waits.fetch_add(1, std::memory_order_relaxed);
                                cv_work.wait(lock);
                                continue;
                            }

                            // Check node conflict with currently in-flight workers
                            bool node_busy = false;
                            for (int32_t other = 0; other < num_workers_; ++other) {
                                if (other != w && in_flight_target[other] == peek_ev.target) {
                                    node_busy = true;
                                    break;
                                }
                            }
                            if (node_busy) {
                                lock_waits.fetch_add(1, std::memory_order_relaxed);
                                cv_work.wait(lock);
                                continue;
                            }

                            // Safe to pop!
                            ev = shared_queue.pop();
                            in_flight_t[w] = ev.timestamp;
                            in_flight_target[w] = ev.target;
                            active_workers.fetch_add(1, std::memory_order_relaxed);
                            break;
                        }
                    }

                    if (ev.timestamp > t_max) {
                        std::unique_lock<std::mutex> lock(queue_mutex);
                        in_flight_t[w] = std::numeric_limits<double>::infinity();
                        in_flight_target[w] = -1;
                        active_workers.fetch_sub(1, std::memory_order_relaxed);
                        cv_work.notify_all();
                        continue;
                    }

                    if (total_processed.fetch_add(1, std::memory_order_relaxed) >= max_events) {
                        std::unique_lock<std::mutex> lock(queue_mutex);
                        done.store(true, std::memory_order_release);
                        in_flight_t[w] = std::numeric_limits<double>::infinity();
                        in_flight_target[w] = -1;
                        active_workers.fetch_sub(1, std::memory_order_relaxed);
                        cv_work.notify_all();
                        return;
                    }

                    // Process impulse under shard lock
                    bool fired = false;
                    {
                        size_t shard = static_cast<size_t>(ev.target) % NUM_SHARDS;
                        std::lock_guard<std::mutex> nlock(node_locks[shard]);
                        fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
                    }

                    local_children.clear();
                    if (fired) {
                        per_worker_spikes[w].push_back({ev.timestamp, ev.target});

                        graph_.get_outgoing(ev.target, targets, weights, delays, count);
                        total_edges.fetch_add(count, std::memory_order_relaxed);

                        for (uint32_t i = 0; i < count; ++i) {
                            double arrival_t = ev.timestamp + static_cast<double>(delays[i]);
                            if (arrival_t <= t_max) {
                                local_children.push_back(Event{
                                    arrival_t,
                                    0, // assigned under lock
                                    ev.target,
                                    targets[i],
                                    weights[i],
                                    static_cast<int32_t>(EventKind::SPIKE)
                                });
                            }
                        }
                    }

                    // Commit child events and release in-flight status
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex);
                        for (auto& child : local_children) {
                            child.seq_id = seq_counter++;
                            shared_queue.push(child);
                        }
                        in_flight_t[w] = std::numeric_limits<double>::infinity();
                        in_flight_target[w] = -1;
                        active_workers.fetch_sub(1, std::memory_order_relaxed);
                        cv_work.notify_all();
                    }
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
        res.scheduler_name = "cpp_locked_workers_" + std::to_string(num_workers_);
        res.wall_time_sec = diff.count();
        res.total_events_processed = total_processed.load();
        res.total_edges_traversed = total_edges.load();
        res.total_spikes = state.total_spikes;
        res.peak_queue_size = shared_queue.peak_size();
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
        res.lock_waits = lock_waits.load();
        res.rss_bytes = get_actual_peak_rss_bytes();
        res.estimated_memory_bytes = state.memory_bytes() + graph_.memory_bytes() + shared_queue.memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
};

} // namespace sc
