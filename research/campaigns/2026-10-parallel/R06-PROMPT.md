# R06 — Evolution, LoRA and durable consolidation

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Investigate whether short-term experience-driven connection changes can be selectively converted to durable learning and whether evolution improves resilience without freezing useful adaptation.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Specify timescales: evolving latent state, reversible plastic edge memory, durable LoRA or adapter weights and selected structural / hyperparameter changes. Do not equate LoRA with all learning.

2. Compare adapters, replay, elastic weight consolidation, test-time training, fast weights, learned plasticity rules, evolutionary strategies and population-based training; seek both supporting and contradictory primary studies.

3. Explain how a proposed fast-weight state would train a low-rank durable adapter and how promotion is validated without corrupting the active system.

4. Study robustness fitness surfaces, evolution of topology versus parameters versus plasticity rules, multi-objective selection and total interaction/compute costs on local hardware.

5. Prevent trivial optimizing for frozen non-learning stability: test future adaptability on held-out tasks alongside memory retention.

## Expected research deliverables

1. research/findings/R06-evolution-consolidation/REPORT.md: lifecycle, mathematical options, approximate resource budget and risks.

2. A concrete factorized experiment comparing baseline, plastic-only, adapter-only, evolution-only and combined training under matched total costs.

3. A promotion and rollback protocol with measures for retention, future learning, perturbation tolerance and external utility.

## Decisive tests and objections to prioritize

1. Can optimizing perturbation robustness cause stagnant but stable behavior?

2. When does low-rank consolidation overwrite old knowledge despite small trainable parameter count?

3. Does additional evolutionary population compute fully explain apparent superiority?

## Related investigations

Other researchers in the same campaign are investigating **R04, R05, R07, R10**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/adaptive-plasticity-and-guardrails.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E003-feedback-adapters.md
- https://arxiv.org/abs/2501.00663

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r06-evolution-consolidation** from latest main.
- Own only **research/findings/R06-evolution-consolidation/** and optional new **prototypes/research-r06-evolution-consolidation/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R06] Evolution, LoRA and durable consolidation**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
