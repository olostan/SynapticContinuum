    // =========================================================================
    // STAGE 3: Parallel Schedulers Comparison (D4 Matrix across Physical + SMT)
    // =========================================================================
    std::cout << "\n[Stage 3] Parallel Schedulers Comparison across W (D4 Matrix)..." << std::endl;
    json_out << "  \"stage3_schedulers\": [\n";

    std::string b_id_s3 = "exp0004_stage3_schedulers_N" + std::to_string(N_topo) + "_D16_c0.10";
    auto node_to_reg24 = sc::Exp4Partitioners::partition_contiguous(N_topo, 24);
    bool first_sched = true;

    for (int32_t W : bcfg.smt_counts) {
        sc::Exp4OwnerInstrumentedEngine owner(cfg_topo, g_eval.graph, W, part_oracle);
        auto rep_owner = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return owner.run(heldout_inputs, 6.0);
        });

        sc::Exp4PersistentPoolEngine pool24(cfg_topo, g_eval.graph, W, 24, node_to_reg24);
        auto rep_pool24 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool24.run(heldout_inputs, 6.0);
        });

        sc::Exp4OpenMPEngine omp24(cfg_topo, g_eval.graph, W, 24, node_to_reg24);
        auto rep_omp24 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return omp24.run(heldout_inputs, 6.0);
        });

        sc::Exp4PairwiseWatermarkEngine wm24(cfg_topo, g_eval.graph, W, 24, node_to_reg24);
        auto rep_wm24 = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return wm24.run(heldout_inputs, 6.0);
        });

        sc::Exp4AdaptiveEngine adaptive(cfg_topo, g_eval.graph, W, 24, node_to_reg24, 1.30, 2);
        auto rep_adapt = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return adaptive.run_adaptive(heldout_inputs, 6.0);
        });

        auto emit_s3_rec = [&](const std::string& eng_id, const sc::RepStatsSummary& rsum, int32_t R_val) {
            sc::CanonicalRecordParams rp;
            rp.benchmark_id = b_id_s3;
            rp.run_id = b_id_s3 + "_" + bcfg.build_id + "_" + eng_id + "_W" + std::to_string(W);
            rp.build_id = bcfg.build_id;
            rp.workload_name = "stage3_scheduler_matrix";
            rp.num_nodes = N_topo;
            rp.num_edges = g_eval.graph.num_edges;
            rp.topology_type = "modular_sbm_c0.10";
            rp.engine_id = eng_id;
            rp.num_workers = W;
            rp.num_regions = R_val;
            rp.t_max = 6.0;
            rp.warmups = bcfg.warmups;
            rp.reps = bcfg.repetitions;
            rp.external_events = heldout_inputs.size();
            rp.graph_payload_bytes = g_eval.graph.memory_bytes();
            rp.graph_checksum = g_eval_csum;
            rp.input_events_checksum = heldout_in_csum;
            rp.rep_summary = rsum;
            rp.serial_digest = res_ser_heldout.state_digest;
            rp.serial_spikes = res_ser_heldout.total_spikes;
            rp.serial_events = res_ser_heldout.total_events_processed;
            append_record(rp);
        };

        emit_s3_rec("cpp_owner_static", rep_owner, W);
        emit_s3_rec("cpp_persistent_pool", rep_pool24, 24);
        emit_s3_rec("cpp_openmp_epoch", rep_omp24, 24);
        emit_s3_rec("cpp_pairwise_watermark", rep_wm24, 24);
        emit_s3_rec("cpp_adaptive", rep_adapt, 24);

        if (!first_sched) json_out << ",\n";
        first_sched = false;
        json_out << "    {\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"events\": " << rep_pool24.last_stats.total_events_processed << ",\n"
                 << "      \"owner_barrier_sec\": " << std::fixed << std::setprecision(7) << rep_owner.mean_sim_sec << ",\n"
                 << "      \"owner_spawn_overhead_sec\": " << rep_owner.last_stats.thread_spawn_join_overhead_sec << ",\n"
                 << "      \"persistent_pool_sec\": " << rep_pool24.mean_sim_sec << ",\n"
                 << "      \"openmp_epoch_sec\": " << rep_omp24.mean_sim_sec << ",\n"
                 << "      \"pairwise_watermark_sec\": " << rep_wm24.mean_sim_sec << ",\n"
                 << "      \"watermark_monotonicity_violations\": " << rep_wm24.last_stats.watermark_monotonicity_violations << ",\n"
                 << "      \"delayed_channel_deliveries\": " << rep_wm24.last_stats.delayed_channel_deliveries << ",\n"
                 << "      \"horizon_clamp_events\": " << rep_wm24.last_stats.horizon_clamp_events << ",\n"
                 << "      \"adaptive_scheduler_sec\": " << rep_adapt.mean_sim_sec << ",\n"
                 << "      \"migrations_count\": " << rep_adapt.last_stats.total_migrations << ",\n"
                 << "      \"migrated_queue_events\": " << rep_adapt.last_stats.migrated_queue_events << ",\n"
                 << "      \"migrated_mailbox_events\": " << rep_adapt.last_stats.migrated_mailbox_events << ",\n"
                 << "      \"migration_pause_sec\": " << rep_adapt.last_stats.migration_pause_sec << ",\n"
                 << "      \"all_exact_parity_with_serial\": "
                 << (((rep_owner.last_stats.state_digest == res_ser_heldout.state_digest) &&
                      (rep_pool24.last_stats.state_digest == res_ser_heldout.state_digest) &&
                      (rep_omp24.last_stats.state_digest == res_ser_heldout.state_digest) &&
                      (rep_wm24.last_stats.state_digest == res_ser_heldout.state_digest) &&
                      (rep_adapt.last_stats.state_digest == res_ser_heldout.state_digest)) ? "true" : "false") << "\n"
                 << "    }";
    }
    json_out << "\n  ],\n";

    // =========================================================================
    // STAGE 3B: High-Scale Benchmark (N = 100,000 Neurons + Degree/Activity Sweep)
    // =========================================================================
    std::cout << "\n[Stage 3B] High-Scale Benchmark (N = 100,000 Neurons)..." << std::endl;
    json_out << "  \"stage3b_high_scale_100k\": [\n";

    int32_t N_100k = (bcfg.profile == "smoke") ? 20000 : 100000;
    sc::SubstrateConfig cfg_100k;
    cfg_100k.num_nodes = N_100k;
    cfg_100k.mean_out_degree = 16;

    uint64_t rss_before_100k = sc::get_current_rss_bytes();
    auto g_100k_disc = sc::Exp4GraphGenerators::create_disconnected_modules(N_100k, 16, 6, seed_topo);
    uint64_t rss_after_100k = sc::get_current_rss_bytes();
    uint64_t g_100k_csum = sc::compute_graph_checksum(g_100k_disc.graph);
    std::vector<sc::ExternalEvent> inputs_100k;
    for (int32_t m = 0; m < 6; ++m) {
        int32_t start_n = m * (N_100k / 6);
        for (int32_t s = 0; s < 500; ++s) {
            inputs_100k.push_back({0.02 * s, start_n + (s % 100), 1.5f});
        }
    }
    uint64_t in_100k_csum = sc::compute_inputs_checksum(inputs_100k);

    sc::Exp4SerialEngine ser_100k(cfg_100k, g_100k_disc.graph);
    auto rep_ser_100k = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
        auto t0 = std::chrono::high_resolution_clock::now();
        auto res = ser_100k.run(inputs_100k, 10.0);
        auto t1 = std::chrono::high_resolution_clock::now();
        return sc::sim_result_to_stats(res, std::chrono::duration<double>(t1 - t0).count(), 6);
    });

    std::string b_id_100k = "exp0004_stage3b_100k_disconnected_N" + std::to_string(N_100k) + "_D16";
    {
        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_100k;
        rp.run_id = b_id_100k + "_" + bcfg.build_id + "_cpp_serial_W1";
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage3b_100k_scaling";
        rp.num_nodes = N_100k;
        rp.num_edges = g_100k_disc.graph.num_edges;
        rp.topology_type = "disconnected_modules";
        rp.engine_id = "cpp_serial";
        rp.num_workers = 1;
        rp.num_regions = 6;
        rp.t_max = 10.0;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = inputs_100k.size();
        rp.graph_payload_bytes = g_100k_disc.graph.memory_bytes();
        rp.rss_before_build_bytes = rss_before_100k;
        rp.rss_after_build_bytes = rss_after_100k;
        rp.rss_after_sim_bytes = sc::get_current_rss_bytes();
        rp.graph_checksum = g_100k_csum;
        rp.input_events_checksum = in_100k_csum;
        rp.rep_summary = rep_ser_100k;
        rp.serial_digest = rep_ser_100k.last_stats.state_digest;
        rp.serial_spikes = rep_ser_100k.last_stats.total_spikes;
        rp.serial_events = rep_ser_100k.last_stats.total_events_processed;
        append_record(rp);
    }

    double t_100k_w1 = 0.0;
    bool first_100k = true;
    for (int32_t W : bcfg.worker_counts) {
        sc::Exp4PersistentPoolEngine pool_100k(cfg_100k, g_100k_disc.graph, W, 6, g_100k_disc.planted_labels);
        auto rep_100k = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
            return pool_100k.run(inputs_100k, 10.0);
        });
        if (W == 1) t_100k_w1 = rep_100k.mean_sim_sec;
        double speedup = (t_100k_w1 > 0) ? (t_100k_w1 / rep_100k.mean_sim_sec) : 1.0;

        sc::CanonicalRecordParams rp;
        rp.benchmark_id = b_id_100k;
        rp.run_id = b_id_100k + "_" + bcfg.build_id + "_cpp_persistent_pool_W" + std::to_string(W);
        rp.build_id = bcfg.build_id;
        rp.workload_name = "stage3b_100k_scaling";
        rp.num_nodes = N_100k;
        rp.num_edges = g_100k_disc.graph.num_edges;
        rp.topology_type = "disconnected_modules";
        rp.engine_id = "cpp_persistent_pool";
        rp.num_workers = W;
        rp.num_regions = 6;
        rp.t_max = 10.0;
        rp.warmups = bcfg.warmups;
        rp.reps = bcfg.repetitions;
        rp.external_events = inputs_100k.size();
        rp.graph_payload_bytes = g_100k_disc.graph.memory_bytes();
        rp.rss_before_build_bytes = rss_before_100k;
        rp.rss_after_build_bytes = rss_after_100k;
        rp.rss_after_sim_bytes = sc::get_current_rss_bytes();
        rp.graph_checksum = g_100k_csum;
        rp.input_events_checksum = in_100k_csum;
        rp.rep_summary = rep_100k;
        rp.serial_digest = rep_ser_100k.last_stats.state_digest;
        rp.serial_spikes = rep_ser_100k.last_stats.total_spikes;
        rp.serial_events = rep_ser_100k.last_stats.total_events_processed;
        append_record(rp);

        if (!first_100k) json_out << ",\n";
        first_100k = false;
        json_out << "    {\n"
                 << "      \"N\": " << N_100k << ",\n"
                 << "      \"W\": " << W << ",\n"
                 << "      \"serial_sim_sec\": " << std::fixed << std::setprecision(7) << rep_ser_100k.mean_sim_sec << ",\n"
                 << "      \"mean_sim_sec\": " << rep_100k.mean_sim_sec << ",\n"
                 << "      \"median_sim_sec\": " << rep_100k.median_sim_sec << ",\n"
                 << "      \"std_sim_sec\": " << rep_100k.std_sim_sec << ",\n"
                 << "      \"self_speedup\": " << std::setprecision(3) << speedup << ",\n"
                 << "      \"speedup_vs_serial\": " << (rep_ser_100k.mean_sim_sec / rep_100k.mean_sim_sec) << ",\n"
                 << "      \"events\": " << rep_100k.last_stats.total_events_processed << ",\n"
                 << "      \"spikes\": " << rep_100k.last_stats.total_spikes << ",\n"
                 << "      \"events_per_sec\": " << std::setprecision(2) << (rep_100k.last_stats.total_events_processed / rep_100k.mean_sim_sec) << ",\n"
                 << "      \"state_digest\": \"" << sc::to_hex_digest(rep_100k.last_stats.state_digest) << "\",\n"
                 << "      \"parity_with_serial\": " << ((rep_100k.last_stats.state_digest == rep_ser_100k.last_stats.state_digest) ? "true" : "false") << ",\n"
                 << "      \"peak_rss_mb\": " << std::setprecision(2) << (rep_100k.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                 << "    }";
    }
    json_out << "\n  ],\n";

    // =========================================================================
    // STAGE 3C, 3D, 3E: Scale Ladder (N=1M Short & Sustained >=1M Ev, N=3M, N=10M)
    // =========================================================================
    if (bcfg.profile != "smoke") {
        std::cout << "\n[Stage 3C] N = 1,000,000 Short-Horizon (186,881 ev) & Sustained (>= 1,000,000 ev) Benchmarks..." << std::endl;
        json_out << "  \"stage3c_high_scale_1m\": [\n";

        int32_t N_1m = 1000000;
        sc::SubstrateConfig cfg_1m;
        cfg_1m.num_nodes = N_1m;
        cfg_1m.mean_out_degree = 16;

        uint64_t rss_before_1m = sc::get_current_rss_bytes();
        auto g_1m = sc::Exp4GraphGenerators::create_disconnected_modules(N_1m, 16, 6, seed_topo);
        uint64_t rss_after_1m = sc::get_current_rss_bytes();
        uint64_t g_1m_csum = sc::compute_graph_checksum(g_1m.graph);

        // Workload 1: Original short-horizon stimulus (12,000 external -> 186,881 total events)
        std::vector<sc::ExternalEvent> inputs_1m_short;
        inputs_1m_short.reserve(12000);
        for (int32_t m = 0; m < 6; ++m) {
            int32_t start_n = m * (N_1m / 6);
            for (int32_t s = 0; s < 2000; ++s) {
                inputs_1m_short.push_back({0.005 * s, start_n + (s % 500), 1.5f});
            }
        }

        // Workload 2: Sustained >= 1,000,000 processed events stimulus (72,000 external -> ~1,120,000 total events)
        std::vector<sc::ExternalEvent> inputs_1m_sustained;
        inputs_1m_sustained.reserve(72000);
        for (int32_t m = 0; m < 6; ++m) {
            int32_t start_n = m * (N_1m / 6);
            for (int32_t s = 0; s < 12000; ++s) {
                inputs_1m_sustained.push_back({0.001 * s, start_n + (s % 3000), 1.5f});
            }
        }

        bool first_1m = true;
        auto run_1m_workload = [&](const std::string& w_tag, const std::vector<sc::ExternalEvent>& in_ev, double t_lim) {
            uint64_t in_1m_csum = sc::compute_inputs_checksum(in_ev);
            sc::Exp4SerialEngine ser_1m(cfg_1m, g_1m.graph);
            auto rep_ser_1m = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                auto t0 = std::chrono::high_resolution_clock::now();
                auto res = ser_1m.run(in_ev, t_lim);
                auto t1 = std::chrono::high_resolution_clock::now();
                return sc::sim_result_to_stats(res, std::chrono::duration<double>(t1 - t0).count(), 6);
            });

            std::string b_id_1m = "exp0004_stage3c_1m_" + w_tag + "_N1000000_D16";
            {
                sc::CanonicalRecordParams rp;
                rp.benchmark_id = b_id_1m;
                rp.run_id = b_id_1m + "_" + bcfg.build_id + "_cpp_serial_W1";
                rp.build_id = bcfg.build_id;
                rp.workload_name = "stage3c_1m_" + w_tag;
                rp.num_nodes = N_1m;
                rp.num_edges = g_1m.graph.num_edges;
                rp.topology_type = "disconnected_modules";
                rp.engine_id = "cpp_serial";
                rp.num_workers = 1;
                rp.num_regions = 6;
                rp.t_max = t_lim;
                rp.warmups = bcfg.warmups;
                rp.reps = bcfg.repetitions;
                rp.external_events = in_ev.size();
                rp.graph_payload_bytes = g_1m.graph.memory_bytes();
                rp.rss_before_build_bytes = rss_before_1m;
                rp.rss_after_build_bytes = rss_after_1m;
                rp.rss_after_sim_bytes = sc::get_current_rss_bytes();
                rp.graph_checksum = g_1m_csum;
                rp.input_events_checksum = in_1m_csum;
                rp.rep_summary = rep_ser_1m;
                rp.serial_digest = rep_ser_1m.last_stats.state_digest;
                rp.serial_spikes = rep_ser_1m.last_stats.total_spikes;
                rp.serial_events = rep_ser_1m.last_stats.total_events_processed;
                append_record(rp);
            }

            double t_w1 = 0.0;
            for (int32_t W : bcfg.worker_counts) {
                sc::Exp4PersistentPoolEngine pool_1m(cfg_1m, g_1m.graph, W, 6, g_1m.planted_labels);
                auto rep_1m = sc::execute_with_reps(bcfg.warmups, bcfg.repetitions, [&]() {
                    return pool_1m.run(in_ev, t_lim);
                });
                if (W == 1) t_w1 = rep_1m.mean_sim_sec;
                double speedup = (t_w1 > 0) ? (t_w1 / rep_1m.mean_sim_sec) : 1.0;

                sc::CanonicalRecordParams rp;
                rp.benchmark_id = b_id_1m;
                rp.run_id = b_id_1m + "_" + bcfg.build_id + "_cpp_persistent_pool_W" + std::to_string(W);
                rp.build_id = bcfg.build_id;
                rp.workload_name = "stage3c_1m_" + w_tag;
                rp.num_nodes = N_1m;
                rp.num_edges = g_1m.graph.num_edges;
                rp.topology_type = "disconnected_modules";
                rp.engine_id = "cpp_persistent_pool";
                rp.num_workers = W;
                rp.num_regions = 6;
                rp.t_max = t_lim;
                rp.warmups = bcfg.warmups;
                rp.reps = bcfg.repetitions;
                rp.external_events = in_ev.size();
                rp.graph_payload_bytes = g_1m.graph.memory_bytes();
                rp.rss_before_build_bytes = rss_before_1m;
                rp.rss_after_build_bytes = rss_after_1m;
                rp.rss_after_sim_bytes = sc::get_current_rss_bytes();
                rp.graph_checksum = g_1m_csum;
                rp.input_events_checksum = in_1m_csum;
                rp.rep_summary = rep_1m;
                rp.serial_digest = rep_ser_1m.last_stats.state_digest;
                rp.serial_spikes = rep_ser_1m.last_stats.total_spikes;
                rp.serial_events = rep_ser_1m.last_stats.total_events_processed;
                append_record(rp);

                if (!first_1m) json_out << ",\n";
                first_1m = false;
                json_out << "    {\n"
                         << "      \"workload\": \"" << w_tag << "\",\n"
                         << "      \"N\": " << N_1m << ",\n"
                         << "      \"W\": " << W << ",\n"
                         << "      \"serial_sim_sec\": " << std::fixed << std::setprecision(7) << rep_ser_1m.mean_sim_sec << ",\n"
                         << "      \"mean_sim_sec\": " << rep_1m.mean_sim_sec << ",\n"
                         << "      \"median_sim_sec\": " << rep_1m.median_sim_sec << ",\n"
                         << "      \"std_sim_sec\": " << rep_1m.std_sim_sec << ",\n"
                         << "      \"rep_wall_sim_sec\": " << sc::format_double_vec(rep_1m.rep_sim_sec) << ",\n"
                         << "      \"self_speedup\": " << std::setprecision(3) << speedup << ",\n"
                         << "      \"speedup_vs_serial\": " << (rep_ser_1m.mean_sim_sec / rep_1m.mean_sim_sec) << ",\n"
                         << "      \"events\": " << rep_1m.last_stats.total_events_processed << ",\n"
                         << "      \"spikes\": " << rep_1m.last_stats.total_spikes << ",\n"
                         << "      \"events_per_sec\": " << std::setprecision(2) << (rep_1m.last_stats.total_events_processed / rep_1m.mean_sim_sec) << ",\n"
                         << "      \"graph_checksum\": \"" << sc::to_hex_digest(g_1m_csum) << "\",\n"
                         << "      \"input_events_checksum\": \"" << sc::to_hex_digest(in_1m_csum) << "\",\n"
                         << "      \"state_digest\": \"" << sc::to_hex_digest(rep_1m.last_stats.state_digest) << "\",\n"
                         << "      \"reference_serial_digest\": \"" << sc::to_hex_digest(rep_ser_1m.last_stats.state_digest) << "\",\n"
                         << "      \"parity_with_serial\": " << ((rep_1m.last_stats.state_digest == rep_ser_1m.last_stats.state_digest) ? "true" : "false") << ",\n"
                         << "      \"rss_before_build_mb\": " << std::setprecision(2) << (rss_before_1m / (1024.0 * 1024.0)) << ",\n"
                         << "      \"rss_after_build_mb\": " << (rss_after_1m / (1024.0 * 1024.0)) << ",\n"
                         << "      \"peak_rss_mb\": " << (rep_1m.last_stats.peak_rss_bytes / (1024.0 * 1024.0)) << "\n"
                         << "    }";
                std::cout << "  [1M " << w_tag << "] W=" << W << " | Mean: " << (rep_1m.mean_sim_sec * 1000.0)
                          << " ms | Med: " << (rep_1m.median_sim_sec * 1000.0) << " ms | SelfSpeedup: " << speedup
                          << "x | vsSerial: " << (rep_ser_1m.mean_sim_sec / rep_1m.mean_sim_sec)
                          << "x | Ev: " << rep_1m.last_stats.total_events_processed << std::endl;
            }
        };

        run_1m_workload("short_horizon_186k", inputs_1m_short, 10.0);
        run_1m_workload("sustained_1m_events", inputs_1m_sustained, 15.0);
        json_out << "\n  ],\n";
    }
