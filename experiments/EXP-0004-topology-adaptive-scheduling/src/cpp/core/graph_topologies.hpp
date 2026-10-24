#pragma once

#include "types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/prng.hpp"
#include <vector>
#include <algorithm>
#include <cmath>
#include <unordered_set>
#include <stdexcept>
#include <iostream>

namespace sc {

struct GeneratedGraphWithLabels {
    NeuralGraphCSR graph;
    std::vector<int32_t> planted_labels;
};

class Exp4GraphGenerators {
public:
    static NeuralGraphCSR create_uniform_random(
        int32_t num_nodes,
        int32_t mean_out_degree,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        return GraphFactory::create_random(num_nodes, mean_out_degree, seed, weight_scale, min_delay, max_delay);
    }

    static NeuralGraphCSR create_watts_strogatz_small_world(
        int32_t num_nodes,
        int32_t mean_out_degree,
        float rewiring_p,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        DeterministicRNG rng(seed);
        NeuralGraphCSR g;
        g.num_nodes = num_nodes;
        g.row_ptr.resize(num_nodes + 1, 0);

        uint32_t k = std::min(static_cast<uint32_t>(mean_out_degree),
                              (num_nodes > 1) ? static_cast<uint32_t>(num_nodes - 1) : 0U);
        uint32_t k_fwd = k / 2;
        uint32_t k_bwd = k - k_fwd;

        std::vector<std::vector<uint32_t>> all_targets(num_nodes);
        std::vector<std::vector<float>> all_weights(num_nodes);
        std::vector<std::vector<float>> all_delays(num_nodes);

        uint64_t total_edges = 0;

        for (int32_t u = 0; u < num_nodes; ++u) {
            std::vector<uint32_t> targets;
            targets.reserve(k);

            // Construct ring lattice neighbors
            for (uint32_t i = 1; i <= k_fwd; ++i) {
                uint32_t tgt = (static_cast<uint32_t>(u) + i) % num_nodes;
                if (tgt != static_cast<uint32_t>(u)) targets.push_back(tgt);
            }
            for (uint32_t i = 1; i <= k_bwd; ++i) {
                uint32_t tgt = (static_cast<uint32_t>(u) + num_nodes - i) % num_nodes;
                if (tgt != static_cast<uint32_t>(u)) targets.push_back(tgt);
            }

            // Rewire edges with probability p
            if (rewiring_p > 0.0f) {
                for (size_t i = 0; i < targets.size(); ++i) {
                    if (rng.uniform_float(0.0f, 1.0f) < rewiring_p) {
                        uint32_t cand = rng.uniform_uint(num_nodes);
                        int attempts = 0;
                        while ((cand == static_cast<uint32_t>(u) ||
                               std::find(targets.begin(), targets.end(), cand) != targets.end()) &&
                               attempts < 50) {
                            cand = rng.uniform_uint(num_nodes);
                            attempts++;
                        }
                        if (cand != static_cast<uint32_t>(u) &&
                            std::find(targets.begin(), targets.end(), cand) == targets.end()) {
                            targets[i] = cand;
                        }
                    }
                }
            }

            // Remove any accidental duplicates or self-loops
            std::vector<uint32_t> clean_targets;
            clean_targets.reserve(targets.size());
            for (uint32_t t : targets) {
                if (t != static_cast<uint32_t>(u) &&
                    std::find(clean_targets.begin(), clean_targets.end(), t) == clean_targets.end()) {
                    clean_targets.push_back(t);
                }
            }

            bool is_inhibitory = (rng.uniform_float(0.0f, 1.0f) < 0.20f);
            std::vector<float> weights(clean_targets.size());
            std::vector<float> delays(clean_targets.size());
            for (size_t i = 0; i < clean_targets.size(); ++i) {
                float w_raw = rng.uniform_float(0.5f, 1.5f) * weight_scale;
                weights[i] = is_inhibitory ? -w_raw : w_raw;
                delays[i] = rng.uniform_float(min_delay, max_delay);
            }

            total_edges += clean_targets.size();
            all_targets[u] = std::move(clean_targets);
            all_weights[u] = std::move(weights);
            all_delays[u] = std::move(delays);
        }

        g.num_edges = total_edges;
        g.targets.resize(total_edges);
        g.weights.resize(total_edges);
        g.delays.resize(total_edges);

        uint64_t offset = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            g.row_ptr[u] = offset;
            size_t count = all_targets[u].size();
            for (size_t i = 0; i < count; ++i) {
                g.targets[offset + i] = static_cast<int32_t>(all_targets[u][i]);
                g.weights[offset + i] = all_weights[u][i];
                g.delays[offset + i] = all_delays[u][i];
            }
            offset += count;
        }
        g.row_ptr[num_nodes] = offset;

        return g;
    }

    static GeneratedGraphWithLabels create_modular_sbm(
        int32_t num_nodes,
        int32_t mean_out_degree,
        int32_t num_modules,
        float cross_module_ratio_c,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        DeterministicRNG rng(seed);
        GeneratedGraphWithLabels res;
        res.graph.num_nodes = num_nodes;
        res.graph.row_ptr.resize(num_nodes + 1, 0);
        res.planted_labels.resize(num_nodes, 0);

        if (num_modules <= 1) {
            res.graph = create_uniform_random(num_nodes, mean_out_degree, seed, weight_scale, min_delay, max_delay);
            return res;
        }

        int32_t nodes_per_module = num_nodes / num_modules;
        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t m = u / nodes_per_module;
            if (m >= num_modules) m = num_modules - 1;
            res.planted_labels[u] = m;
        }

        uint32_t k = std::min(static_cast<uint32_t>(mean_out_degree),
                              (num_nodes > 1) ? static_cast<uint32_t>(num_nodes - 1) : 0U);
        uint32_t k_cross = static_cast<uint32_t>(std::round(k * cross_module_ratio_c));
        if (k_cross > k) k_cross = k;
        uint32_t k_intra = k - k_cross;

        std::vector<std::vector<uint32_t>> all_targets(num_nodes);
        std::vector<std::vector<float>> all_weights(num_nodes);
        std::vector<std::vector<float>> all_delays(num_nodes);

        uint64_t total_edges = 0;

        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t my_m = res.planted_labels[u];
            uint32_t m_start = static_cast<uint32_t>(my_m * nodes_per_module);
            uint32_t m_end = (my_m == num_modules - 1) ? static_cast<uint32_t>(num_nodes)
                                                       : static_cast<uint32_t>((my_m + 1) * nodes_per_module);
            uint32_t m_size = m_end - m_start;

            std::vector<uint32_t> targets;
            targets.reserve(k);

            // Sample intra-module edges
            uint32_t intra_needed = (m_size > 1) ? std::min(k_intra, m_size - 1) : 0U;
            int attempts = 0;
            while (targets.size() < intra_needed && attempts < 100) {
                uint32_t cand = m_start + rng.uniform_uint(m_size);
                attempts++;
                if (cand == static_cast<uint32_t>(u)) continue;
                if (std::find(targets.begin(), targets.end(), cand) == targets.end()) {
                    targets.push_back(cand);
                }
            }

            // Sample cross-module edges
            if (k_cross > 0 && num_nodes > static_cast<int32_t>(m_size)) {
                attempts = 0;
                while (targets.size() < (intra_needed + k_cross) && attempts < 200) {
                    uint32_t cand = rng.uniform_uint(num_nodes);
                    attempts++;
                    if (cand >= m_start && cand < m_end) continue; // Must be cross-module
                    if (std::find(targets.begin(), targets.end(), cand) == targets.end()) {
                        targets.push_back(cand);
                    }
                }
            }

            bool is_inhibitory = (rng.uniform_float(0.0f, 1.0f) < 0.20f);
            std::vector<float> weights(targets.size());
            std::vector<float> delays(targets.size());
            for (size_t i = 0; i < targets.size(); ++i) {
                float w_raw = rng.uniform_float(0.5f, 1.5f) * weight_scale;
                weights[i] = is_inhibitory ? -w_raw : w_raw;
                delays[i] = rng.uniform_float(min_delay, max_delay);
            }

            total_edges += targets.size();
            all_targets[u] = std::move(targets);
            all_weights[u] = std::move(weights);
            all_delays[u] = std::move(delays);
        }

        res.graph.num_edges = total_edges;
        res.graph.targets.resize(total_edges);
        res.graph.weights.resize(total_edges);
        res.graph.delays.resize(total_edges);

        uint64_t offset = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            res.graph.row_ptr[u] = offset;
            size_t count = all_targets[u].size();
            for (size_t i = 0; i < count; ++i) {
                res.graph.targets[offset + i] = static_cast<int32_t>(all_targets[u][i]);
                res.graph.weights[offset + i] = all_weights[u][i];
                res.graph.delays[offset + i] = all_delays[u][i];
            }
            offset += count;
        }
        res.graph.row_ptr[num_nodes] = offset;

        return res;
    }

    static GeneratedGraphWithLabels create_disconnected_modules(
        int32_t num_nodes,
        int32_t mean_out_degree,
        int32_t num_modules,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        // Disconnected control: cross_module_ratio_c = 0.0
        return create_modular_sbm(num_nodes, mean_out_degree, num_modules, 0.0f, seed, weight_scale, min_delay, max_delay);
    }

    static GeneratedGraphWithLabels create_hierarchical_modular(
        int32_t num_nodes,
        int32_t mean_out_degree,
        int32_t num_top_branches,
        int32_t sub_modules_per_branch,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        DeterministicRNG rng(seed);
        int32_t total_leaf_modules = num_top_branches * sub_modules_per_branch;
        GeneratedGraphWithLabels res;
        res.graph.num_nodes = num_nodes;
        res.graph.row_ptr.resize(num_nodes + 1, 0);
        res.planted_labels.resize(num_nodes, 0);

        int32_t nodes_per_leaf = num_nodes / total_leaf_modules;
        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t leaf = u / nodes_per_leaf;
            if (leaf >= total_leaf_modules) leaf = total_leaf_modules - 1;
            res.planted_labels[u] = leaf;
        }

        uint32_t k = std::min(static_cast<uint32_t>(mean_out_degree),
                              (num_nodes > 1) ? static_cast<uint32_t>(num_nodes - 1) : 0U);

        std::vector<std::vector<uint32_t>> all_targets(num_nodes);
        std::vector<std::vector<float>> all_weights(num_nodes);
        std::vector<std::vector<float>> all_delays(num_nodes);
        uint64_t total_edges = 0;

        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t leaf_u = res.planted_labels[u];
            int32_t branch_u = leaf_u / sub_modules_per_branch;

            std::vector<uint32_t> targets;
            targets.reserve(k);

            int attempts = 0;
            while (targets.size() < k && attempts < 300) {
                attempts++;
                float r = rng.uniform_float(0.0f, 1.0f);
                uint32_t cand = 0;

                if (r < 0.65f) {
                    // Level 0: Same leaf module
                    uint32_t l_start = static_cast<uint32_t>(leaf_u * nodes_per_leaf);
                    uint32_t l_end = (leaf_u == total_leaf_modules - 1) ? static_cast<uint32_t>(num_nodes)
                                                                        : static_cast<uint32_t>((leaf_u + 1) * nodes_per_leaf);
                    uint32_t l_size = l_end - l_start;
                    if (l_size <= 1) continue;
                    cand = l_start + rng.uniform_uint(l_size);
                } else if (r < 0.90f) {
                    // Level 1: Same top branch, different leaf
                    int32_t other_sub = rng.uniform_uint(sub_modules_per_branch);
                    int32_t target_leaf = branch_u * sub_modules_per_branch + other_sub;
                    uint32_t l_start = static_cast<uint32_t>(target_leaf * nodes_per_leaf);
                    uint32_t l_end = (target_leaf == total_leaf_modules - 1) ? static_cast<uint32_t>(num_nodes)
                                                                             : static_cast<uint32_t>((target_leaf + 1) * nodes_per_leaf);
                    uint32_t l_size = l_end - l_start;
                    cand = l_start + rng.uniform_uint(l_size);
                } else {
                    // Level 2: Different top branch
                    cand = rng.uniform_uint(num_nodes);
                }

                if (cand == static_cast<uint32_t>(u)) continue;
                if (std::find(targets.begin(), targets.end(), cand) == targets.end()) {
                    targets.push_back(cand);
                }
            }

            bool is_inhibitory = (rng.uniform_float(0.0f, 1.0f) < 0.20f);
            std::vector<float> weights(targets.size());
            std::vector<float> delays(targets.size());
            for (size_t i = 0; i < targets.size(); ++i) {
                float w_raw = rng.uniform_float(0.5f, 1.5f) * weight_scale;
                weights[i] = is_inhibitory ? -w_raw : w_raw;
                delays[i] = rng.uniform_float(min_delay, max_delay);
            }

            total_edges += targets.size();
            all_targets[u] = std::move(targets);
            all_weights[u] = std::move(weights);
            all_delays[u] = std::move(delays);
        }

        res.graph.num_edges = total_edges;
        res.graph.targets.resize(total_edges);
        res.graph.weights.resize(total_edges);
        res.graph.delays.resize(total_edges);

        uint64_t offset = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            res.graph.row_ptr[u] = offset;
            size_t count = all_targets[u].size();
            for (size_t i = 0; i < count; ++i) {
                res.graph.targets[offset + i] = static_cast<int32_t>(all_targets[u][i]);
                res.graph.weights[offset + i] = all_weights[u][i];
                res.graph.delays[offset + i] = all_delays[u][i];
            }
            offset += count;
        }
        res.graph.row_ptr[num_nodes] = offset;

        return res;
    }

    static NeuralGraphCSR create_degree_preserving_rewired(
        const NeuralGraphCSR& base_graph,
        uint64_t num_swaps,
        uint64_t seed
    ) {
        DeterministicRNG rng(seed);
        NeuralGraphCSR g = base_graph;
        if (g.num_edges < 4 || g.num_nodes < 4) return g;

        // Build flat edge array for uniform edge sampling
        struct EdgeIdx {
            int32_t src;
            uint64_t pos; // index in g.targets
        };
        std::vector<EdgeIdx> edges;
        edges.reserve(g.num_edges);

        for (int32_t u = 0; u < g.num_nodes; ++u) {
            uint64_t start = g.row_ptr[u];
            uint64_t end = g.row_ptr[u + 1];
            for (uint64_t p = start; p < end; ++p) {
                edges.push_back({u, p});
            }
        }

        uint64_t E = edges.size();
        for (uint64_t step = 0; step < num_swaps; ++step) {
            uint64_t idx1 = rng.uniform_uint(static_cast<uint32_t>(E));
            uint64_t idx2 = rng.uniform_uint(static_cast<uint32_t>(E));
            if (idx1 == idx2) continue;

            int32_t u1 = edges[idx1].src;
            int32_t u2 = edges[idx2].src;
            if (u1 == u2) continue;

            uint64_t pos1 = edges[idx1].pos;
            uint64_t pos2 = edges[idx2].pos;

            int32_t v1 = g.targets[pos1];
            int32_t v2 = g.targets[pos2];

            // Maslov-Sneppen swap: (u1 -> v1, u2 -> v2) becomes (u1 -> v2, u2 -> v1)
            // Conditions: no self loops, no duplicate targets
            if (u1 == v2 || u2 == v1 || v1 == v2) continue;

            // Check if u1 already has edge to v2
            bool has_u1_v2 = false;
            for (uint64_t p = g.row_ptr[u1]; p < g.row_ptr[u1 + 1]; ++p) {
                if (g.targets[p] == v2) { has_u1_v2 = true; break; }
            }
            if (has_u1_v2) continue;

            // Check if u2 already has edge to v1
            bool has_u2_v1 = false;
            for (uint64_t p = g.row_ptr[u2]; p < g.row_ptr[u2 + 1]; ++p) {
                if (g.targets[p] == v1) { has_u2_v1 = true; break; }
            }
            if (has_u2_v1) continue;

            // Perform valid swap
            g.targets[pos1] = v2;
            g.targets[pos2] = v1;
        }

        return g;
    }

    static NeuralGraphCSR create_node_id_permuted(
        const NeuralGraphCSR& base_graph,
        uint64_t seed
    ) {
        DeterministicRNG rng(seed);
        int32_t N = base_graph.num_nodes;
        std::vector<int32_t> perm(N);
        for (int32_t i = 0; i < N; ++i) perm[i] = i;

        // Fisher-Yates shuffle
        for (int32_t i = N - 1; i > 0; --i) {
            uint32_t j = rng.uniform_uint(i + 1);
            std::swap(perm[i], perm[j]);
        }

        // Build new graph where node u' = perm[u]
        std::vector<std::vector<int32_t>> new_targets(N);
        std::vector<std::vector<float>> new_weights(N);
        std::vector<std::vector<float>> new_delays(N);

        for (int32_t u = 0; u < N; ++u) {
            int32_t u_new = perm[u];
            uint64_t start = base_graph.row_ptr[u];
            uint64_t end = base_graph.row_ptr[u + 1];
            size_t count = end - start;

            new_targets[u_new].reserve(count);
            new_weights[u_new].reserve(count);
            new_delays[u_new].reserve(count);

            for (uint64_t p = start; p < end; ++p) {
                int32_t v = base_graph.targets[p];
                int32_t v_new = perm[v];
                new_targets[u_new].push_back(v_new);
                new_weights[u_new].push_back(base_graph.weights[p]);
                new_delays[u_new].push_back(base_graph.delays[p]);
            }
        }

        NeuralGraphCSR g;
        g.num_nodes = N;
        g.num_edges = base_graph.num_edges;
        g.row_ptr.resize(N + 1, 0);
        g.targets.resize(base_graph.num_edges);
        g.weights.resize(base_graph.num_edges);
        g.delays.resize(base_graph.num_edges);

        uint64_t offset = 0;
        for (int32_t u = 0; u < N; ++u) {
            g.row_ptr[u] = offset;
            size_t count = new_targets[u].size();
            for (size_t i = 0; i < count; ++i) {
                g.targets[offset + i] = new_targets[u][i];
                g.weights[offset + i] = new_weights[u][i];
                g.delays[offset + i] = new_delays[u][i];
            }
            offset += count;
        }
        g.row_ptr[N] = offset;

        return g;
    }

    static NeuralGraphCSR create_from_edge_list(
        int32_t num_nodes,
        const std::vector<std::pair<int32_t, int32_t>>& edges,
        uint64_t seed,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        DeterministicRNG rng(seed);
        NeuralGraphCSR g;
        g.num_nodes = num_nodes;
        g.row_ptr.resize(num_nodes + 1, 0);

        std::vector<std::vector<int32_t>> adj(num_nodes);
        for (const auto& edge : edges) {
            int32_t u = edge.first;
            int32_t v = edge.second;
            if (u >= 0 && u < num_nodes && v >= 0 && v < num_nodes && u != v) {
                if (std::find(adj[u].begin(), adj[u].end(), v) == adj[u].end()) {
                    adj[u].push_back(v);
                }
            }
        }

        uint64_t total_edges = 0;
        for (int32_t u = 0; u < num_nodes; ++u) total_edges += adj[u].size();

        g.num_edges = total_edges;
        g.targets.resize(total_edges);
        g.weights.resize(total_edges);
        g.delays.resize(total_edges);

        uint64_t offset = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            g.row_ptr[u] = offset;
            bool is_inhibitory = (rng.uniform_float(0.0f, 1.0f) < 0.20f);
            for (size_t i = 0; i < adj[u].size(); ++i) {
                float w_raw = rng.uniform_float(0.5f, 1.5f) * weight_scale;
                g.targets[offset + i] = adj[u][i];
                g.weights[offset + i] = is_inhibitory ? -w_raw : w_raw;
                g.delays[offset + i] = rng.uniform_float(min_delay, max_delay);
            }
            offset += adj[u].size();
        }
        g.row_ptr[num_nodes] = offset;

        return g;
    }
};

} // namespace sc
