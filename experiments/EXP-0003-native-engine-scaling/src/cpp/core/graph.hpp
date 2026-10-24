#pragma once

#include "types.hpp"
#include "prng.hpp"
#include <vector>
#include <fstream>
#include <stdexcept>
#include <string>
#include <cstring>
#include <iostream>

namespace sc {

enum class TopologyType : int32_t {
    RANDOM = 0,
    MODULAR = 1
};

class NeuralGraphCSR {
public:
    int32_t num_nodes = 0;
    uint64_t num_edges = 0;
    std::vector<uint64_t> row_ptr;
    std::vector<int32_t> targets;
    std::vector<float> weights;
    std::vector<float> delays;

    size_t memory_bytes() const noexcept {
        return row_ptr.size() * sizeof(uint64_t) +
               targets.size() * sizeof(int32_t) +
               weights.size() * sizeof(float) +
               delays.size() * sizeof(float);
    }

    inline void get_outgoing(
        int32_t node,
        const int32_t*& out_targets,
        const float*& out_weights,
        const float*& out_delays,
        uint32_t& count
    ) const noexcept {
        uint64_t start = row_ptr[node];
        uint64_t end = row_ptr[node + 1];
        count = static_cast<uint32_t>(end - start);
        out_targets = targets.data() + start;
        out_weights = weights.data() + start;
        out_delays = delays.data() + start;
    }

    // Save to portable binary file
    bool save_binary(const std::string& path) const {
        std::ofstream out(path, std::ios::binary);
        if (!out) return false;

        const char magic[4] = {'S', 'C', 'G', '1'};
        out.write(magic, 4);
        out.write(reinterpret_cast<const char*>(&num_nodes), sizeof(num_nodes));
        out.write(reinterpret_cast<const char*>(&num_edges), sizeof(num_edges));

        out.write(reinterpret_cast<const char*>(row_ptr.data()), row_ptr.size() * sizeof(uint64_t));
        out.write(reinterpret_cast<const char*>(targets.data()), targets.size() * sizeof(int32_t));
        out.write(reinterpret_cast<const char*>(weights.data()), weights.size() * sizeof(float));
        out.write(reinterpret_cast<const char*>(delays.data()), delays.size() * sizeof(float));
        return out.good();
    }

    // Load from portable binary file
    static NeuralGraphCSR load_binary(const std::string& path) {
        std::ifstream in(path, std::ios::binary);
        if (!in) throw std::runtime_error("Cannot open graph file: " + path);

        char magic[4];
        in.read(magic, 4);
        if (std::memcmp(magic, "SCG1", 4) != 0) {
            throw std::runtime_error("Invalid SCG1 magic in graph file: " + path);
        }

        NeuralGraphCSR g;
        in.read(reinterpret_cast<char*>(&g.num_nodes), sizeof(g.num_nodes));
        in.read(reinterpret_cast<char*>(&g.num_edges), sizeof(g.num_edges));

        g.row_ptr.resize(g.num_nodes + 1);
        g.targets.resize(g.num_edges);
        g.weights.resize(g.num_edges);
        g.delays.resize(g.num_edges);

        in.read(reinterpret_cast<char*>(g.row_ptr.data()), g.row_ptr.size() * sizeof(uint64_t));
        in.read(reinterpret_cast<char*>(g.targets.data()), g.targets.size() * sizeof(int32_t));
        in.read(reinterpret_cast<char*>(g.weights.data()), g.weights.size() * sizeof(float));
        in.read(reinterpret_cast<char*>(g.delays.data()), delays_size(g.num_edges));
        if (!in) throw std::runtime_error("Error reading graph data from: " + path);
        return g;
    }

private:
    static size_t delays_size(uint64_t n) { return n * sizeof(float); }
};

class NeuralGraphLiteral {
public:
    int32_t num_nodes = 0;
    std::vector<std::vector<int32_t>> adj_targets;
    std::vector<std::vector<float>> adj_weights;
    std::vector<std::vector<float>> adj_delays;

    size_t memory_bytes() const noexcept {
        size_t b = adj_targets.capacity() * sizeof(std::vector<int32_t>);
        for (int32_t i = 0; i < num_nodes; ++i) {
            b += adj_targets[i].capacity() * sizeof(int32_t);
            b += adj_weights[i].capacity() * sizeof(float);
            b += adj_delays[i].capacity() * sizeof(float);
        }
        return b;
    }

    static NeuralGraphLiteral from_csr(const NeuralGraphCSR& csr) {
        NeuralGraphLiteral lit;
        lit.num_nodes = csr.num_nodes;
        lit.adj_targets.resize(csr.num_nodes);
        lit.adj_weights.resize(csr.num_nodes);
        lit.adj_delays.resize(csr.num_nodes);

        for (int32_t u = 0; u < csr.num_nodes; ++u) {
            uint64_t start = csr.row_ptr[u];
            uint64_t end = csr.row_ptr[u + 1];
            size_t deg = end - start;
            (void)deg;
            lit.adj_targets[u].assign(csr.targets.begin() + start, csr.targets.begin() + end);
            lit.adj_weights[u].assign(csr.weights.begin() + start, csr.weights.begin() + end);
            lit.adj_delays[u].assign(csr.delays.begin() + start, csr.delays.begin() + end);
        }
        return lit;
    }
};

class GraphFactory {
public:
    static NeuralGraphCSR create_random(
        int32_t num_nodes,
        int32_t mean_out_degree,
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

        std::vector<std::vector<uint32_t>> all_targets(num_nodes);
        std::vector<std::vector<float>> all_weights(num_nodes);
        std::vector<std::vector<float>> all_delays(num_nodes);

        uint64_t total_edges = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            std::vector<uint32_t> targets = rng.sample_unique(k, static_cast<uint32_t>(num_nodes), static_cast<uint32_t>(u));
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

    static NeuralGraphCSR create_modular(
        int32_t num_nodes,
        int32_t mean_out_degree,
        uint64_t seed,
        int32_t num_clusters = 4,
        float intra_prob = 0.80f,
        float weight_scale = 0.25f,
        float min_delay = 0.2f,
        float max_delay = 2.0f
    ) {
        DeterministicRNG rng(seed);
        NeuralGraphCSR g;
        g.num_nodes = num_nodes;
        g.row_ptr.resize(num_nodes + 1, 0);

        if (num_clusters <= 1 || num_nodes <= num_clusters) {
            return create_random(num_nodes, mean_out_degree, seed, weight_scale, min_delay, max_delay);
        }

        int32_t cluster_size = (num_nodes + num_clusters - 1) / num_clusters;
        uint32_t k = std::min(static_cast<uint32_t>(mean_out_degree),
                              (num_nodes > 1) ? static_cast<uint32_t>(num_nodes - 1) : 0U);

        std::vector<std::vector<uint32_t>> all_targets(num_nodes);
        std::vector<std::vector<float>> all_weights(num_nodes);
        std::vector<std::vector<float>> all_delays(num_nodes);

        uint64_t total_edges = 0;
        for (int32_t u = 0; u < num_nodes; ++u) {
            int32_t my_cluster = u / cluster_size;
            uint32_t c_start = static_cast<uint32_t>(my_cluster * cluster_size);
            uint32_t c_end = std::min(static_cast<uint32_t>((my_cluster + 1) * cluster_size), static_cast<uint32_t>(num_nodes));
            uint32_t c_len = c_end - c_start;

            std::vector<uint32_t> targets;
            targets.reserve(k);

            while (targets.size() < k) {
                bool choose_intra = (rng.uniform_float(0.0f, 1.0f) < intra_prob) && (c_len > 1);
                uint32_t cand = 0;
                if (choose_intra) {
                    cand = c_start + rng.uniform_uint(c_len);
                } else {
                    cand = rng.uniform_uint(num_nodes);
                }

                if (cand == static_cast<uint32_t>(u)) continue;

                bool dup = false;
                for (uint32_t x : targets) {
                    if (x == cand) { dup = true; break; }
                }
                if (!dup) targets.push_back(cand);
            }
            std::sort(targets.begin(), targets.end());

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
};

class EventGenerator {
public:
    static std::vector<ExternalEvent> generate(
        int32_t num_nodes,
        double active_fraction,
        double rate_hz,
        double t_max,
        uint64_t seed,
        const std::string& timing_type = "poisson"
    ) {
        DeterministicRNG rng(seed);
        uint32_t m = std::max(1U, static_cast<uint32_t>(std::round(num_nodes * active_fraction)));
        m = std::min(m, static_cast<uint32_t>(num_nodes));

        std::vector<uint32_t> active_nodes = rng.sample_unique(m, static_cast<uint32_t>(num_nodes), UINT32_MAX);

        std::vector<ExternalEvent> events;
        for (uint32_t node : active_nodes) {
            double curr_t = 0.0;
            if (timing_type == "regular") {
                double interval = 1.0 / rate_hz;
                curr_t = rng.uniform_double(0.0, interval);
                while (curr_t <= t_max) {
                    events.push_back({curr_t, static_cast<int32_t>(node), 1.2f, -1, static_cast<int32_t>(EventKind::EXTERNAL)});
                    curr_t += interval;
                }
            } else if (timing_type == "bursty") {
                // Bursts of events with Poisson inter-burst intervals
                curr_t = rng.exponential(rate_hz * 0.2); // burst arrival
                while (curr_t <= t_max) {
                    uint32_t burst_size = 1 + rng.uniform_uint(5);
                    for (uint32_t b = 0; b < burst_size && curr_t <= t_max; ++b) {
                        events.push_back({curr_t + b * 0.05, static_cast<int32_t>(node), 1.2f, -1, static_cast<int32_t>(EventKind::EXTERNAL)});
                    }
                    curr_t += rng.exponential(rate_hz * 0.2);
                }
            } else {
                // Default: Poisson process
                curr_t = rng.exponential(rate_hz);
                while (curr_t <= t_max) {
                    events.push_back({curr_t, static_cast<int32_t>(node), 1.2f, -1, static_cast<int32_t>(EventKind::EXTERNAL)});
                    curr_t += rng.exponential(rate_hz);
                }
            }
        }

        // Sort events deterministically by timestamp, then by target
        std::sort(events.begin(), events.end(), [](const ExternalEvent& a, const ExternalEvent& b) {
            if (a.timestamp != b.timestamp) return a.timestamp < b.timestamp;
            return a.target < b.target;
        });

        return events;
    }

    static bool save_binary(const std::vector<ExternalEvent>& events, const std::string& path) {
        std::ofstream out(path, std::ios::binary);
        if (!out) return false;
        const char magic[4] = {'S', 'C', 'E', '1'};
        out.write(magic, 4);
        uint64_t count = events.size();
        out.write(reinterpret_cast<const char*>(&count), sizeof(count));
        for (const auto& ev : events) {
            out.write(reinterpret_cast<const char*>(&ev.timestamp), sizeof(ev.timestamp));
            out.write(reinterpret_cast<const char*>(&ev.target), sizeof(ev.target));
            out.write(reinterpret_cast<const char*>(&ev.amplitude), sizeof(ev.amplitude));
            out.write(reinterpret_cast<const char*>(&ev.source), sizeof(ev.source));
            out.write(reinterpret_cast<const char*>(&ev.kind), sizeof(ev.kind));
        }
        return out.good();
    }

    static std::vector<ExternalEvent> load_binary(const std::string& path) {
        std::ifstream in(path, std::ios::binary);
        if (!in) throw std::runtime_error("Cannot open events file: " + path);
        char magic[4];
        in.read(magic, 4);
        if (std::memcmp(magic, "SCE1", 4) != 0) throw std::runtime_error("Invalid SCE1 magic: " + path);
        uint64_t count = 0;
        in.read(reinterpret_cast<char*>(&count), sizeof(count));
        std::vector<ExternalEvent> events(count);
        for (uint64_t i = 0; i < count; ++i) {
            in.read(reinterpret_cast<char*>(&events[i].timestamp), sizeof(events[i].timestamp));
            in.read(reinterpret_cast<char*>(&events[i].target), sizeof(events[i].target));
            in.read(reinterpret_cast<char*>(&events[i].amplitude), sizeof(events[i].amplitude));
            in.read(reinterpret_cast<char*>(&events[i].source), sizeof(events[i].source));
            in.read(reinterpret_cast<char*>(&events[i].kind), sizeof(events[i].kind));
        }
        return events;
    }
};

} // namespace sc
