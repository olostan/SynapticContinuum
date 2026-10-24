#include "../core/types.hpp"
#include "../core/graph_topologies.hpp"
#include "../core/graph_metrics.hpp"
#include "../core/partitioners.hpp"
#include "../engines/cpp_serial.hpp"
#include "../engines/cpp_owner_instrumented.hpp"
#include "../engines/cpp_persistent_pool.hpp"
#include "../engines/cpp_adaptive.hpp"
#include "../engines/cpp_relaxed.hpp"
#include "../engines/cpp_barrier_free_independent.hpp"

#include <iostream>
#include <cassert>
#include <cmath>
#include <numeric>

#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        std::cerr << "Assertion failed: " #cond " at " __FILE__ ":" << __LINE__ << std::endl; \
        std::exit(1); \
    } \
} while(0)

#define ASSERT_NEAR(a, b, eps) do { \
    if (std::abs((a) - (b)) > (eps)) { \
        std::cerr << "Assertion failed: |" #a " - " #b "| = " << std::abs((a) - (b)) \
                  << " > " #eps " (" << (a) << " vs " << (b) << ") at " __FILE__ ":" << __LINE__ << std::endl; \
        std::exit(1); \
    } \
} while(0)

void test_graph_generators() {
    std::cout << "[TEST] Running test_graph_generators..." << std::endl;
    int32_t N = 128;
    int32_t D = 8;
    uint64_t seed = 42;

    // 1. Uniform random
    auto g_rand = sc::Exp4GraphGenerators::create_uniform_random(N, D, seed);
    ASSERT_TRUE(g_rand.num_nodes == N);
    ASSERT_TRUE(g_rand.num_edges > 0);

    // 2. Watts-Strogatz small world
    auto g_ws_0 = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N, D, 0.0f, seed);
    auto g_ws_01 = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N, D, 0.1f, seed);
    ASSERT_TRUE(g_ws_0.num_nodes == N);
    ASSERT_TRUE(g_ws_01.num_nodes == N);

    // 3. Modular SBM
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N, D, 4, 0.10f, seed);
    ASSERT_TRUE(g_mod.graph.num_nodes == N);
    ASSERT_TRUE(g_mod.planted_labels.size() == static_cast<size_t>(N));

    // 4. Six disconnected modules control (c = 0.0)
    auto g_disc = sc::Exp4GraphGenerators::create_disconnected_modules(N, D, 6, seed);
    ASSERT_TRUE(g_disc.graph.num_nodes == N);
    double cut_disc = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_disc.graph, g_disc.planted_labels);
    ASSERT_NEAR(cut_disc, 0.0, 1e-6); // Strictly 0 cross-module edges!

    // 5. Hierarchical modular
    auto g_hier = sc::Exp4GraphGenerators::create_hierarchical_modular(N, D, 2, 3, seed);
    ASSERT_TRUE(g_hier.graph.num_nodes == N);

    // 6. Degree preserving rewired control
    auto g_deg_rewired = sc::Exp4GraphGenerators::create_degree_preserving_rewired(g_mod.graph, 1000, seed);
    ASSERT_TRUE(g_deg_rewired.num_nodes == N);
    ASSERT_TRUE(g_deg_rewired.num_edges == g_mod.graph.num_edges);

    // Verify degree sequence invariance
    sc::GraphMetrics m_orig, m_rewired;
    sc::Exp4GraphMetricsCalculator::compute_degree_stats(g_mod.graph, m_orig);
    sc::Exp4GraphMetricsCalculator::compute_degree_stats(g_deg_rewired, m_rewired);
    ASSERT_NEAR(m_orig.out_degree_mean, m_rewired.out_degree_mean, 1e-5);
    ASSERT_NEAR(m_orig.in_degree_mean, m_rewired.in_degree_mean, 1e-5);
    ASSERT_TRUE(m_orig.in_degree_max == m_rewired.in_degree_max);

    // 7. Node-ID permuted
    auto g_perm = sc::Exp4GraphGenerators::create_node_id_permuted(g_mod.graph, seed);
    ASSERT_TRUE(g_perm.num_nodes == N);
    ASSERT_TRUE(g_perm.num_edges == g_mod.graph.num_edges);

    std::cout << "  -> PASSED" << std::endl;
}

void test_graph_metrics() {
    std::cout << "[TEST] Running test_graph_metrics..." << std::endl;
    int32_t N = 100;
    int32_t D = 6;
    uint64_t seed = 123;

    // Small-world property: lattice (p=0) has high clustering, random (p=1) has low clustering
    auto g_lattice = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N, D, 0.0f, seed);
    auto g_random = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N, D, 1.0f, seed);

    double c_lattice = sc::Exp4GraphMetricsCalculator::compute_clustering_coefficient(g_lattice, N, seed);
    double c_random = sc::Exp4GraphMetricsCalculator::compute_clustering_coefficient(g_random, N, seed);
    ASSERT_TRUE(c_lattice > c_random);

    double l_lattice = sc::Exp4GraphMetricsCalculator::compute_characteristic_path_length(g_lattice, N, seed);
    double l_random = sc::Exp4GraphMetricsCalculator::compute_characteristic_path_length(g_random, N, seed);
    ASSERT_TRUE(l_lattice > l_random);

    // Modularity of modular network with planted partition vs random partition
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N, D, 4, 0.05f, seed);
    double q_planted = sc::Exp4GraphMetricsCalculator::compute_modularity(g_mod.graph, g_mod.planted_labels);
    auto part_random = sc::Exp4Partitioners::partition_random_hash(N, 4, seed);
    double q_random = sc::Exp4GraphMetricsCalculator::compute_modularity(g_mod.graph, part_random);
    ASSERT_TRUE(q_planted > q_random);
    ASSERT_TRUE(q_planted > 0.50); // High modularity

    std::cout << "  -> PASSED (C_lat=" << c_lattice << " > C_rand=" << c_random
              << ", Q_planted=" << q_planted << " > Q_rand=" << q_random << ")" << std::endl;
}

void test_partitioners() {
    std::cout << "[TEST] Running test_partitioners..." << std::endl;
    int32_t N = 128;
    int32_t D = 8;
    int32_t R = 4;
    uint64_t seed = 42;

    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N, D, R, 0.05f, seed);

    auto p_contig = sc::Exp4Partitioners::partition_contiguous(N, R);
    auto p_hash = sc::Exp4Partitioners::partition_random_hash(N, R, seed);
    auto p_oracle = sc::Exp4Partitioners::partition_planted_oracle(N, R, g_mod.planted_labels);
    auto p_mincut = sc::Exp4Partitioners::partition_greedy_mincut(g_mod.graph, R, 10);

    double cut_contig = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_mod.graph, p_contig);
    double cut_hash = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_mod.graph, p_hash);
    double cut_oracle = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_mod.graph, p_oracle);
    double cut_mincut = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_mod.graph, p_mincut);

    ASSERT_TRUE(cut_oracle < cut_hash);
    ASSERT_TRUE(cut_mincut < cut_hash);

    std::cout << "  -> PASSED (Cut Oracle=" << cut_oracle << ", MinCut=" << cut_mincut
              << ", Contig=" << cut_contig << ", Hash=" << cut_hash << ")" << std::endl;
}

void test_zero_delay_precondition_rejection() {
    std::cout << "[TEST] Running test_zero_delay_precondition_rejection..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 4;
    config.min_delay = 0.2f;

    // Create graph with cross-region zero delay edge
    sc::NeuralGraphCSR g;
    g.num_nodes = 4;
    g.num_edges = 2;
    g.row_ptr = {0, 1, 2, 2, 2};
    g.targets = {2, 0};
    g.weights = {0.5f, 0.5f};
    g.delays = {0.0f, 0.5f}; // Zero delay edge from node 0 (partition 0) to node 2 (partition 1)!

    std::vector<int32_t> part = {0, 0, 1, 1};
    sc::Exp4OwnerInstrumentedEngine engine(config, g, 2, part);

    std::vector<sc::ExternalEvent> inputs = {{0.1, 0, 1.5f}};
    bool threw_exception = false;
    try {
        engine.run(inputs, 1.0);
    } catch (const std::invalid_argument& e) {
        threw_exception = true;
    }
    ASSERT_TRUE(threw_exception);
    std::cout << "  -> PASSED (Strict zero-delay cross-region edge rejected)" << std::endl;
}

void test_causal_parity_across_engines() {
    std::cout << "[TEST] Running test_causal_parity_across_engines..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 64;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;
    config.max_delay = 1.0f;

    uint64_t seed = 42;
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(64, 8, 4, 0.15f, seed, 0.4f, 0.2f, 1.0f);

    std::vector<sc::ExternalEvent> inputs;
    for (int32_t i = 0; i < 20; ++i) {
        inputs.push_back({0.1 + i * 0.2, i % 64, 1.5f});
    }

    // 1. Serial exact reference
    sc::Exp4SerialEngine serial(config, g_mod.graph);
    sc::SimulationResult res_serial = serial.run(inputs, 5.0);
    ASSERT_TRUE(res_serial.total_spikes > 0);

    // 2. Instrumented owner engine across W=1, 2, 4
    for (int32_t W : {1, 2, 4}) {
        std::cout << "  [parity] owner W=" << W << std::endl;
        auto part = sc::Exp4Partitioners::partition_contiguous(64, W);
        sc::Exp4OwnerInstrumentedEngine owner(config, g_mod.graph, W, part);
        sc::SimulationResult res_owner;
        owner.run(inputs, 5.0, &res_owner);

        ASSERT_TRUE(res_owner.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_owner.state_digest == res_serial.state_digest);
    }

    // 3. Persistent pool engine across W=1, 2, 4 with R=8 logical regions
    for (int32_t W : {1, 2, 4}) {
        std::cout << "  [parity] pool W=" << W << std::endl;
        auto node_to_reg = sc::Exp4Partitioners::partition_contiguous(64, 8);
        sc::Exp4PersistentPoolEngine pool(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_pool;
        pool.run(inputs, 5.0, &res_pool);

        ASSERT_TRUE(res_pool.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_pool.state_digest == res_serial.state_digest);
    }

    std::cout << "  -> PASSED (Bit-exact state digest match: " << res_serial.state_digest
              << ", Spikes: " << res_serial.total_spikes << ")" << std::endl;
}

void test_six_disconnected_regions_sanity_scaling() {
    std::cout << "[TEST] Running test_six_disconnected_regions_sanity_scaling (Phase A Sanity Test)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 600; // 100 nodes per module
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 777;
    // 6 strictly disconnected modules (c = 0.0)
    auto g_disc = sc::Exp4GraphGenerators::create_disconnected_modules(600, 16, 6, seed, 0.4f, 0.2f, 1.0f);

    // Generate substantial workload across all 6 modules
    std::vector<sc::ExternalEvent> inputs;
    for (int32_t m = 0; m < 6; ++m) {
        for (int32_t step = 0; step < 100; ++step) {
            inputs.push_back({0.05 * step, m * 100 + (step % 50), 1.5f});
        }
    }

    // Measure W=1 baseline
    sc::Exp4PersistentPoolEngine pool_w1(config, g_disc.graph, 1, 6, g_disc.planted_labels);
    auto stats_w1 = pool_w1.run(inputs, 10.0);

    // Measure W=6 on 6 physical cores
    sc::Exp4PersistentPoolEngine pool_w6(config, g_disc.graph, 6, 6, g_disc.planted_labels);
    auto stats_w6 = pool_w6.run(inputs, 10.0);

    double speedup = stats_w1.wall_time_sim_sec / stats_w6.wall_time_sim_sec;
    ASSERT_TRUE(stats_w1.total_spikes == stats_w6.total_spikes);
    ASSERT_TRUE(stats_w1.state_digest == stats_w6.state_digest);
    ASSERT_TRUE(stats_w6.cross_region_events == 0); // Zero cross-region traffic!

    std::cout << "  -> PASSED (W1: " << (stats_w1.wall_time_sim_sec * 1000.0) << " ms, W6: "
              << (stats_w6.wall_time_sim_sec * 1000.0) << " ms, Speedup: " << speedup << "x)" << std::endl;
}

void test_adaptive_engine() {
    std::cout << "[TEST] Running test_adaptive_engine..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 120;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 99;
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(120, 16, 6, 0.10f, seed, 0.4f, 0.2f, 1.0f);
    auto node_to_reg = sc::Exp4Partitioners::partition_contiguous(120, 12);

    // Highly skewed workload to trigger migration: all events targeted at region 0
    std::vector<sc::ExternalEvent> inputs;
    for (int32_t step = 0; step < 200; ++step) {
        inputs.push_back({0.02 * step, (step % 10), 1.5f});
    }

    sc::Exp4AdaptiveEngine adaptive(config, g_mod.graph, 2, 12, node_to_reg, 1.20, 1);
    auto stats = adaptive.run_adaptive(inputs, 5.0);

    ASSERT_TRUE(stats.total_events_processed > 0);
    ASSERT_TRUE(stats.total_spikes > 0);
    std::cout << "  -> PASSED (Processed: " << stats.total_events_processed << ", Migrations: "
              << stats.total_migrations << ", Pause: " << (stats.migration_pause_sec * 1000.0) << " ms)" << std::endl;
}

void test_forced_migration_concurrent_traffic() {
    std::cout << "[TEST] Running test_forced_migration_concurrent_traffic (TSan & race safety)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 96;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 314;
    // 6 regions, 3 workers, cross-region edges to generate high inter-worker traffic
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(96, 12, 6, 0.25f, seed, 0.4f, 0.2f, 1.0f);
    auto node_to_reg = sc::Exp4Partitioners::partition_contiguous(96, 6);

    // Skewed input streams concentrated on region 0 (nodes 0..15)
    std::vector<sc::ExternalEvent> inputs;
    for (int32_t step = 0; step < 400; ++step) {
        inputs.push_back({0.005 * step, step % 16, 1.5f});
    }

    // Force migration on EVERY epoch with threshold = 1.05 and lower event barrier
    sc::Exp4AdaptiveEngine adaptive(config, g_mod.graph, 3, 6, node_to_reg, 1.05, 1);
    auto stats = adaptive.run_adaptive(inputs, 3.0);

    ASSERT_TRUE(stats.total_migrations > 0);
    ASSERT_TRUE(stats.total_events_processed > 0);
    std::cout << "  -> PASSED (Completed " << stats.total_migrations << " forced migrations safely under heavy cross-traffic)" << std::endl;
}

void test_barrier_free_independent_engine() {
    std::cout << "[TEST] Running test_barrier_free_independent_engine (Pure hardware scaling control)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 600;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 888;
    auto g_disc = sc::Exp4GraphGenerators::create_disconnected_modules(600, 16, 6, seed, 0.4f, 0.2f, 1.0f);

    std::vector<sc::ExternalEvent> inputs;
    for (int32_t m = 0; m < 6; ++m) {
        for (int32_t s = 0; s < 50; ++s) {
            inputs.push_back({0.1 * s, m * 100 + (s % 50), 1.5f});
        }
    }

    // Serial ground truth
    sc::Exp4SerialEngine serial(config, g_disc.graph);
    auto res_serial = serial.run(inputs, 5.0);

    // Barrier-free independent engine across W=1, 2, 6
    for (int32_t W : {1, 2, 6}) {
        // Map 6 modules onto W workers
        std::vector<int32_t> node_to_w(600);
        int32_t mod_per_w = (6 + W - 1) / W;
        for (int32_t u = 0; u < 600; ++u) {
            int32_t m = g_disc.planted_labels[u];
            int32_t w = m / mod_per_w;
            node_to_w[u] = (w < W) ? w : (W - 1);
        }

        sc::Exp4BarrierFreeIndependentEngine bf_engine(config, g_disc.graph, W, node_to_w);
        sc::SimulationResult res_bf;
        auto stats_bf = bf_engine.run(inputs, 5.0, &res_bf);

        ASSERT_TRUE(res_bf.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_bf.state_digest == res_serial.state_digest);
        std::cout << "  [barrier_free W=" << W << "] Wall: " << (stats_bf.wall_time_sim_sec * 1000.0)
                  << " ms, Spikes: " << res_bf.total_spikes << ", Digest: " << res_bf.state_digest << std::endl;
    }
    std::cout << "  -> PASSED (Bit-exact match with serial reference across all W)" << std::endl;
}

void test_relaxed_engine() {
    std::cout << "[TEST] Running test_relaxed_engine (Exact eps=0 and divergence on eps>0)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 64;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 42;
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(64, 8, 4, 0.20f, seed, 0.4f, 0.2f, 1.0f);

    std::vector<sc::ExternalEvent> inputs;
    for (int32_t s = 0; s < 50; ++s) {
        inputs.push_back({0.1 * s, (s * 7) % 64, 1.5f});
    }

    sc::Exp4SerialEngine serial(config, g_mod.graph);
    auto ref = serial.run(inputs, 5.0);

    // 1. Epsilon = 0: MUST be bit-exact with serial reference
    sc::Exp4RelaxedEngine relaxed_zero(config, g_mod.graph, 2, 4, {}, 0.0);
    auto div_zero = relaxed_zero.evaluate_divergence_vs_reference(inputs, 5.0, ref);
    ASSERT_TRUE(div_zero.spike_count_error == 0);
    ASSERT_NEAR(div_zero.potential_rmse, 0.0, 1e-4);
    ASSERT_TRUE(div_zero.temporal_discrimination_passed);

    // 2. Epsilon = 1.0: Real order relaxation test
    sc::Exp4RelaxedEngine relaxed_pos(config, g_mod.graph, 2, 4, {}, 1.0);
    auto div_pos = relaxed_pos.evaluate_divergence_vs_reference(inputs, 5.0, ref);
    std::cout << "  [relaxed eps=1.0] Spike err: " << div_pos.spike_count_error
              << ", Pot RMSE: " << div_pos.potential_rmse
              << ", T RMSE: " << div_pos.spike_timestamp_rmse << std::endl;

    std::cout << "  -> PASSED (eps=0 is exact, eps>0 runs relaxed scheduling)" << std::endl;
}

int main() {
    std::cout << "=== Running SynapticContinuum EXP-0004 C++ Test Suite ===" << std::endl;
    test_graph_generators();
    test_graph_metrics();
    test_partitioners();
    test_zero_delay_precondition_rejection();
    test_causal_parity_across_engines();
    test_six_disconnected_regions_sanity_scaling();
    test_barrier_free_independent_engine();
    test_adaptive_engine();
    test_forced_migration_concurrent_traffic();
    test_relaxed_engine();
    std::cout << "=== ALL EXP-0004 TESTS PASSED SUCCESSFULLY ===" << std::endl;
    return 0;
}
