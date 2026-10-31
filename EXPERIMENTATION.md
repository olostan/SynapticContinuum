# Experimentation protocol — SynapticContinuum

**Version 1.1 · 2026-10-30**. This protocol governs *new executable experiment directories* under `experiments/EXP-####-slug/`. Existing E001–E006 proposal documents remain valid and unchanged. Experiments are research, not production releases. The primary scientific goal is causal, persistent endogenous neural-state development, **not** conversational correctness, speed, or consciousness claims.

## Contract: design, execution, evidence, review

1. **Design agent** authors immutable-first `SPEC.md` (question, competing hypotheses, predictions, falsifiers, data, exact baselines, negative controls, interventions, split design, statistical plan), `PROMPT.md` (delegation), and `manifest.yaml` (runtime constraints). Commit these to a feature branch and optionally open a design PR; never claim an experiment has run.
2. **Execution agent** checks out the exact branch and reads this file, then SPEC, manifest, PROMPT. Detects physical hardware/backend and records configuration *before* modifying source. Implement experiment under its own folder, preserving experiment semantics. Run deterministic unit tests, tiny smoke test, then predeclared evaluation. Do not rewrite hypotheses/targets after looking at results; log an explicit `AMENDMENTS.md` with timestamp and justification when indispensable, marking affected runs exploratory.
3. **Evidence**: each run has a UTC timestamp+host-class+seed unique ID; commit source, dependency lock files if practical, run commands, small JSON/CSV aggregates and a detailed `REPORT.md`. Do not require committing checkpoints, recordings, full tensor dumps, large generated datasets or logs.
4. **Review agent** independently reads SPEC and raw *small* evidence, checks leakage, statistical variance and baseline parity, reproduces at least a smoke run where practical, and writes a skeptical review or PR comment. Only then may findings be described as independently reproduced.
5. **Synthesis** links conclusions to commits and reviews; negative or inconclusive findings are first-class outputs. Experiments never automatically update FOUNDATIONS/ATLAS.

## Required per-experiment layout

```text
experiments/EXP-####-slug/
  SPEC.md           preregistered scientific design and decisions
  PROMPT.md         reproducible local execution agent instructions
  manifest.yaml     targets, budgets, seeds, reproducibility
  src/              committed implementation
  tests/            deterministic correctness/smoke tests
  configs/          versioned configurations
  runs/             small records only, e.g. 2026.../metrics.json
  REPORT.md         detailed result narrative; initially NOT RUN
  AMENDMENTS.md     only if deviations occur
```
A planned experiment may have only the first three files. No speculative empty directories are required. Unique ID is allocated once, never reused; run IDs are separate. Source/data provenance and command lines are essential to reproduce an experiment without stored binary artifacts.

## Evidence requirements and comparison discipline

- Record repository commit and dirty-tree status, exact executable command/arguments, seed, OS/kernel, CPU/GPU, available RAM, Python/compiler/backend version, framework versions, accelerator availability, precision, training steps, batch sizes, optimizer, data generator version and hashes or deterministic generation parameters; device temperature/power only if measured.
- Train/validation/test splits must be deterministic and separated by *causal generalization target* (e.g. disjoint time intervals), not merely by random example ID. Report N and class balance. No retuning on held-out test.
- Baselines should include a trivial deterministic solution when one exists, plus a strong time-aware recurrent/SSM or other appropriate model; equalize event access, timing information and tuning effort. Show trainable parameters, steps, approximate MAC/FLOPs, wall time and peak RAM; total equality across all resource axes is impossible, so report Pareto comparisons.
- Report distributions across independent seeds, not just best run: individual scores, mean, dispersion/confidence interval with method, failures/NaNs, negative controls and held-out performance. Never interpolate unrun results.
- For free-running latent dynamics, independently vary elapsed physical/environment time, internal update count, input access and pre-readout compute. Intervene on hidden state and compare replay/sleep/noise and event-only controls. No claim of thought or consciousness from instability, complexity, random novelty or performance alone.
- Maintain full narrative: what was attempted, what actually executed, deviations, warnings, surprises, contradictory and null evidence, what is still unknown, and how someone can rerun exactly.

## Small-Git / large-local policy (mandatory)

**Git includes:** human-written source, tests, configurations, prompts, reviewed documentation, tiny reproducibility metadata, aggregate metrics and small plots when useful. Default limits: individual data/report artifacts <= 1 MiB, per-run checked-in evidence <= 5 MiB. Above those limits: do not commit; summarize and reference locally or in opt-in external archival storage. A human may explicitly approve rare exceptions.

**Git excludes:** model/checkpoint weights (*.pt, *.pth, *.ckpt, *.safetensors, *.onnx, *.npz), tensor dumps, generated datasets, full stdout/stderr logs, recordings/videos, profiler traces, caches, build products, virtual environments, and large binary figures. Add per-experiment `.gitignore` and run a pre-commit size/diff check. Avoid Git LFS by default; a large artifact has no automatic scientific value.

**Recreation first:** generated data uses committed generation code+seed+config+version; pretrained data/models require exact source/version/license/hash (do not commit weights). If an essential unrecoverable artifact exists, report its limitations and optional external checksum/location, never claim full reproducibility without access.

**Run locally:** write bulk artifacts outside repo (default `$SC_ARTIFACT_ROOT/EXP-####/<run-id>/`, falling back to a user-chosen path outside repo). Reports include artifact manifest of filename, purpose, byte count, SHA-256 and whether retained/deleted. A cleaned-up bulky artifact is marked **not archived**, not falsely claimed available. Small metrics may be checked into `runs/<run-id>/metrics.json`. Never put private files, API keys, proprietary research or personal data in a public PR.

## Target machines (discovery, not assumptions)

- Apple Silicon MacBook Pro M4 Pro, ~48 GB unified RAM: prefer locally validated MLX or PyTorch/MPS for training if supported. Capture device actual discovery; CPU fallback.
- Always-on Linux mini PC ~16 GB RAM shared with integrated GPU: prefer PyTorch CPU for guaranteed simple correctness; use Vulkan only with experimentally verified framework backend and measured support, never assume a PyTorch Vulkan training backend works. Stay below available memory; recommend short smoke then bounded overnight run.
- Both: choose a common mathematical definition and data splits. Record numerical differences and unsupported operations. Hardware-specific optimizations must not silently change the tested algorithm.

## Local handoff

```text
Read EXPERIMENTATION.md and execute experiments/EXP-####-slug/PROMPT.md
from the named GitHub branch. Preserve SPEC.md and all falsification controls,
discover this machine's accelerator, implement and smoke-test, run within
manifest resource limits, commit code and compact evidence, write REPORT.md,
and open a PR to main. Never merge; never upload large artifacts.
```

If a long run terminates early, record partial metrics, reason and whether checkpoint resume is possible. Do not fabricate missing metrics. A PR can be **ready for design review** without any runs and should say so.


## Vision alignment for newly proposed experiments (2026-10-24)

Before designing a new executable EXP, read [VISION.md](VISION.md), [THEORY.md](THEORY.md), [FOUNDATIONS.md](FOUNDATIONS.md) and [ATLAS.md](ATLAS.md). A task benchmark, explicit-symbol world, neural-activity plot or simulation-scale result is only an **instrument**. State which uncertainty about *persistent, self-initiated, nonlinguistic meaning, branching hypotheses, revisable temporal belief, significance-steered attention, active information seeking or lifelong adaptation* the proposed test can constrain. Include honest simpler baseline(s), a way to detect semantic inference by the measurement decoder itself, and a stopping criterion. The candidate mechanism need not encompass the full vision, but every proposed claim must say what it does **not** test. Do not retroactively reinterpret earlier EXP results or turn the unmerged EXP-0006 design into an approved architecture.

## Candidate-theory experimental safeguards (2026-10-30)

The new [THEORY.md](THEORY.md) is **not** an experiment specification. If evaluating parallel/convergent prediction, heterogeneous tempo, retrospective attribution, modulation or dormant-memory reactivation, preregister:
- **What the variable means:** distinguish actual predictive function from generic state transition, serial textual outputs from high-dimensional internal computation, and concurrent semantic activity from asynchronous/hardware scheduling.
- **The memory source:** active state, temporary residual trace, durable learned parameter, episodic store or external retrieval. Include no-idle-compute, memory-only and time-feature shortcut controls.
- **The modulator route:** sensory, internal/homeostatic, predicted consequences, history-dependent, fixed or learned; test individual route removal, shuffled gain, delayed feedback and return to baseline. Measure false alarms, over-suppression, reactivation and rumination, not only task accuracy.
- **The causal account:** distinguish an explanatory chain inferred by an interpreter/LLM from actual influential latent states. Intervene on single and joint contributing histories, replace with matched/sham state, and repeat with the exact same observations, elapsed time and compute.
- **The external oracle:** observed events, true environment state, learner beliefs, imagined/counterfactual continuations, and model text must have distinct provenance. Prevent semantic labels and hidden world truth leaking through stimulus generation or evaluation code.
- **Competitive baselines:** include (as appropriate) finite-state controllers, indexed/episodic memory, time-aware GRU/SSM, generative world models, Bayesian/probabilistic models, fixed schedulers, existing codelet/priority systems, and equal-resource retrained ablations.
- **Reportable outcomes:** causal usefulness and retained generalization, calibration of alternative hypotheses, cost/latency/resource use, failure rates and credible null outcomes. Never infer artificial consciousness or proven human-style cognition.

Prioritize small tests of **delayed joint influence and long-dormant cue reactivation** before multi-component architectures. Add heterogeneous time and multimodal modulation only as separately falsifiable factors. Experimental identifiers, designs, seeds and runtime are still subject to normal approval/review; earlier E/EXP reports are immutable historical evidence and must not be upgraded retroactively.
