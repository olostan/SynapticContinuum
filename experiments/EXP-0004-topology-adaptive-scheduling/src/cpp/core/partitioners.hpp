#pragma once

#include "types.hpp"
#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/graph.hpp"
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <cmath>

namespace sc {

class Exp4Partitioners {
public:
    static std::vector<int32_t> partition_contiguous(int32_t num_nodes, int32_t num_regions) {
        std::vector<int32_t> part(num_nodes);
        if (num_regions <= 1) {
            std::fill(part.begin(), part.end(), 0);
            return part;
        }
        int32_t nodes_per_region = (num_nodes + num_regions - 1) / num_regions;
        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t p = u / nodes_per_region;
            part[u] = (p < num_regions) ? p : (num_regions - 1);
        }
        return part;
    }

    static std::vector<int32_t> partition_random_hash(int32_t num_nodes, int32_t num_regions, uint64_t seed = 42) {
        std::vector<int32_t> part(num_nodes);
        if (num_regions <= 1) {
            std::fill(part.begin(), part.end(), 0);
            return part;
        }
        for (int32_t u = 0; u < num_nodes; ++u) {
            uint64_t x = static_cast<uint64_t>(u) ^ seed;
            x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
            x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
            x = x ^ (x >> 31);
            part[u] = static_cast<int32_t>(x % static_cast<uint64_t>(num_regions));
        }
        return part;
    }

    static std::vector<int32_t> partition_planted_oracle(
        int32_t num_nodes,
        int32_t num_regions,
        const std::vector<int32_t>& planted_labels
    ) {
        if (planted_labels.size() == static_cast<size_t>(num_nodes)) {
            // If planted modules match num_regions, direct mapping
            std::vector<int32_t> part(num_nodes);
            for (int32_t u = 0; u < num_nodes; ++u) {
                part[u] = planted_labels[u] % num_regions;
            }
            return part;
        }
        return partition_contiguous(num_nodes, num_regions);
    }

    /**
     * Greedy Boundary Swap Heuristic (formerly partition_greedy_mincut)
     * NOTE: This is a greedy local-boundary improvement heuristic, NOT an exact mincut algorithm
     * or multilevel spectral/Kernighan-Lin/METIS partitioner. It evaluates outgoing edges and swaps
     * boundary nodes to reduce local cut while respecting soft capacity balance.
     */
    static std::vector<int32_t> partition_greedy_boundary_heuristic(
        const NeuralGraphCSR& g,
        int32_t num_regions,
        int32_t max_passes = 5
    ) {
        int32_t N = g.num_nodes;
        if (num_regions <= 1 || N <= num_regions) {
            return std::vector<int32_t>(N, 0);
        }

        // Start from contiguous partition
        std::vector<int32_t> part = partition_contiguous(N, num_regions);
        std::vector<int32_t> region_sizes(num_regions, 0);
        for (int32_t u = 0; u < N; ++u) {
            region_sizes[part[u]]++;
        }

        int32_t max_size = static_cast<int32_t>(std::ceil(1.3 * (static_cast<double>(N) / num_regions)));
        int32_t min_size = static_cast<int32_t>(std::floor(0.7 * (static_cast<double>(N) / num_regions)));

        for (int pass = 0; pass < max_passes; ++pass) {
            bool improved = false;

            for (int32_t u = 0; u < N; ++u) {
                int32_t curr_p = part[u];
                if (region_sizes[curr_p] <= min_size) continue;

                // Count edges from/to u in each region
                std::vector<int32_t> edges_in_region(num_regions, 0);
                uint64_t start = g.row_ptr[u];
                uint64_t end = g.row_ptr[u + 1];

                for (uint64_t p = start; p < end; ++p) {
                    int32_t v = g.targets[p];
                    if (v >= 0 && v < N) {
                        edges_in_region[part[v]]++;
                    }
                }

                int32_t current_intra = edges_in_region[curr_p];
                int32_t best_p = curr_p;
                int32_t best_gain = 0;

                for (int32_t r = 0; r < num_regions; ++r) {
                    if (r == curr_p) continue;
                    if (region_sizes[r] >= max_size) continue;

                    int32_t gain = edges_in_region[r] - current_intra;
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_p = r;
                    }
                }

                if (best_gain > 0 && best_p != curr_p) {
                    region_sizes[curr_p]--;
                    region_sizes[best_p]++;
                    part[u] = best_p;
                    improved = true;
                }
            }

            if (!improved) break;
        }

        return part;
    }

    // Backward-compatibility alias for partition_greedy_boundary_heuristic
    static std::vector<int32_t> partition_greedy_mincut(
        const NeuralGraphCSR& g,
        int32_t num_regions,
        int32_t max_passes = 5
    ) {
        return partition_greedy_boundary_heuristic(g, num_regions, max_passes);
    }

    struct PairwiseEventRecord {
        int32_t src;
        int32_t tgt;
        uint32_t count;
    };

    static std::vector<int32_t> partition_activity_aware(
        int32_t num_nodes,
        int32_t num_regions,
        const std::vector<PairwiseEventRecord>& warmup_events,
        int32_t max_passes = 5
    ) {
        if (num_regions <= 1 || num_nodes <= num_regions) {
            return std::vector<int32_t>(num_nodes, 0);
        }

        // Start from contiguous partition
        std::vector<int32_t> part = partition_contiguous(num_nodes, num_regions);
        std::vector<int32_t> region_sizes(num_regions, 0);
        for (int32_t u = 0; u < num_nodes; ++u) {
            region_sizes[part[u]]++;
        }

        // Build adjacency map of communication traffic
        std::vector<std::vector<std::pair<int32_t, uint32_t>>> comm(num_nodes);
        for (const auto& rec : warmup_events) {
            if (rec.src >= 0 && rec.src < num_nodes && rec.tgt >= 0 && rec.tgt < num_nodes && rec.src != rec.tgt) {
                comm[rec.src].push_back({rec.tgt, rec.count});
                comm[rec.tgt].push_back({rec.src, rec.count}); // Symmetrical affinity
            }
        }

        int32_t max_size = static_cast<int32_t>(std::ceil(1.3 * (static_cast<double>(num_nodes) / num_regions)));
        int32_t min_size = static_cast<int32_t>(std::floor(0.7 * (static_cast<double>(num_nodes) / num_regions)));

        for (int pass = 0; pass < max_passes; ++pass) {
            bool improved = false;

            for (int32_t u = 0; u < num_nodes; ++u) {
                int32_t curr_p = part[u];
                if (region_sizes[curr_p] <= min_size) continue;
                if (comm[u].empty()) continue;

                std::vector<uint32_t> traffic_in_region(num_regions, 0);
                for (const auto& edge : comm[u]) {
                    int32_t v = edge.first;
                    uint32_t w = edge.second;
                    traffic_in_region[part[v]] += w;
                }

                uint32_t current_intra_traffic = traffic_in_region[curr_p];
                int32_t best_p = curr_p;
                int64_t best_gain = 0;

                for (int32_t r = 0; r < num_regions; ++r) {
                    if (r == curr_p) continue;
                    if (region_sizes[r] >= max_size) continue;

                    int64_t gain = static_cast<int64_t>(traffic_in_region[r]) - static_cast<int64_t>(current_intra_traffic);
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_p = r;
                    }
                }

                if (best_gain > 0 && best_p != curr_p) {
                    region_sizes[curr_p]--;
                    region_sizes[best_p]++;
                    part[u] = best_p;
                    improved = true;
                }
            }

            if (!improved) break;
        }

        return part;
    }
};

} // namespace sc
