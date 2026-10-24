# Experiment proposals

Experiments here are **proposals**, not claims of executed research. Start with the smallest decisive test and baseline. No required order or mandatory implementation.

- [E001 — Frozen middle-block recurrence](E001-frozen-block-loops.md) — inference-only retrofit.
- [E002 — Latent cellular automaton](E002-latent-ca.md) — self-organized neural dynamics on controlled formal tasks.
- [E003 — Feedback adapters and LoRA](E003-feedback-adapters.md) — small post-training to support recurrence.

- [E004 — Timed greeting](E004-timed-greeting.md) — learn a delayed output event after HI, including silence and output-feedback controls.
- [E005 — Temporal memory ablation](E005-temporal-memory-ablation.md) — compare delayed synaptic response, shared traces and simple timestamp-aware recurrence.
- [E006 — Live delayed feedback](E006-live-feedback.md) — test event-associated modulation and independent regression guardrails without whole-state snapshots.

For each executed test, save the revision, model and dataset provenance, commands, training configuration, seeds, matched compute, all outcomes including failures, and environment constraints. Summaries go to [results/](../results/). Large checkpoints do not belong in Git.


## Executable research series (EXP-####)

- [EXP-0001 — Temporal memory](EXP-0001-temporal-memory/REPORT.md)
- [EXP-0002 — Event-driven dynamics](EXP-0002-event-driven-dynamics/REPORT.md)
- [EXP-0003 — Native engine scaling](EXP-0003-native-engine-scaling/REPORT.md)
- [EXP-0004 — Topology and adaptive scheduling](EXP-0004-topology-adaptive-scheduling/REPORT.md) — completed Linux report, [benchmark catalog](EXP-0004-topology-adaptive-scheduling/BENCHMARK_CATALOG.md).
- [EXP-0005 — Scientific simulation substrates](EXP-0005-scientific-simulation-substrates/SPEC.md) — DESIGN ONLY, NOT RUN; [work packages](EXP-0005-scientific-simulation-substrates/WORKPACKAGES.md), [external architecture analysis](EXP-0005-scientific-simulation-substrates/ARCHITECTURES.md). Scientific claims and code from past experiments are not automatically transferred; EXP-0005 remains subject to independent review.

- [EXP-0006 — Persistent Adaptive Microcosm](EXP-0006-persistent-adaptive-microcosm/README.md) — **DESIGN ONLY / NOT RUN**: primary test of continually evolving internal representations, long-form learning/forgetting, interruption/resume, teacher-free transfer, controlled local LLM feedback, and explicit tiny-to-large scale criteria. [Scientific spec](EXP-0006-persistent-adaptive-microcosm/SPEC.md) · [longitudinal measurements](EXP-0006-persistent-adaptive-microcosm/MEASUREMENT.md) · [growth gates](EXP-0006-persistent-adaptive-microcosm/SCALING.md).
