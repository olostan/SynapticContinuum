#pragma once

#include "types.hpp"
#include <vector>
#include <cmath>
#include <memory>
#include <algorithm>

namespace sc {

class ExponentialTraceBankNative {
public:
    ExponentialTraceBankNative(int32_t num_nodes, int32_t num_bases, float tau_min = 1.0f, float tau_max = 50.0f)
        : num_nodes_(num_nodes), num_bases_(num_bases) {
        if (num_bases_ > 0) {
            taus_.resize(num_bases_);
            if (num_bases_ == 1) {
                taus_[0] = tau_min;
            } else {
                for (int32_t b = 0; b < num_bases_; ++b) {
                    float t = static_cast<float>(b) / static_cast<float>(num_bases_ - 1);
                    taus_[b] = tau_min * std::pow(tau_max / tau_min, t);
                }
            }
            values_.resize(static_cast<size_t>(num_nodes_) * num_bases_, 0.0f);
            last_times_.resize(num_nodes_, 0.0);
        }
    }

    void advance_and_add(int32_t node, double current_time, float amplitude) {
        if (num_bases_ == 0) return;
        double dt = current_time - last_times_[node];
        size_t offset = static_cast<size_t>(node) * num_bases_;
        if (dt > 0.0) {
            for (int32_t b = 0; b < num_bases_; ++b) {
                values_[offset + b] *= std::exp(static_cast<float>(-dt / taus_[b]));
            }
        }
        for (int32_t b = 0; b < num_bases_; ++b) {
            values_[offset + b] += amplitude;
        }
        last_times_[node] = current_time;
    }

    size_t memory_bytes() const noexcept {
        return taus_.size() * sizeof(float) +
               values_.size() * sizeof(float) +
               last_times_.size() * sizeof(double);
    }

private:
    int32_t num_nodes_;
    int32_t num_bases_;
    std::vector<float> taus_;
    std::vector<float> values_;
    std::vector<double> last_times_;
};

class BoundedEventHistoryNative {
public:
    BoundedEventHistoryNative(int32_t num_nodes, int32_t capacity_L)
        : num_nodes_(num_nodes), capacity_L_(capacity_L) {
        if (capacity_L_ > 0) {
            size_t total = static_cast<size_t>(num_nodes_) * capacity_L_;
            timestamps_.resize(total, 0.0f);
            amplitudes_.resize(total, 0.0f);
            kinds_.resize(total, 0);
            heads_.resize(num_nodes_, 0);
            counts_.resize(num_nodes_, 0);
        }
    }

    void record_event(int32_t node, double current_time, float amplitude, int32_t kind) {
        if (capacity_L_ == 0) return;
        size_t head = heads_[node];
        size_t idx = static_cast<size_t>(node) * capacity_L_ + head;
        timestamps_[idx] = static_cast<float>(current_time);
        amplitudes_[idx] = amplitude;
        kinds_[idx] = static_cast<int8_t>(kind);
        heads_[node] = static_cast<int32_t>((head + 1) % capacity_L_);
        if (counts_[node] < capacity_L_) counts_[node]++;
    }

    size_t memory_bytes() const noexcept {
        return timestamps_.size() * sizeof(float) +
               amplitudes_.size() * sizeof(float) +
               kinds_.size() * sizeof(int8_t) +
               heads_.size() * sizeof(int32_t) +
               counts_.size() * sizeof(int32_t);
    }

private:
    int32_t num_nodes_;
    int32_t capacity_L_;
    std::vector<float> timestamps_;
    std::vector<float> amplitudes_;
    std::vector<int8_t> kinds_;
    std::vector<int32_t> heads_;
    std::vector<int32_t> counts_;
};

class SubstrateStateLiteral {
public:
    SubstrateConfig config;
    int32_t num_nodes;
    std::vector<float> potentials;
    std::vector<double> last_update_times;
    std::vector<double> refractory_until;
    std::vector<int32_t> spike_counts;
    uint64_t total_spikes = 0;

    std::unique_ptr<ExponentialTraceBankNative> trace_bank;
    std::unique_ptr<BoundedEventHistoryNative> history_buffer;

    explicit SubstrateStateLiteral(const SubstrateConfig& cfg)
        : config(cfg),
          num_nodes(cfg.num_nodes),
          potentials(cfg.num_nodes, 0.0f),
          last_update_times(cfg.num_nodes, 0.0),
          refractory_until(cfg.num_nodes, -1e9),
          spike_counts(cfg.num_nodes, 0) {
        if (cfg.trace_bases_B > 0) {
            trace_bank = std::make_unique<ExponentialTraceBankNative>(num_nodes, cfg.trace_bases_B);
        }
        if (cfg.history_capacity_L > 0) {
            history_buffer = std::make_unique<BoundedEventHistoryNative>(num_nodes, cfg.history_capacity_L);
        }
    }

    inline void advance_node_potential(int32_t node, double current_time) noexcept {
        double dt = current_time - last_update_times[node];
        if (dt > 0.0) {
            potentials[node] *= std::exp(static_cast<float>(-dt / config.tau_m));
            last_update_times[node] = current_time;
        }
    }

    void advance_all_potentials(double current_time) noexcept {
        for (int32_t i = 0; i < num_nodes; ++i) {
            advance_node_potential(i, current_time);
        }
    }

    inline bool receive_impulse(int32_t node, double current_time, float amplitude, int32_t kind = 1) noexcept {
        advance_node_potential(node, current_time);

        if (trace_bank) trace_bank->advance_and_add(node, current_time, amplitude);
        if (history_buffer) history_buffer->record_event(node, current_time, amplitude, kind);

        if (current_time < refractory_until[node]) {
            potentials[node] = config.v_reset;
            return false;
        }

        potentials[node] += amplitude;

        if (potentials[node] >= config.threshold) {
            potentials[node] = config.v_reset;
            refractory_until[node] = current_time + config.refractory_period;
            spike_counts[node]++;
            total_spikes++;
            return true;
        }
        return false;
    }

    size_t memory_bytes() const noexcept {
        size_t b = potentials.size() * sizeof(float) +
                   last_update_times.size() * sizeof(double) +
                   refractory_until.size() * sizeof(double) +
                   spike_counts.size() * sizeof(int32_t);
        if (trace_bank) b += trace_bank->memory_bytes();
        if (history_buffer) b += history_buffer->memory_bytes();
        return b;
    }
};

class SubstrateStatePacked {
public:
    SubstrateConfig config;
    int32_t num_nodes;
    float* potentials = nullptr;
    double* last_update_times = nullptr;
    double* refractory_until = nullptr;
    int32_t* spike_counts = nullptr;
    uint64_t total_spikes = 0;

    std::unique_ptr<ExponentialTraceBankNative> trace_bank;
    std::unique_ptr<BoundedEventHistoryNative> history_buffer;

    explicit SubstrateStatePacked(const SubstrateConfig& cfg)
        : config(cfg), num_nodes(cfg.num_nodes) {
        potentials_buf_.resize(num_nodes, 0.0f);
        last_times_buf_.resize(num_nodes, 0.0);
        refractory_buf_.resize(num_nodes, -1e9);
        spike_counts_buf_.resize(num_nodes, 0);

        potentials = potentials_buf_.data();
        last_update_times = last_times_buf_.data();
        refractory_until = refractory_buf_.data();
        spike_counts = spike_counts_buf_.data();

        if (cfg.trace_bases_B > 0) {
            trace_bank = std::make_unique<ExponentialTraceBankNative>(num_nodes, cfg.trace_bases_B);
        }
        if (cfg.history_capacity_L > 0) {
            history_buffer = std::make_unique<BoundedEventHistoryNative>(num_nodes, cfg.history_capacity_L);
        }
    }

    inline void advance_node_potential(int32_t node, double current_time) noexcept {
        double dt = current_time - last_update_times[node];
        if (dt > 0.0) {
            potentials[node] *= std::exp(static_cast<float>(-dt / config.tau_m));
            last_update_times[node] = current_time;
        }
    }

    void advance_all_potentials(double current_time) noexcept {
        for (int32_t i = 0; i < num_nodes; ++i) {
            advance_node_potential(i, current_time);
        }
    }

    inline bool receive_impulse(int32_t node, double current_time, float amplitude, int32_t kind = 1) noexcept {
        advance_node_potential(node, current_time);

        if (trace_bank) trace_bank->advance_and_add(node, current_time, amplitude);
        if (history_buffer) history_buffer->record_event(node, current_time, amplitude, kind);

        if (current_time < refractory_until[node]) {
            potentials[node] = config.v_reset;
            return false;
        }

        potentials[node] += amplitude;

        if (potentials[node] >= config.threshold) {
            potentials[node] = config.v_reset;
            refractory_until[node] = current_time + config.refractory_period;
            spike_counts[node]++;
            total_spikes++;
            return true;
        }
        return false;
    }

    size_t memory_bytes() const noexcept {
        size_t b = potentials_buf_.size() * sizeof(float) +
                   last_times_buf_.size() * sizeof(double) +
                   refractory_buf_.size() * sizeof(double) +
                   spike_counts_buf_.size() * sizeof(int32_t);
        if (trace_bank) b += trace_bank->memory_bytes();
        if (history_buffer) b += history_buffer->memory_bytes();
        return b;
    }

private:
    std::vector<float> potentials_buf_;
    std::vector<double> last_times_buf_;
    std::vector<double> refractory_buf_;
    std::vector<int32_t> spike_counts_buf_;
};

} // namespace sc
