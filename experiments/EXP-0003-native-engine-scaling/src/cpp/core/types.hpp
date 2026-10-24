#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <cmath>
#include <sys/resource.h>

namespace sc {

enum class EventKind : int32_t {
    EXTERNAL = 0,
    SPIKE = 1,
    FEEDBACK = 2,
    PACEMAKER = 3,
    PROBE = 4,
    SHAM = 5
};

struct Event {
    double timestamp;
    uint64_t seq_id;
    int32_t source;
    int32_t target;
    float amplitude;
    int32_t kind;

    // Deterministic priority ordering:
    // 1. timestamp (earlier first)
    // 2. target (lower node index first)
    // 3. source (lower source index first)
    // 4. seq_id (stable tie-breaking)
    bool operator>(const Event& other) const noexcept {
        if (timestamp != other.timestamp) {
            return timestamp > other.timestamp;
        }
        if (target != other.target) {
            return target > other.target;
        }
        if (source != other.source) {
            return source > other.source;
        }
        return seq_id > other.seq_id;
    }

    bool operator<(const Event& other) const noexcept {
        if (timestamp != other.timestamp) {
            return timestamp < other.timestamp;
        }
        if (target != other.target) {
            return target < other.target;
        }
        if (source != other.source) {
            return source < other.source;
        }
        return seq_id < other.seq_id;
    }

    bool operator==(const Event& other) const noexcept {
        return timestamp == other.timestamp &&
               target == other.target &&
               source == other.source &&
               seq_id == other.seq_id &&
               amplitude == other.amplitude &&
               kind == other.kind;
    }
};

struct SubstrateConfig {
    int32_t num_nodes = 128;
    int32_t mean_out_degree = 16;
    float tau_m = 5.0f;
    float threshold = 1.0f;
    float v_reset = 0.0f;
    float refractory_period = 1.0f;
    float min_delay = 0.2f;
    float max_delay = 2.0f;
    int32_t history_capacity_L = 0;
    int32_t trace_bases_B = 0;
    bool homeostasis = false;
    float homeostasis_rate = 0.05f;
    float homeostasis_tau = 20.0f;
};

struct SpikeRecord {
    double timestamp;
    int32_t node;

    bool operator==(const SpikeRecord& other) const noexcept {
        return std::abs(timestamp - other.timestamp) < 1e-6 && node == other.node;
    }
};

struct ExternalEvent {
    double timestamp;
    int32_t target;
    float amplitude;
    int32_t source = -1;
    int32_t kind = static_cast<int32_t>(EventKind::EXTERNAL);
};

struct SimulationResult {
    std::string scheduler_name;
    double wall_time_sec = 0.0;
    uint64_t total_events_processed = 0;
    uint64_t total_edges_traversed = 0;
    uint64_t total_spikes = 0;
    uint64_t peak_queue_size = 0;
    double final_time = 0.0;
    std::vector<float> final_potentials;
    std::vector<SpikeRecord> spike_records;
    uint64_t state_digest = 0;
    double injected_active_fraction = 0.0;
    double propagated_active_fraction = 0.0;
    bool max_queue_exceeded = false;
    uint64_t rss_bytes = 0;             // Actual OS peak RSS measured via getrusage
    uint64_t estimated_memory_bytes = 0; // Model-based theoretical estimate
    uint64_t lock_waits = 0;
    uint64_t causal_stalls = 0;
    uint64_t cross_region_events = 0;
};

// Query operating system process peak resident set size
inline uint64_t get_actual_peak_rss_bytes() noexcept {
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
#if defined(__APPLE__)
        return static_cast<uint64_t>(usage.ru_maxrss); // bytes on Darwin
#else
        return static_cast<uint64_t>(usage.ru_maxrss) * 1024ULL; // kilobytes on Linux
#endif
    }
    return 0;
}

// 64-bit FNV-1a hash combiner
inline uint64_t hash_combine64(uint64_t hash, uint64_t value) noexcept {
    hash ^= value;
    hash *= 1099511628211ULL;
    return hash;
}

inline uint64_t compute_state_digest(
    const std::vector<SpikeRecord>& spikes,
    const std::vector<float>& potentials
) noexcept {
    uint64_t h = 14695981039346656037ULL; // FNV-1a 64-bit offset basis
    for (const auto& spk : spikes) {
        union { double d; uint64_t u; } u_t;
        u_t.d = spk.timestamp;
        h = hash_combine64(h, u_t.u);
        h = hash_combine64(h, static_cast<uint64_t>(static_cast<uint32_t>(spk.node)));
    }
    for (float v : potentials) {
        union { float f; uint32_t u; } u_v;
        u_v.f = v;
        h = hash_combine64(h, static_cast<uint64_t>(u_v.u));
    }
    return h;
}

} // namespace sc
