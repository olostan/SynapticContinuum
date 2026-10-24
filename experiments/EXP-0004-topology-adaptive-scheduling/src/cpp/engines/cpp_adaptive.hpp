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
        int32_t min_migration_interval_epochs = 2
    ) : Exp4PersistentPoolEngine(config, graph, num_workers, num_regions, node_to_region),
        imbalance_threshold_(imbalance_threshold),
        min_migration_interval_epochs_(min_migration_interval_epochs),
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
        if (mean_ev > 50.0 && w_heavy != w_light) {
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
                    // Extract events belonging to candidate_r from w_heavy and push to w_light
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
    int32_t epoch_counter_;
    std::vector<uint64_t> last_worker_events_;
};

} // namespace sc
