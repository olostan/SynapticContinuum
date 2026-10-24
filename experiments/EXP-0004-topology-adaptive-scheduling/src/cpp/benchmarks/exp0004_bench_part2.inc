#include "exp0004_bench_part1.inc"

namespace sc {

inline Exp4ProfilingStats sim_result_to_stats(const SimulationResult& res, double total_sec, int32_t R = 1) {
    Exp4ProfilingStats st;
    st.scheduler_name = res.scheduler_name;
    st.num_workers = 1;
    st.num_regions = R;
    st.wall_time_sim_sec = res.wall_time_sec;
    st.wall_time_total_sec = total_sec;
    st.total_events_processed = res.total_events_processed;
    st.total_edges_traversed = res.total_edges_traversed;
    st.total_spikes = res.total_spikes;
    st.cross_region_events = 0;
    st.peak_rss_bytes = res.rss_bytes;
    st.state_digest = res.state_digest;
    st.worker_active_sec = {res.wall_time_sec};
    st.worker_barrier1_sec = {0.0};
    st.worker_mailbox_sec = {0.0};
    st.worker_barrier2_sec = {0.0};
    st.worker_events_processed = {res.total_events_processed};
    return st;
}

template <typename StateType = SubstrateStatePacked>
Exp4ProfilingStats run_serial_custom_graph(
    const SubstrateConfig& cfg,
    const NeuralGraphCSR* csr,
    const NeuralGraphCompactCSR* compact_csr,
    const NeuralGraphProceduralSBM* proc_sbm,
    const std::vector<ExternalEvent>& external_events,
    double t_max
) {
    auto t0 = std::chrono::high_resolution_clock::now();
    StateType state(cfg);
    BinaryHeapQueue queue(std::max(size_t{16384}, external_events.size() * 2 + 1024));
    uint64_t seq = 0;
    for (const auto& ee : external_events) {
        if (ee.timestamp <= t_max) {
            queue.push(Event{ee.timestamp, seq++, ee.source, ee.target, ee.amplitude, ee.kind});
        }
    }

    auto t_sim_start = std::chrono::high_resolution_clock::now();
    uint64_t processed = 0;
    uint64_t edges_trav = 0;
    std::vector<SpikeRecord> spikes;

    while (!queue.empty()) {
        if (queue.peek().timestamp > t_max) break;
        Event ev = queue.pop();
        processed++;

        bool fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind);
        if (fired) {
            spikes.push_back({ev.timestamp, ev.target});
            if (csr) {
                const int32_t* tgts = nullptr;
                const float* w = nullptr;
                const float* d = nullptr;
                uint32_t cnt = 0;
                csr->get_outgoing(ev.target, tgts, w, d, cnt);
                edges_trav += cnt;
                for (uint32_t i = 0; i < cnt; ++i) {
                    double arr = ev.timestamp + static_cast<double>(d[i]);
                    if (arr <= t_max) {
                        queue.push(Event{arr, seq++, ev.target, tgts[i], w[i], static_cast<int32_t>(EventKind::SPIKE)});
                    }
                }
            } else if (compact_csr) {
                uint32_t start = compact_csr->row_ptr[ev.target];
                uint32_t end = compact_csr->row_ptr[ev.target + 1];
                edges_trav += (end - start);
                for (uint32_t idx = start; idx < end; ++idx) {
                    float w = static_cast<float>(compact_csr->weights_q16[idx]) * NeuralGraphCompactCSR::WEIGHT_SCALE;
                    float d = static_cast<float>(compact_csr->delays_q16[idx]) * NeuralGraphCompactCSR::DELAY_SCALE;
                    double arr = ev.timestamp + static_cast<double>(d);
                    if (arr <= t_max) {
                        queue.push(Event{arr, seq++, ev.target, compact_csr->targets[idx], w, static_cast<int32_t>(EventKind::SPIKE)});
                    }
                }
            } else if (proc_sbm) {
                int32_t k = proc_sbm->out_degree;
                edges_trav += k;
                for (int32_t e_idx = 0; e_idx < k; ++e_idx) {
                    int32_t tgt = 0;
                    float w = 0.0f, d = 0.2f;
                    proc_sbm->generate_edge(ev.target, e_idx, tgt, w, d);
                    double arr = ev.timestamp + static_cast<double>(d);
                    if (arr <= t_max) {
                        queue.push(Event{arr, seq++, ev.target, tgt, w, static_cast<int32_t>(EventKind::SPIKE)});
                    }
                }
            }
        }
    }

    auto t_sim_end = std::chrono::high_resolution_clock::now();
    state.advance_all_potentials(t_max);
    auto t1 = std::chrono::high_resolution_clock::now();

    std::vector<float> final_pots(cfg.num_nodes, 0.0f);
    if constexpr (std::is_same_v<StateType, SubstrateStatePacked>) {
        std::copy(state.potentials, state.potentials + cfg.num_nodes, final_pots.begin());
    } else {
        for (int32_t i = 0; i < cfg.num_nodes; ++i) {
            final_pots[i] = state.neurons[i].potential;
        }
    }

    Exp4ProfilingStats st;
    st.scheduler_name = "cpp_serial_custom";
    st.num_workers = 1;
    st.num_regions = 1;
    st.wall_time_sim_sec = std::chrono::duration<double>(t_sim_end - t_sim_start).count();
    st.wall_time_total_sec = std::chrono::duration<double>(t1 - t0).count();
    st.total_events_processed = processed;
    st.total_edges_traversed = edges_trav;
    st.total_spikes = spikes.size();
    st.peak_rss_bytes = get_actual_peak_rss_bytes();
    st.state_digest = compute_state_digest(spikes, final_pots);
    st.worker_active_sec = {st.wall_time_sim_sec};
    st.worker_barrier1_sec = {0.0};
    st.worker_mailbox_sec = {0.0};
    st.worker_barrier2_sec = {0.0};
    return st;
}

inline std::vector<int32_t> load_partition_file(const std::string& path, int32_t expected_N) {
    std::vector<int32_t> labels;
    labels.reserve(expected_N);
    std::ifstream f(path);
    int32_t val = 0;
    while (f >> val) {
        labels.push_back(val);
    }
    return labels;
}

inline void write_graph_edge_list(const NeuralGraphCSR& g, const std::string& path) {
    std::ofstream f(path);
    f << g.num_nodes << " " << g.num_edges << "\n";
    for (int32_t u = 0; u < g.num_nodes; ++u) {
        for (uint64_t p = g.row_ptr[u]; p < g.row_ptr[u + 1]; ++p) {
            f << u << " " << g.targets[p] << "\n";
        }
    }
}

} // namespace sc
