# R09 — Controlled greeting prototype experiments

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Audit and, where reproducibly possible, extend the toy HI -> HELLO code into a meaningful controlled research baseline. Do not pretend this demonstration establishes general communication, continuous learning or consciousness.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Inspect prototypes/continuous-greeting/demo.py, its training code and metrics. Run as provided if execution environment allows; verify single seed claims and investigate reproducibility and hidden assumptions.

2. Examine whether the evaluation/printed communication probabilities use the same outgoing event feedback as the claimed inference flow; if not, create a corrected *separate* prototype and document the effect.

3. Test multiple seeds, held-out pause lengths, H alone, reversed input, silence, irrelevant symbols, long idle periods, interruptions, repeated outputs and deliberate external delivery loss.

4. Compare with trivial event-pattern detection, feed-forward network, timestamp-aware RNN and compact multiscale trace model with matched compute and parameter budget.

5. Design a later experiment emitting H,E,L,L,O as separate events, clearly distinguishing direct supervised output labels from learned communication semantics, and preserving incoming/outgoing concurrent signals.

## Expected research deliverables

1. research/findings/R09-greeting-prototype/REPORT.md: baseline audit, tests executed, honest results and failures.

2. When executable: new code and regression tests only under prototypes/research-r09-greeting-prototype/, including exact commands and deterministic seeds.

3. Recommendations on which experimental measures would actually distinguish the architecture from a simple classifier.

## Decisive tests and objections to prioritize

1. Output event count should be exactly one for valid greetings and zero for negative cases, not simply a high late sigmoid.

2. Check generalization to unseen timing and input orders.

3. Audit whether output feedback meaningfully affects neural state or is a no-op under current measurement code.

## Related investigations

Other researchers in the same campaign are investigating **R02, R03, R04, R08**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/prototypes/continuous-greeting/demo.py
- https://github.com/olostan/SynapticContinuum/blob/main/prototypes/continuous-greeting/README.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E004-timed-greeting.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E005-temporal-memory-ablation.md

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r09-greeting-prototype** from latest main.
- Own only **research/findings/R09-greeting-prototype/** and optional new **prototypes/research-r09-greeting-prototype/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R09] Controlled greeting prototype experiments**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
