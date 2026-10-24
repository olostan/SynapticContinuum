# EXP-0003 — Protocol Amendments and Corrections

**Date:** 2026-10-23  
**Status:** Preregistered amendments addressing independent peer review findings on PR #11.

---

### Amendment 1: Timing Boundary Isolation (Simulation-Only vs End-to-End)
- **Deviation**: The initial exploratory benchmark run timed `run_py_event()` by wrapping the stopwatch around both graph/stimulus fixture construction and the simulation loop, whereas C++ `sc_engine_cli.cpp` timed `eng.run()` after native graph construction. This inflated Python vs C++ ratios (reported as 48×–2600×).
- **Correction**: Pre-generate identical fixtures once (`create_py_fixture`) and isolate `sched.run()` wall time inside Python (`median_sim_wall_time_sec`). Separately measure `median_e2e_wall_time_sec` including initialization.
- **Impact**: True isolated simulation-only speedup of C++ literal port over Python is **34.5× to 84.4×** (and end-to-end speedup is 2.3× to 7.9×). Initial exploratory ratios are superseded.

---

### Amendment 2: Causal Correctness of Parallel Execution Engines
- **Deviation**: Initial `cpp_locked.hpp` popped min elements concurrently without enforcing chronological arrival or safe commit horizons, and `cpp_owner.hpp` used a fallback epoch lookahead without validating cross-region edge delays.
- **Correction**:
  1. Implemented a conservative safe commit horizon in `cpp_locked.hpp`: workers can only pop events with $t \le \min(t_{\text{in-flight}}) + d_{\min}$, and updates to the same node are serialized.
  2. In `cpp_owner.hpp`, derived conservative lookahead dynamically from the minimum cross-region directed edge delay $d_{\min, \text{cross}} = \min_{(u \to v) \in E, \text{part}(u) \neq \text{part}(v)} d_{uv}$.
  3. Established deterministic simultaneous-event tie-breaking order: `(timestamp, target, source, seq_id)`.
- **Impact**: Zero non-causal events. Full bit-exact state digest and spike trajectory replay verified against serial reference across $W \in \{1, 2, 4\}$ workers.

---

### Amendment 3: Sequential Impulse Dispatch in Hybrid Batching
- **Deviation**: Initial `cpp_hybrid.hpp` summed amplitudes of simultaneous same-node arrivals before threshold evaluation, which altered LIF firing/refractory semantics for mixed excitatory-inhibitory or suprathreshold pulses.
- **Correction**: Batched queue extraction remains $O(1)$, but all extracted simultaneous events are dispatched sequentially through `state.receive_impulse()`, ensuring identical threshold crossing, reset, and refractory clamping.
- **Impact**: Verified against adversarial simultaneous arrival test cases (suprathreshold + inhibitory, multiple subthreshold). Bit-exact state digest equality with serial reference achieved under all conditions.

---

### Amendment 4: Dual Memory Accounting (OS Peak RSS vs Theoretical Model)
- **Deviation**: Initial reporting used a theoretical model calculation (`state + graph + queue`) labeled as `rss_bytes`.
- **Correction**: Replaced with OS-measured process peak resident set size via `getrusage(RUSAGE_SELF, ...)` (`peak_rss_bytes`), while separately retaining theoretical modeling as `estimated_memory_bytes`.
- **Impact**: For $N=1,000,000$, actual OS peak RSS is $\approx 515.8 \text{ MB}$ (inclusive of runtime memory pools and glibc arenas), compared to the theoretical compact structure footprint of $226.1 \text{ MB}$.

---

### Amendment 5: Matched-Fidelity Synchronous vs Event-Driven Crossover (Empirically Measured)
- **Deviation**: The prior report hypothesized that matched fidelity ($\Delta t \le 0.01$) would shift the crossover to $\sim 20–25\%$ activity, based on a single 32-node fixture, while published crossover tables only showed $\Delta t = 0.10$.
- **Correction**: Executed a comprehensive empirical benchmark (`fidelity_sweep`) measuring simulation time, RMSE potential error, spike count discrepancy, and mean timestamp quantization error across $N \in \{128, 1024, 10000\}$ and $f \in \{0.001, 0.010, 0.050, 0.100, 0.200, 0.500, 1.000\}$.
- **Impact**: The measured crossover under matched fidelity ($\Delta t = 0.01$) is **$f^* \approx 0.06–0.08$** across workloads. The earlier $20–25\%$ figure is formally demoted to an unvalidated analytical extrapolation and superseded by empirical measurements.

---

### Amendment 6: Zero-Delay Causality Precondition and Graph Validation
- **Deviation**: The previous revision substituted `epoch_delta = 0.001` in `cpp_owner.hpp` and `min_graph_delay = 0.001` in `cpp_locked.hpp` when non-positive delays were encountered, which is not a conservative bound and can permit causal arrival inversions across workers.
- **Correction**: Formally instituted the **Positive-Lookahead Precondition** for conservative parallel execution. Both `cpp_owner` (for cross-region edges) and `cpp_locked` (for all edges with $W > 1$) validate graph delays prior to simulation and throw `std::invalid_argument` if non-positive delays are detected. Single-worker execution ($W=1$) remains supported for zero delays via priority queue ordering.
- **Impact**: Prevents unsynchronized partitions from advancing past instantaneous cross-region events. Unit tests verify rejection of zero-delay cross-region cycles and explain arrival inversion hazards.

---

### Amendment 7: Simultaneous Event Replay and Atomic Counter Thread Safety
- **Deviation**: Under heavy simultaneous event batches across $W=6$ and $W=8$ workers, non-atomic increments to `state.total_spikes` caused multithreaded lost-update races in reported spike counts.
- **Correction**: Upgraded `SubstrateStatePacked::total_spikes` to `std::atomic<uint64_t>` and derived `res.total_spikes` deterministically from sorted, merged `res.spike_records.size()`. Added regression tests for $W=6$ and $W=8$ verifying identical 64-bit state digests and spike counts over repeated runs.
- **Impact**: Full bit-exact determinism preserved across arbitrary thread inter-leavings and non-power-of-two core allocations.

---

### Amendment 8: Clarification of Python Memory Accounting
- **Clarification**: In the Python benchmark branch, memory values reflect theoretical model estimation (`estimated_memory_bytes`) and overall interpreter footprint rather than isolated native substrate allocation. C++ benchmarks report true OS peak RSS via `getrusage`.
