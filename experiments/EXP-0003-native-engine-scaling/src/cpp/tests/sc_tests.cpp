#include "../core/types.hpp"
#include "../core/prng.hpp"
#include "../core/graph.hpp"
#include "../core/state.hpp"
#include "../engines/cpp_literal.hpp"
#include "../engines/cpp_packed.hpp"
#include "../engines/cpp_queues.hpp"
#include "../engines/cpp_sync.hpp"
#include "../engines/cpp_locked.hpp"
#include "../engines/cpp_owner.hpp"
#include "../engines/cpp_hybrid.hpp"

#include <iostream>
#include <cassert>
#include <cmath>
#include <stdexcept>

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

void test_analytic_decay_oracle() {
    std::cout << "[TEST] Running test_analytic_decay_oracle..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 2;
    config.tau_m = 4.0f;
    config.threshold = 10.0f;

    sc::SubstrateStatePacked state(config);
    state.potentials[0] = 2.0f;
    state.last_update_times[0] = 1.0;

    state.advance_node_potential(0, 5.0); // dt = 4.0 = tau_m
    float expected = 2.0f * std::exp(-1.0f);
    ASSERT_NEAR(state.potentials[0], expected, 1e-6f);
    std::cout << "  -> PASSED" << std::endl;
}

void test_subthreshold_and_threshold_reset() {
    std::cout << "[TEST] Running test_subthreshold_and_threshold_reset..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 1;
    config.threshold = 1.0f;
    config.v_reset = 0.0f;
    config.refractory_period = 2.0f;

    sc::SubstrateStatePacked state(config);

    // Subthreshold
    bool fired1 = state.receive_impulse(0, 1.0, 0.8f);
    ASSERT_TRUE(!fired1);
    ASSERT_NEAR(state.potentials[0], 0.8f, 1e-6f);

    // Suprathreshold
    bool fired2 = state.receive_impulse(0, 2.0, 0.5f);
    ASSERT_TRUE(fired2);
    ASSERT_NEAR(state.potentials[0], 0.0f, 1e-6f);
    ASSERT_TRUE(state.spike_counts[0] == 1);
    ASSERT_NEAR(state.refractory_until[0], 4.0, 1e-6);
    std::cout << "  -> PASSED" << std::endl;
}

void test_refractory_clamping() {
    std::cout << "[TEST] Running test_refractory_clamping..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 1;
    config.threshold = 1.0f;
    config.v_reset = 0.0f;
    config.refractory_period = 2.0f;

    sc::SubstrateStatePacked state(config);

    // Spike at t=1.0 -> refractory until t=3.0
    state.receive_impulse(0, 1.0, 1.5f);
    ASSERT_NEAR(state.refractory_until[0], 3.0, 1e-6);

    // Inside refractory at t=2.0
    bool fired_inside = state.receive_impulse(0, 2.0, 5.0f);
    ASSERT_TRUE(!fired_inside);
    ASSERT_NEAR(state.potentials[0], 0.0f, 1e-6f);

    // Outside refractory at t=3.1
    bool fired_after = state.receive_impulse(0, 3.1, 1.2f);
    ASSERT_TRUE(fired_after);
    ASSERT_TRUE(state.spike_counts[0] == 2);
    std::cout << "  -> PASSED" << std::endl;
}

void test_golden_chain_parity() {
    std::cout << "[TEST] Running test_golden_chain_parity (3-node feedforward chain)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 3;
    config.tau_m = 5.0f;
    config.threshold = 1.0f;
    config.refractory_period = 1.0f;
    config.min_delay = 1.0f;
    config.max_delay = 1.0f;

    // Node 0 -> Node 1 (delay 1.0, weight 1.5)
    // Node 1 -> Node 2 (delay 1.0, weight 1.5)
    sc::NeuralGraphCSR graph;
    graph.num_nodes = 3;
    graph.num_edges = 2;
    graph.row_ptr = {0, 1, 2, 2};
    graph.targets = {1, 2};
    graph.weights = {1.5f, 1.5f};
    graph.delays = {1.0f, 1.0f};

    std::vector<sc::ExternalEvent> ext_events = {
        {1.0, 0, 1.5f, -1, static_cast<int32_t>(sc::EventKind::EXTERNAL)}
    };
    double t_max = 5.0;

    // 1. Literal Engine
    sc::NeuralGraphLiteral lit_graph = sc::NeuralGraphLiteral::from_csr(graph);
    sc::CppLiteralEngine lit_eng(config, lit_graph);
    auto res_lit = lit_eng.run(ext_events, t_max);

    ASSERT_TRUE(res_lit.total_spikes == 3);
    ASSERT_TRUE(res_lit.spike_records.size() == 3);
    ASSERT_NEAR(res_lit.spike_records[0].timestamp, 1.0, 1e-6);
    ASSERT_TRUE(res_lit.spike_records[0].node == 0);
    ASSERT_NEAR(res_lit.spike_records[1].timestamp, 2.0, 1e-6);
    ASSERT_TRUE(res_lit.spike_records[1].node == 1);
    ASSERT_NEAR(res_lit.spike_records[2].timestamp, 3.0, 1e-6);
    ASSERT_TRUE(res_lit.spike_records[2].node == 2);

    // 2. Packed Engine
    sc::CppPackedEngine packed_eng(config, graph);
    auto res_packed = packed_eng.run(ext_events, t_max);
    ASSERT_TRUE(res_packed.total_spikes == 3);
    ASSERT_TRUE(res_packed.state_digest == res_lit.state_digest);

    // 3. Queues Engines
    sc::CppQueuesEngine q_bin(config, graph, sc::QueueType::BINARY_HEAP);
    auto res_q_bin = q_bin.run(ext_events, t_max);
    ASSERT_TRUE(res_q_bin.state_digest == res_lit.state_digest);

    sc::CppQueuesEngine q_dary4(config, graph, sc::QueueType::DARY_HEAP_4);
    auto res_q_dary4 = q_dary4.run(ext_events, t_max);
    ASSERT_TRUE(res_q_dary4.state_digest == res_lit.state_digest);

    sc::CppQueuesEngine q_bucket(config, graph, sc::QueueType::BUCKET_QUEUE);
    auto res_q_bucket = q_bucket.run(ext_events, t_max);
    ASSERT_TRUE(res_q_bucket.state_digest == res_lit.state_digest);

    // 4. Hybrid Engine
    sc::CppHybridEngine hybrid_eng(config, graph);
    auto res_hybrid = hybrid_eng.run(ext_events, t_max);
    ASSERT_TRUE(res_hybrid.state_digest == res_lit.state_digest);

    std::cout << "  -> PASSED" << std::endl;
}

void test_trace_digest_parity() {
    std::cout << "[TEST] Running test_trace_digest_parity on random graph N=128, D=16..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 128;
    config.mean_out_degree = 16;

    auto graph = sc::GraphFactory::create_random(128, 16, 42);
    auto events = sc::EventGenerator::generate(128, 0.10, 1.0, 10.0, 42);

    auto lit_graph = sc::NeuralGraphLiteral::from_csr(graph);
    sc::CppLiteralEngine lit_eng(config, lit_graph);
    auto res_lit = lit_eng.run(events, 10.0);

    sc::CppPackedEngine packed_eng(config, graph);
    auto res_packed = packed_eng.run(events, 10.0);

    ASSERT_TRUE(res_lit.total_spikes == res_packed.total_spikes);
    ASSERT_TRUE(res_lit.total_events_processed == res_packed.total_events_processed);
    ASSERT_TRUE(res_lit.total_edges_traversed == res_packed.total_edges_traversed);
    ASSERT_TRUE(res_lit.state_digest == res_packed.state_digest);

    std::cout << "  -> PASSED (Literal vs Packed bit-exact digest parity: " << res_lit.state_digest << ")" << std::endl;
}

void test_sync_dt_convergence() {
    std::cout << "[TEST] Running test_sync_dt_convergence..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 16;
    config.mean_out_degree = 4;
    config.threshold = 100.0f; // linear subthreshold regime

    auto graph = sc::GraphFactory::create_random(16, 4, 123);
    auto events = sc::EventGenerator::generate(16, 0.50, 2.0, 10.0, 123);

    sc::CppPackedEngine ed_eng(config, graph);
    auto res_ref = ed_eng.run(events, 10.0);

    std::vector<double> dts = {0.2, 0.1, 0.05, 0.025};
    std::vector<double> errors;

    for (double dt : dts) {
        sc::CppDenseSyncEngine sync_eng(config, graph, dt);
        auto res_sync = sync_eng.run(events, 10.0);

        double err = 0.0;
        for (int32_t i = 0; i < config.num_nodes; ++i) {
            double diff = res_sync.final_potentials[i] - res_ref.final_potentials[i];
            err += diff * diff;
        }
        errors.push_back(std::sqrt(err));
    }

    std::cout << "  dt errors: dt=0.2: " << errors[0]
              << ", dt=0.1: " << errors[1]
              << ", dt=0.05: " << errors[2]
              << ", dt=0.025: " << errors[3] << std::endl;

    // Error must decrease monotonically with dt
    ASSERT_TRUE(errors[0] > errors[1]);
    ASSERT_TRUE(errors[1] > errors[2]);
    ASSERT_TRUE(errors[2] > errors[3]);

    std::cout << "  -> PASSED" << std::endl;
}

void test_parallel_engines() {
    std::cout << "[TEST] Running test_parallel_engines (Locked vs Owner)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 64;
    config.mean_out_degree = 8;

    auto graph = sc::GraphFactory::create_modular(64, 8, 777, 4, 0.80f);
    auto events = sc::EventGenerator::generate(64, 0.20, 1.0, 5.0, 777);

    sc::CppLockedEngine locked_eng(config, graph, 2);
    auto res_locked = locked_eng.run(events, 5.0);
    ASSERT_TRUE(res_locked.total_events_processed > 0);

    sc::CppOwnerEngine owner_eng(config, graph, 2);
    auto res_owner = owner_eng.run(events, 5.0);
    ASSERT_TRUE(res_owner.total_events_processed > 0);
    ASSERT_TRUE(res_owner.causal_stalls > 0);

    std::cout << "  -> PASSED (Locked events: " << res_locked.total_events_processed
              << ", Owner events: " << res_owner.total_events_processed
              << ", cross-region messages: " << res_owner.cross_region_events << ")" << std::endl;
}

int main() {
    std::cout << "===========================================" << std::endl;
    std::cout << "Running SynapticContinuum EXP-0003 Native Tests" << std::endl;
    std::cout << "===========================================" << std::endl;

    test_analytic_decay_oracle();
    test_subthreshold_and_threshold_reset();
    test_refractory_clamping();
    test_golden_chain_parity();
    test_trace_digest_parity();
    test_sync_dt_convergence();
    test_parallel_engines();

    std::cout << "===========================================" << std::endl;
    std::cout << "All C++ native tests passed successfully!" << std::endl;
    std::cout << "===========================================" << std::endl;
    return 0;
}
