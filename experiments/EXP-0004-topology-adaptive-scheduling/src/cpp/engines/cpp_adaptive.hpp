#pragma once

#include "cpp_persistent_pool.hpp"
#include <vector>
#include <numeric>
#include <chrono>
#include <iostream>

namespace sc {

class Exp4AdaptiveEngine : public Exp4PersistentPoolEngine {
public:
    explicit Exp4AdaptiveEngine(
        const SubstrateConfig& config,
        const NeuralGraphCSR& graph,
        int32_t num_workers,
        int32_t num_regions,
        const std::vector<int32_t>& node_to_region = {},
        double imbalance_threshold = 1.35,
        int32_t min_migration_interval_epochs = 2,
        double min_epoch_events = 10.0
    ) : Exp4PersistentPoolEngine(config, graph, num_workers, num_regions, node_to_region),
        imbalance_threshold_(imbalance_threshold),
        min_migration_interval_epochs_(min_migration_interval_epochs),
        min_epoch_events_(min_epoch_events),
        epoch_counter_(0)
    {
        last_worker_events_.assign(num_workers_, 0);
    }

    Exp4ProfilingStats run_adaptive(
        const std::vector<ExternalEvent>& external_events,
        double t_max,
        SimulationResult* out_sim_result = nullptr
    ) {
        epoch_counter_ = 0;
        total_migrations_recorded_ = 0;
        migration_pause_recorded_sec_ = 0.0;
        last_worker_events_.assign(num_workers_, 0);

        auto stats = run(external_events, t_max, out_sim_result);
        stats.scheduler_name = "cpp_adaptive_W" + std::to_string(num_workers_) + "_R" + std::to_string(num_regions_);
        stats.total_migrations = total_migrations_recorded_;
        stats.migration_pause_sec = migration_pause_recorded_sec_;
        return stats;
    }

protected:
    void on_epoch_boundary(double current_epoch_limit) override {
        (void)current_epoch_limit;
        epoch_counter_++;

        if (epoch_counter_ % min_migration_interval_epochs_ != 0 || num_workers_ <= 1 || num_regions_ <= num_workers_) {
            return;
        }

        auto t_mig_start = std::chrono::high_resolution_clock::now();

        // Calculate worker events during this epoch window
        std::vector<uint64_t> epoch_w_events(num_workers_);
        uint64_t max_ev = 0, min_ev = std::numeric_limits<uint64_t>::max(), sum_ev = 0;
        int32_t w_heavy = 0, w_light = 0;

        for (int32_t w = 0; w < num_workers_; ++w) {
            uint64_t curr = worker_events_[w];
            uint64_t delta = (curr >= last_worker_events_[w]) ? (curr - last_worker_events_[w]) : 0;
            epoch_w_events[w] = delta;
            last_worker_events_[w] = curr;
            sum_ev += delta;

            if (delta > max_ev) {
                max_ev = delta;
                w_heavy = w;
            }
            if (delta < min_ev) {
                min_ev = delta;
                w_light = w;
            }
        }

        double mean_ev = static_cast<double>(sum_ev) / num_workers_;
        // std::cout << "DEBUG: epoch " << epoch_counter_ << " sum_ev=" << sum_ev << " mean=" << mean_ev << " heavy=" << w_heavy << "(" << max_ev << ") light=" << w_light << "(" << min_ev << ")" << std::endl;
        if (mean_ev >= min_epoch_events_ && w_heavy != w_light) {
            double imbalance = static_cast<double>(max_ev) / mean_ev;
            if (imbalance >= imbalance_threshold_) {
                // Find a region in w_heavy to migrate to w_light
                int32_t candidate_r = -1;
                size_t heavy_count = 0;
                for (int32_t r = 0; r < num_regions_; ++r) {
                    if (region_owner_[r] == w_heavy) {
                        heavy_count++;
                        if (candidate_r == -1) candidate_r = r;
                    }
                }

                if (heavy_count >= 2 && candidate_r != -1) {
                    // Migrate candidate_r from w_heavy to w_light:
                    // 1. Move local queue events belonging to candidate_r from w_heavy to w_light
                    auto& q_heavy = worker_queues_[w_heavy];
                    auto& q_light = worker_queues_[w_light];

                    std::vector<Event> retained;
                    retained.reserve(q_heavy.size());

                    while (!q_heavy.empty()) {
                        Event ev = q_heavy.pop();
                        int32_t reg = node_to_region_[ev.target];
                        if (reg == candidate_r) {
                            q_light.push(ev);
                        } else {
                            retained.push_back(ev);
                        }
                    }

                    for (const auto& ev : retained) {
                        q_heavy.push(ev);
                    }

                    // 2. Safely transfer in-flight mailbox events destined for candidate_r
                    for (int32_t u = 0; u < num_workers_; ++u) {
                        if (u == w_heavy) continue;
                        auto& mb = mailboxes_[u][w_heavy];
                        std::vector<Event> retained_mb;
                        retained_mb.reserve(mb.size());

                        for (const auto& ev : mb) {
                            int32_t reg = node_to_region_[ev.target];
                            if (reg == candidate_r) {
                                if (u == w_light) {
                                    // Origin was w_light, destination is now also w_light
                                    q_light.push(ev);
                                } else {
                                    // Move to w_light's incoming mailbox from u
                                    mailboxes_[u][w_light].push_back(ev);
                                }
                            } else {
                                retained_mb.push_back(ev);
                            }
                        }
                        mb = std::move(retained_mb);
                    }

                    // 3. Atomically switch ownership
                    region_owner_[candidate_r] = w_light;
                    total_migrations_recorded_++;
                }
            }
        }

        auto t_mig_end = std::chrono::high_resolution_clock::now();
        migration_pause_recorded_sec_ += std::chrono::duration<double>(t_mig_end - t_mig_start).count();
    }

private:
    double imbalance_threshold_;
    int32_t min_migration_interval_epochs_;
    double min_epoch_events_;
    int32_t epoch_counter_;
    std::vector<uint64_t> last_worker_events_;
};

} // namespace sc
