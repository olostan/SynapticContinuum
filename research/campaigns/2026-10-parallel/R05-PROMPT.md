# R05 — Frozen LLM as validator, not teacher

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Explore how an independent frozen conventional LLM can detect semantic regression and suggest challenges without forcing the new system to imitate the LLM or imposing token-based thinking.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Define what can be observed continuously: outgoing communication events, structured claims, actions, environment predictions, outcome observations and limited streaming projections, without requiring whole-network snapshots.

2. Design guardrail messages with uncertainty and abstention: suspected regression, challenge, inconclusive, independently confirmed error, and optional recommended test. Avoid scalar teacher reward based solely on similarity.

3. Review limitations and bias in LLM-as-a-judge, constitutional AI / RLAIF, reward modeling, preference hacking, self-evaluation loops and independence failures.

4. Explore false-positive regression labels when the experimental system is correct but novel, and how an external oracle should overrule a conventional LLM.

5. Test when guardrail calls are worth cost: event-triggered validation, sampled checks, anomaly detection and holdout competence probes.

## Expected research deliverables

1. research/findings/R05-llm-guardrails/REPORT.md: live protocol, threat model, evidence hierarchy and LLM usage policy.

2. A benchmark measuring semantic regression detection precision/recall and harm from false interventions.

3. An operational guardrail decision table distinguishing observe, challenge, quarantine, reject and no-op.

## Decisive tests and objections to prioritize

1. Construct intentionally novel correct solutions disfavored by an LLM judge.

2. Demonstrate failure when judge output is treated as verified truth without independent tests.

3. Compare fixed tests, one LLM judge and multiple judges at equal evaluation budget.

## Related investigations

Other researchers in the same campaign are investigating **R03, R04, R06, R08**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/adaptive-plasticity-and-guardrails.md
- https://github.com/olostan/SynapticContinuum/blob/main/ideas/communication-as-activation.md
- https://arxiv.org/abs/2212.08073

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r05-llm-guardrails** from latest main.
- Own only **research/findings/R05-llm-guardrails/** and optional new **prototypes/research-r05-llm-guardrails/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R05] Frozen LLM as validator, not teacher**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
