#include "exp0004_bench_part2.inc"

int main(int argc, char** argv) {
    sc::BenchmarkConfig bcfg;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--profile" && i + 1 < argc) {
            bcfg.profile = argv[++i];
        } else if (arg == "--build-id" && i + 1 < argc) {
            bcfg.build_id = argv[++i];
        } else if (arg == "--out" && i + 1 < argc) {
            bcfg.out_path = argv[++i];
        } else if (arg == "--python-bin" && i + 1 < argc) {
            bcfg.python_bin = argv[++i];
        } else if (arg == "--ext-script" && i + 1 < argc) {
            bcfg.ext_script = argv[++i];
        }
    }

    if (bcfg.profile == "smoke") {
        bcfg.seeds = {11, 23};
        bcfg.repetitions = 2;
        bcfg.warmups = 1;
        bcfg.worker_counts = {1, 2, 4, 6};
        bcfg.smt_counts = {1, 2, 4, 6};
    } else {
        bcfg.seeds = {11, 23, 37, 41, 53};
        bcfg.repetitions = 5;
        bcfg.warmups = 2;
        bcfg.worker_counts = {1, 2, 4, 6};
        bcfg.smt_counts = {1, 2, 4, 6, 8, 12};
    }

    std::cout << "========================================================\n"
              << " SynapticContinuum EXP-0004 Canonical Benchmark Runner\n"
              << " Profile:  " << bcfg.profile << "\n"
              << " Build ID: " << bcfg.build_id << "\n"
              << " Seeds:    " << bcfg.seeds.size() << " | Warmups: " << bcfg.warmups << " | Reps: " << bcfg.repetitions << "\n"
              << "========================================================\n" << std::endl;

    std::vector<std::string> all_canonical_records;
    auto append_record = [&](const sc::CanonicalRecordParams& p) {
        all_canonical_records.push_back(sc::build_canonical_record_json(p));
    };

    std::ostringstream json_out;
    json_out << "{\n"
             << "  \"experiment\": \"EXP-0004\",\n"
             << "  \"profile\": \"" << bcfg.profile << "\",\n"
             << "  \"build_id\": \"" << bcfg.build_id << "\",\n"
             << "  \"host\": " << sc::get_hardware_env_json(bcfg.build_id) << ",\n";

    // =========================================================================
    // STAGE 0 & PHASE A: Six Disconnected Regions Control vs Random Graph
    // =========================================================================
    std::cout << "[Stage 0 & Phase A] Six Disconnected Regions Control vs Random Graph..." << std::endl;
    json_out << "  \"stage0_disconnected_control\": [\n";

    int32_t N_phaseA = (bcfg.profile == "smoke") ? 1024 : 10000;
    int32_t D_phaseA = 16;
    double t_max_phaseA = (bcfg.profile == "smoke") ? 5.0 : 10.0;

    bool first_disc = true;
    for (uint64_t seed : bcfg.seeds) {
        auto g_disc = sc::Exp4GraphGenerators::create_disconnected_modules(N_phaseA, D_phaseA, 6, seed);
        auto g_rand = sc::Exp4GraphGenerators::create_uniform_random(N_phaseA, D_phaseA, seed);

        sc::SubstrateConfig cfg;
        cfg.num_nodes = N_phaseA;
        cfg.mean_out_degree = D_phaseA;

        std::vector<sc::ExternalEvent> inputs;
        int32_t input_events_count = (bcfg.profile == "smoke") ? 50 : 200;
        for (int32_t m = 0; m < 6; ++m) {
            int32_t start_n = m * (N_phaseA / 6);
            for (int32_t s = 0; s < input_events_count; ++s) {
                inputs.push_back({0.05 * s, start_n + (s % 30), 1.5f});
            }
        }

        // Serial ground truth for Disconnected 6-Modules
        sc::Exp4SerialEngine serial_disc(cfg, g_disc.graph);
        auto rep_serial_disc = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            auto t0 = std::chrono::high_resolution_clock::now();
            auto res = serial_disc.run(inputs, t_max_phaseA);
            auto t1 = std::chrono::high_resolution_clock::now();
            return sc::sim_result_to_stats(res, std::chrono::duration<double>(t1 - t0).count(), 6);
        });
        std::string b_id_disc = "exp0004_stage0_disconnected_N" + std::to_string(N_phaseA) + "_D16_seed" + std::to_string(seed);
        {
            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_disc;
            rp.run_id = b_id_disc + "_" + bcfg.build_id + "_cpp_serial_W1";
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage0_disconnected_6_modules";
            rp.num_nodes = N_phaseA;
            rp.num_edges = g_disc.graph.num_edges;
            rp.topology_type = "disconnected_modules";
            rp.engine_id = "cpp_serial";
            rp.num_workers = 1;
            rp.num_regions = 6;
            rp.t_max = t_max_phaseA;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g_disc.graph.memory_bytes();
            rp.rep_summary = rep_serial_disc;
            rp.serial_digest = rep_serial_disc.last_stats.state_digest;
            rp.serial_spikes = rep_serial_disc.last_stats.total_spikes;
            rp.serial_events = rep_serial_disc.last_stats.total_events_processed;
            append_record(rp);
        }

        // 1. Disconnected Barrier-Free Control across W
        double t_bf_w1 = 0.0;
        for (int32_t W : bcfg.worker_counts) {
            std::vector<int32_t> node_to_w(N_phaseA);
            int32_t mod_per_w = (6 + W - 1) / W;
            for (int32_t u = 0; u < N_phaseA; ++u) {
                int32_t m = g_disc.planted_labels[u];
                int32_t w = m / mod_per_w;
                node_to_w[u] = (w < W) ? w : (W - 1);
            }

            sc::Exp4BarrierFreeIndependentEngine bf_engine(cfg, g_disc.graph, W, node_to_w);
            auto rep_bf = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                return bf_engine.run(inputs, t_max_phaseA);
            });
            if (W == 1) t_bf_w1 = rep_bf.mean_sim_sec;
            double speedup = (t_bf_w1 > 0) ? (t_bf_w1 / rep_bf.mean_sim_sec) : 1.0;

            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_disc;
            rp.run_id = b_id_disc + "_" + bcfg.build_id + "_cpp_barrier_free_W" + std::to_string(W);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage0_disconnected_6_modules";
            rp.num_nodes = N_phaseA;
            rp.num_edges = g_disc.graph.num_edges;
            rp.topology_type = "disconnected_modules";
            rp.engine_id = "cpp_barrier_free_independent";
            rp.num_workers = W;
            rp.num_regions = 6;
            rp.t_max = t_max_phaseA;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g_disc.graph.memory_bytes();
            rp.rep_summary = rep_bf;
            rp.serial_digest = rep_serial_disc.last_stats.state_digest;
            rp.serial_spikes = rep_serial_disc.last_stats.total_spikes;
            rp.serial_events = rep_serial_disc.last_stats.total_events_processed;
            append_record(rp);

            if (!first_disc) json_out << ",\n";
            first_disc = false;
            json_out << "    {\n"
                     << "      \"type\": \"disconnected_barrier_free\",\n"
                     << "      \"N\": " << N_phaseA << ",\n"
                     << "      \"W\": " << W << ",\n"
                     << "      \"seed\": " << seed << ",\n"
                     << "      \"mean_sim_sec\": " << rep_bf.mean_sim_sec << ",\n"
                     << "      \"median_sim_sec\": " << rep_bf.median_sim_sec << ",\n"
                     << "      \"std_sim_sec\": " << rep_bf.std_sim_sec << ",\n"
                     << "      \"self_speedup\": " << speedup << ",\n"
                     << "      \"events\": " << rep_bf.last_stats.total_events_processed << ",\n"
                     << "      \"spikes\": " << rep_bf.last_stats.total_spikes << ",\n"
                     << "      \"cross_events\": 0,\n"
                     << "      \"state_digest\": \"" << sc::to_hex_digest(rep_bf.last_stats.state_digest) << "\",\n"
                     << "      \"parity_with_serial\": " << ((rep_bf.last_stats.state_digest == rep_serial_disc.last_stats.state_digest) ? "true" : "false") << ",\n"
                     << "      \"peak_rss_mb\": " << (rep_bf.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                     << "    }";
        }

        // 2. Disconnected Modules Persistent Pool across W
        double t_disc_w1 = 0.0;
        for (int32_t W : bcfg.worker_counts) {
            sc::Exp4PersistentPoolEngine pool(cfg, g_disc.graph, W, 6, g_disc.planted_labels);
            auto rep_pool = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                return pool.run(inputs, t_max_phaseA);
            });
            if (W == 1) t_disc_w1 = rep_pool.mean_sim_sec;
            double speedup = (t_disc_w1 > 0) ? (t_disc_w1 / rep_pool.mean_sim_sec) : 1.0;

            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_disc;
            rp.run_id = b_id_disc + "_" + bcfg.build_id + "_cpp_persistent_pool_W" + std::to_string(W);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage0_disconnected_6_modules";
            rp.num_nodes = N_phaseA;
            rp.num_edges = g_disc.graph.num_edges;
            rp.topology_type = "disconnected_modules";
            rp.engine_id = "cpp_persistent_pool";
            rp.num_workers = W;
            rp.num_regions = 6;
            rp.t_max = t_max_phaseA;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g_disc.graph.memory_bytes();
            rp.rep_summary = rep_pool;
            rp.serial_digest = rep_serial_disc.last_stats.state_digest;
            rp.serial_spikes = rep_serial_disc.last_stats.total_spikes;
            rp.serial_events = rep_serial_disc.last_stats.total_events_processed;
            append_record(rp);

            json_out << ",\n    {\n"
                     << "      \"type\": \"disconnected_6_modules\",\n"
                     << "      \"N\": " << N_phaseA << ",\n"
                     << "      \"W\": " << W << ",\n"
                     << "      \"seed\": " << seed << ",\n"
                     << "      \"mean_sim_sec\": " << rep_pool.mean_sim_sec << ",\n"
                     << "      \"median_sim_sec\": " << rep_pool.median_sim_sec << ",\n"
                     << "      \"std_sim_sec\": " << rep_pool.std_sim_sec << ",\n"
                     << "      \"self_speedup\": " << speedup << ",\n"
                     << "      \"events\": " << rep_pool.last_stats.total_events_processed << ",\n"
                     << "      \"spikes\": " << rep_pool.last_stats.total_spikes << ",\n"
                     << "      \"cross_events\": " << rep_pool.last_stats.cross_region_events << ",\n"
                     << "      \"state_digest\": \"" << sc::to_hex_digest(rep_pool.last_stats.state_digest) << "\",\n"
                     << "      \"parity_with_serial\": " << ((rep_pool.last_stats.state_digest == rep_serial_disc.last_stats.state_digest) ? "true" : "false") << ",\n"
                     << "      \"peak_rss_mb\": " << (rep_pool.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                     << "    }";
        }

        // Serial ground truth for Uniform Random Graph
        sc::Exp4SerialEngine serial_rand(cfg, g_rand);
        auto rep_serial_rand = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            auto t0 = std::chrono::high_resolution_clock::now();
            auto res = serial_rand.run(inputs, t_max_phaseA);
            auto t1 = std::chrono::high_resolution_clock::now();
            return sc::sim_result_to_stats(res, std::chrono::duration<double>(t1 - t0).count(), 6);
        });
        std::string b_id_rand = "exp0004_stage0_uniform_random_N" + std::to_string(N_phaseA) + "_D16_seed" + std::to_string(seed);
        {
            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_rand;
            rp.run_id = b_id_rand + "_" + bcfg.build_id + "_cpp_serial_W1";
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage0_uniform_random";
            rp.num_nodes = N_phaseA;
            rp.num_edges = g_rand.num_edges;
            rp.topology_type = "uniform_random";
            rp.engine_id = "cpp_serial";
            rp.partitioner = "contiguous";
            rp.num_workers = 1;
            rp.num_regions = 6;
            rp.t_max = t_max_phaseA;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g_rand.memory_bytes();
            rp.rep_summary = rep_serial_rand;
            rp.serial_digest = rep_serial_rand.last_stats.state_digest;
            rp.serial_spikes = rep_serial_rand.last_stats.total_spikes;
            rp.serial_events = rep_serial_rand.last_stats.total_events_processed;
            append_record(rp);
        }

        double t_rand_w1 = 0.0;
        for (int32_t W : bcfg.worker_counts) {
            auto part_contig = sc::Exp4Partitioners::partition_contiguous(N_phaseA, W);
            sc::Exp4PersistentPoolEngine pool(cfg, g_rand, W, W, part_contig);
            auto rep_rand = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                return pool.run(inputs, t_max_phaseA);
            });
            if (W == 1) t_rand_w1 = rep_rand.mean_sim_sec;
            double speedup = (t_rand_w1 > 0) ? (t_rand_w1 / rep_rand.mean_sim_sec) : 1.0;

            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_rand;
            rp.run_id = b_id_rand + "_" + bcfg.build_id + "_cpp_persistent_pool_W" + std::to_string(W);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage0_uniform_random";
            rp.num_nodes = N_phaseA;
            rp.num_edges = g_rand.num_edges;
            rp.topology_type = "uniform_random";
            rp.engine_id = "cpp_persistent_pool";
            rp.partitioner = "contiguous";
            rp.num_workers = W;
            rp.num_regions = W;
            rp.t_max = t_max_phaseA;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g_rand.memory_bytes();
            rp.rep_summary = rep_rand;
            rp.serial_digest = rep_serial_rand.last_stats.state_digest;
            rp.serial_spikes = rep_serial_rand.last_stats.total_spikes;
            rp.serial_events = rep_serial_rand.last_stats.total_events_processed;
            append_record(rp);

            json_out << ",\n    {\n"
                     << "      \"type\": \"random_graph\",\n"
                     << "      \"N\": " << N_phaseA << ",\n"
                     << "      \"W\": " << W << ",\n"
                     << "      \"seed\": " << seed << ",\n"
                     << "      \"mean_sim_sec\": " << rep_rand.mean_sim_sec << ",\n"
                     << "      \"median_sim_sec\": " << rep_rand.median_sim_sec << ",\n"
                     << "      \"std_sim_sec\": " << rep_rand.std_sim_sec << ",\n"
                     << "      \"self_speedup\": " << speedup << ",\n"
                     << "      \"events\": " << rep_rand.last_stats.total_events_processed << ",\n"
                     << "      \"spikes\": " << rep_rand.last_stats.total_spikes << ",\n"
                     << "      \"cross_events\": " << rep_rand.last_stats.cross_region_events << ",\n"
                     << "      \"state_digest\": \"" << sc::to_hex_digest(rep_rand.last_stats.state_digest) << "\",\n"
                     << "      \"parity_with_serial\": " << ((rep_rand.last_stats.state_digest == rep_serial_rand.last_stats.state_digest) ? "true" : "false") << ",\n"
                     << "      \"peak_rss_mb\": " << (rep_rand.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                     << "    }";
        }
    }
    json_out << "\n  ],\n";

    // =========================================================================
    // STAGE 1: Controlled Topology Generators, Metrics & Trace Replay
    // =========================================================================
    std::cout << "\n[Stage 1] Controlled Topology Sweep & Graph Metrics..." << std::endl;
    json_out << "  \"stage1_topology_sweep\": [\n";

    int32_t N_topo = (bcfg.profile == "smoke") ? 1024 : 10000;
    int32_t D_topo = 16;
    uint64_t seed_topo = bcfg.seeds[0];
    sc::SubstrateConfig cfg_topo;
    cfg_topo.num_nodes = N_topo;
    cfg_topo.mean_out_degree = D_topo;

    bool first_topo = true;
    auto record_topo_bench = [&](
        const std::string& name,
        const sc::NeuralGraphCSR& g,
        const std::vector<int32_t>& part,
        const std::string& extra_param
    ) {
        auto m = sc::Exp4GraphMetricsCalculator::compute_all_metrics(g, part, 300, 100, seed_topo);

        std::vector<sc::ExternalEvent> inputs;
        for (int32_t s = 0; s < 100; ++s) {
            inputs.push_back({0.05 * s, (s * 37) % N_topo, 1.5f});
        }

        sc::Exp4SerialEngine serial_eng(cfg_topo, g);
        auto res_ser = serial_eng.run(inputs, 5.0);

        sc::Exp4PersistentPoolEngine pool_w1(cfg_topo, g, 1, 6, part);
        auto rep_w1 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool_w1.run(inputs, 5.0);
        });

        sc::Exp4PersistentPoolEngine pool_w6(cfg_topo, g, 6, 6, part);
        auto rep_w6 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool_w6.run(inputs, 5.0);
        });

        double speedup = (rep_w6.mean_sim_sec > 0) ? (rep_w1.mean_sim_sec / rep_w6.mean_sim_sec) : 1.0;
        std::string b_id = "exp0004_stage1_" + name + "_" + extra_param + "_N" + std::to_string(N_topo);

        for (int32_t W_val : {1, 6}) {
            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id;
            rp.run_id = b_id + "_" + bcfg.build_id + "_W" + std::to_string(W_val);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage1_topology_" + name + "_" + extra_param;
            rp.num_nodes = N_topo;
            rp.num_edges = g.num_edges;
            rp.topology_type = name + "_" + extra_param;
            rp.clustering_coeff = m.clustering_coefficient;
            rp.path_length = m.characteristic_path_length;
            rp.modularity_q = m.modularity_q;
            rp.edge_cut_fraction = m.edge_cut_fraction;
            rp.engine_id = "cpp_persistent_pool";
            rp.num_workers = W_val;
            rp.num_regions = 6;
            rp.t_max = 5.0;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = inputs.size();
            rp.graph_payload_bytes = g.memory_bytes();
            rp.rep_summary = (W_val == 1) ? rep_w1 : rep_w6;
            rp.serial_digest = res_ser.state_digest;
            rp.serial_spikes = res_ser.total_spikes;
            rp.serial_events = res_ser.total_events_processed;
            append_record(rp);
        }

        if (!first_topo) json_out << ",\n";
        first_topo = false;
        json_out << "    {\n"
                 << "      \"name\": \"" << name << "\",\n"
                 << "      \"parameter\": \"" << extra_param << "\",\n"
                 << "      \"N\": " << N_topo << ",\n"
                 << "      \"D\": " << D_topo << ",\n"
                 << "      \"clustering_coeff\": " << m.clustering_coefficient << ",\n"
                 << "      \"path_length\": " << m.characteristic_path_length << ",\n"
                 << "      \"modularity_q\": " << m.modularity_q << ",\n"
                 << "      \"edge_cut\": " << m.edge_cut_fraction << ",\n"
                 << "      \"total_events\": " << rep_w6.last_stats.total_events_processed << ",\n"
                 << "      \"total_spikes\": " << rep_w6.last_stats.total_spikes << ",\n"
                 << "      \"cross_events_w6\": " << rep_w6.last_stats.cross_region_events << ",\n"
                 << "      \"w1_sim_sec\": " << rep_w1.mean_sim_sec << ",\n"
                 << "      \"w6_sim_sec\": " << rep_w6.mean_sim_sec << ",\n"
                 << "      \"speedup_w6\": " << speedup << ",\n"
                 << "      \"parity_with_serial\": " << ((rep_w6.last_stats.state_digest == res_ser.state_digest) ? "true" : "false") << "\n"
                 << "    }";
    };

    for (float p : {0.0f, 0.01f, 0.10f, 0.50f, 1.00f}) {
        auto g_ws = sc::Exp4GraphGenerators::create_watts_strogatz_small_world(N_topo, D_topo, p, seed_topo);
        auto part = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
        std::ostringstream ps; ps << "p" << std::fixed << std::setprecision(2) << p;
        record_topo_bench("watts_strogatz", g_ws, part, ps.str());
    }

    for (float c : {0.0f, 0.01f, 0.10f, 0.50f, 1.00f}) {
        auto g_mod = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, c, seed_topo);
        std::ostringstream cs; cs << "c" << std::fixed << std::setprecision(2) << c;
        record_topo_bench("modular_sbm", g_mod.graph, g_mod.planted_labels, cs.str());
    }

    auto g_hier = sc::Exp4GraphGenerators::create_hierarchical_modular(N_topo, D_topo, 2, 3, seed_topo);
    record_topo_bench("hierarchical_modular", g_hier.graph, g_hier.planted_labels, "2x3");

    auto g_mod_base = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, 0.10f, seed_topo);
    auto g_deg_rewired = sc::Exp4GraphGenerators::create_degree_preserving_rewired(g_mod_base.graph, N_topo * D_topo * 5, seed_topo);
    record_topo_bench("degree_preserving_rewired", g_deg_rewired, g_mod_base.planted_labels, "swaps5E");

    auto g_permuted = sc::Exp4GraphGenerators::create_node_id_permuted(g_mod_base.graph, seed_topo);
    auto part_contig_perm = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
    record_topo_bench("node_id_permuted", g_permuted, part_contig_perm, "shuffled");

    json_out << "\n  ],\n";

    // =========================================================================
    // STAGE 1B: Pure Trace Replay Microbenchmark (Empty-Edge Graph so trace_events == total_events_processed)
    // =========================================================================
    std::cout << "\n[Stage 1B] Pure Trace Replay Microbenchmark (Isolating Queue/Dispatch from Synaptic Fan-out)..." << std::endl;
    json_out << "  \"stage1b_trace_replay\": [\n";

    // Record a substantial trace (~120,000 events in standard mode) and replay on an EMPTY-EDGE graph
    std::vector<sc::ExternalEvent> trace_stimuli;
    int32_t trace_stim_count = (bcfg.profile == "smoke") ? 500 : 12000;
    for (int32_t s = 0; s < trace_stim_count; ++s) {
        trace_stimuli.push_back({0.001 * s, (s * 41) % N_topo, 1.6f});
    }
    sc::Exp4SerialEngine trace_ref_serial(cfg_topo, g_mod_base.graph);
    std::vector<sc::TraceEvent> recorded_trace;
    trace_ref_serial.run(trace_stimuli, 15.0, true, &recorded_trace);

    std::vector<sc::ExternalEvent> replay_inputs;
    replay_inputs.reserve(recorded_trace.size());
    for (const auto& te : recorded_trace) {
        replay_inputs.push_back({te.timestamp, te.target, te.amplitude, te.source, te.kind});
    }

    // Empty-edge CSR graph so replaying recorded_trace generates ZERO additional endogenous edges:
    // total_events_processed == replay_inputs.size() identically!
    sc::NeuralGraphCSR empty_graph;
    empty_graph.num_nodes = N_topo;
    empty_graph.num_edges = 0;
    empty_graph.row_ptr.assign(N_topo + 1, 0);

    sc::Exp4SerialEngine replay_serial(cfg_topo, empty_graph);
    auto res_replay_ser = replay_serial.run(replay_inputs, 15.0);

    std::string b_id_tr = "exp0004_stage1b_trace_replay_N" + std::to_string(N_topo) + "_ev" + std::to_string(replay_inputs.size());
    bool first_tr = true;
    double t_tr_w1 = 0.0;
    for (int32_t W : bcfg.worker_counts) {
        sc::Exp4PersistentPoolEngine pool_tr(cfg_topo, empty_graph, W, 6, g_mod_base.planted_labels);
        auto rep_tr = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool_tr.run(replay_inputs, 15.0);
        });
        if (W == 1) t_tr_w1 = rep_tr.mean_sim_sec;
        double speedup = (t_tr_w1 > 0) ? (t_tr_w1 / rep_tr.mean_sim_sec) : 1.0;
        double ev_per_sec = static_cast<double>(rep_tr.last_stats.total_events_processed) / std::max(1e-9, rep_tr.mean_sim_sec);

        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_tr;
        rp.run_id = b_id_tr + "_" + bcfg.build_id + "_W" + std::to_string(W);
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage1b_pure_trace_replay";
        rp.semantic_class = "trace-replay-only";
        rp.num_nodes = N_topo;
        rp.num_edges = 0;
        rp.topology_type = "empty_replay_graph";
        rp.engine_id = "cpp_persistent_pool";
        rp.num_workers = W;
        rp.num_regions = 6;
        rp.t_max = 15.0;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = replay_inputs.size();
        rp.rep_summary = rep_tr;
        rp.serial_digest = res_replay_ser.state_digest;
        rp.serial_spikes = res_replay_ser.total_spikes;
        rp.serial_events = res_replay_ser.total_events_processed;
        append_record(rp);

        if (!first_tr) json_out << ",\n";
        first_tr = false;
        json_out << "    {\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"trace_events\": " << replay_inputs.size() << ",\n"
                 << "      \"total_events_processed\": " << rep_tr.last_stats.total_events_processed << ",\n"
                 << "      \"mean_sim_sec\": " << std::fixed << std::setprecision(7) << rep_tr.mean_sim_sec << ",\n"
                 << "      \"median_sim_sec\": " << rep_tr.median_sim_sec << ",\n"
                 << "      \"std_sim_sec\": " << rep_tr.std_sim_sec << ",\n"
                 << "      \"self_speedup\": " << std::setprecision(3) << speedup << ",\n"
                 << "      \"events_per_sec\": " << std::fixed << std::setprecision(2) << ev_per_sec << ",\n"
                 << "      \"parity_with_serial\": " << ((rep_tr.last_stats.state_digest == res_replay_ser.state_digest) ? "true" : "false") << "\n"
                 << "    }";
    }
    json_out << "\n  ],\n";
