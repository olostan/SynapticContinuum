#include "../core/types.hpp"
#include "../core/graph_topologies.hpp"
#include "../core/graph_representations.hpp"
#include "../core/graph_metrics.hpp"
#include "../core/partitioners.hpp"
#include "../engines/cpp_serial.hpp"
#include "../engines/cpp_owner_instrumented.hpp"
#include "../engines/cpp_persistent_pool.hpp"
#include "../engines/cpp_openmp_epoch.hpp"
#include "../engines/cpp_pairwise_watermark.hpp"
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

    // 3. Modular SBM (direct flat vs vec-of-vec bit-exact equivalence)
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N, D, 4, 0.10f, seed);
    auto g_mod_vov = sc::Exp4GraphGenerators::create_modular_sbm_vec_of_vec(N, D, 4, 0.10f, seed);
    ASSERT_TRUE(g_mod.graph.num_nodes == N);
    ASSERT_TRUE(g_mod.graph.num_edges == g_mod_vov.graph.num_edges);
    ASSERT_TRUE(g_mod.graph.targets == g_mod_vov.graph.targets);
    ASSERT_TRUE(g_mod.graph.weights == g_mod_vov.graph.weights);
    ASSERT_TRUE(g_mod.graph.delays == g_mod_vov.graph.delays);
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

    // 3. Persistent pool engine across W=1, 2, 4 with R=8 logical regions (BinaryHeap, DaryHeap<4>, DaryHeap<8>, BucketEventQueue)
    for (int32_t W : {1, 2, 4}) {
        std::cout << "  [parity] pool BinaryHeap/Dary4/Dary8/Bucket W=" << W << std::endl;
        auto node_to_reg = sc::Exp4Partitioners::partition_contiguous(64, 8);
        sc::Exp4PersistentPoolEngineT<sc::BinaryHeapQueue> pool_bin(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_bin;
        pool_bin.run(inputs, 5.0, &res_bin);
        ASSERT_TRUE(res_bin.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_bin.state_digest == res_serial.state_digest);

        sc::Exp4PersistentPoolEngineT<sc::DaryHeapQueue<4>> pool_d4(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_d4;
        pool_d4.run(inputs, 5.0, &res_d4);
        ASSERT_TRUE(res_d4.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_d4.state_digest == res_serial.state_digest);

        sc::Exp4PersistentPoolEngineT<sc::DaryHeapQueue<8>> pool_d8(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_d8;
        pool_d8.run(inputs, 5.0, &res_d8);
        ASSERT_TRUE(res_d8.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_d8.state_digest == res_serial.state_digest);

        sc::Exp4PersistentPoolEngineT<sc::BucketEventQueue> pool_bkt(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_bkt;
        pool_bkt.run(inputs, 5.0, &res_bkt);
        ASSERT_TRUE(res_bkt.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_bkt.state_digest == res_serial.state_digest);

        // 4. OpenMP Epoch Engine
        sc::Exp4OpenMPEngine omp_eng(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_omp;
        omp_eng.run(inputs, 5.0, &res_omp);
        ASSERT_TRUE(res_omp.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_omp.state_digest == res_serial.state_digest);

        // 5. Pairwise Watermark Engine (no global barriers)
        sc::Exp4PairwiseWatermarkEngine wm_eng(config, g_mod.graph, W, 8, node_to_reg);
        sc::SimulationResult res_wm;
        wm_eng.run(inputs, 5.0, &res_wm);
        ASSERT_TRUE(res_wm.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_wm.state_digest == res_serial.state_digest);
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
    std::cout << "[TEST] Running test_forced_migration_concurrent_traffic (TSan, race safety & bit-exact parity)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 96;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.min_delay = 0.2f;

    uint64_t seed = 314;
    // 6 regions, 3 workers, cross-region edges to generate high inter-worker traffic
    auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(96, 12, 6, 0.25f, seed, 0.4f, 0.2f, 1.0f);
    auto node_to_reg = sc::Exp4Partitioners::partition_contiguous(96, 6);

    // Skewed input streams concentrated on region 0 (nodes 0..15) and region 2 (nodes 32..47)
    std::vector<sc::ExternalEvent> inputs;
    for (int32_t step = 0; step < 400; ++step) {
        inputs.push_back({0.005 * step, step % 16, 1.5f});
        if (step % 3 == 0) {
            inputs.push_back({0.005 * step + 0.001, 32 + (step % 16), 1.5f});
        }
    }

    // Serial ground-truth reference
    sc::Exp4SerialEngine serial(config, g_mod.graph);
    auto res_serial = serial.run(inputs, 3.0);

    // Force migration on EVERY epoch with threshold = 1.01 and min_epoch_events = 1.0
    sc::Exp4AdaptiveEngine adaptive(config, g_mod.graph, 3, 6, node_to_reg, 1.01, 1, 1.0);
    sc::SimulationResult res_adaptive;
    auto stats = adaptive.run_adaptive(inputs, 3.0, &res_adaptive);

    ASSERT_TRUE(stats.total_migrations > 0);
    ASSERT_TRUE(stats.migrated_queue_events > 0);
    ASSERT_TRUE(stats.migrated_mailbox_events > 0);
    ASSERT_TRUE(stats.total_events_processed == res_serial.total_events_processed);
    ASSERT_TRUE(stats.total_spikes == res_serial.total_spikes);
    ASSERT_TRUE(stats.state_digest == res_serial.state_digest);

    std::cout << "  -> PASSED (Migrations: " << stats.total_migrations
              << ", Queue Ev Moved: " << stats.migrated_queue_events
              << ", Mailbox Ev Moved: " << stats.migrated_mailbox_events
              << ", Bit-exact digest match: " << stats.state_digest << ")" << std::endl;
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

    // 1. Epsilon = 0: MUST be bit-exact with serial reference and 100% temporal discrimination accuracy
    sc::Exp4RelaxedEngine relaxed_zero(config, g_mod.graph, 2, 4, {}, 0.0);
    auto div_zero = relaxed_zero.evaluate_divergence_vs_reference(inputs, 5.0, ref, 100);
    ASSERT_TRUE(div_zero.spike_count_error == 0);
    ASSERT_TRUE(div_zero.backward_time_events == 0);
    ASSERT_TRUE(div_zero.state_digest == div_zero.reference_digest);
    ASSERT_NEAR(div_zero.potential_rmse, 0.0, 1e-4);
    ASSERT_NEAR(div_zero.temporal_discrimination_accuracy, 1.0, 1e-6);
    ASSERT_TRUE(div_zero.temporal_discrimination_passed);

    // 2. Epsilon = 1.0: Real order relaxation test with measured backward-time violations and degraded discrimination
    sc::Exp4RelaxedEngine relaxed_pos(config, g_mod.graph, 2, 4, {}, 1.0);
    auto div_pos = relaxed_pos.evaluate_divergence_vs_reference(inputs, 5.0, ref, 100);
    ASSERT_TRUE(div_pos.backward_time_events > 0);
    ASSERT_TRUE(div_pos.temporal_discrimination_accuracy < 1.0);
    ASSERT_TRUE(!div_pos.temporal_discrimination_passed);
    std::cout << "  [relaxed eps=1.0] Spike err: " << div_pos.spike_count_error
              << ", Backward ev: " << div_pos.backward_time_events
              << ", Exact matches: " << div_pos.exact_spike_matches << "/" << ref.total_spikes
              << ", Pot RMSE: " << div_pos.potential_rmse
              << ", Discrim Acc: " << div_pos.temporal_discrimination_accuracy << " (chance=0.50)" << std::endl;

    std::cout << "  -> PASSED (eps=0 is exact, eps>0 runs relaxed scheduling with measured violations)" << std::endl;
}

void test_pairwise_watermark_adversarial_stress() {
    std::cout << "[TEST] Running test_pairwise_watermark_adversarial_stress (Adversarial asymmetric delays, cyclic ring, dense random, TSan)..." << std::endl;
    sc::SubstrateConfig cfg;
    cfg.num_nodes = 48;
    cfg.tau_m = 5.0f;
    cfg.threshold = 1.0f;
    cfg.min_delay = 0.05f;
    cfg.max_delay = 2.50f;

    // Case A: Adversarial directed cyclic ring with 50x asymmetric cross-worker delays
    // Worker 0 -> Worker 1 has tiny delay (0.05s); Worker 1 -> Worker 2 has medium delay (0.40s);
    // Worker 2 -> Worker 3 has large delay (2.00s); Worker 3 -> Worker 0 has tiny delay (0.06s),
    // plus cross-chords (0 -> 2 delay 1.50s, 2 -> 0 delay 0.07s).
    sc::NeuralGraphCSR g_adv;
    g_adv.num_nodes = 48;
    std::vector<int32_t> part48(48);
    for (int32_t u = 0; u < 48; ++u) {
        part48[u] = u / 8; // 6 regions of 8 nodes
    }

    g_adv.row_ptr.resize(49, 0);
    std::vector<std::vector<std::tuple<int32_t, float, float>>> adj(48);
    for (int32_t u = 0; u < 48; ++u) {
        int32_t r_u = part48[u];
        // Intra-region dense recurrent excitation
        for (int32_t k = 1; k <= 3; ++k) {
            int32_t v = (r_u * 8) + ((u + k) % 8);
            adj[u].emplace_back(v, 0.55f, 0.05f + 0.01f * k);
        }
        // Directed cyclic ring + asymmetric chords across regions
        int32_t r_next = (r_u + 1) % 6;
        float d_ring = (r_u % 2 == 0) ? 0.05f : 1.75f; // 35x asymmetry!
        adj[u].emplace_back(r_next * 8 + (u % 8), 0.65f, d_ring);

        int32_t r_opp = (r_u + 3) % 6;
        float d_chord = (r_u < 3) ? 0.06f : 0.95f;
        adj[u].emplace_back(r_opp * 8 + ((u * 3) % 8), 0.45f, d_chord);
    }

    for (int32_t u = 0; u < 48; ++u) {
        g_adv.row_ptr[u + 1] = g_adv.row_ptr[u] + adj[u].size();
        for (const auto& [v, w, d] : adj[u]) {
            g_adv.targets.push_back(v);
            g_adv.weights.push_back(w);
            g_adv.delays.push_back(d);
        }
    }
    g_adv.num_edges = g_adv.targets.size();

    // Starved / bursty stimulus: only Region 0 and Region 3 receive external pulses,
    // forcing other workers to advance watermarks while empty and wait on asymmetric incoming channels!
    std::vector<sc::ExternalEvent> adv_inputs;
    for (int32_t s = 0; s < 120; ++s) {
        adv_inputs.push_back({0.02 * s, s % 8, 1.45f});
        if (s % 5 == 0) {
            adv_inputs.push_back({0.02 * s + 0.003, 24 + (s % 8), 1.55f});
        }
    }

    sc::Exp4SerialEngine ser_adv(cfg, g_adv);
    auto res_ser_adv = ser_adv.run(adv_inputs, 6.0);
    ASSERT_TRUE(res_ser_adv.total_spikes > 50);

    for (int32_t W : {2, 4, 6}) {
        sc::Exp4PairwiseWatermarkEngine wm_adv(cfg, g_adv, W, 6, part48);
        sc::SimulationResult res_wm;
        auto st = wm_adv.run(adv_inputs, 6.0, &res_wm);

        ASSERT_TRUE(st.watermark_monotonicity_violations == 0);
        ASSERT_TRUE(st.delayed_channel_deliveries > 0);
        ASSERT_TRUE(st.horizon_clamp_events > 0);
        ASSERT_TRUE(res_wm.total_events_processed == res_ser_adv.total_events_processed);
        ASSERT_TRUE(res_wm.total_spikes == res_ser_adv.total_spikes);
        ASSERT_TRUE(res_wm.state_digest == res_ser_adv.state_digest);
    }

    // Case B: Dense Uniform Random Graph (80%+ cross-worker traffic) across W=2, 4, 6
    sc::SubstrateConfig cfg_rand;
    cfg_rand.num_nodes = 96;
    cfg_rand.mean_out_degree = 12;
    cfg_rand.min_delay = 0.10f;
    cfg_rand.max_delay = 1.50f;
    auto g_rand = sc::Exp4GraphGenerators::create_uniform_random(96, 12, 2026, 0.45f, 0.10f, 1.50f);
    auto part96 = sc::Exp4Partitioners::partition_random_hash(96, 12, 2026);

    std::vector<sc::ExternalEvent> rand_inputs;
    for (int32_t s = 0; s < 150; ++s) {
        rand_inputs.push_back({0.015 * s, (s * 19) % 96, 1.5f});
    }
    sc::Exp4SerialEngine ser_rand(cfg_rand, g_rand);
    auto res_ser_rand = ser_rand.run(rand_inputs, 4.0);

    for (int32_t W : {2, 4, 6}) {
        sc::Exp4PairwiseWatermarkEngine wm_rand(cfg_rand, g_rand, W, 12, part96);
        sc::SimulationResult res_wm;
        auto st = wm_rand.run(rand_inputs, 4.0, &res_wm);

        ASSERT_TRUE(st.watermark_monotonicity_violations == 0);
        ASSERT_TRUE(st.delayed_channel_deliveries > 0);
        ASSERT_TRUE(res_wm.total_events_processed == res_ser_rand.total_events_processed);
        ASSERT_TRUE(res_wm.total_spikes == res_ser_rand.total_spikes);
        ASSERT_TRUE(res_wm.state_digest == res_ser_rand.state_digest);
    }

    std::cout << "  -> PASSED (0 watermark monotonicity violations, exact spike/event/digest parity on cyclic asymmetric + dense random graphs)" << std::endl;
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
    test_pairwise_watermark_adversarial_stress();
    std::cout << "=== ALL EXP-0004 TESTS PASSED SUCCESSFULLY ===" << std::endl;
    return 0;
}
