# Local execution-agent prompt — EXP-0002

You are an independent principal scientist and systems engineer executing **EXP-0002 Event-driven neural dynamics and temporal memory** in https://github.com/olostan/SynapticContinuum.

## Before coding

1. Fetch latest main **after the design-only EXP-0002 preparation PR is merged**. Create branch `experiment/exp-0002-event-driven-dynamics` from that main.
2. Read `AGENTS.md`, `FOUNDATIONS.md`, `EXPERIMENTATION.md`, `research/campaigns/2026-10-parallel/COMMON.md`, relevant R01/R02 summaries, merged EXP-0001 REPORT/AMENDMENTS, and merged PR #7 feasibility report.
3. Treat this directory's `SPEC.md` as the preregistered, immutable-first contract and `manifest.yaml` as the resource/run plan. Check for unexpected existing experiment IDs or changed branches.
4. Record real host environment (CPU, RAM, interpreter, PyTorch/NumPy, acceleration, git SHA and dirty tree) before implementation. CPU is default; do not upgrade drivers or install massive ML stacks.

## Execution order

- Implement deterministic scheduler and analytically exact lazy-decay reference first. Explicitly define timestamp tie-breaking, zero-delay cycles, refractory/state resets and future-event generation.
- Add focused unit/property tests: exact exponential partition invariance, timestamp ordering, no future leakage, bounded history truncation, self-loop/zero-delay termination, reference trajectory parity and deterministic event-log replay.
- Smoke test small fixed graphs. Do not start a parameter sweep until correctness passes.
- Execute preregistered staged screening, not a giant Cartesian sweep: scheduler crossover; history-depth/activation-density cost; task-relevant temporal retention; autonomous-activity causal intervention versus freeze, replay, noise, sham and equal-compute.
- Preserve **exact same mathematical dynamics** for scheduler comparisons; label models with different rules as architecture comparisons, never speedups.
- Report input-driven active fraction separately from propagated active fraction. Measure the CPU scheduler honestly, including heap/queue and memory overhead. Compare with equivalent synchronous approximations while varying dt and reporting error.
- If adding learning, use matched budgets and independent seeds/splits, train on silence if evaluating silence, and avoid explicit delta-time shortcut in learned readout.
- Enforce per-cell event limits, 10 GiB RSS cap, and wall budgets. Any omitted cell must be marked NOT RUN with reason. Save preliminary evidence after each stage.
- For changes after seeing results, append `AMENDMENTS.md` with date, why, and exploratory/confirmatory qualification. Do not silently change SPEC.md, task thresholds, or decide success criteria post hoc.

## Report requirements

Write a substantial but readable `REPORT.md` with executive summary, competing hypotheses, laws of dynamics, exact commands/configs, task/data construction, timing and numerical accuracy, benchmark tables, history L×activation f curves, activity/stability metrics, intervention effect sizes with sham/random controls, per-seed variability, non-results and limitations. Separate **observations**, **inferences**, and **open questions**. Do not interpret persistent random activity as cognition.

Store compact aggregate JSON/CSV metrics and source/config/test code in Git; full event streams, weights, caches, profilers and logs outside Git as required by `EXPERIMENTATION.md`. Include actual checksums/artifact retention statements where applicable. Do not commit large files.

## GitHub deliverable

Open a distinct PR from `experiment/exp-0002-event-driven-dynamics` to `main` titled `[EXP-0002] Execute event-driven neural dynamics and temporal memory`. Include tested configurations and exclusions, source/run provenance, report link, and concise falsification summary. Leave open; do not merge automatically. Request an independent skeptical scientific review.

**Success is a reproducible and falsifiable answer, including negative results—not an attractive demonstration or a GPU benchmark.**
