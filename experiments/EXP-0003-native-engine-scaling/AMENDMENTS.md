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

### Amendment 5: Matched-Fidelity Synchronous vs Event-Driven Crossover
- **Clarification**: Synchronous simulation at fixed $\Delta t = 0.1$ incurs spike timing quantization error ($\le 0.1$). Matched continuous-time fidelity requires $\Delta t \le 0.01$ (reducing potential error from $1.09$ to $<0.003$ and eliminating spike count discrepancies), which increases synchronous computational cost by 10×.
- **Impact**: Crossover claims are explicitly conditioned on declared fidelity budgets.
