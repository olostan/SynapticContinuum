# R02 — Temporal kernels and synaptic memory

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Formalize temporal memory on neural connections, including mathematical expressivity, stability and feasible cost. The system should learn relationships among past activities, rather than only the latest activation.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Derive explicit discrete and continuous formulas for per-edge finite-lag kernels, connection-local state, sparse delayed edges, source-shared multiscale leaky traces and low-rank temporal bases.

2. Disentangle fixed learned temporal kernel parameters from rapidly plastic kernel state; neither is identical to storing every previous set of weights.

3. Compute parameter, activation storage, training memory, FLOPs and bandwidth at several representative sizes: 128/512/4096 units, 8/64 lags and sparse vs dense connectivity. State O(N²K) precisely rather than calling it exponential.

4. Study perturbation propagation, gain control, contraction, periodic attractors, positive-feedback runaway, damped updates and edge-specific adaptivity; state which mathematical guarantees require restrictive assumptions.

5. Research how temporal synapses relate to convolutional RNNs, delay lines, spiking synaptic filters, S4/Mamba, LTC and reservoir computing.

## Expected research deliverables

1. research/findings/R02-temporal-connections/REPORT.md with explicit equations and two or more executable tensor-level choices.

2. Cost and capacity comparison with a simple timestamp-aware RNN, a state-space model and a fixed recurrent baseline.

3. Experiment plan for synthetic irregular events separating the effect of long pauses from extra computational steps.

## Decisive tests and objections to prioritize

1. Train on identical A-B-C symbols with varying delays that alter the true label; test unseen delays.

2. Compare against a plain RNN given exact delta-time as an input, matched for total compute.

3. Include tasks where extra temporal kernels *should not* help, to avoid favoring the design by dataset construction.

## Related investigations

Other researchers in the same campaign are investigating **R10, R03, R09, R08**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/temporal-connection-memory.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E005-temporal-memory-ablation.md
- https://arxiv.org/abs/2111.00396
- https://arxiv.org/abs/2312.00752

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r02-temporal-connections** from latest main.
- Own only **research/findings/R02-temporal-connections/** and optional new **prototypes/research-r02-temporal-connections/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R02] Temporal kernels and synaptic memory**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
