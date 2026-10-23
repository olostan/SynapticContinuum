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

        // Per-node mutexes to prevent concurrent updates to the same node
        // Sharded into 256 mutexes to minimize memory overhead
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
                        while (shared_queue.empty() && !done.load(std::memory_order_relaxed)) {
                            if (active_workers.load(std::memory_order_relaxed) == 0 && shared_queue.empty()) {
                                done.store(true, std::memory_order_release);
                                cv_work.notify_all();
                                return;
                            }
                            lock_waits.fetch_add(1, std::memory_order_relaxed);
                            cv_work.wait(lock);
                        }

                        if (done.load(std::memory_order_relaxed) || total_processed.load(std::memory_order_relaxed) >= max_events) {
                            return;
                        }

                        if (shared_queue.empty()) {
                            continue;
                        }

                        ev = shared_queue.pop();
                        active_workers.fetch_add(1, std::memory_order_relaxed);
                    }

                    if (ev.timestamp > t_max) {
                        active_workers.fetch_sub(1, std::memory_order_relaxed);
                        continue;
                    }

                    total_processed.fetch_add(1, std::memory_order_relaxed);

                    // Update node state under shard lock
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
                                    0, // seq_id assigned under queue_mutex
                                    ev.target,
                                    targets[i],
                                    weights[i],
                                    static_cast<int32_t>(EventKind::SPIKE)
                                });
                            }
                        }
                    }

                    {
                        std::unique_lock<std::mutex> lock(queue_mutex);
                        for (auto& child : local_children) {
                            child.seq_id = seq_counter++;
                            shared_queue.push(child);
                        }
                        active_workers.fetch_sub(1, std::memory_order_relaxed);
                        if (!local_children.empty()) {
                            cv_work.notify_all();
                        } else if (shared_queue.empty() && active_workers.load(std::memory_order_relaxed) == 0) {
                            done.store(true, std::memory_order_release);
                            cv_work.notify_all();
                        }
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
        res.rss_bytes = state.memory_bytes() + graph_.memory_bytes() + shared_queue.memory_bytes();

        return res;
    }

private:
    SubstrateConfig config_;
    NeuralGraphCSR graph_;
    int32_t num_workers_;
};

} // namespace sc
