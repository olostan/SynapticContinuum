# SynapticContinuum EXP-0004: Research Protocol Amendments

**Status**: APPROVED & FULLY EXECUTED POST-PREREGISTRATION EXPANSION  
**Date**: 2026-10-24  
**Governing Document**: [SPEC.md](SPEC.md), [EXPERIMENTATION.md](../../EXPERIMENTATION.md), PR #13 Code Reviews  
**Author**: Principal Experimental Engineer  
**Approved By**: Repository Owner (`@olostan`) via PR #13 review directives  

---

## 1. Context and Rationale

Following initial execution (`a19abe1`) and rigorous scientific and code audits on PR #13, we enacted and executed eight protocol amendments to eliminate concurrency hazards, enforce zero-fabrication schema and proof-chain validation, remove unsupported hardware cache claims, separate exact from approximate/procedural representations, validate pairwise watermark monotonicity under adversarial delays, and scale execution up to $N = 10,000,000$ neurons ($160,000,000$ synapses) within the 15.57 GiB bare-metal Linux host's 60% available-RAM safety gate.

---

## 2. Executed Protocol Amendments

### Amendment 1: Three-Barrier Migration Protocol & Conservative All-Region Lookahead
- **Mechanism**:
  1. `epoch_barrier_`: All $W$ workers finish local event processing up to $t_{\text{epoch}}$ and arrive.
  2. *Coordinator Migration Phase*: While workers park at `migration_barrier_`, thread 0 rebalances overloaded regions, transfers queued events (`migrated_queue_events`), and reroutes in-flight mailbox messages (`migrated_mailbox_events`).
  3. `migration_barrier_` & `drain_barrier_`: Workers drain rebalanced mailboxes and synchronize before the next epoch.
  4. Because region-to-worker ownership changes dynamically in `Exp4AdaptiveEngine`, lookahead is computed across all inter-region edges (`check_all_inter_region_delays_ = true`), guaranteeing that no future migration can expose a smaller cross-worker delay than the conservative epoch window.
- **Verification**: `test_forced_migration_concurrent_traffic` verified `15` migrations (`2,769` migrated queue events, `47` migrated mailbox events) with 100% bit-exact `state_digest` parity (`14408938184421392896`) against `Exp4SerialEngine` and **0 errors under ASan/UBSan and TSan**.

### Amendment 2: Strict Schema-Validated Benchmark Records & Immutable Proof Chain (`schemas/benchmark_schema.json` & `scripts/pareto_query.py`)
- **Mechanism**: Removed all post-hoc record synthesis and default fabrication from `scripts/pareto_query.py`. `exp0004_bench` directly emits 182 canonical `benchmark_records` per build (`364` total across `znver3_o3` and `portable_o3`), including `graph_checksum`, `input_events_checksum`, `reference_serial_digest`, `git_commit_sha`, and `/proc/self/statm` resident memory (`rss_before_build_bytes`, `rss_after_build_bytes`, `rss_after_sim_bytes`). `scripts/pareto_query.py` enforces that `parity_with_serial == True` requires `semantic_class in ("exact", "trace-replay-only")`, `state_digest == reference_serial_digest`, and `backward_time_events == 0`, and partitions Pareto frontiers by `(benchmark_id, graph_checksum, input_events_checksum)` so small-graph runs never prune large-graph runs.

### Amendment 3: Multi-Repetition $N=1\text{M}$ & $N=10\text{M}$ Analysis and Separation of Measured Facts from Plausible Hypotheses
- **Correction**: Removed the unverified claim attributing $N=1\text{M}$ scaling to per-core L3 cache partitioning on a shared 16 MiB L3 cache without PMU counters (`kernel.perf_event_paranoid = 4` on this bare-metal Linux host, `systemd-detect-virt = none`).
- **Execution & Scientific Wording**: Executed $N=1,000,000, D=16$ under both the short-horizon workload (186,881 events) and a sustained workload (1,403,156 processed events) with 2 warmups and 5 timed repetitions, and $N=3\text{M} / 10\text{M}$ with 1 warmup and 3 timed repetitions, recording all per-repetition wall times (`rep_wall_sim_sec`) and comparing against both $W=1$ (`self_speedup`) and `Exp4SerialEngine` (`speedup_vs_serial`). Per-worker heap-depth reduction ($\mathcal{O}(\log(Q/W))$) and single-worker barrier/OS scheduling dispersion are framed strictly as **plausible contributing hypotheses** rather than proven causal decompositions.

### Amendment 4: Stage 1B Zero-Edge Pure Trace Replay
- **Mechanism**: Stage 1B replays the 970,974-event trace on a zero-edge graph (`num_edges = 0`), ensuring `trace_events == total_events_processed == 970,974` and isolating queue/dispatch throughput from synaptic fan-out.

### Amendment 5: Comparative Matrices D1 (Queues), D2 (Semantic Separation & AoS/SoA Exact Parity), D3 (METIS & igraph Leiden), D4 (OpenMP & Adversarial Pairwise Watermarks), and D6 (`NOT RUN` External Simulators)
- **D1**: Benchmarked `BinaryHeapQueue` (2-ary), `DaryHeapQueue<4>`, `DaryHeapQueue<8>`, and `BucketEventQueue`.
- **D2**: Aligned `SubstrateStateAoS` floating-point negation with `SubstrateStatePacked` so `csr_direct_flat_aos_L0` achieves bit-exact `state_digest` parity (`0x8db008f0e20e0b69`) with `csr_direct_flat_soa_L0`. Explicitly labeled `csr_compact_quantized_8B` as `semantic_class = "quantized-approx"` (`parity_with_serial = false`, reporting weight/delay quantization max error and RMSE) and `procedural_on_the_fly_0B` as `semantic_class = "procedural-synthetic"` (`parity_with_serial = false`).
- **D3**: Integrated external library baselines **`pymetis` (`metis_kway`)** and **`python-igraph` (`igraph_leiden`)** alongside `contiguous`, `random_hash`, `planted_oracle`, `greedy_boundary_heuristic`, and `activity_aware`.
- **D4**: Implemented `Exp4OpenMPEngine` (`-fopenmp`) and `Exp4PairwiseWatermarkEngine` with monotonic watermark enforcement (`watermark_monotonicity_violations`, `delayed_channel_deliveries`, `horizon_clamp_events`), verified under `test_pairwise_watermark_adversarial_stress` on directed cyclic rings with $35\times$ delay asymmetry and dense random graphs under TSan.

### Amendment 6: Direct Flat CSR Construction & Extreme Scale Ladder ($N = 3\text{M}$ and $N = 10\text{M}$)
- **Mechanism**: Eliminated intermediate `std::vector<std::vector<...>>` allocations during graph construction, cutting peak build memory by $\approx 50\%$ and enabling preflight-gated ($\le 60\%$ available RAM) execution at **$N=3,000,000, D=16$** (~2.08 GB RSS, 1.68M events) and **$N=10,000,000, D=4$ & $D=16$** (up to 160M synapses, ~6.49 GB RSS, 1.57M events) with 100% bit-exact serial parity.

### Amendment 7: Stage 4 Causal Violation Counters & 100-Trial Temporal Order Discrimination
- **Mechanism**: Instrumented `Exp4RelaxedEngine` with `backward_time_events`, `out_of_order_worker_events`, `exact_spike_matches`, and a 100-trial temporal order discrimination task ($A \to B$ vs $B \to A$ against a 50% chance baseline).
