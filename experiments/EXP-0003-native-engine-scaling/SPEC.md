# EXP-0003 — Native execution, adaptive scheduling, and cross-platform scaling

**Status: PREREGISTERED DESIGN ONLY — NOT RUN.** 2026-10-23. Governed by ../../EXPERIMENTATION.md. Builds on merged EXP-0002, whose Python queue, dynamics and report are the reference, not proof of universal speed ratios.

## Scientific question

At equal neuronal dynamics and numerical fidelity, which portions of execution cost come from (a) Python overhead, (b) data representation / queue choice, (c) synchronization / ownership, and (d) batching / mode selection? How do those costs vary with network size, edge degree, *event rate per simulated time*, time locality, history size, and topology on Linux x86-64 and macOS ARM64?

**Primary preregistered hypotheses — all falsifiable, none presumed true**
- H1: a semantics-preserving literal C++ port outperforms Python object-per-event execution in event-heavy workloads; may NOT outpace NumPy vectorization at high occupancy.
- H2: packed native graph/state/event layouts and alternative queues outperform the literal port in some measured regime, with possible reversals depending on arrival-time distribution.
- H3: exclusive-region ownership can improve throughput relative to a correct shared-queue+mutex baseline when partitions have useful independent work; cross-region traffic, lookahead constraints, or low load may eliminate gains.
- H4: exact-time compatible batching and adaptive scheduling can extend event-driven competitiveness into high-activity regimes, without violating identical dynamics. Switching overhead can erase benefits.
- H5: crossover is NOT a universal threshold in percent active; it depends on event rate, graph size, degree, topology, queue occupancy, timestep accuracy, and memory locality. Larger N may or may not favor event execution.

## Mandatory implementation ladder — isolate changes

A. **PY-EVENT:** unchanged EXP-0002 Python event-driven scheduler, pinned commit; optionally isolated literal adaptation solely for deterministic shared-input protocol. Record separately if adapted.
B. **PY-SYNC:** EXP-0002 NumPy dense synchronous and sparse synchronous baselines with dt/error curves.
C. **CPP-LITERAL:** straightforward single-thread port of EXP-0002 event semantics; ordinary object-like heap and adjacency, no structural redesign. Isolate Python-to-native effect; demonstrate trace parity.
D. **CPP-PACKED:** single-thread contiguous SoA/AoS alternatives, CSR adjacency, compact POD events, reusable allocation/slab, preallocation, optimized access and cache locality. Compare one optimization at a time against C; preserve toggles.
E. **CPP-QUEUES:** binary heap, indexed/batched heap and timing buckets/calendar or hierarchical bucket queues *where applicable*. Include monotonic-times/finite-width constraints, rebucketing cost, exact ordering, and adversarial burst/delay distributions. Do not label any scheduler O(1) without empirical and domain qualifiers.
F. **CPP-SYNC:** strong C++ dense state-sweep plus sparse/scheduled vectorized reference, and a C++ synchronous simulator with time-step convergence. Equal fidelity is essential; do NOT only compare against Python dense.
G. **CPP-LOCKED:** correct parallel shared-priority-queue baseline with mutexes and ordered state protection; correctness before timing.
H. **CPP-OWNER:** static region ownership, local queues, message-based cross-region events, fixed worker pool; compare to G, measure causal/lookahead stalls.
I. **CPP-DYNAMIC:** optional dynamic region migration / rebalancing, with ownership epochs, drain/hand-off, deterministic replay and exact causal safety; compare at same thread counts to H, account for migration expense.
J. **CPP-HYBRID:** optional per-region switching: exact event processing, equal-timestamp aggregation only when threshold/refractory semantics remain identical, and dense/batched mode when valid. Approximate time-window batching must be tagged APPROXIMATE with an error-vs-speed Pareto curve and can never be claimed equivalent to exact event streams.

A–H required for core campaign **if feasible within budget**; I/J may be staged contingent on measured opportunity, and omissions explicitly NOT RUN. Do not generate ten trivial wrappers around the same implementation. Avoid excessive sophistication that prevents dependable measurements.

## Correctness contract

Reference model is EXP-0002 delayed leaky integrate/fire: exact between-event decay, impulses, threshold emission, reset, refractory clamp, weighted directed synaptic delays, stable event tie-breaking. Pin and document the reference commit, exact conventions and floating point types. Need deterministic graph/event generator with stable serialization independent of NumPy RNG and C++ standard RNG; prefer generate once in a portable binary/CSV small fixture with checksums plus deterministic streaming counter-based generator for large scenarios. Same input events, same graph edges, same seeds, same run horizon on both hosts.

Verify, before any optimized benchmark:
1. analytic decay and independent impulse-response oracle;
2. small golden traces (event timestamp, target, source, amplitude, spike, state), including simultaneous arrivals, threshold ties, refractory, inhibition, zero-delay cycles, nonuniform delays and empty queue;
3. exact event sequence / digest for serial variants, including stable tie IDs and numerical tolerance; compare both full small traces and compact digest for large runs;
4. no speculative processing beyond conservative safe horizon, correct cross-region event delivery, epoch migration and exact-once ownership;
5. parallel determinism across repeated runs and thread counts OR document nondeterministic floating-point accumulation, use defined deterministic reduction, and verify bounded numerical + behavioral error (do not claim exact reproducibility when not achieved);
6. equivalence at selected causal interventions from EXP-0002;
7. synchronous dt grid refinement and error relative to continuous timestamp simulator: compare wall time ONLY at declared error budget, e.g. max spike timestamp delta <= 0.05 simulated units **and** task decision agreement >=99.5% when a decision is defined. These are starting acceptance thresholds subject to preregistered viability verification on smoke fixtures; if infeasible, report no equal-fidelity crossover rather than tuning criterion after observing results.

**Important:** EXP-0002 Python dense synchronous binning/aggregation may differ semantically; characterize discrepancy. An event-to-event exact reference and a fixed-step approximation must not be called mathematically identical without testing.

## Measurement matrix: staged, not full Cartesian product

- N={128,1024,10000,100000,1000000}; optional 3M/10M on Mac *after* resource gate, and 10M on Linux only if affordable. N=1B is projection only, not an allocated run.
- Out-degree D={4,16,64}; static random and modular/clustered local graphs (document generation and graph-cut fraction). Optional power-law only if generator is deterministic.
- Unique activated nodes f={0.001,0.01,0.10,0.50,1.00}, **independently** varying firing rate per active neuron r={0.01,1,10} / simulated time unit. Capture actual endogenous spike rate, event arrival rate, total event count, average fan-in.
- History depth L={0,16,64,256} on selected states, and optional B={0,4,8} exponential trace banks, compact 64-bit timestamps and justified precision.
- Distributions: regular, Poisson, bursty; temporal delays including zero, positive lower bound and heterogeneous delays; queue occupancy and region cut fraction.
- Workers={1,2,4,6} Linux physical-core headline; additionally 8/12 SMT *diagnostic*, not core claims. On Mac discover performance vs efficiency cores, compare same pinned worker sets plus all-performance-core subset when controllable.
- Bench N={128,1024,10000}, D=16, f={.01,.10,1}, r=1, history=0, topology=random, seeds={11,23,37} FIRST on both hosts for cross-run paired comparisons. After correctness and screening, N={100000,1000000}, selected f/r/D/topologies, 5 seeds {11,23,37,41,53} on primary claims. Stage additional N/params only if estimated RAM and time within budget, and select based on timing/technical feasibility, NOT sought favorable performance.
- Every benchmark must specify simulated time span, warmups, replicate counts, input event count, graph generation time and whether included. Separate initialization/setup, runtime steady state, replay, and tear-down. Min 5 independent timed repetitions per primary cell, report median/p95 across reps, separate across-seed variation and bootstrap CI when enough replicates. Use alternating / randomized variant order with recorded order; predeclare timeouts. Avoid comparing benchmark figures from hosts with different workloads.
- Measure seconds, events/sec, simulated seconds/sec, processed nodes/edges, branch queue operations, queue occupancy/p95, RSS/peak allocations, bytes/neuron and bytes/edge, cache misses/bandwidth **if actual counters available**, migration counts/time, cross-region messages, lock wait/worker idle time, causal lookahead stalls, load balance, memory paging/major faults, CPU frequency/temperature if truly observed. Failure and censoring rates.
- Compare equal **workload** and equal **fidelity**; reports must not mix them.

## Two-host plan and resource safety

**Phase Linux:** AMD Ryzen 5 PRO 5650GE, currently ~16GB DDR4 upgrading to **32GB total (2 × 16GB)**. Detect actual RAM at runtime; do not assume upgrade installed. CPU-first, native GCC/Clang; no new GPU toolchain.

**Phase Mac:** Apple M4 Pro MacBook Pro with **48GB unified RAM**; macOS ARM64. Run the SAME source commit/configs and matched baseline cells, then optional extended profiles. Compiler/platform-specific binaries, optimized flags recorded; use portable C++20 and CMake or similarly minimal build. Avoid x86-only intrinsics in shared code; compiler-specific SIMD as separate optional variant. Do not require ROS, MPI, CUDA or GPU.

Memory preflight: estimate actual graph, state, queue, scratch, history, generator and copy overhead, compare to current **available** memory, use <=60% of available by default, cap process RSS as measured, and stop gracefully before swap or OOM. Linux 16GB and Mac 48GB differ; no false assertion that size alone predicts total cost. Max per-cell wall 10 min; main host campaign 6h upper cap, configurable. Warm-up/thermal state and power profiles documented.

Both hosts commit separate small result bundles keyed by {source_sha, config_hash, host_fingerprint, compiler, timestamp, seed}, never overwrite. Linux implementation PR remains open while Mac results are added to SAME head branch when practical; ensure no silent source changes between paired runs. If Mac must be later, open follow-up cross-host evidence PR referencing original SHA and retaining separate datasets.

## Analysis and required decisions

Produce paired plots/table of:
- Python vs C++ literal speedup (same algorithm).
- C++ literal vs packed vs queue strategy (one optimization at a time).
- Native dense/sparse vs native event at equal correctness budget, crossover boundary as N,D,f,r vary.
- Parallel mutex vs static/dynamic owner at fixed thread count and graph cut; speedup, efficiency, overhead breakdown and violation count.
- Exact event vs exact compatible batch vs explicitly approximate adaptive mode; whether mode switching is actually beneficial.
- memory/throughput scaling by architecture on both machines; **observed** and separately labeled billion-neuron extrapolations with assumptions, uncertainty and feasibility limitations.

Negative results and regressions are first-class. No claims of linear thread scaling, lock-free superiority, guaranteed big-network advantage, or cognition from execution metrics. Final recommendation to EXP-0004 must identify measured fastest **validated** substrate per workload, and semantic limitations, for subsequent research into learning/plasticity and endogenous dynamics.

## Version control/review

Design-only now. Implementation later in `experiment/exp-0003-native-engine-scaling`; preserve SPEC. Changes after results in AMENDMENTS. Keep source/tests/configs and compact per-run data, REPORT; exclude binaries, raw high-volume event dumps, weights. Independent review before claims are treated as reproduced.
