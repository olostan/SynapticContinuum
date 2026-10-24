#pragma once

#include "types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/state.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/prng.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/queues/binary_heap.hpp"
#include <vector>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <chrono>

namespace sc {

/**
 * NeuralGraphCompactCSR
 * 
 * D2 Graph Representation: Quantized Compact CSR (8 bytes per edge vs 12 bytes in standard CSR).
 * - row_ptr: uint32_t (4 bytes per node vs 8 bytes)
 * - targets: int32_t (4 bytes per edge)
 * - weights_q16: int16_t (2 bytes per edge, fixed-point scale 1.0f / 4096.0f)
 * - delays_q16: uint16_t (2 bytes per edge, fixed-point scale 1.0f / 4096.0f)
 */
class NeuralGraphCompactCSR {
public:
    static constexpr float WEIGHT_SCALE = 1.0f / 4096.0f;
    static constexpr float DELAY_SCALE = 1.0f / 4096.0f;

    int32_t num_nodes = 0;
    uint32_t num_edges = 0;
    std::vector<uint32_t> row_ptr;
    std::vector<int32_t> targets;
    std::vector<int16_t> weights_q16;
    std::vector<uint16_t> delays_q16;

    static NeuralGraphCompactCSR from_standard_csr(const NeuralGraphCSR& g) {
        NeuralGraphCompactCSR cg;
        cg.num_nodes = g.num_nodes;
        cg.num_edges = static_cast<uint32_t>(g.num_edges);
        cg.row_ptr.resize(g.num_nodes + 1);
        for (int32_t u = 0; u <= g.num_nodes; ++u) {
            cg.row_ptr[u] = static_cast<uint32_t>(g.row_ptr[u]);
        }
        cg.targets = g.targets;
        cg.weights_q16.resize(g.num_edges);
        cg.delays_q16.resize(g.num_edges);

        for (size_t i = 0; i < g.num_edges; ++i) {
            int32_t wq = static_cast<int32_t>(std::round(g.weights[i] * 4096.0f));
            wq = std::clamp(wq, -32767, 32767);
            cg.weights_q16[i] = static_cast<int16_t>(wq);

            int32_t dq = static_cast<int32_t>(std::round(g.delays[i] * 4096.0f));
            dq = std::clamp(dq, 1, 65535);
            cg.delays_q16[i] = static_cast<uint16_t>(dq);
        }
        return cg;
    }

    size_t memory_footprint_bytes() const noexcept {
        return row_ptr.capacity() * sizeof(uint32_t)
             + targets.capacity() * sizeof(int32_t)
             + weights_q16.capacity() * sizeof(int16_t)
             + delays_q16.capacity() * sizeof(uint16_t);
    }
};

/**
 * NeuralGraphProceduralSBM
 * 
 * D2 Graph Representation: Procedural On-the-Fly Implicit Connectivity (0 bytes per edge).
 * Computes outgoing targets, weights, and delays deterministically from `(seed, source_node, edge_index)`
 * using SplitMix64 mixing without storing an explicit edge table in RAM.
 */
class NeuralGraphProceduralSBM {
public:
    int32_t num_nodes = 0;
    int32_t out_degree = 16;
    int32_t num_modules = 6;
    float cross_ratio_c = 0.05f;
    uint64_t seed = 42;
    float weight_scale = 0.40f;
    float min_delay = 0.2f;
    float max_delay = 1.0f;

    size_t memory_footprint_bytes() const noexcept {
        return sizeof(*this);
    }

    static inline uint64_t splitmix64(uint64_t x) noexcept {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }

    inline void generate_edge(
        int32_t u,
        int32_t edge_idx,
        int32_t& out_target,
        float& out_weight,
        float& out_delay
    ) const noexcept {
        uint64_t h_node = splitmix64(seed ^ (static_cast<uint64_t>(u) * 0x517cc1b727220a95ULL));
        bool is_inhibitory = ((h_node & 0xFFFFULL) < 13107ULL); // ~20% inhibitory

        uint64_t h_edge = splitmix64(h_node ^ static_cast<uint64_t>(edge_idx));
        int32_t nodes_per_mod = std::max(1, num_nodes / num_modules);
        int32_t my_m = std::min(num_modules - 1, u / nodes_per_mod);
        int32_t m_start = my_m * nodes_per_mod;
        int32_t m_end = (my_m == num_modules - 1) ? num_nodes : (my_m + 1) * nodes_per_mod;
        int32_t m_size = std::max(1, m_end - m_start);

        int32_t k_cross = static_cast<int32_t>(std::round(out_degree * cross_ratio_c));
        int32_t k_intra = out_degree - k_cross;

        if (edge_idx < k_intra && m_size > 1) {
            int32_t offset = static_cast<int32_t>(h_edge % static_cast<uint64_t>(m_size - 1));
            int32_t cand = m_start + offset;
            if (cand >= u) cand++;
            out_target = cand;
        } else {
            int32_t cand = static_cast<int32_t>(h_edge % static_cast<uint64_t>(num_nodes - 1));
            if (cand >= u) cand++;
            out_target = cand;
        }

        float u_w = static_cast<float>((h_edge >> 16) & 0xFFFFULL) / 65535.0f;
        float w_raw = (0.5f + u_w) * weight_scale;
        out_weight = is_inhibitory ? -w_raw : w_raw;

        float u_d = static_cast<float>((h_edge >> 32) & 0xFFFFULL) / 65535.0f;
        out_delay = min_delay + u_d * (max_delay - min_delay);
    }
};

/**
 * SubstrateStateAoS
 * 
 * D2 State Representation: Array-of-Structs (AoS) per-neuron state layout.
 * Co-locates potential, last_update_time, last_spike_time, refractory_until, and ring buffer index
 * in a single 32-byte cache-line-friendly struct per neuron (compared to 5 separate SoA arrays in SubstrateStatePacked).
 */
struct alignas(32) NeuronStateRecordAoS {
    float potential = 0.0f;
    int32_t spike_count = 0;
    double last_update_time = 0.0;
    double refractory_until = -1e9;
    double pad0 = 0.0;
};

class SubstrateStateAoS {
public:
    SubstrateConfig config;
    std::vector<NeuronStateRecordAoS> neurons;

    explicit SubstrateStateAoS(const SubstrateConfig& cfg)
        : config(cfg), neurons(cfg.num_nodes) {}

    bool receive_impulse(int32_t target, double timestamp, float weight, int32_t kind = 1) noexcept {
        (void)kind;
        auto& n = neurons[target];
        double dt = timestamp - n.last_update_time;
        if (dt > 0.0) {
            n.potential *= std::exp(static_cast<float>(-dt / config.tau_m));
            n.last_update_time = timestamp;
        }

        if (timestamp < n.refractory_until) {
            n.potential = config.v_reset;
            return false;
        }

        n.potential += weight;
        if (n.potential >= config.threshold) {
            n.potential = config.v_reset;
            n.refractory_until = timestamp + config.refractory_period;
            n.spike_count++;
            return true;
        }
        return false;
    }

    void advance_all_potentials(double final_time) noexcept {
        for (int32_t i = 0; i < config.num_nodes; ++i) {
            double dt = final_time - neurons[i].last_update_time;
            if (dt > 0.0) {
                neurons[i].potential *= std::exp(static_cast<float>(-dt / config.tau_m));
                neurons[i].last_update_time = final_time;
            }
        }
    }

    size_t memory_footprint_bytes() const noexcept {
        return neurons.capacity() * sizeof(NeuronStateRecordAoS);
    }
};

} // namespace sc
