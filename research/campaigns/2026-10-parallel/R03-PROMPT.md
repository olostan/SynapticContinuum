# R03 — Communication as live neural activity

**Independent research assignment / separate ChatGPT conversation.**

## Your mission

You are an independent principal AI research scientist and technically critical systems engineer investigating SynapticContinuum. Investigate communication when input, output, feedback and internal activity are asynchronous events acting on a common evolving substrate—not separate prompts and completed responses.

Repository: https://github.com/olostan/SynapticContinuum

**First read** the current README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md and AGENTS.md; then read the shared campaign [protocol](COMMON.md), [track map](README.md), and the exact references listed below. Read the other track titles to understand adjacent work. Never presume their PRs have already been published.

## Specific investigation agenda

1. Formalize an event containing timestamp, source/provenance, modality, payload, event identity and optional causal predecessor; avoid conflating imagined contents, observed contents, attempted action and delivered action.

2. Contrast dedicated communication region, distributed latent observer, global workspace/synchrony and learned output ports. For each specify possible supervision and how the region triggers output without driving all cognition through vocabulary sampling.

3. Analyze how an internally initiated outgoing event feeds back as a copy of the intended action. Investigate dropped/truncated output, interrupted speech, duplicate emissions and actual delivery acknowledgments.

4. Explore prefix streaming with varying pause lengths: 'What is the ... capital of ... France'. Separate predictive work done during silence from the semantic information carried by deliberate hesitations.

5. Propose a progression from a single HELLO output channel to learned H-E-L-L-O timed emissions, then to simultaneous listening/speaking without collapsing into a conventional next-token inner loop.

## Expected research deliverables

1. research/findings/R03-streaming-communication/REPORT.md describing precise ports, event timing and competition/cooperation among neural regions.

2. At least two implementable communication mechanisms with pseudocode and an honest comparison to conventional streaming LMs.

3. A falsifiable experiment suite: silence, partial input, interruption, output misdelivery, overlapping events and refractory behavior.

## Decisive tests and objections to prioritize

1. Can outgoing action activity be remembered without believing the physical output was delivered?

2. Can a system adapt to a sudden new input while it is already emitting communication?

3. Does full-duplex activation provide an advantage over a strong streaming autoregressive baseline at matched latency and compute?

## Related investigations

Other researchers in the same campaign are investigating **R02, R04, R05, R09**. Use the campaign [index](README.md) to see their assignments. When informative, review actually open peer PRs at https://github.com/olostan/SynapticContinuum/pulls and cite their findings as provisional. Do not wait for these researchers, change their files, or prematurely combine conclusions.

## Existing starting material (verify rather than trust)

- https://github.com/olostan/SynapticContinuum/blob/main/ideas/communication-as-activation.md
- https://github.com/olostan/SynapticContinuum/blob/main/ideas/persistent-state-and-speech.md
- https://github.com/olostan/SynapticContinuum/blob/main/experiments/E004-timed-greeting.md
- https://arxiv.org/abs/2410.00037

## Research quality bar

Do not just restate the vision. Deeply investigate current and historic papers, primary sources, independent reproductions, implementable mathematical mechanisms and counterevidence. Verify bibliographic details and distinguish published claims from your inference. Give at least two competing methods and a strong, simple null model. Explain how each experiment isolates causality, computational cost, data access, and repeated-seed variance. Prescribe no single architecture unless comparisons warrant it.

Every research finding must be labeled appropriately as observed locally, reported in verified literature, hypothesized, speculative or contradicted. State what finding would decisively refute this track's idea. Code or experimental outcomes that were not actually run must not be presented as executed. Do not interpret recurrent complexity or synchrony as evidence of consciousness or intelligence.

## GitHub publishing instructions

- Create branch **research/r03-streaming-communication** from latest main.
- Own only **research/findings/R03-streaming-communication/** and optional new **prototypes/research-r03-streaming-communication/**. The only mandatory file is REPORT.md within that findings folder. Put citations, matrices, negative results, sample code and optional independent notes beside it.
- Do not modify shared README/FOUNDATIONS/ATLAS/RESEARCH_LANDSCAPE/SOURCES/AGENTS, existing ideas, other experiments, other tracks or existing prototype files; propose changes in REPORT.md.
- Commit your artifacts and open **one GitHub PR targeting main** titled **[R03] Communication as live neural activity**. Leave it open; never auto-merge, push to main, or force-push.
- PR body should include major findings, closest prior work, uncertainties, exact paths, tests genuinely executed and 2–4 review questions.
- If GitHub write access is not available, still produce a complete report and say explicitly that no PR was created. Never invent PR URLs.

Finish with the actual PR link if created, strongest novel or non-novel finding, strongest objection, and next decisive experiment.
