# R10 — Dynamical systems, stability and asynchronous updates

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Study the mathematics and numerical behavior of a persistent time-filtered self-modifying neural system, including useful transient computation, fixed points, oscillations, chaotic divergence and update scheduling.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Compare differential equations, delay differential equations, event-driven jump systems, recurrent networks, reservoir computing, leaky integrators, spiking synapses and asynchronous cellular automata. Specify clocks clearly.

2. Analyze equilibrium, local Jacobian spectrum, recurrence gain, perturbation amplification, limit cycles, learned delays, plastic changes to eigenstructure and the effect of numerical integration step size.

3. Discuss which claims of stability can be proven with contraction/passivity bounds and which are only empirical heuristics; note tradeoffs with responsiveness and long-range memory.

4. Study simultaneous events and asynchronous scheduling: reproducibility, race conditions, stale reads, starvation and GPU batching efficiency. Compare synchronous, event-driven and adaptive-budget updates.

5. Connect measurable dynamics to real tasks: retention over silence, recovery from perturbation, learning on new evidence, graceful adaptation and compute/energy footprint; do not reward noise or entropy alone.

## Expected research deliverables

1. research/findings/R10-dynamics-stability/REPORT.md with a mathematically explicit family of update rules and stability assumptions.

2. A proposed simulation with sweeps of delay, gain, plasticity strength and idle duration; plots only if computed.

3. A failure taxonomy distinguishing numerical explosion, attractor collapse, semantic decay, catastrophic forgetting and plasticity loss.

## Decisive tests and objections to prioritize

1. Can a network preserve useful state without active idle computation?

2. Does stability regularization suppress difficult temporal computation?

3. Is any apparent 'edge of chaos' relation robust across tasks, seeds and parameter budgets?

## Related investigations

Other researchers in the same campaign are investigating **R02, R04, R08, R09**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/stability-and-adversarial-hypotheses.md
- https://github.com/olostan/SynapticContinuum/blob/main/ideas/latent-cellular-automata.md
- https://arxiv.org/abs/2006.04439
- https://arxiv.org/abs/1806.07366

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r10-dynamics-stability** from latest main.
- Own only **research/findings/R10-dynamics-stability/** and optional new **prototypes/research-r10-dynamics-stability/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R10] Dynamical systems, stability and asynchronous updates**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
