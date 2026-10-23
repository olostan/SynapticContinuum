# R01 — Literature, prior art and citation audit

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Produce the strongest possible evidence-graded map of existing work and identify what remains genuinely untested. Be particularly skeptical of broad novelty claims.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Audit every high-impact paper in SOURCES.md and RESEARCH_LANDSCAPE.md against the primary PDF/author implementation: verify authors, exact title, date/version, methodology, experimental setup and claimed results. Flag broken references and unsupported summaries.

2. Search historically as well as recently: neural temporal coding and synaptic kernels, delay differential neural systems, adaptive recurrent networks, predictive processing, continual RL, plasticity, TTT, Liquid Time-Constant Networks, CTM, neural CA, Deep Equilibrium, recurrent-depth LM work and streaming speech.

3. Build a closest-neighbor matrix: what the approach implements, level of overlap, what SynapticContinuum might add, and the most damaging alternative explanation.

4. Identify already-running research projects and their public implementations; do not claim a distinct combination without systematically ruling out close equivalents.

5. Separate a new *system integration* proposition from a novel neural computation primitive; neither alone demonstrates superiority.

## Expected research deliverables

1. research/findings/R01-literature-novelty/REPORT.md — comprehensive critical survey and novelty boundary.

2. A machine-friendly bibliography, e.g. REFERENCES.md, with per-claim evidence status and proposed corrections to existing source files.

3. A list of at least five potentially invalid originality claims and three genuinely falsifiable remaining hypotheses.

## Decisive tests and objections to prioritize

1. Compare CTM's per-neuron activation history against our proposed per-connection temporal kernels at the method/equation level.

2. Distinguish Coconut latent token feedback, Huginn recurrent depth, and autonomous state evolution under irregular external events.

3. Identify whether 'continuous input/output as activation' reduces to streaming RNN+decoder under controlled tests.

## Related investigations

Other researchers in the same campaign are investigating **R02, R03, R07, R08**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/RESEARCH_LANDSCAPE.md
- https://github.com/olostan/SynapticContinuum/blob/main/SOURCES.md
- https://arxiv.org/abs/2505.05522
- https://arxiv.org/abs/2005.08926
- https://arxiv.org/abs/2407.04620

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r01-literature-novelty** from latest main.
- Own only **research/findings/R01-literature-novelty/** and optional new **prototypes/research-r01-literature-novelty/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R01] Literature, prior art and citation audit**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
