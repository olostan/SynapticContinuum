    if (bcfg.profile != "smoke") {
        // =====================================================================
        // STAGE 3D: N = 3,000,000 and N = 10,000,000 Scale Ladder (Preflight Gated <= 60% Available RAM)
        // =====================================================================
        std::cout << "\n[Stage 3D] Scale Ladder: N = 3,000,000 (D=16) and N = 10,000,000 (D=4 & D=16)..." << std::endl;
        json_out << "  \"stage3d_extreme_scale_ladder\": [\n";
        bool first_ext = true;

        auto run_scale_cell = [&](int32_t N_ext, int32_t D_ext, int32_t stim_per_mod) {
            auto mem = sc::query_host_mem();
            uint64_t safe_budget = static_cast<uint64_t>(mem.available_ram_bytes * 0.60);
            uint64_t est_bytes = static_cast<uint64_t>(N_ext) * 44ULL + static_cast<uint64_t>(N_ext) * static_cast<uint64_t>(D_ext) * 12ULL + (128ULL * 1024 * 1024);

            if (est_bytes > safe_budget) {
                std::cout << "  [SKIP Preflight] N=" << N_ext << " D=" << D_ext << " est=" << (est_bytes / (1024*1024))
                          << " MB > 60% avail (" << (safe_budget / (1024*1024)) << " MB)" << std::endl;
                return;
            }

            sc::SubstrateConfig cfg_ext;
            cfg_ext.num_nodes = N_ext;
            cfg_ext.mean_out_degree = D_ext;

            uint64_t rss_before_ext = sc::get_current_rss_bytes();
            auto g_ext = sc::Exp4GraphGenerators::create_disconnected_modules(N_ext, D_ext, 6, seed_topo);
            uint64_t rss_after_ext = sc::get_current_rss_bytes();
            uint64_t g_ext_csum = sc::compute_graph_checksum(g_ext.graph);

            std::vector<sc::ExternalEvent> in_ext;
            in_ext.reserve(static_cast<size_t>(6 * stim_per_mod));
            int32_t stride = (D_ext == 4) ? 500 : 3000;
            float amp = (D_ext == 4) ? 1.8f : 1.5f;
            double dt_stim = (10.0 / std::max(1, stim_per_mod));
            for (int32_t m = 0; m < 6; ++m) {
                int32_t start_n = m * (N_ext / 6);
                for (int32_t s = 0; s < stim_per_mod; ++s) {
                    in_ext.push_back({dt_stim * s, start_n + (s % stride), amp});
                }
            }
            uint64_t in_ext_csum = sc::compute_inputs_checksum(in_ext);

            int32_t ext_warmups = 1;
            int32_t ext_reps = 3;

            sc::Exp4SerialEngine ser_ext(cfg_ext, g_ext.graph);
            auto rep_ser_ext = sc::execute_with_reps(ext_warmups, ext_reps, [&]() {
                auto t0 = std::chrono::high_resolution_clock::now();
                auto res = ser_ext.run(in_ext, 15.0);
                auto t1 = std::chrono::high_resolution_clock::now();
                return sc::sim_result_to_stats(res, std::chrono::duration<double>(t1 - t0).count(), 6);
            });

            std::string b_id_ext = "exp0004_stage3d_scale_N" + std::to_string(N_ext) + "_D" + std::to_string(D_ext);
            {
                sc::CanonicalRecordParams rp;
                rp.benchmark_id = b_id_ext;
                rp.run_id = b_id_ext + "_" + bcfg.build_id + "_cpp_serial_W1";
                rp.build_id = bcfg.build_id;
                rp.workload_name = "stage3d_scale_N" + std::to_string(N_ext) + "_D" + std::to_string(D_ext);
                rp.num_nodes = N_ext;
                rp.num_edges = g_ext.graph.num_edges;
                rp.mean_out_degree = D_ext;
                rp.topology_type = "disconnected_modules";
                rp.engine_id = "cpp_serial";
                rp.num_workers = 1;
                rp.num_regions = 6;
                rp.t_max = 15.0;
                rp.warmups = ext_warmups;
                rp.reps = ext_reps;
                rp.external_events = in_ext.size();
                rp.graph_payload_bytes = g_ext.graph.memory_bytes();
                rp.rss_before_build_bytes = rss_before_ext;
                rp.rss_after_build_bytes = rss_after_ext;
                rp.rss_after_sim_bytes = sc::get_current_rss_bytes();
                rp.graph_checksum = g_ext_csum;
                rp.input_events_checksum = in_ext_csum;
                rp.rep_summary = rep_ser_ext;
                rp.serial_digest = rep_ser_ext.last_stats.state_digest;
                rp.serial_spikes = rep_ser_ext.last_stats.total_spikes;
                rp.serial_events = rep_ser_ext.last_stats.total_events_processed;
                append_record(rp);
            }

            double t_w1 = 0.0;
            for (int32_t W : {1, 6}) {
                sc::Exp4PersistentPoolEngine pool_ext(cfg_ext, g_ext.graph, W, 6, g_ext.planted_labels);
                auto rep_ext = sc::execute_with_reps(ext_warmups, ext_reps, [&]() {
                    return pool_ext.run(in_ext, 15.0);
                });
                if (W == 1) t_w1 = rep_ext.mean_sim_sec;
                double speedup = (t_w1 > 0) ? (t_w1 / rep_ext.mean_sim_sec) : 1.0;
                uint64_t rss_after_sim_ext = sc::get_current_rss_bytes();

                sc::CanonicalRecordParams rp;
                rp.benchmark_id = b_id_ext;
                rp.run_id = b_id_ext + "_" + bcfg.build_id + "_cpp_persistent_pool_W" + std::to_string(W);
                rp.build_id = bcfg.build_id;
                rp.workload_name = "stage3d_scale_N" + std::to_string(N_ext) + "_D" + std::to_string(D_ext);
                rp.num_nodes = N_ext;
                rp.num_edges = g_ext.graph.num_edges;
                rp.mean_out_degree = D_ext;
                rp.topology_type = "disconnected_modules";
                rp.engine_id = "cpp_persistent_pool";
                rp.num_workers = W;
                rp.num_regions = 6;
                rp.t_max = 15.0;
                rp.warmups = ext_warmups;
                rp.reps = ext_reps;
                rp.external_events = in_ext.size();
                rp.graph_payload_bytes = g_ext.graph.memory_bytes();
                rp.rss_before_build_bytes = rss_before_ext;
                rp.rss_after_build_bytes = rss_after_ext;
                rp.rss_after_sim_bytes = rss_after_sim_ext;
                rp.graph_checksum = g_ext_csum;
                rp.input_events_checksum = in_ext_csum;
                rp.rep_summary = rep_ext;
                rp.serial_digest = rep_ser_ext.last_stats.state_digest;
                rp.serial_spikes = rep_ser_ext.last_stats.total_spikes;
                rp.serial_events = rep_ser_ext.last_stats.total_events_processed;
                append_record(rp);

                if (!first_ext) json_out << ",\n";
                first_ext = false;
                json_out << "    {\n"
                         << "      \"N\": " << N_ext << ",\n"
                         << "      \"D\": " << D_ext << ",\n"
                         << "      \"W\": " << W << ",\n"
                         << "      \"serial_sim_sec\": " << std::fixed << std::setprecision(7) << rep_ser_ext.mean_sim_sec << ",\n"
                         << "      \"serial_rep_wall_sim_sec\": " << sc::format_double_vec(rep_ser_ext.rep_sim_sec) << ",\n"
                         << "      \"mean_sim_sec\": " << rep_ext.mean_sim_sec << ",\n"
                         << "      \"median_sim_sec\": " << rep_ext.median_sim_sec << ",\n"
                         << "      \"std_sim_sec\": " << rep_ext.std_sim_sec << ",\n"
                         << "      \"rep_wall_sim_sec\": " << sc::format_double_vec(rep_ext.rep_sim_sec) << ",\n"
                         << "      \"self_speedup\": " << std::setprecision(3) << speedup << ",\n"
                         << "      \"speedup_vs_serial\": " << (rep_ser_ext.mean_sim_sec / rep_ext.mean_sim_sec) << ",\n"
                         << "      \"events\": " << rep_ext.last_stats.total_events_processed << ",\n"
                         << "      \"spikes\": " << rep_ext.last_stats.total_spikes << ",\n"
                         << "      \"events_per_sec\": " << std::setprecision(2) << (rep_ext.last_stats.total_events_processed / rep_ext.mean_sim_sec) << ",\n"
                         << "      \"graph_checksum\": \"" << sc::to_hex_digest(g_ext_csum) << "\",\n"
                         << "      \"input_events_checksum\": \"" << sc::to_hex_digest(in_ext_csum) << "\",\n"
                         << "      \"state_digest\": \"" << sc::to_hex_digest(rep_ext.last_stats.state_digest) << "\",\n"
                         << "      \"reference_serial_digest\": \"" << sc::to_hex_digest(rep_ser_ext.last_stats.state_digest) << "\",\n"
                         << "      \"parity_with_serial\": " << ((rep_ext.last_stats.state_digest == rep_ser_ext.last_stats.state_digest) ? "true" : "false") << ",\n"
                         << "      \"graph_payload_mb\": " << std::setprecision(2) << (g_ext.graph.memory_bytes() / (1024.0 * 1024.0)) << ",\n"
                         << "      \"rss_before_build_mb\": " << (rss_before_ext / (1024.0 * 1024.0)) << ",\n"
                         << "      \"rss_after_build_mb\": " << (rss_after_ext / (1024.0 * 1024.0)) << ",\n"
                         << "      \"rss_after_sim_mb\": " << (rss_after_sim_ext / (1024.0 * 1024.0)) << ",\n"
                         << "      \"peak_rss_mb\": " << (rep_ext.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                         << "    }";
                std::cout << "  [Scale N=" << N_ext << " D=" << D_ext << "] W=" << W
                          << " | Mean: " << (rep_ext.mean_sim_sec * 1000.0) << " ms | Speedup: " << speedup
                          << "x | Ev: " << rep_ext.last_stats.total_events_processed
                          << " | Payload: " << (g_ext.graph.memory_bytes() / (1024.0 * 1024.0)) << " MB"
                          << " | PeakRSS: " << (rep_ext.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << " MB" << std::endl;
            }
        };

        // 1. N = 3,000,000, D = 16 (48M edges, ~576 MB CSR payload, >= 1.1M processed events)
        run_scale_cell(3000000, 16, 15000);
        // 2. N = 10,000,000, D = 4 (40M edges, ~560 MB CSR payload, >= 1.1M processed events)
        run_scale_cell(10000000, 4, 250000);
        // 3. N = 10,000,000, D = 16 (160M edges, ~1.92 GB CSR payload, >= 1.1M processed events)
        run_scale_cell(10000000, 16, 15000);

        json_out << "\n  ],\n";
    }

    // =========================================================================
    // STAGE 4: Order Relaxation as Alternative Dynamic Model (With Violation Counters & 100-Trial Discrimination)
    // =========================================================================
    std::cout << "\n[Stage 4] Order Relaxation as Alternative Neural Model..." << std::endl;
    json_out << "  \"stage4_relaxed_ordering\": [\n";

    sc::Exp4SerialEngine exact_serial(cfg_topo, g_eval.graph);
    auto exact_ref = exact_serial.run(heldout_inputs, 6.0);
    std::string b_id_rel = "exp0004_stage4_relaxed_N" + std::to_string(N_topo) + "_D16_c0.10";

    bool first_rel = true;
    for (double eps : {0.0, 0.001, 0.010, 0.100, 0.500, 1.000}) {
        sc::Exp4RelaxedEngine relaxed(cfg_topo, g_eval.graph, 6, 24, part_oracle, eps);
        auto div = relaxed.evaluate_divergence_vs_reference(heldout_inputs, 6.0, exact_ref, 100);
        auto rep_rel = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return relaxed.run(heldout_inputs, 6.0);
        });

        std::ostringstream eps_ss;
        eps_ss << std::fixed << std::setprecision(3) << eps;

        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_rel;
        rp.run_id = b_id_rel + "_" + bcfg.build_id + "_eps" + eps_ss.str() + "_W6";
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage4_relaxed_eps" + eps_ss.str();
        rp.semantic_class = (eps == 0.0) ? "exact" : "relaxed-model";
        rp.num_nodes = N_topo;
        rp.num_edges = g_eval.graph.num_edges;
        rp.topology_type = "modular_sbm_c0.10";
        rp.engine_id = "cpp_relaxed";
        rp.algorithm_family = (eps == 0.0) ? "conservative_pdes" : "bounded_order_relaxed";
        rp.num_workers = 6;
        rp.num_regions = 24;
        rp.t_max = 6.0;
        rp.epsilon = eps;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = heldout_inputs.size();
        rp.graph_payload_bytes = g_eval.graph.memory_bytes();
        rp.graph_checksum = g_eval_csum;
        rp.input_events_checksum = heldout_in_csum;
        rp.rep_summary = rep_rel;
        rp.serial_digest = exact_ref.state_digest;
        rp.serial_spikes = exact_ref.total_spikes;
        rp.serial_events = exact_ref.total_events_processed;
        rp.exact_spike_matches = div.exact_spike_matches;
        rp.backward_time_events = div.backward_time_events;
        rp.out_of_order_worker_events = div.out_of_order_worker_events;
        rp.spike_count_error = div.spike_count_error;
        rp.spike_timestamp_rmse = div.spike_timestamp_rmse;
        rp.potential_rmse = div.potential_rmse;
        rp.temporal_discrimination_accuracy = div.temporal_discrimination_accuracy;
        rp.temporal_discrimination_passed = div.temporal_discrimination_passed;
        append_record(rp);

        if (!first_rel) json_out << ",\n";
        first_rel = false;
        json_out << "    {\n"
                 << "      \"epsilon\": " << std::fixed << std::setprecision(3) << eps << ",\n"
                 << "      \"semantic_class\": \"" << ((eps == 0.0) ? "exact" : "relaxed-model") << "\",\n"
                 << "      \"mean_sim_sec\": " << std::setprecision(7) << rep_rel.mean_sim_sec << ",\n"
                 << "      \"median_sim_sec\": " << rep_rel.median_sim_sec << ",\n"
                 << "      \"std_sim_sec\": " << rep_rel.std_sim_sec << ",\n"
                 << "      \"total_events\": " << div.total_events << ",\n"
                 << "      \"total_spikes\": " << div.total_spikes << ",\n"
                 << "      \"exact_spike_matches\": " << div.exact_spike_matches << ",\n"
                 << "      \"backward_time_events\": " << div.backward_time_events << ",\n"
                 << "      \"out_of_order_worker_events\": " << div.out_of_order_worker_events << ",\n"
                 << "      \"spike_count_error\": " << div.spike_count_error << ",\n"
                 << "      \"spike_timestamp_rmse\": " << std::setprecision(6) << div.spike_timestamp_rmse << ",\n"
                 << "      \"potential_rmse\": " << div.potential_rmse << ",\n"
                 << "      \"state_digest\": \"" << sc::to_hex_digest(div.state_digest) << "\",\n"
                 << "      \"reference_digest\": \"" << sc::to_hex_digest(div.reference_digest) << "\",\n"
                 << "      \"parity_with_serial\": " << ((eps == 0.0 && div.state_digest == div.reference_digest && div.backward_time_events == 0) ? "true" : "false") << ",\n"
                 << "      \"temporal_discrimination_trials\": " << div.temporal_discrimination_trials << ",\n"
                 << "      \"temporal_discrimination_correct\": " << div.temporal_discrimination_correct << ",\n"
                 << "      \"temporal_discrimination_accuracy\": " << std::setprecision(4) << div.temporal_discrimination_accuracy << ",\n"
                 << "      \"temporal_discrimination_chance_baseline\": " << div.temporal_discrimination_chance_baseline << ",\n"
                 << "      \"temporal_discrimination_passed\": " << (div.temporal_discrimination_passed ? "true" : "false") << "\n"
                 << "    }";
    }
    json_out << "\n  ],\n";

    // Emit canonical schema-validated benchmark_records array
    json_out << "  \"benchmark_records\": [\n";
    for (size_t idx = 0; idx < all_canonical_records.size(); ++idx) {
        if (idx > 0) json_out << ",\n";
        json_out << all_canonical_records[idx];
    }
    json_out << "\n  ]\n";
    json_out << "}\n";

    std::string final_json = json_out.str();
    if (!bcfg.out_path.empty()) {
        std::ofstream f(bcfg.out_path);
        if (f) {
            f << final_json;
            std::cout << "\nCanonical metrics (" << all_canonical_records.size() << " schema-v1.0.0 records) written to: " << bcfg.out_path << std::endl;
        } else {
            std::cerr << "Failed to open output file: " << bcfg.out_path << std::endl;
            return 1;
        }
    }

    std::cout << "\nEXP-0004 benchmark execution completed successfully." << std::endl;
    return 0;
}
