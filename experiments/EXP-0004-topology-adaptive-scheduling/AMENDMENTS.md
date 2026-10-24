# SynapticContinuum EXP-0004: Research Protocol Amendments

**Status**: APPROVED & FULLY EXECUTED POST-PREREGISTRATION EXPANSION  
**Date**: 2026-10-24  
**Governing Document**: [SPEC.md](SPEC.md), [EXPERIMENTATION.md](../../EXPERIMENTATION.md), PR #13 Code Reviews  
**Author**: Principal Experimental Engineer  
**Approved By**: Repository Owner (`@olostan`) via PR #13 review directives  

---

## 1. Context and Rationale

Following initial execution (`a19abe1`) and two rounds of rigorous scientific and code audit on PR #13, we enacted and executed seven protocol amendments to eliminate concurrency hazards, enforce zero-fabrication schema validation, remove unsupported hardware cache claims, complete the comparative matrices (D1, D2, D3, D4, D6), and scale execution up to $N = 10,000,000$ neurons ($160,000,000$ synapses) within the 16 GB host's 60% available-RAM safety gate.

---

## 2. Executed Protocol Amendments

### Amendment 1: Three-Barrier Migration Protocol & Conservative All-Region Lookahead
- **Mechanism**:
  1. `epoch_barrier_`: All $W$ workers finish local event processing up to $t_{\text{epoch}}$ and arrive.
  2. *Coordinator Migration Phase*: While workers park at `migration_barrier_`, thread 0 rebalances overloaded regions, transfers queued events (`migrated_queue_events`), and reroutes in-flight mailbox messages (`migrated_mailbox_events`).
  3. `migration_barrier_` & `drain_barrier_`: Workers drain rebalanced mailboxes and synchronize before the next epoch.
  4. Because region-to-worker ownership changes dynamically in `Exp4AdaptiveEngine`, lookahead is computed across all inter-region edges (`check_all_inter_region_delays_ = true`), guaranteeing that no future migration can expose a smaller cross-worker delay than the conservative epoch window.
- **Verification**: `test_forced_migration_concurrent_traffic` verified `14` migrations (`2,769` migrated queue events, `47` migrated mailbox events) with 100% bit-exact `state_digest` parity (`14408938184421392896`) against `Exp4SerialEngine` and **0 errors under ASan/UBSan and TSan**.

### Amendment 2: Strict Schema-Validated Benchmark Records (`schemas/benchmark_schema.json` & `scripts/pareto_query.py`)
- **Mechanism**: Removed all post-hoc record synthesis and default fabrication from `scripts/pareto_query.py`. `exp0004_bench` directly emits 182 canonical `benchmark_records` per build (`364` total across `znver3_o3` and `portable_o3`), validated by `jsonschema.validate` and checked for exact arithmetic consistency (`events_per_sec == total_events_processed / wall_time_sim_sec`) and measured `parity_with_serial`.

### Amendment 3: Multi-Repetition $N=1\text{M}$ Analysis & Removal of Unmeasured L3 Cache Claims
- **Correction**: Removed the unverified claim attributing $N=1\text{M}$ scaling to per-core L3 cache partitioning on a shared 16 MiB L3 cache without PMU counters (`perf_event_open` is unavailable in WSL2).
- **Execution**: Executed $N=1,000,000, D=16$ under both the short-horizon workload (186,881 events) and a sustained workload (1,403,156 processed events) with 2 warmups and 5 timed repetitions, recording all per-repetition wall times and comparing against both $W=1$ (`self_speedup`) and `Exp4SerialEngine` (`speedup_vs_serial`).

### Amendment 4: Stage 1B Zero-Edge Pure Trace Replay
- **Mechanism**: Stage 1B replays the 970,974-event trace on a zero-edge graph (`num_edges = 0`), ensuring `trace_events == total_events_processed == 970,974` and isolating queue/dispatch throughput from synaptic fan-out.

### Amendment 5: Comparative Matrices D1 (Queues), D2 (Representations/History $L$), D3 (METIS & igraph Leiden), D4 (OpenMP & Pairwise Watermarks), and D6 (`NOT RUN` External Simulators)
- **D1**: Benchmarked `BinaryHeapQueue` (2-ary), `DaryHeapQueue<4>`, `DaryHeapQueue<8>`, and `BucketEventQueue`.
- **D2**: Benchmarked `csr_vec_of_vec` vs `csr_direct_flat` vs `csr_compact_quantized_8B` vs `procedural_on_the_fly_0B`, `soa_packed` vs `aos_neuron_struct`, and history depths $L \in \{0, 16, 64\}$.
- **D3**: Integrated external library baselines **`pymetis` (`metis_kway`)** and **`python-igraph` (`igraph_leiden`)** alongside `contiguous`, `random_hash`, `planted_oracle`, `greedy_boundary_heuristic`, and `activity_aware`.
- **D4**: Implemented `Exp4OpenMPEngine` (`-fopenmp`) and `Exp4PairwiseWatermarkEngine` (Chandy-Misra-Bryant pairwise lookahead watermarks without global barriers) alongside `owner_barrier`, `persistent_pool`, and `adaptive_scheduler`.

### Amendment 6: Direct Flat CSR Construction & Extreme Scale Ladder ($N = 3\text{M}$ and $N = 10\text{M}$)
- **Mechanism**: Eliminated intermediate `std::vector<std::vector<...>>` allocations during graph construction, cutting peak build memory by $\approx 50\%$ and enabling preflight-gated ($\le 60\%$ available RAM) execution at **$N=3,000,000, D=16$** (2.08 GB RSS, 1.68M events) and **$N=10,000,000, D=4$ & $D=16$** (up to 160M synapses, 6.49 GB RSS, 1.57M events) with 100% bit-exact serial parity.

### Amendment 7: Stage 4 Causal Violation Counters & 100-Trial Temporal Order Discrimination
- **Mechanism**: Instrumented `Exp4RelaxedEngine` with `backward_time_events`, `out_of_order_worker_events`, `exact_spike_matches`, and a 100-trial temporal order discrimination task ($A \to B$ vs $B \to A$ against a 50% chance baseline).
