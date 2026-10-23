# Research Landscape, Prior Art, and Differentiation

**Reviewed:** 2026-10-22. **Status:** living, critical literature map; not a systematic review, peer review, or novelty certification.

## Purpose and scope

This document compares [the founding vision](FOUNDATIONS.md) and [research atlas](ATLAS.md) with published research. It distinguishes three claims that should never be merged:

1. **Existing result:** some neural architectures perform repeated latent computation, model temporal activation history, process irregular event streams, or update memory online.
2. **SynapticContinuum hypothesis:** a shared, *persistent*, event-responsive neural substrate can integrate internal activity, input, output, multiple timescales and possibly plasticity while communication is an optional actuator, not the inner clock.
3. **Unestablished added value:** this combination provides more useful reasoning, learning or efficiency than simpler streaming memory, recurrent networks, state-space models, trained recurrent-depth networks or ordinary agents.

The **combination is a research direction, not an established invention**. Individual ingredients have substantial prior art.

## The closest neighbors and the real differences

| Reference | What is already done | Overlap with SynapticContinuum | What remains distinct as a *hypothesis* | Essential control / follow-up |
|---|---|---|---|---|
| [Continuous Thought Machines (CTM), Darlow et al., 2025](https://arxiv.org/abs/2505.05522) | Explicit internal neural time, per-neuron processing of activation history, synchrony as representation, adaptive compute; published task results. | **Very high**; especially temporal neural signals and thought-like iterative processing. | Persistent operation across external events with unified communication and feedback events; possibly distinct per-*connection* temporal responses rather than CTM's per-neuron temporal processing. **Read implementation before claiming this gap is exclusive.** | Reproduce a small CTM or closely faithful counterpart; test persisted state, silences and interrupts. |
| [Coconut, Hao et al., 2024](https://arxiv.org/abs/2412.06769) | Intermediate LM hidden representations fed back as later latent reasoning inputs, without decoding inner thoughts to words. | **High** for latent token-free reasoning steps. | Autonomous/event-responsive state evolution not bounded to a planned latent-thinking segment. | Same decoder, latent step count and compute budget; test beyond the initial prompt. |
| [Huginn / recurrent-depth model, Geiping et al., 2025](https://arxiv.org/abs/2502.05171) | Trained recursive latent-depth reasoning with test-time compute scaling. | **High** for repeatedly applying latent computation. | Persistent cross-event substrate with temporal input/communication as endogenous events; not just deeper reasoning before answer. | Compare equal-FLOP recurrent-depth and free-running models. |
| [Training-Free Looped Transformers, Chen et al., 2026](https://arxiv.org/abs/2605.23872) | Frozen mid-blocks reused at inference; naive looping frequently hurts; damped looping can help selected tests. | **High** for low-cost pretrained retrofit. | Self-timed state and asynchronous or dynamically scheduled neural interactions are not shown by standard fixed loops. | Include naive, damped and adapter-trained frozen checkpoints; record degradation over long horizons. |
| [T²MLR, Cai et al., 2026](https://arxiv.org/abs/2607.15178) | Prior token's mid-layer state carried into a subsequent token; pretrained retrofit with fine-tuning. | **High** for learned internal feedback to pretrained Transformers. | Recurrence decoupled from subsequent token positions. | Compare token-position recurrence with silent inter-event recurrence. |
| [Growing Neural Cellular Automata, Mordvintsev et al., 2020](https://distill.pub/2020/growing-ca/) | Differentiable local cell updates can maintain and regenerate global spatial patterns. | **High** for local propagation, persistence and self-organization. | Linguistic/event semantics, learned semantic topology and useful reasoning remain unproved. | Compare learned semantic graph, spatial lattice and nonlocal attention with equal parameter budgets. |
| [Liquid Time-Constant Networks, Hasani et al., 2020](https://arxiv.org/abs/2006.04439) | Continuous-time neural state, adaptive time constants, bounded dynamics and temporal processing. | **High** for time-continuous persistent recurrent state. | Dynamic communication/plasticity integration and pretrained LM coupling are extensions, not replacements of earlier continuous-time computation. | LTC as low-cost dynamic baseline; compare solver cost and wall-clock. |
| [Neural Controlled Differential Equations, Kidger et al., 2020](https://arxiv.org/abs/2005.08926) | Irregular observations drive a continuous hidden state via a control path. | **High** for event arrival and between-event dynamics. | Hypothesis of useful self-generated latent work and separate action channels beyond solving irregular-series tasks. | Compare controlled-input evolution against self-excited activity and idle/sleep. |
| [Deep Equilibrium Models, Bai et al., 2019](https://arxiv.org/abs/1909.01377) | Implicit fixed-point representation with tied transformations. | **Medium-high** for recurrent latent computation and stability. | Continual trajectories, adaptation and behavior across events instead of only equilibrium inference. | Fixed-point solver vs oscillatory/transient trajectories with matched cost. |
| [Titans, Behrouz et al., 2025](https://arxiv.org/abs/2501.00663) | Learned long-term neural memory, with updates during inference. | **High** for experience-dependent persistent memory. | Autonomous dynamics and communication-as-event are additional, **not known to be beneficial**. | Memory-update-only baseline is mandatory. |
| [Test-Time Training layers, Sun et al., 2024](https://arxiv.org/abs/2407.04620) | Hidden state is itself a learned model updated through self-supervised test-time learning. | **Very high** for state/parameter adaptation during experience. | Separation of ongoing transient activity, reversible fast synaptic state, durable weights and independently timed output. | Test whether TTT-style memory substitutes for fast plasticity. |
| [S4, Gu et al., 2021](https://arxiv.org/abs/2111.00396) and [Mamba, Gu & Dao, 2023](https://arxiv.org/abs/2312.00752) | Efficient learned recurrence/state-space sequence models; Mamba selectively updates states from input. | **High** for efficient compact latent memory. | Autonomous evolving state during no input and shared action-feedback channels, if shown to matter. | Critical wall-time, accuracy and state-capacity controls. |
| [Differentiable Plasticity, Miconi et al., 2018](https://proceedings.mlr.press/v80/miconi18a.html) and [e-prop, Bellec et al., 2020](https://www.nature.com/articles/s41467-020-17236-y) | Trainable fast-plastic connections and eligibility-based learning in recurrent/spiking systems. | **Very high** for fast adaptation and delayed modulatory signals. | Multi-rate integration in a shared event-output architecture; three-factor rules themselves are not original. | Implement proper algorithmic comparison, not an oversimplified trace labeled e-prop. |
| [Moshi, Défossez et al., 2024](https://arxiv.org/abs/2410.00037) | Streaming full-duplex audio/text dialogue including interruptions, with codec tokens. | **Medium-high** for interactive input/output streams. | A free-running non-token neural substrate is still a separate question, but full-duplex interaction is **not** new. | Compare latency and interruptions; acknowledge tokenized audio. |
| [Neural Hawkes Process, Mei & Eisner, 2016](https://arxiv.org/abs/1612.09328) | Temporal point-event dynamics and event intensity. | **Medium** for output events and irregular timing. | Semantically rich persistent activity is not established. | Event timing likelihood/threshold calibration. |
| [Universal Transformers, Dehghani et al., 2018](https://arxiv.org/abs/1807.03819) | Recurrent refinement and adaptive computation/halting. | **Medium-high** for variable-depth computation. | No commitment to token-driven input and output as the system's only schedule. | Adaptive-depth baseline. |

## Relationship graph

- **Latent internal compute:** Universal Transformer → Huginn / Coconut / Looped Transformers / T²MLR → candidate retrofitted free-running core.
- **Continuous/event-driven dynamics:** Neural ODE / Neural CDE / LTC → candidate continuous-state core and input ports.
- **Local organization:** neural CA → learned semantic region graph (not yet validated).
- **Persistent memory:** S4 / Mamba / Titans / TTT → strong alternatives to continuous autonomous computation.
- **Plasticity:** differentiable plasticity / e-prop → eligibility, reversible state, delayed feedback hypotheses.
- **Communication:** Neural Hawkes / Moshi → externally timed event ports, turn-taking, action-copy hypotheses.
- These lines are **conceptual relationships**, not evidence of direct citation influence or chronological architectural descent.

## Audit of core claims and their risks

| Claim | Evidence assessment | Risk | Required refinement |
|---|---|---|---|
| Computation without sampled intermediate vocabulary tokens is possible | Established by several latent-reasoning/recurrent architectures | **Low** | Never claim it as original. |
| Dynamics can run during silence | Mathematically/technically feasible in recurrent continuous-time systems | **Low** for feasibility, **high** for value | Distinguish simulation clock, wall time and environment timestamps. |
| Useful cognition requires or benefits from perpetual neural updates | Not established | **Very high** | Idle-vs-frozen-vs-event-triggered compute-matched trial with energy measurement. |
| Temporal influence per connection improves over per-neuron memory or simple SSM | Open; delay kernels and synaptic filtering are prior art | **High** | Equal FLOPs/parameters/history dimension; ablate source-shared vs edge-local traces. |
| Existing pretrained LM blocks can be stably reused as a long-running recurrent core | Limited mixed precedent, distribution mismatch remains | **Very high** | Long-horizon norms, perturbation growth, control with damped loops and LoRA. |
| Neuron/region activations have independently meaningful semantic roles | Usually unjustified without feature analysis | **High** | Use learned slots, sparse features, or latent groups; test basis sensitivity. |
| Outputs can be emitted as events while state continues changing | Implementable as gated readout | **Medium** | Evaluate concurrency, refractory behavior and action/delivery separation. |
| Local eligibility traces solve delayed semantic feedback | Only in bounded settings; credit assignment remains hard | **Very high** | Delayed rewards and misleading/counterfactual event pairs. |
| LLM critic is useful as a protective semantic guardrail | Plausible but subject to bias, circular rewards and evaluator errors | **High** | Holdout ground truth, false-positive/false-negative rates, no imitation default. |
| Rich complex/chaotic activity indicates reasoning or consciousness | Unsupported | **Critical** | Never use activity complexity or chaos as success metric; no consciousness claim. |

## Where novelty could actually emerge

These are **not novelty claims**. Each requires a paper-level closest-method review and demonstrable advantage.

1. A stable *pretrained* neural substrate that **continues state evolution across irregular observations, interruptions and communications**, without vocabulary emission being its update clock.
2. Useful, economical **connection-local temporal memory** beyond matched recurrent and state-space alternatives.
3. Learned **action-event generation + action copy + independent receipt observation** in one persistent latent dynamical system.
4. **Multi-timescale plasticity and consolidation** that improves adaptation under delayed supervision while retaining prior capability.
5. **Selective activation/sleep** where autonomous compute occurs only if it outperforms maintaining state without work.

A negative result demonstrating that memory-only streaming models dominate is also valuable.

## Review of experiments and suggested reprioritization

**E004 timed HI→HELLO:** useful integration smoke test; classifying an emitted HELLO is not language acquisition, spontaneous language, or evidence of cognitive novelty. Explicitly compare a two-state finite-state machine and an ordinary RNN. Record zero-input false positives per hour, not only per tick; timing split and multiple seeds.

**E005 temporal ablation:** highest priority as a direct test of the distinctive per-connection history idea. In addition to all listed controls, compare LTC/CDE-style elapsed-time models and shared exponential traces. Hold output head fixed where possible.

**E006 delayed feedback:** valuable after E004/E005; distinguish inference-time hidden-state changes from learned parameter updates, and from supervised gradients.

**Proposed E007 idle-computation value:** identical event history with (A) sleeping memory, (B) idle recurrent updates, (C) update on events only, (D) extra compute only before answer. Fix train/test separation, FLOPs, parameter count and available observations. Report accuracy, memory horizon, latency, energy and drift. This can directly falsify the core premise.

**Proposed E008 communication provenance:** emit an intended action, independently deliver/drop/alter it, then inject delayed acknowledgment. Test whether internal predictions correctly distinguish *attempted* from *observed* output.

**Proposed E009 pretrained retrofit stability:** pretrained frozen, damped-loop, adapter and trained recurrent block across increasing silent durations; measure eventual collapse, fixed-point/limit-cycle attraction, task accuracy and cost.

## Bibliographic quality checks (2026-10-22)

Checked primary arXiv / original-publication title-and-abstract matches for CTM (2505.05522), Training-Free Looped Transformers (2605.23872), T²MLR (2607.15178), LTC (2006.04439), Neural CDE (2005.08926), Titans (2501.00663), TTT (2407.04620), Moshi (2410.00037), and original Distill neural CA article. These are **identity/abstract checks, not full method-and-reproduction audits**.

The repository bibliography contains numerous additional specific identifiers; **do not treat the whole bibliography as individually validated merely because it is linked**. LOTUS (2606.31779), the latent-RL counterpaper (2512.11816), and Huginn (2502.05171) were additionally checked against their arXiv identity/abstract pages: titles and qualitative descriptions match. Still to verify directly: all code-repository-to-paper pairings, the 'edge of chaos' article metadata, and precise S4/Mamba/e-prop quantitative claims. For each disputed reference record an explicit verification result rather than silently accepting an arXiv-looking URL.

Publication-year caveat: a preprint first posted late in one calendar year may appear as a publication the next (for example Titans, first posted 2024-12-31, commonly cited as 2025).

This is **an evolving narrative bibliography, not a systematic review**: no full database query protocol, exhaustiveness guarantee, comparative reproduced results, or independent experimental validation yet.

## Next research-agent assignments (parallel, minimal overhead)

- **CTM replication skeptic:** investigate precisely what CTM already provides across thought ticks and whether output/readout separation is truly novel.
- **Streaming alternatives:** implement minimal LTC/CDE, RNN, SSM/TTT baselines against E005/E007.
- **Retrofit engineer:** test frozen recurrent loops under long silence and quantify degradation before introducing extra mechanisms.
- **Neuroplasticity scout:** identify which connection memory features are new combinations and which are established synaptic-filter models.
- **Evaluator:** formalize failure metrics and adversarial controls; reject visual patterns or fluent output as primary evidence.

## Editorial recommendations

- Add a link to this map in README and FOUNDATIONS.
- Keep FOUNDATIONS short and hypothesis-centered; do **not** turn it into a manifesto asserting precedence.
- Keep SOURCES as the annotated bibliography and use this file for **explicit comparative judgments and audit limitations**.
- Attribute mathematical primitives (time delays, eligibility traces, ODE/CDE, recurrent loops) to prior art.
- State the most important unresolved scientific question in one line: **What useful behavior is obtained by allowing neural activity to evolve between external events that cannot be obtained more cheaply by preserved state plus computation on demand?**
