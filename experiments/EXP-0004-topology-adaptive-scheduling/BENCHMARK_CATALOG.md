# SynapticContinuum EXP-0004: Benchmark Catalog & Workload Registry

**Schema Version**: `1.0.0` ([schemas/benchmark_schema.json](schemas/benchmark_schema.json))  
**Document Status**: ACTIVE & STRICTLY VALIDATED (364 Schema-v1.0.0 Records Emitted, `git_commit_sha`: `85568f9`)  
**Host Architecture (Current)**: Bare-Metal Linux x86_64 (`lenobox`, `systemd-detect-virt = none`, AMD Ryzen 5 PRO 5650GE, 6C/12T, 16 MiB L3, 15.57 GiB DDR4 RAM)  
**Host Architecture (Planned Follow-on)**: Apple Silicon M4 Pro (Darwin ARM64, 14-core [10P + 4E], 48 GB Unified Memory) — **MAC PENDING**  

---

## 1. Overview and Design Principles

The SynapticContinuum Benchmark Catalog standardizes benchmark configurations across experiments (EXP-0004, EXP-0005+), ensuring that performance claims across different engines, queue structures, data representations, and hardware platforms share identical mathematical stimuli and graph definitions.

### Key Integrity Rules (Enforced by `scripts/pareto_query.py`):
1. **Immutable Workload Benchmark ID & Proof Chain**: `benchmark_id` uniquely identifies the **workload** (stage, topology, $N$, $D$, stimulus regime) and remains **invariant** across worker counts $W$, engine implementations (`cpp_serial`, `cpp_persistent_pool`, `cpp_openmp_epoch`, `cpp_pairwise_watermark`, etc.), and compiler build IDs (`znver3_o3`, `portable_o3`). Every record carries `graph_checksum`, `input_events_checksum`, `reference_serial_digest`, `state_digest`, and `git_commit_sha`.
2. **Per-Workload Pareto Partitioning (No Cross-Workload Pruning)**:
   - `compute_pareto_frontier` in `scripts/pareto_query.py` partitions records by `(benchmark_id, graph_checksum, input_events_checksum)` by default before computing non-dominated frontiers (`wall_time_sim_sec`, `events_per_sec`, `peak_rss_bytes`), ensuring a small $N=10,000$ run never dominates or prunes an $N=10,000,000$ run.
3. **Zero Post-Hoc Normalization or Default Fabrication**:
   - `exp0004_bench` directly emits canonical `benchmark_records` conforming to [`schemas/benchmark_schema.json`](schemas/benchmark_schema.json).
   - `scripts/pareto_query.py` validates every record with `jsonschema.validate` and verifies arithmetic consistency (`events_per_sec == total_events_processed / wall_time_sim_sec`). No missing fields or defaults are synthesized in Python.
4. **Measured Causal Parity Gate & Semantic Separation (`parity_with_serial`)**:
   - `parity_with_serial` is permitted to be `true` **only** when `semantic_class` is `"exact"` or `"trace-replay-only"`, `Exp4SerialEngine` was executed on the identical workload, `state_digest == reference_serial_digest`, and `backward_time_events == 0`.
   - Approximate or synthetic representations (`"quantized-approx"`, `"procedural-synthetic"`, `"relaxed-model"`, `"fixed-dt-approx"`) must have `parity_with_serial == false` and are automatically refused from `exact` Pareto frontiers.

---

## 2. Canonical Workload Registry Emitted by `exp0004_bench`

| `benchmark_id` | Stage & Workload Description | Graph Topology | $N$ | $D$ | Processed Events | Semantic Class | Records per Build |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exp0004_stage0_disconnected_N10000_D16` | Stage 0 Disconnected Control (5 seeds) | Disconnected 6-Module ($c=0.0$) | 10,000 | 16 | 31,963–33,784 | `exact` | 45 |
| `exp0004_stage0_random_N10000_D16` | Stage 0 Uniform Random Control (5 seeds) | Uniform Random ($D=16$) | 10,000 | 16 | 33,221–35,442 | `exact` | 25 |
| `exp0004_stage1_topo_<name>_N10000_D16` | Stage 1 Controlled Topology Sweep (13 regimes) | WS, SBM, Hierarchical, Rewired, Permuted | 10,000 | 16 | 1,684–1,772 | `exact` | 39 |
| `exp0004_stage1b_trace_replay_N10000` | Stage 1B Pure Trace Replay (`num_edges=0`) | Empty-Edge Replay Graph | 10,000 | 0 | 970,974 | `trace-replay-only` | 5 |
| `exp0004_stage2_partition_N10000_D16_c0.10` | Stage 2 Partitioning Strategies (D3, incl. METIS & Leiden) | Modular SBM ($c=0.10$) | 10,000 | 16 | 22,111 | `exact` | 8 |
| `exp0004_stage2b_queues_N10000_D16_c0.10` | Stage 2B Priority Queue Family (D1: 2/4/8-ary, Bucket) | Modular SBM ($c=0.10$) | 10,000 | 16 | 22,111 | `exact` | 8 |
| `exp0004_stage2c_repr_<label>_N100000_D16` | Stage 2C Representations, Layouts & History $L$ (D2) | Modular SBM ($c=0.05$) | 100,000 | 16 | 4,227–4,752 | `exact` / `quantized-approx` / `procedural-synthetic` | 7 |
| `exp0004_stage3_schedulers_N10000_D16_c0.10` | Stage 3 Parallel Schedulers (D4 across $W=1..12$) | Modular SBM ($c=0.10, R=24$) | 10,000 | 16 | 22,111 | `exact` | 19 |
| `exp0004_stage3b_100k_disconnected_N100000_D16` | Stage 3B High-Scale 100k Sweep | Disconnected 6-Module | 100,000 | 16 | 49,245 | `exact` | 5 |
| `exp0004_stage3c_1m_short_horizon_186k_N1000000_D16` | Stage 3C 1M Short-Horizon (5 reps) | Disconnected 6-Module | 1,000,000 | 16 | 186,881 | `exact` | 5 |
| `exp0004_stage3c_1m_sustained_1m_events_N1000000_D16` | Stage 3C 1M Sustained $\ge 1.4\text{M}$ Events (5 reps) | Disconnected 6-Module | 1,000,000 | 16 | 1,403,156 | `exact` | 5 |
| `exp0004_stage3d_scale_N3000000_D16` | Stage 3D Extreme Scale 3M Neurons (48M edges) | Disconnected 6-Module | 3,000,000 | 16 | 1,684,864 | `exact` | 3 |
| `exp0004_stage3d_scale_N10000000_D4` | Stage 3D Extreme Scale 10M Neurons ($D=4$, 40M edges) | Disconnected 6-Module | 10,000,000 | 4 | 1,658,352 | `exact` | 3 |
| `exp0004_stage3d_scale_N10000000_D16` | Stage 3D Extreme Scale 10M Neurons ($D=16$, 160M edges) | Disconnected 6-Module | 10,000,000 | 16 | 1,572,432 | `exact` | 3 |
| `exp0004_stage4_relaxed_N10000_D16_c0.10` | Stage 4 Order Relaxation ($\epsilon \in [0, 1]$) & Discrimination | Modular SBM ($c=0.10, R=24$) | 10,000 | 16 | 22,000–22,111 | `exact` / `relaxed-model` | 6 |

---

## 3. Querying the Benchmark Catalog & Pareto Frontier

Use `scripts/pareto_query.py` to validate all records and compute non-dominated Pareto frontiers (partitioned per workload `(benchmark_id, graph_checksum, input_events_checksum)` by default):

```bash
# Validate all 364 records across znver3_o3 and portable_o3 and print per-workload exact Pareto frontiers
./.venv/bin/python scripts/pareto_query.py --path runs --semantic-class exact --pareto

# Filter by minimum scale (N >= 1,000,000) and memory budget (<= 7.0 GiB)
./.venv/bin/python scripts/pareto_query.py --path runs --min-nodes 1000000 --max-memory-gib 7.0 --semantic-class exact --pareto

# Filter for a single workload benchmark_id across all engines and worker counts
./.venv/bin/python scripts/pareto_query.py --path runs --benchmark-id exp0004_stage3_schedulers_N10000_D16_c0.10 --pareto
```

---

## 4. Mac Apple Silicon M4 Pro Handoff Guide (Darwin ARM64 `MAC PENDING`)

`CMakeLists.txt` automatically detects Darwin ARM64 (`APPLE` + `arm64`) and checks compiler support for `-mcpu=apple-m4` (with fallback to `-mcpu=native` / `-O3`). When running on the 48 GB M4 Pro machine (using `fish` shell syntax):
```fish
set -gx OMP_NUM_THREADS 10
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 10
./.venv/bin/python -m src.python.orchestrator --profile standard --build-id m4pro_o3 --out runs
./.venv/bin/python scripts/pareto_query.py --path runs --pareto
```
