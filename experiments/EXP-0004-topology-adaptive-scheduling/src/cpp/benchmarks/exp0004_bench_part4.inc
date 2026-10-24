    // =========================================================================
    // STAGE 2: Partitioning Strategies Comparison (Including METIS & igraph Leiden)
    // =========================================================================
    std::cout << "\n[Stage 2] Partitioning Strategies Comparison (D3 Matrix)..." << std::endl;
    json_out << "  \"stage2_partition_strategies\": [\n";

    auto g_eval = sc::Exp4GraphGenerators::create_modular_sbm(N_topo, D_topo, 6, 0.10f, seed_topo);

    std::vector<sc::ExternalEvent> warmup_inputs;
    for (int32_t s = 0; s < 100; ++s) {
        warmup_inputs.push_back({0.05 * s, (s * 17) % N_topo, 1.5f});
    }
    sc::Exp4SerialEngine serial_warmup(cfg_topo, g_eval.graph);
    std::vector<sc::TraceEvent> warmup_trace;
    serial_warmup.run(warmup_inputs, 3.0, true, &warmup_trace);

    std::vector<sc::Exp4Partitioners::PairwiseEventRecord> warmup_comm;
    for (const auto& te : warmup_trace) {
        if (te.source >= 0) {
            warmup_comm.push_back({te.source, te.target, 1});
        }
    }

    auto part_contig = sc::Exp4Partitioners::partition_contiguous(N_topo, 6);
    auto part_hash = sc::Exp4Partitioners::partition_random_hash(N_topo, 6, seed_topo);
    auto part_oracle = sc::Exp4Partitioners::partition_planted_oracle(N_topo, 6, g_eval.planted_labels);
    auto part_boundary = sc::Exp4Partitioners::partition_greedy_boundary_heuristic(g_eval.graph, 6, 10);
    auto part_activity = sc::Exp4Partitioners::partition_activity_aware(N_topo, 6, warmup_comm, 10);

    std::vector<std::pair<std::string, std::vector<int32_t>>> partition_list = {
        {"contiguous", part_contig},
        {"random_hash", part_hash},
        {"planted_oracle", part_oracle},
        {"greedy_boundary_heuristic", part_boundary},
        {"activity_aware", part_activity}
    };

    // Invoke external library baselines: pymetis (METIS k-way) and python-igraph (Leiden)
    std::string edge_tmp = "/tmp/exp0004_eval_edges.txt";
    std::string metis_tmp = "/tmp/exp0004_part_metis.txt";
    std::string leiden_tmp = "/tmp/exp0004_part_leiden.txt";
    sc::write_graph_edge_list(g_eval.graph, edge_tmp);

    std::string py_exe = bcfg.python_bin.empty() ? ".venv/bin/python" : bcfg.python_bin;
    std::string ext_py = bcfg.ext_script.empty() ? "scripts/compute_external_partitions.py" : bcfg.ext_script;
    std::string cmd = py_exe + " " + ext_py + " --edges " + edge_tmp + " --parts 6 --out-metis " + metis_tmp + " --out-leiden " + leiden_tmp;
    int ext_rc = std::system(cmd.c_str());
    if (ext_rc == 0) {
        auto part_metis = sc::load_partition_file(metis_tmp, N_topo);
        auto part_leiden = sc::load_partition_file(leiden_tmp, N_topo);
        if (static_cast<int32_t>(part_metis.size()) == N_topo) {
            partition_list.push_back({"metis_kway", part_metis});
        }
        if (static_cast<int32_t>(part_leiden.size()) == N_topo) {
            partition_list.push_back({"igraph_leiden", part_leiden});
        }
    }

    std::vector<sc::ExternalEvent> heldout_inputs;
    for (int32_t s = 0; s < 1500; ++s) {
        heldout_inputs.push_back({0.004 * s, (s * 31) % N_topo, 1.55f});
    }

    sc::Exp4SerialEngine serial_heldout(cfg_topo, g_eval.graph);
    auto res_ser_heldout = serial_heldout.run(heldout_inputs, 6.0);

    std::string b_id_part = "exp0004_stage2_partition_eval_N" + std::to_string(N_topo) + "_D16_c0.10";
    bool first_part = true;
    for (const auto& pentry : partition_list) {
        const auto& pname = pentry.first;
        const auto& pmap = pentry.second;

        double edge_cut = sc::Exp4GraphMetricsCalculator::compute_edge_cut(g_eval.graph, pmap);
        double modularity = sc::Exp4GraphMetricsCalculator::compute_modularity(g_eval.graph, pmap);

        sc::Exp4PersistentPoolEngine pool(cfg_topo, g_eval.graph, 6, 6, pmap);
        auto rep_p = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool.run(heldout_inputs, 6.0);
        });

        double active_event_cut = (rep_p.last_stats.total_events_processed > 0)
            ? (static_cast<double>(rep_p.last_stats.cross_region_events) / rep_p.last_stats.total_events_processed) : 0.0;

        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_part;
        rp.run_id = b_id_part + "_" + bcfg.build_id + "_" + pname + "_W6";
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage2_partition_comparison";
        rp.num_nodes = N_topo;
        rp.num_edges = g_eval.graph.num_edges;
        rp.topology_type = "modular_sbm_c0.10";
        rp.modularity_q = modularity;
        rp.edge_cut_fraction = edge_cut;
        rp.engine_id = "cpp_persistent_pool";
        rp.partitioner = pname;
        rp.num_workers = 6;
        rp.num_regions = 6;
        rp.t_max = 6.0;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = heldout_inputs.size();
        rp.graph_payload_bytes = g_eval.graph.memory_bytes();
        rp.rep_summary = rep_p;
        rp.serial_digest = res_ser_heldout.state_digest;
        rp.serial_spikes = res_ser_heldout.total_spikes;
        rp.serial_events = res_ser_heldout.total_events_processed;
        append_record(rp);

        if (!first_part) json_out << ",\n";
        first_part = false;
        json_out << "    {\n"
                 << "      \"partitioner\": \"" << pname << "\",\n"
                 << "      \"edge_cut\": " << std::fixed << std::setprecision(4) << edge_cut << ",\n"
                 << "      \"modularity_q\": " << modularity << ",\n"
                 << "      \"total_events\": " << rep_p.last_stats.total_events_processed << ",\n"
                 << "      \"cross_events\": " << rep_p.last_stats.cross_region_events << ",\n"
                 << "      \"active_event_cut\": " << active_event_cut << ",\n"
                 << "      \"mean_sim_sec\": " << std::fixed << std::setprecision(7) << rep_p.mean_sim_sec << ",\n"
                 << "      \"median_sim_sec\": " << rep_p.median_sim_sec << ",\n"
                 << "      \"std_sim_sec\": " << rep_p.std_sim_sec << ",\n"
                 << "      \"events_per_sec\": " << std::setprecision(2) << (rep_p.last_stats.total_events_processed / rep_p.mean_sim_sec) << ",\n"
                 << "      \"backlog_imbalance\": " << std::setprecision(4) << rep_p.last_stats.backlog_imbalance_ratio << ",\n"
                 << "      \"parity_with_serial\": " << ((rep_p.last_stats.state_digest == res_ser_heldout.state_digest) ? "true" : "false") << "\n"
                 << "    }";
    }
    json_out << "\n  ],\n";

    // =========================================================================
    // STAGE 2B & 2C: Algorithm / Queue (D1) & Representation / History (D2) Sweep
    // =========================================================================
    std::cout << "\n[Stage 2B] Priority Queue Family Comparison (D1 Matrix)..." << std::endl;
    json_out << "  \"stage2b_queue_comparison\": [\n";
    std::string b_id_q = "exp0004_stage2b_queue_matrix_N" + std::to_string(N_topo);
    bool first_q = true;
    auto run_queue_cell = [&](const std::string& qname, auto&& make_pool_fn) {
        for (int32_t W_q : {1, 6}) {
            auto pool_q = make_pool_fn(W_q);
            auto rep_q = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                return pool_q.run(heldout_inputs, 6.0);
            });
            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_q;
            rp.run_id = b_id_q + "_" + bcfg.build_id + "_" + qname + "_W" + std::to_string(W_q);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage2b_queue_comparison";
            rp.num_nodes = N_topo;
            rp.num_edges = g_eval.graph.num_edges;
            rp.topology_type = "modular_sbm_c0.10";
            rp.engine_id = "cpp_persistent_pool";
            rp.queue_family = qname;
            rp.partitioner = "planted_oracle";
            rp.num_workers = W_q;
            rp.num_regions = 6;
            rp.t_max = 6.0;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = heldout_inputs.size();
            rp.graph_payload_bytes = g_eval.graph.memory_bytes();
            rp.rep_summary = rep_q;
            rp.serial_digest = res_ser_heldout.state_digest;
            rp.serial_spikes = res_ser_heldout.total_spikes;
            rp.serial_events = res_ser_heldout.total_events_processed;
            append_record(rp);

            if (!first_q) json_out << ",\n";
            first_q = false;
            json_out << "    {\n"
                     << "      \"queue_family\": \"" << qname << "\",\n"
                     << "      \"W\": " << W_q << ",\n"
                     << "      \"mean_sim_sec\": " << std::fixed << std::setprecision(7) << rep_q.mean_sim_sec << ",\n"
                     << "      \"median_sim_sec\": " << rep_q.median_sim_sec << ",\n"
                     << "      \"std_sim_sec\": " << rep_q.std_sim_sec << ",\n"
                     << "      \"events\": " << rep_q.last_stats.total_events_processed << ",\n"
                     << "      \"events_per_sec\": " << std::setprecision(2) << (rep_q.last_stats.total_events_processed / rep_q.mean_sim_sec) << ",\n"
                     << "      \"parity_with_serial\": " << ((rep_q.last_stats.state_digest == res_ser_heldout.state_digest) ? "true" : "false") << "\n"
                     << "    }";
        }
    };
    run_queue_cell("binary_heap_2ary", [&](int32_t W_q) {
        return sc::Exp4PersistentPoolEngineT<sc::BinaryHeapQueue>(cfg_topo, g_eval.graph, W_q, 6, part_oracle);
    });
    run_queue_cell("dary_heap_4ary", [&](int32_t W_q) {
        return sc::Exp4PersistentPoolEngineT<sc::DaryHeapQueue<4>>(cfg_topo, g_eval.graph, W_q, 6, part_oracle);
    });
    run_queue_cell("dary_heap_8ary", [&](int32_t W_q) {
        return sc::Exp4PersistentPoolEngineT<sc::DaryHeapQueue<8>>(cfg_topo, g_eval.graph, W_q, 6, part_oracle);
    });
    run_queue_cell("calendar_bucket_queue", [&](int32_t W_q) {
        return sc::Exp4PersistentPoolEngineT<sc::BucketEventQueue>(cfg_topo, g_eval.graph, W_q, 6, part_oracle);
    });
    json_out << "\n  ],\n";

    std::cout << "\n[Stage 2C] Graph Representation, State Layout & History Depth Sweep (D2 Matrix)..." << std::endl;
    json_out << "  \"stage2c_representation_and_history\": [\n";
    int32_t N_rep = (bcfg.profile == "smoke") ? 10000 : 100000;
    sc::SubstrateConfig cfg_rep;
    cfg_rep.num_nodes = N_rep;
    cfg_rep.mean_out_degree = 16;

    auto t_vov0 = std::chrono::high_resolution_clock::now();
    auto g_rep_vov = sc::Exp4GraphGenerators::create_modular_sbm_vec_of_vec(N_rep, 16, 6, 0.05f, seed_topo);
    double build_vov_sec = std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - t_vov0).count();

    auto t_flat0 = std::chrono::high_resolution_clock::now();
    auto g_rep_flat = sc::Exp4GraphGenerators::create_modular_sbm(N_rep, 16, 6, 0.05f, seed_topo);
    double build_flat_sec = std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - t_flat0).count();

    auto t_comp0 = std::chrono::high_resolution_clock::now();
    auto g_rep_compact = sc::NeuralGraphCompactCSR::from_standard_csr(g_rep_flat.graph);
    double build_compact_sec = std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - t_comp0).count();

    sc::NeuralGraphProceduralSBM g_rep_proc;
    g_rep_proc.num_nodes = N_rep;
    g_rep_proc.out_degree = 16;
    g_rep_proc.num_modules = 6;
    g_rep_proc.cross_ratio_c = 0.05f;
    g_rep_proc.seed = seed_topo;

    std::vector<sc::ExternalEvent> inputs_rep;
    for (int32_t s = 0; s < 300; ++s) {
        inputs_rep.push_back({0.02 * s, (s * 97) % N_rep, 1.5f});
    }

    auto rep_ser_flat = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_rep, &g_rep_flat.graph, nullptr, nullptr, inputs_rep, 6.0);
    });
    auto rep_ser_vov = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_rep, &g_rep_vov.graph, nullptr, nullptr, inputs_rep, 6.0);
    });
    auto rep_ser_aos = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStateAoS>(cfg_rep, &g_rep_flat.graph, nullptr, nullptr, inputs_rep, 6.0);
    });
    auto rep_ser_compact = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_rep, nullptr, &g_rep_compact, nullptr, inputs_rep, 6.0);
    });
    auto rep_ser_proc = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_rep, nullptr, nullptr, &g_rep_proc, inputs_rep, 6.0);
    });

    sc::SubstrateConfig cfg_L16 = cfg_rep; cfg_L16.history_capacity_L = 16;
    sc::SubstrateConfig cfg_L64 = cfg_rep; cfg_L64.history_capacity_L = 64;
    auto rep_ser_L16 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_L16, &g_rep_flat.graph, nullptr, nullptr, inputs_rep, 6.0);
    });
    auto rep_ser_L64 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        return sc::run_serial_custom_graph<sc::SubstrateStatePacked>(cfg_L64, &g_rep_flat.graph, nullptr, nullptr, inputs_rep, 6.0);
    });

    struct RepRow {
        std::string label;
        std::string repr;
        std::string layout;
        int32_t L;
        double build_sec;
        size_t payload_bytes;
        sc::RepStatsSummary stats;
        bool exact_same_graph;
    };
    std::vector<RepRow> rep_rows = {
        {"csr_vec_of_vec_soa_L0", "csr_vec_of_vec", "soa_packed", 0, build_vov_sec, g_rep_vov.graph.memory_bytes(), rep_ser_vov, true},
        {"csr_direct_flat_soa_L0", "csr_direct_flat", "soa_packed", 0, build_flat_sec, g_rep_flat.graph.memory_bytes(), rep_ser_flat, true},
        {"csr_direct_flat_aos_L0", "csr_direct_flat", "aos_record", 0, build_flat_sec, g_rep_flat.graph.memory_bytes(), rep_ser_aos, true},
        {"csr_direct_flat_soa_L16", "csr_direct_flat", "soa_packed", 16, build_flat_sec, g_rep_flat.graph.memory_bytes() + static_cast<size_t>(N_rep) * 16 * 9, rep_ser_L16, true},
        {"csr_direct_flat_soa_L64", "csr_direct_flat", "soa_packed", 64, build_flat_sec, g_rep_flat.graph.memory_bytes() + static_cast<size_t>(N_rep) * 64 * 9, rep_ser_L64, true},
        {"csr_compact_q16_soa_L0", "csr_compact_quantized_8B", "soa_packed", 0, build_compact_sec, g_rep_compact.memory_footprint_bytes(), rep_ser_compact, false},
        {"procedural_implicit_soa_L0", "procedural_on_the_fly_0B", "soa_packed", 0, 0.0, g_rep_proc.memory_footprint_bytes(), rep_ser_proc, false}
    };

    bool first_rep = true;
    for (const auto& rr : rep_rows) {
        std::string b_id_r = rr.exact_same_graph
            ? ("exp0004_stage2c_repr_N" + std::to_string(N_rep))
            : ("exp0004_stage2c_" + rr.label + "_N" + std::to_string(N_rep));
        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_r;
        rp.run_id = b_id_r + "_" + bcfg.build_id + "_" + rr.label;
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage2c_representation_sweep";
        rp.semantic_class = rr.exact_same_graph ? "exact" : "relaxed-model";
        rp.num_nodes = N_rep;
        rp.num_edges = (rr.repr == "procedural_on_the_fly_0B") ? (static_cast<uint64_t>(N_rep) * 16) : g_rep_flat.graph.num_edges;
        rp.topology_type = "modular_sbm_c0.05";
        rp.representation = rr.repr;
        rp.state_layout = rr.layout;
        rp.history_capacity_L = rr.L;
        rp.engine_id = "cpp_serial";
        rp.num_workers = 1;
        rp.num_regions = 1;
        rp.t_max = 6.0;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = inputs_rep.size();
        rp.graph_payload_bytes = rr.payload_bytes;
        rp.rep_summary = rr.stats;
        rp.has_serial_ref = rr.exact_same_graph;
        rp.serial_digest = rep_ser_flat.last_stats.state_digest;
        rp.serial_spikes = rep_ser_flat.last_stats.total_spikes;
        rp.serial_events = rep_ser_flat.last_stats.total_events_processed;
        append_record(rp);

        if (!first_rep) json_out << ",\n";
        first_rep = false;
        json_out << "    {\n"
                 << "      \"label\": \"" << rr.label << "\",\n"
                 << "      \"representation\": \"" << rr.repr << "\",\n"
                 << "      \"state_layout\": \"" << rr.layout << "\",\n"
                 << "      \"history_L\": " << rr.L << ",\n"
                 << "      \"build_sec\": " << std::fixed << std::setprecision(7) << rr.build_sec << ",\n"
                 << "      \"payload_mb\": " << std::setprecision(3) << (rr.payload_bytes / (1024.0 * 1024.0)) << ",\n"
                 << "      \"mean_sim_sec\": " << std::setprecision(7) << rr.stats.mean_sim_sec << ",\n"
                 << "      \"median_sim_sec\": " << rr.stats.median_sim_sec << ",\n"
                 << "      \"std_sim_sec\": " << rr.stats.std_sim_sec << ",\n"
                 << "      \"events\": " << rr.stats.last_stats.total_events_processed << ",\n"
                 << "      \"events_per_sec\": " << std::setprecision(2) << (rr.stats.last_stats.total_events_processed / rr.stats.mean_sim_sec) << ",\n"
                 << "      \"state_digest\": \"" << sc::to_hex_digest(rr.stats.last_stats.state_digest) << "\"\n"
                 << "    }";
    }
    json_out << "\n  ],\n";
