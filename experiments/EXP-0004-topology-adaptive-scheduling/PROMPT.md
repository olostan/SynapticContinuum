# EXP-0004 — Linux execution handoff

Repository: https://github.com/olostan/SynapticContinuum
Experiment: experiments/EXP-0004-topology-adaptive-scheduling/

1. Pull main and branch `experiment/exp-0004-topology-adaptive-scheduling` (after this design-only PR merged). Read AGENTS.md, FOUNDATIONS.md, EXPERIMENTATION.md, research/campaigns/2026-10-parallel/COMMON.md, EXP-0002 REPORT, EXP-0003 SPEC/REPORT/AMENDMENTS, and EXP-0004 SPEC.md/manifest.yaml end to end.
2. Record host specs and versioned source commits. Preserve SPEC preregistration; deviations documented transparently in AMENDMENTS. Implement independently under EXP-0004; do not silently rewrite prior experiments.
3. Begin with strict serial reference correctness and profiler. Validate six disconnected regions control before adaptive scheduling. Measure thread start, active, idle, barriers, queue, cross-region messages. If W=6 fails to scale on truly independent sufficiently busy regions, identify why before adding sophistication.
4. Implement controlled synthetic random/small-world/hierarchical modular/degree-preserving controls, graph properties, ID permutation, and locality-aware partitioning; separate graph-structure effects from input/event-workload effects using identical stimuli and a trace-replay microbenchmark.
5. Build persistent workers, many logical regions per worker, exclusive ownership and safe versioned migration only in staged increments. Compare with static/barrier owner at same W and same workloads. Preserve event order under stated positive-delay preconditions; for zero-delay edges reject or correctly handle, never fabricated epsilon.
6. Run Linux staged matrix with bounded resource preflight and independent seeds/repetitions. Keep exact execution and optional relaxed epsilon model separate and labeled. Optional public biological connectome pilot only after confirming download/license/source/hash; skip cleanly if unavailable. Never commit datasets or giant event logs.
7. Produce reproducible `scripts/run-exp0004.sh --profile smoke|standard|extended` (or equivalent) with stable output paths, small metrics JSON, and REPORT.md with plots/tables, full negative findings, profiler breakdown, self-scaling and source provenance. Record NOT RUN cells.
8. Open PR `[EXP-0004] Topology and adaptive region scheduling — Linux evidence` to main, **do not merge**; seek independent scientific/code review. Goal is reliable experimental evidence, not marketing speedup.

Critical: a random-graph run with 1.2x on six cores is not automatically a broken scheduler, and a large graph isn't automatically more biologically realistic. Test alternatives with data, causal parity and measured work.
