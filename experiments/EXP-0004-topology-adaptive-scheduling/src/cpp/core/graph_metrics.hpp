#pragma once

#include "types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/prng.hpp"
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <unordered_set>

namespace sc {

class Exp4GraphMetricsCalculator {
public:
    static GraphMetrics compute_all_metrics(
        const NeuralGraphCSR& g,
        const std::vector<int32_t>& partition_map,
        int32_t max_clustering_samples = 500,
        int32_t max_path_sources = 100,
        uint64_t seed = 42
    ) {
        GraphMetrics m;
        compute_degree_stats(g, m);
        m.clustering_coefficient = compute_clustering_coefficient(g, max_clustering_samples, seed);
        m.characteristic_path_length = compute_characteristic_path_length(g, max_path_sources, seed);
        m.edge_cut_fraction = compute_edge_cut(g, partition_map);
        m.modularity_q = compute_modularity(g, partition_map);
        return m;
    }

    static void compute_degree_stats(const NeuralGraphCSR& g, GraphMetrics& m) {
        int32_t N = g.num_nodes;
        if (N == 0) return;

        std::vector<uint32_t> in_degrees(N, 0);
        std::vector<uint32_t> out_degrees(N, 0);

        for (int32_t u = 0; u < N; ++u) {
            uint32_t out_d = static_cast<uint32_t>(g.row_ptr[u + 1] - g.row_ptr[u]);
            out_degrees[u] = out_d;
            for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
                int32_t v = g.targets[p];
                if (v >= 0 && v < N) {
                    in_degrees[v]++;
                }
            }
        }

        double sum_in = 0, sum_out = 0;
        uint32_t max_in = 0, max_out = 0;
        for (int32_t u = 0; u < N; ++u) {
            sum_in += in_degrees[u];
            sum_out += out_degrees[u];
            if (in_degrees[u] > max_in) max_in = in_degrees[u];
            if (out_degrees[u] > max_out) max_out = out_degrees[u];
        }

        m.in_degree_mean = sum_in / N;
        m.in_degree_max = max_in;
        m.out_degree_mean = sum_out / N;
        m.out_degree_max = max_out;

        double var_in = 0, var_out = 0;
        for (int32_t u = 0; u < N; ++u) {
            double diff_in = in_degrees[u] - m.in_degree_mean;
            var_in += diff_in * diff_in;
            double diff_out = out_degrees[u] - m.out_degree_mean;
            var_out += diff_out * diff_out;
        }
        m.in_degree_var = var_in / N;
        m.out_degree_var = var_out / N;
    }

    static double compute_clustering_coefficient(
        const NeuralGraphCSR& g,
        int32_t max_samples = 500,
        uint64_t seed = 42
    ) {
        int32_t N = g.num_nodes;
        if (N < 3) return 0.0;

        // Build undirected neighbor list for fast neighbor lookup
        std::vector<std::vector<int32_t>> adj(N);
        for (int32_t u = 0; u < N; ++u) {
            for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
                int32_t v = g.targets[p];
                if (u != v) {
                    adj[u].push_back(v);
                    adj[v].push_back(u);
                }
            }
        }
        for (int32_t u = 0; u < N; ++u) {
            std::sort(adj[u].begin(), adj[u].end());
            adj[u].erase(std::unique(adj[u].begin(), adj[u].end()), adj[u].end());
        }

        DeterministicRNG rng(seed);
        int32_t S = std::min(N, max_samples);
        double total_c = 0.0;
        int32_t valid_nodes = 0;

        for (int32_t s = 0; s < S; ++s) {
            int32_t u = (S == N) ? s : static_cast<int32_t>(rng.uniform_uint(N));
            const auto& nbrs = adj[u];
            size_t k = nbrs.size();
            if (k < 2) continue;

            uint64_t triangles = 0;
            for (size_t i = 0; i < k; ++i) {
                int32_t v = nbrs[i];
                for (size_t j = i + 1; j < k; ++j) {
                    int32_t w = nbrs[j];
                    if (std::binary_search(adj[v].begin(), adj[v].end(), w)) {
                        triangles++;
                    }
                }
            }

            double possible = static_cast<double>(k) * (k - 1) / 2.0;
            total_c += static_cast<double>(triangles) / possible;
            valid_nodes++;
        }

        return (valid_nodes > 0) ? (total_c / valid_nodes) : 0.0;
    }

    static double compute_characteristic_path_length(
        const NeuralGraphCSR& g,
        int32_t max_sources = 100,
        uint64_t seed = 42
    ) {
        int32_t N = g.num_nodes;
        if (N < 2) return 0.0;

        DeterministicRNG rng(seed);
        int32_t S = std::min(N, max_sources);

        double total_distance = 0.0;
        uint64_t reachable_pairs = 0;

        std::vector<int32_t> dist(N);
        std::queue<int32_t> q;

        for (int32_t s = 0; s < S; ++s) {
            int32_t src = (S == N) ? s : static_cast<int32_t>(rng.uniform_uint(N));
            std::fill(dist.begin(), dist.end(), -1);
            dist[src] = 0;
            q.push(src);

            while (!q.empty()) {
                int32_t u = q.front();
                q.pop();

                int32_t d_u = dist[u];
                for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
                    int32_t v = g.targets[p];
                    if (dist[v] == -1) {
                        dist[v] = d_u + 1;
                        total_distance += dist[v];
                        reachable_pairs++;
                        q.push(v);
                    }
                }
            }
        }

        return (reachable_pairs > 0) ? (total_distance / static_cast<double>(reachable_pairs)) : 0.0;
    }

    static double compute_edge_cut(
        const NeuralGraphCSR& g,
        const std::vector<int32_t>& partition_map
    ) {
        if (g.num_edges == 0 || partition_map.size() != static_cast<size_t>(g.num_nodes)) {
            return 0.0;
        }

        uint64_t cut_edges = 0;
        for (int32_t u = 0; u < g.num_nodes; ++u) {
            int32_t part_u = partition_map[u];
            for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
                int32_t v = g.targets[p];
                if (v >= 0 && v < g.num_nodes && partition_map[v] != part_u) {
                    cut_edges++;
                }
            }
        }

        return static_cast<double>(cut_edges) / static_cast<double>(g.num_edges);
    }

    static double compute_modularity(
        const NeuralGraphCSR& g,
        const std::vector<int32_t>& partition_map
    ) {
        if (g.num_edges == 0 || partition_map.size() != static_cast<size_t>(g.num_nodes)) {
            return 0.0;
        }

        int32_t max_p = 0;
        for (int32_t p : partition_map) {
            if (p > max_p) max_p = p;
        }
        size_t num_parts = static_cast<size_t>(max_p + 1);

        std::vector<double> out_deg_sum(num_parts, 0.0);
        std::vector<double> in_deg_sum(num_parts, 0.0);
        std::vector<double> intra_edges(num_parts, 0.0);

        double E = static_cast<double>(g.num_edges);

        for (int32_t u = 0; u < g.num_nodes; ++u) {
            int32_t part_u = partition_map[u];
            uint32_t k_out = static_cast<uint32_t>(g.row_ptr[u + 1] - g.row_ptr[u]);
            out_deg_sum[part_u] += k_out;

            for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
                int32_t v = g.targets[p];
                if (v >= 0 && v < g.num_nodes) {
                    int32_t part_v = partition_map[v];
                    in_deg_sum[part_v] += 1.0;
                    if (part_u == part_v) {
                        intra_edges[part_u] += 1.0;
                    }
                }
            }
        }

        // Newman's modularity: Q = sum_m [ intra_m / E - (out_deg_m * in_deg_m) / E^2 ]
        double Q = 0.0;
        for (size_t m = 0; m < num_parts; ++m) {
            double actual = intra_edges[m] / E;
            double expected = (out_deg_sum[m] * in_deg_sum[m]) / (E * E);
            Q += (actual - expected);
        }

        return Q;
    }
};

} // namespace sc
