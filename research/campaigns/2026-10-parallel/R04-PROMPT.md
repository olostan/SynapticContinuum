# R04 — Online plasticity and grounded reinforcement

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Find defensible learning signals for useful continuous neural activity that do not rely on human-labeled intermediate thoughts, subjective confidence, or a self-grading loop.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Compare three-factor reward-modulated plasticity, exact e-prop versus heuristic eligibility traces, online gradients, BPTT, differentiable plasticity, intrinsic learning progress, model-based control and short-lived synaptic states.

2. Write delayed feedback equations with event attribution: rewards arriving at t+delay must affect eligible paths from the causal emission, not merely whatever neurons happen to be firing now.

3. Disentangle useful task improvement from noise, surprise, activity complexity, prediction against self-generated targets and gaming the validator.

4. Investigate fast learning during a continuous stream, plus separate slower stable updates. Include a control where the network stores memory but never changes permanent parameters.

5. Design responses to bad, corrupted, delayed, contradictory or withheld feedback; include ways to abstain or refrain from updates.

## Expected research deliverables

1. research/findings/R04-online-plasticity/REPORT.md: candidate update rules and operational/tensor cost.

2. A fully specified controlled environment with delayed oracle reward, noisy-TV-like distractions and event IDs.

3. Falsification conditions and quantitative metrics: adaptation speed, preserved ability, credit accuracy, drift, false response rate.

## Decisive tests and objections to prioritize

1. Does eligibility-based feedback outperform delayed undifferentiated reward under matched compute?

2. What delay makes learned traces useless, and can multi-timescale traces recover without a full trajectory log?

3. Is self-supervised learning progress robust to irreducible randomness and prediction evaluator drift?

## Related investigations

Other researchers in the same campaign are investigating **R03, R05, R06, R10**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/adaptive-plasticity-and-guardrails.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E006-live-feedback.md
- https://www.nature.com/articles/s41467-020-17236-y
- https://proceedings.mlr.press/v80/miconi18a.html

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r04-online-plasticity** from latest main.
- Own only **research/findings/R04-online-plasticity/** and optional new **prototypes/research-r04-online-plasticity/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R04] Online plasticity and grounded reinforcement**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
