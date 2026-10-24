#pragma once

#include "../../../../EXP-0003-native-engine-scaling/src/cpp/core/types.hpp"
#include <string>
#include <vector>
#include <cstdint>
#include <chrono>

namespace sc {

enum class Exp4TopologyType : int32_t {
    UNIFORM_RANDOM = 0,
    WATTS_STROGATZ = 1,
    MODULAR_SBM = 2,
    DISCONNECTED_MODULES = 3,
    HIERARCHICAL_MODULAR = 4,
    DEGREE_PRESERVED_REWIRED = 5,
    NODE_ID_PERMUTED = 6,
    BIOLOGICAL_CONNECTOME = 7
};

inline std::string topology_type_to_string(Exp4TopologyType type) {
    switch (type) {
        case Exp4TopologyType::UNIFORM_RANDOM: return "uniform_random";
        case Exp4TopologyType::WATTS_STROGATZ: return "watts_strogatz";
        case Exp4TopologyType::MODULAR_SBM: return "modular_sbm";
        case Exp4TopologyType::DISCONNECTED_MODULES: return "disconnected_modules";
        case Exp4TopologyType::HIERARCHICAL_MODULAR: return "hierarchical_modular";
        case Exp4TopologyType::DEGREE_PRESERVED_REWIRED: return "degree_preserved_rewired";
        case Exp4TopologyType::NODE_ID_PERMUTED: return "node_id_permuted";
        case Exp4TopologyType::BIOLOGICAL_CONNECTOME: return "biological_connectome";
        default: return "unknown";
    }
}

enum class Exp4PartitionType : int32_t {
    CONTIGUOUS = 0,
    RANDOM_HASH = 1,
    PLANTED_ORACLE = 2,
    GREEDY_MINCUT = 3,
    ACTIVITY_AWARE = 4,
    METIS_KWAY = 5,
    IGRAPH_LEIDEN = 6
};

inline std::string partition_type_to_string(Exp4PartitionType type) {
    switch (type) {
        case Exp4PartitionType::CONTIGUOUS: return "contiguous";
        case Exp4PartitionType::RANDOM_HASH: return "random_hash";
        case Exp4PartitionType::PLANTED_ORACLE: return "planted_oracle";
        case Exp4PartitionType::GREEDY_MINCUT: return "greedy_boundary_heuristic";
        case Exp4PartitionType::ACTIVITY_AWARE: return "activity_aware";
        case Exp4PartitionType::METIS_KWAY: return "metis_kway";
        case Exp4PartitionType::IGRAPH_LEIDEN: return "igraph_leiden";
        default: return "unknown";
    }
}

struct GraphMetrics {
    double clustering_coefficient = 0.0;
    double characteristic_path_length = 0.0;
    double small_world_sigma = 0.0;
    double modularity_q = 0.0;
    double edge_cut_fraction = 0.0;
    double active_event_cut_fraction = 0.0;
    double in_degree_mean = 0.0;
    uint32_t in_degree_max = 0;
    double in_degree_var = 0.0;
    double out_degree_mean = 0.0;
    uint32_t out_degree_max = 0;
    double out_degree_var = 0.0;
};

struct Exp4ProfilingStats {
    std::string scheduler_name;
    int32_t num_workers = 1;
    int32_t num_regions = 1;
    double wall_time_sim_sec = 0.0;
    double wall_time_total_sec = 0.0;
    uint64_t total_events_processed = 0;
    uint64_t total_edges_traversed = 0;
    uint64_t total_spikes = 0;
    uint64_t cross_region_events = 0;
    uint64_t total_migrations = 0;
    uint64_t migrated_queue_events = 0;
    uint64_t migrated_mailbox_events = 0;
    double migration_pause_sec = 0.0;
    double edge_cut_fraction = 0.0;
    double active_event_cut_fraction = 0.0;
    double backlog_imbalance_ratio = 1.0; // max_events_worker / mean_events_worker
    size_t peak_rss_bytes = 0;
    uint64_t state_digest = 0;

    // Per-worker fine-grained timing breakdowns (seconds)
    std::vector<double> worker_active_sec;
    std::vector<double> worker_barrier1_sec;
    std::vector<double> worker_mailbox_sec;
    std::vector<double> worker_barrier2_sec;
    std::vector<uint64_t> worker_events_processed;
    double thread_spawn_join_overhead_sec = 0.0;

    // Pairwise watermark telemetry
    uint64_t watermark_monotonicity_violations = 0;
    uint64_t delayed_channel_deliveries = 0;
    uint64_t horizon_clamp_events = 0;
};

// Trace event for replay microbenchmarking
struct TraceEvent {
    double timestamp;
    int32_t source;
    int32_t target;
    float amplitude;
    int32_t kind;
};

} // namespace sc
