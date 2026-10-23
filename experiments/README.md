# Experiment proposals

Experiments here are **proposals**, not claims of executed research. Start with the smallest decisive test and baseline. No required order or mandatory implementation.

- [E001 — Frozen middle-block recurrence](E001-frozen-block-loops.md) — inference-only retrofit.
- [E002 — Latent cellular automaton](E002-latent-ca.md) — self-organized neural dynamics on controlled formal tasks.
- [E003 — Feedback adapters and LoRA](E003-feedback-adapters.md) — small post-training to support recurrence.

- [E004 — Timed greeting](E004-timed-greeting.md) — learn a delayed output event after HI, including silence and output-feedback controls.
- [E005 — Temporal memory ablation](E005-temporal-memory-ablation.md) — compare delayed synaptic response, shared traces and simple timestamp-aware recurrence.
- [E006 — Live delayed feedback](E006-live-feedback.md) — test event-associated modulation and independent regression guardrails without whole-state snapshots.

For each executed test, save the revision, model and dataset provenance, commands, training configuration, seeds, matched compute, all outcomes including failures, and environment constraints. Summaries go to [results/](../results/). Large checkpoints do not belong in Git.
