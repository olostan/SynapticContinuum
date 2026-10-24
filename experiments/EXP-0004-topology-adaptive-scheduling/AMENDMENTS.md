# SynapticContinuum EXP-0004: Research Protocol Amendments

**Status**: APPROVED POST-PREREGISTRATION EXPANSION  
**Date**: 2026-10-24  
**Governing Document**: [SPEC.md](SPEC.md), [EXPERIMENTATION.md](../../EXPERIMENTATION.md), PR #13 Code Review  
**Author**: Principal Experimental Engineer  
**Approved By**: Repository Owner (`@olostan`) via PR #13 review directive  

---

## 1. Context and Rationale

The original preregistered specification for EXP-0004 ([SPEC.md](SPEC.md)) formulated six core hypotheses ($H1$ through $H6$) investigating how network topology, event locality, persistent worker pooling, dynamic region migration, and order relaxation affect conservative parallel discrete-event simulation (PDES) on multi-core hardware.

Following initial execution and code review of PR #13 (commit `a19abe1`), an independent audit identified several concurrency, benchmarking, and methodological opportunities to strengthen scientific rigor:
1. **Migration Phase Synchronization**: In the initial prototype, dynamic region migration could mutate worker queues while workers were advancing to mailbox drain.
2. **Order Relaxation Engine**: The initial `cpp_relaxed.hpp` wrapped the strict persistent pool without altering the synchronization window or scheduling policy.
3. **Hardware Scaling Baseline**: The original 6-module disconnected scaling test ($2.53\times$ speedup) was confounded by two global barriers per epoch. A barrier-free independent worker loop was needed to establish the true hardware event-processing ceiling.
4. **Heuristic Partitioning Nomenclature**: The greedy boundary swap method was labeled `mincut`, risking confusion with exact mincut or multilevel spectral/METIS partitioning algorithms.
5. **Workload Volume**: Early Stage 1 runs processed only hundreds of events, causing barrier latency to dominate computational time. Sustained workloads ($\ge 10^6$ events) were required to characterize large-scale steady-state throughput.
6. **Cross-Experiment Contract**: Future experiments (EXP-0005+) required a machine-readable JSON schema, canonical fixtures, and a queryable Pareto frontier tool.

---

## 2. Approved Protocol Amendments

### Amendment 1: Three-Barrier Migration Phase Protocol
- **Mechanism**: Replaced the two-barrier epoch cycle with a three-barrier protocol:
  1. `epoch_barrier_`: All $W$ workers complete event processing up to $t_{\text{epoch}}$ and arrive.
  2. *Coordinator Migration Phase*: All $W$ workers park at `migration_barrier_`. The coordinator exclusively rebalances regions, transfers pending queue events, and reroutes in-flight mailbox messages.
  3. `migration_barrier_`: Coordinator releases all workers to drain their rebalanced mailboxes safely.
  4. `drain_barrier_`: All workers finish mailbox drain before beginning the next epoch.
- **Verification**: Zero data races verified under GCC ThreadSanitizer (`-fsanitize=thread`) with forced migration on every epoch under heavy cross-traffic.

### Amendment 2: Physical Barrier-Free Hardware Scaling Control
- **Mechanism**: Added `Exp4BarrierFreeIndependentEngine`. For strictly disconnected topologies ($c=0.0$), workers execute disjoint partitions of the graph with zero global barriers, zero mutexes, and zero mailbox overhead.
- **Scientific Role**: Disentangles engine computation efficiency from synchronization overhead. Establishes the empirical hardware ceiling for multi-core scaling on the test host (AMD Ryzen 5 PRO 5650GE).

### Amendment 3: Genuine Order Relaxation & Discrimination Task
- **Mechanism**: Implemented `Exp4RelaxedEngine` with parameter $\epsilon$. Expands the epoch lookahead to $\Delta t = d_{\min, \text{cross}} + \epsilon$. Late-arriving events are applied to neuron potentials without rollback.
- **Evaluation**: Evaluates divergence against the exact serial continuous-time reference across $\epsilon \in \{0.0, 0.1, 0.5, 1.0, 2.0\}$. Includes a temporal sequence discrimination task ($A \to B$ vs $B \to A$) to verify causal sensitivity.

### Amendment 4: Accurate Heuristic Partitioning Terminology
- **Change**: Formally renamed `partition_greedy_mincut` to `partition_greedy_boundary_heuristic`.
- **Clarification**: Documented that this algorithm is a local greedy boundary swap heuristic with soft capacity balancing, distinct from global exact mincut or multilevel partitioners (e.g. METIS, KaHIP). Retained an inline alias for backward compatibility.

### Amendment 5: Cross-Experiment Benchmark Contract & Schema
- **Artifacts**:
  - `schemas/benchmark_schema.json`: Validated versioned schema for benchmark results.
  - `BENCHMARK_CATALOG.md`: Canonical catalog of workload IDs and configurations.
  - `scripts/pareto_query.py`: Query tool filtering by memory, topology, and scale to extract Pareto-optimal backends.

### Amendment 6: Scale Ladder Expansion with RAM Preflight Guardrails
- **Execution**: Scaled network sizes $N \in \{10\text{k}, 100\text{k}, 1\text{M}, 3\text{M}\}$ on the 16 GB Linux host under strict memory preflight ($\le 60\%$ currently available RAM).
- **Workload Volume**: Sustained event horizons generating $\ge 1\text{M}$ processed events on large runs.

### Amendment 7: Modern CMake & Compiler Target Tracking
- **Configuration**:
  - Modern target-based CMake with `Threads::Threads`.
  - Tracked compiler optimization variants: Portable Release (`-O3 -DNDEBUG`) vs Host-Tuned Zen3 (`-O3 -march=znver3 -mtune=znver3 -DNDEBUG`).
  - Separate debug/sanitizer targets (`topology_tests_asan`, `topology_tests_tsan`).
  - Documented tool restrictions (unprivileged `perf` counters recorded as unavailable rather than simulated).

---

## 3. Preservation of Historical Findings

All preliminary findings reported in the initial execution (`a19abe1`) are preserved in `REPORT.md` under Section 8 (Intellectual History & Audit Trail). The amendments expand and refine our empirical conclusions without retroactively altering preregistered commitments.
