# R01 — Cross-track briefing (read this first)

**Status:** literature investigation, **not** a completed scientific experiment.  
**Full investigation:** [REPORT.md](REPORT.md) · **Source audit:** [REFERENCES.md](REFERENCES.md) · **Review:** [R01 PR #1](https://github.com/olostan/SynapticContinuum/pull/1)

## Core conclusion

**Do not confuse comparison of neural mechanisms with comparison of research objectives.** Much of SynapticContinuum's proposed *machinery* has existing precedents; that does not settle its central *phenomenological and causal* question:

> Can a persistent neural system develop internally initiated, lasting, causally consequential representations or behaviors when no external prompt or required response is driving it?

The goal is **not** improved answer correctness, fluent conversation, lower latency, or cheaper inference. Those are useful controls/diagnostics, not the definition of success. Conversely, self-sustained complexity or apparent novelty alone is **not** evidence of thought or consciousness.

## What R01 found

- **[Published mechanisms]** CTM already uses neural internal time and **per-neuron activation histories**; it also studies continuous environment interaction in RL. Coconut and Huginn demonstrate latent computation without sampled intermediate words. LTC, Neural CDEs, SSMs, TTT, differentiable plasticity, and neural CA cover other important pieces. [Closest-neighbor matrix](REPORT.md#closest-neighbor-matrix)
- **[Architectural hypothesis]** A **per-connection** temporal response differs from CTM's neuron-local history processing, but shared trace banks plus ordinary recurrence may express equivalent finite-dimensional histories. Novel parametrization is not proof of advantage. [CTM technical comparison](REPORT.md#ctm-comparison-at-the-equation-level-not-merely-nomenclature)
- **[Important counterevidence]** CTM reports RL performance similar to LSTM baselines in its studied conditions; autonomous internal activity is not demonstrated to be better merely by existing. [CTM primary paper](https://arxiv.org/abs/2505.05522)
- **[Unestablished]** We have **no local demonstration** of emergent cognition, self-reflection, or unique beneficial idle-time state development. Even a successful behavioral result would not establish subjective consciousness.

## Two distinct questions for every track

1. **A — Mechanism / prior art:** What pieces already exist? What exact difference is being tested? Is a smaller RNN/SSM/trace or explicit event-loop baseline enough?
2. **B — Emergent phenomenon:** What persistent, internally generated representation/change arises, and how can we intervene to prove a causal effect beyond replay, random dynamics, clock scheduling, or simply extra compute?

**B guides the scientific aim; A provides the toolbox and falsification controls.** A model may be unremarkable on conventional benchmark accuracy yet yield interesting falsifiable developmental dynamics. But we must not rename arbitrary wandering or attractor cycling “cognition.”

## Highest-value experiment

Compare time-aware GRU/LSTM, source-shared temporal traces, CTM-style neuron history, LTC/SSM, and edge-specific temporal kernels **under independent idle-time schedules**: sleep/preserve state, evolve during silence, event-only updates, and equal additional computation immediately before readout. Fix inputs, data access, parameters/computation bands, elapsed-time signals, training budget, and multiple seeds. **Intervene on intermediate state trajectories**, then test held-out behavior or predictions. [Full protocol](REPORT.md#highest-value-experiment-e-r01-1--edge-memory--idle-compute-factorial)

**Falsifying outcome:** any apparent “endogenous development” is equally explained by ordinary stored memory, replay, injected time, or extra pre-response steps.

## Coordination notes

R02 (temporal kernels), R03 (communication), R04 (plasticity), R05 (guardrail), R06 (consolidation), R07 (retrofit), R08 (skepticism), R09 (prototype), and R10 (dynamics): use this as **context, not an architectural decision or shared-track requirement**. Keep contradictory results. Detailed bibliography and limits are in [REFERENCES.md](REFERENCES.md).

**Suggested additional research lens:** complement architecture comparison with prior art on spontaneous activity, developmental learning, intrinsic motivation, open-ended learning, artificial life, predictive processing, and recurrent self-modeling. This is a proposed next investigation, **not** an audited conclusion of R01.
