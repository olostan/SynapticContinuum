# R08 — Skeptical review and falsification

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Conduct an independent, deliberately adversarial evaluation of the entire project. Strongly challenge whether persistent idle computation, temporal kernels, plasticity and self-output offer a material advantage over existing models.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Construct strongest null hypotheses and concrete counterexamples for each major claim: temporal connection memory, event-centric input/output, idle-time computation, self-action copy, eligibility feedback, LoRA consolidation, evolution and pretrained retrofit.

2. Review possible illusions of success from extra compute, larger state, timestamps, easier data distribution, hidden labels, evaluator leakage, cherry-picked seeds, or classifier-only output from an overpowered frozen language head.

3. Identify closest technically equivalent models (RNN, SSM/Mamba, continuous-time ODE/CDE, spiking models, adaptive depth, CTM, neural CA, memory-only online models) and the simplest valid reproduction baselines.

4. Formulate 'kill tests' that could invalidate the added-value claim even if a demonstration looks impressive. Include input loss, long silent time, changing rewards and opposing validator signals.

5. Point to claims in current design docs that should be weakened, corrected or abandoned, but do not edit shared docs.

## Expected research deliverables

1. research/findings/R08-skeptical-falsification/REPORT.md: sharp criticisms, supporting sources, strongest alternatives and tests.

2. An evidence-strength / go-no-go matrix for individual hypotheses, not an all-or-nothing verdict.

3. Three to five discriminating experiments with predeclared failure and success observations.

## Decisive tests and objections to prioritize

1. Can a cheap timestamp-aware RNN match temporal-synapse benefits?

2. Can a sleeping-state model match a perpetually updated one at substantially lower cost?

3. Do communication success and state 'self-awareness' disappear once action confirmation is distinguished from intention?

## Related investigations

Other researchers in the same campaign are investigating **All; specifically R01 R02 R05 R09.**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/RESEARCH_LANDSCAPE.md
- https://github.com/olostan/SynapticContinuum/blob/main/ATLAS.md
- https://github.com/olostan/SynapticContinuum/blob/main/ideas/stability-and-adversarial-hypotheses.md
- https://arxiv.org/abs/2312.00752

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r08-skeptical-falsification** from latest main.
- Own only **research/findings/R08-skeptical-falsification/** and optional new **prototypes/research-r08-skeptical-falsification/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R08] Skeptical review and falsification**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
