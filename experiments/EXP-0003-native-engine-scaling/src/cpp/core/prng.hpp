#pragma once

#include "types.hpp"
#include <cstdint>
#include <cmath>
#include <vector>
#include <algorithm>

namespace sc {

class DeterministicRNG {
public:
    explicit DeterministicRNG(uint64_t seed = 42) noexcept : state_(seed ? seed : 0x123456789ABCDEF0ULL) {}

    void set_seed(uint64_t seed) noexcept {
        state_ = seed ? seed : 0x123456789ABCDEF0ULL;
    }

    uint64_t next_u64() noexcept {
        state_ += 0x9e3779b97f4a7c15ULL;
        uint64_t z = state_;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }

    // Fast uniform integer in [0, n)
    uint32_t uniform_uint(uint32_t n) noexcept {
        if (n <= 1) return 0;
        uint64_t x = next_u64() & 0xFFFFFFFFULL;
        return static_cast<uint32_t>((x * static_cast<uint64_t>(n)) >> 32);
    }

    // Float in [min_val, max_val) with 24-bit precision
    float uniform_float(float min_val, float max_val) noexcept {
        uint64_t r = next_u64();
        float u = static_cast<float>(r >> 40) * (1.0f / 16777216.0f);
        return min_val + u * (max_val - min_val);
    }

    // Double in [min_val, max_val) with 53-bit precision
    double uniform_double(double min_val, double max_val) noexcept {
        uint64_t r = next_u64();
        double u = static_cast<double>(r >> 11) * (1.0 / 9007199254740992.0);
        return min_val + u * (max_val - min_val);
    }

    // Exponential distribution with parameter rate (lambda)
    double exponential(double rate) noexcept {
        if (rate <= 0.0) return 1e9;
        double u = uniform_double(1e-12, 1.0);
        return -std::log(u) / rate;
    }

    // Deterministic selection of k unique targets from [0, num_nodes) excluding exclude_node
    std::vector<uint32_t> sample_unique(uint32_t count, uint32_t num_nodes, uint32_t exclude_node) {
        std::vector<uint32_t> result;
        uint32_t max_avail = (exclude_node < num_nodes) ? (num_nodes - 1) : num_nodes;
        uint32_t k = std::min(count, max_avail);
        if (k == 0) return result;

        result.reserve(k);
        if (k >= max_avail) {
            for (uint32_t i = 0; i < num_nodes; ++i) {
                if (i != exclude_node) result.push_back(i);
            }
            return result;
        }

        while (result.size() < k) {
            uint32_t cand = uniform_uint(num_nodes);
            if (cand == exclude_node) continue;
            bool duplicate = false;
            for (uint32_t val : result) {
                if (val == cand) {
                    duplicate = true;
                    break;
                }
            }
            if (!duplicate) {
                result.push_back(cand);
            }
        }
        std::sort(result.begin(), result.end());
        return result;
    }

private:
    uint64_t state_;
};

} // namespace sc
