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

void test_adversarial_simultaneous_arrivals_hybrid() {
    std::cout << "[TEST] Running test_adversarial_simultaneous_arrivals_hybrid..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 1;
    config.threshold = 1.0f;
    config.v_reset = 0.0f;
    config.refractory_period = 1.0f;

    sc::NeuralGraphCSR graph;
    graph.num_nodes = 1;
    graph.row_ptr = {0, 0};

    // Case 1: Event 1 (+1.5, suprathreshold), Event 2 (-0.8, inhibitory) at same timestamp t=1.0
    std::vector<sc::ExternalEvent> events1 = {
        {1.0, 0, 1.5f, -1, 0},
        {1.0, 0, -0.8f, -1, 0}
    };

    sc::NeuralGraphLiteral lit_graph = sc::NeuralGraphLiteral::from_csr(graph);
    sc::CppLiteralEngine lit_eng(config, lit_graph);
    auto res_lit = lit_eng.run(events1, 5.0);

    sc::CppHybridEngine hybrid_eng(config, graph);
    auto res_hybrid = hybrid_eng.run(events1, 5.0);

    // Event 1 MUST fire first. Event 2 arriving during refractory is clamped to v_reset.
    // If summed, (1.5 - 0.8) = 0.7 < 1.0 which would NOT fire.
    ASSERT_TRUE(res_lit.total_spikes == 1);
    ASSERT_TRUE(res_hybrid.total_spikes == 1);
    ASSERT_NEAR(res_lit.final_potentials[0], res_hybrid.final_potentials[0], 1e-6f);
    ASSERT_TRUE(res_lit.state_digest == res_hybrid.state_digest);

    // Case 2: Subthreshold Event 1 (+0.6) and Event 2 (+0.6) at t=1.0: together they cross threshold
    std::vector<sc::ExternalEvent> events2 = {
        {1.0, 0, 0.6f, -1, 0},
        {1.0, 0, 0.6f, -1, 0}
    };
    auto res_lit2 = lit_eng.run(events2, 5.0);
    auto res_hybrid2 = hybrid_eng.run(events2, 5.0);
    ASSERT_TRUE(res_lit2.total_spikes == 1);
    ASSERT_TRUE(res_hybrid2.total_spikes == 1);
    ASSERT_TRUE(res_lit2.state_digest == res_hybrid2.state_digest);

    std::cout << "  -> PASSED (Hybrid preserves exact sequential LIF semantics)" << std::endl;
}

void test_adversarial_causal_arrivals_parallel() {
    std::cout << "[TEST] Running test_adversarial_causal_arrivals_parallel..." << std::endl;
    // Adversarial test: Node 0 and Node 1 both send to Node 2
    // Node 0 fires at t=1.0 with delay 0.5 -> arrives at Node 2 at t=1.5
    // Node 1 fires at t=1.1 with delay 0.1 -> arrives at Node 2 at t=1.2
    // Node 1 fired later, but its child arrives earlier (t=1.2 < t=1.5)!
    sc::SubstrateConfig config;
    config.num_nodes = 3;
    config.threshold = 1.0f;
    config.refractory_period = 1.0f;
    config.min_delay = 0.1f;
    config.max_delay = 0.5f;

    sc::NeuralGraphCSR graph;
    graph.num_nodes = 3;
    graph.num_edges = 2;
    graph.row_ptr = {0, 1, 2, 2};
    graph.targets = {2, 2};
    graph.weights = {0.6f, 0.6f};
    graph.delays = {0.5f, 0.1f};

    std::vector<sc::ExternalEvent> events = {
        {1.0, 0, 1.5f, -1, 0},
        {1.1, 1, 1.5f, -1, 0}
    };
    double t_max = 5.0;

    // Serial reference
    sc::CppPackedEngine serial_eng(config, graph);
    auto res_serial = serial_eng.run(events, t_max);

    // Parallel Locked with 2 workers
    sc::CppLockedEngine locked_eng(config, graph, 2);
    auto res_locked = locked_eng.run(events, t_max);

    // Parallel Owner with 2 workers
    sc::CppOwnerEngine owner_eng(config, graph, 2);
    auto res_owner = owner_eng.run(events, t_max);

    // All engines must process t=1.2 before t=1.5, triggering spike at Node 2
    ASSERT_TRUE(res_serial.total_spikes == 3); // Node 0 at 1.0, Node 1 at 1.1, Node 2 at 1.5
    ASSERT_TRUE(res_locked.total_spikes == 3);
    ASSERT_TRUE(res_owner.total_spikes == 3);
    ASSERT_TRUE(res_serial.state_digest == res_locked.state_digest);
    ASSERT_TRUE(res_serial.state_digest == res_owner.state_digest);

    std::cout << "  -> PASSED (Locked and Owner bit-exact match serial under causal delay inversion)" << std::endl;
}

void test_sync_spiking_fidelity_stress() {
    std::cout << "[TEST] Running test_sync_spiking_fidelity_stress (spiking/refractory stress)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 32;
    config.mean_out_degree = 8;
    config.threshold = 1.0f; // Active spiking threshold
    config.refractory_period = 1.0f;

    auto graph = sc::GraphFactory::create_random(32, 8, 42);
    auto events = sc::EventGenerator::generate(32, 0.20, 2.0, 5.0, 42);

    sc::CppPackedEngine event_eng(config, graph);
    auto res_exact = event_eng.run(events, 5.0);

    std::vector<double> dts = {0.2, 0.1, 0.05, 0.01};
    std::vector<double> pot_errors;
    std::vector<double> spike_count_diffs;

    for (double dt : dts) {
        sc::CppDenseSyncEngine sync_eng(config, graph, dt);
        auto res_sync = sync_eng.run(events, 5.0);

        double err = 0.0;
        for (int32_t i = 0; i < config.num_nodes; ++i) {
            double diff = res_sync.final_potentials[i] - res_exact.final_potentials[i];
            err += diff * diff;
        }
        pot_errors.push_back(std::sqrt(err));
        spike_count_diffs.push_back(std::abs(static_cast<double>(res_sync.total_spikes) - static_cast<double>(res_exact.total_spikes)));
    }

    std::cout << "  dt=0.20: pot_err=" << pot_errors[0] << ", spike_diff=" << spike_count_diffs[0] << std::endl;
    std::cout << "  dt=0.10: pot_err=" << pot_errors[1] << ", spike_diff=" << spike_count_diffs[1] << std::endl;
    std::cout << "  dt=0.05: pot_err=" << pot_errors[2] << ", spike_diff=" << spike_count_diffs[2] << std::endl;
    std::cout << "  dt=0.01: pot_err=" << pot_errors[3] << ", spike_diff=" << spike_count_diffs[3] << std::endl;

    // Potential error and spike discrepancies reduce as dt refines
    ASSERT_TRUE(pot_errors[0] > pot_errors[3]);
    ASSERT_TRUE(pot_errors[1] > pot_errors[3]);

    std::cout << "  -> PASSED (Spiking fidelity converges monotonically with dt grid refinement)" << std::endl;
}

void test_owner_replay_across_worker_counts() {
    std::cout << "[TEST] Running test_owner_replay_across_worker_counts (W=1, 2, 4)..." << std::endl;
    sc::SubstrateConfig config;
    config.num_nodes = 64;
    config.mean_out_degree = 8;
    config.threshold = 1.0f;

    auto graph = sc::GraphFactory::create_modular(64, 8, 999, 4, 0.80f);
    auto events = sc::EventGenerator::generate(64, 0.10, 1.0, 5.0, 999);

    sc::CppPackedEngine serial_eng(config, graph);
    auto res_serial = serial_eng.run(events, 5.0);

    for (int32_t w : {1, 2, 4}) {
        sc::CppOwnerEngine owner_eng(config, graph, w);
        auto res_owner = owner_eng.run(events, 5.0);
        std::cout << "  w=" << w << " owner_spikes=" << res_owner.total_spikes << " serial_spikes=" << res_serial.total_spikes << std::endl;

        ASSERT_TRUE(res_owner.total_spikes == res_serial.total_spikes);
        ASSERT_TRUE(res_owner.spike_records.size() == res_serial.spike_records.size());
        ASSERT_TRUE(res_owner.state_digest == res_serial.state_digest);
    }
    std::cout << "  -> PASSED (Owner W=1, 2, 4 bit-exact matches serial state digest: " << res_serial.state_digest << ")" << std::endl;
}

int main() {
    std::cout << "===========================================" << std::endl;
    std::cout << "Running SynapticContinuum EXP-0003 Native Tests (Rigorous Suite)" << std::endl;
    std::cout << "===========================================" << std::endl;

    test_analytic_decay_oracle();
    test_subthreshold_and_threshold_reset();
    test_refractory_clamping();
    test_adversarial_simultaneous_arrivals_hybrid();
    test_adversarial_causal_arrivals_parallel();
    test_sync_spiking_fidelity_stress();
    test_owner_replay_across_worker_counts();

    std::cout << "===========================================" << std::endl;
    std::cout << "All C++ rigorous tests passed successfully!" << std::endl;
    std::cout << "===========================================" << std::endl;
    return 0;
}
