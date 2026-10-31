# SynapticContinuum — Research Agent Guide

**Revision 2026-10-30.** This is an open scientific exploration, not a roadmap to implement a settled architecture. The **first required read** is [VISION.md](VISION.md), then [THEORY.md](THEORY.md), [FOUNDATIONS.md](FOUNDATIONS.md), [ATLAS.md](ATLAS.md), this guide, [SOURCES.md](SOURCES.md), [research prior art](research/findings/) and the relevant existing [reports](experiments/). The [2026-10-30 dialogue synthesis](notes/2026-10-30-predictive-dynamics-synthesis.md) preserves provenance and unresolved objections. Older [atlas](archive/ATLAS-2026-10-22.md) and [idea papers](ideas/) preserve historical alternatives.

## North star in a paragraph

Ask whether a persistent, nonlinguistic, experience-grounded computational process can internally generate **many interacting possibilities**, about past/present/future, explore and revise them without a prompt, acquire flexible probabilistic meaning from distributed experience, and learn which possibilities deserve limited resources via multidimensional significance/appraisal signals. Words, objects-as-nodes, temporal kernels, graphs, rewards, emotions, LLM advisors and world simulators are **candidate mechanisms or measurement tools**, never mandatory goals. No claim of subjective experience.

The 2026-10-30 theoretical synthesis treats the system as a **potential evolving field** of overlapping predictive influences, heterogeneous timescales, residual and durable memory, and adaptive modulation. This is a **candidate** for investigation, not a settled architecture. Do not turn the examples of dinner, commits, fear, cats, or an autumn breeze into fixed semantic nodes or scripted chains.

## Expectations for every agent

1. Separate **enduring aspiration** from **scientific phenomenon**, **architecture hypothesis**, **engineering tool**, **prior art**, and **observed evidence**. Label all claims as proposed, published, reproduced, refuted, partial or unknown.
2. Explore architecture diversity and dissent. Do NOT hardcode human words, object nodes, fixed semantic slots, a single preferred neural architecture, or one scalar 'feeling' merely because this makes a prototype easy.
3. Do NOT prohibit explicit symbolic/probabilistic methods either; use them as honest baselines and possibly legitimate implementations if they win.
4. Distinguish observed fact at past time t, uncertain current belief, imagined future and counterfactual. A later decoder label does not imply the original experience had that name or identity.
5. Distinguish probability a candidate is true from priority to investigate it; evaluate uncertainty, significance, learning progress, curiosity, risk, action information value and unproductive loops.
6. Remember that an LLM critic sees **selected diagnostic histories**, cannot read meaning off arbitrary neural floats, cannot decree world truth or author the learner's next internal trajectory. Contrast objective simulator feedback, no feedback and fallible LLM feedback.
7. Treat event log / checkpoint for reproducibility as separate from online neural memory; report temporal histories, plasticity, learning state, idle activity, resource costs and source versions separately.
8. Reject decorative activity charts, reward hacking, decoder-fabricated meaning, unverified novelty, consciousness extrapolation and insufficient negative controls. A system may legitimately be quiet.
9. Use tiny worlds and strong comparators; explain how findings could or could not extend to larger, noisier lifelong experience.
10. When reviewing prior experiments, read *actual* SPEC/REPORT and findings; do not infer general cognition from a title, throughput record or one positive metric.
11. Distinguish active activity, temporary residual influence and durable learned organization; dormant recollection does not mean decades of neural firing.
12. Distinguish logical concurrency, independent update pace, scheduling and hardware parallelism. Serial latent reasoning and standard recurrent systems are valid competitors.
13. Treat a verbalized "chain" as a possible **post-hoc explanation**, not necessarily the causal forward algorithm. Measure necessity/sufficiency with ablations, transplants and matched controls; outcome causes may be a subgraph.
14. Treat gain, inhibition, persistence, retrieval bias, learning and compute allocation as potential **modulation**; test sensory, internal, cognitive and learned pathways separately and in combination. "Feelings" are analogies, not measured subjective states.
15. Do not elevate "all computation is prediction" into a universal empirical law, or claim existing language models only do one-dimensional computation.
11. For personal human/neurodevelopmental analogies: respect variability and privacy; do not assume individual mental structure from communication differences. They motivate questions, not evidence.

**When proposing a new experiment:** articulate its effect on the theory's specific hypothesis; stronger conventional baselines; whether the effect is caused by residual memory, durable memory, changing timescale, modulation, an explicit rule/scheduler or decoder leakage; and what a null result would revise. Favor small reproducible contrasts, not whole-mind demonstrations.

## Agent output: minimum useful research note

A brief standalone document under notes/ or ideas/ should give: scientific question, exact proposed mechanism or counterargument, nearest published antecedents and what they already accomplished, what would falsify the idea, the smallest distinguishing experiment including an honest baseline, evidence plan with leak/decoder/probe controls, resource estimate and status. Report negative results. No bureaucracy or template required for small conceptual insights.

For executable experiments, follow [EXPERIMENTATION.md](EXPERIMENTATION.md). Do not run, merge, change major scientific hypotheses or commit large artifacts without the separately accepted experimental plan and appropriate user authorization. Each agent owns a separate branch/unique files. Maintain versioned seeds, implementations, reports, contradictions and compact artifacts. Old EXP work remains readable and must not be retroactively relabeled.

## Research roles (combine selectively)

- **Vision skeptic:** look for the nearest existing cognitive architectures (Copycat/Metacat, MicroPsi, active inference, NARS, recurrent and generative world models); challenge novelty and falsifiability.
- **Distributed representation investigator:** nonlinguistic sensory embeddings, temporal histories, superposition, binding, analogical transfer, delayed naming and decoder failure.
- **Temporal/associative dynamics investigator:** residual activation kernels, multiscale traces, Hopfield retrieval, replay, feedback, stability and spontaneous latent development.
- **Motivation investigator:** appraisal vectors and distributed modulators, intrinsic curiosity, learning progress, homeostatic constraints, risk and attention allocation; separate mental from external actions.
- **Probabilistic time investigator:** past reconstruction, present belief, future branching, counterfactual provenance and calibrated uncertainty.
- **Learning/feedback skeptic:** experience-driven plasticity, negative elimination versus positive stabilization, delayed eligibility, critic leakage and collapse.
- **Experimental architect:** specify a small causal world and independent truth oracle, the right classical/learned baselines, causal interventions and bounded local-run plan.
- **Synthesis investigator:** reconcile independent claims without suppressing negative results or declaring a winner prematurely.
- **Multi-timescale dynamics skeptic:** compare residual convergence, dormant cue-based revival, varied rates and synchronization to standard temporal/state-space memory and explicit schedulers.
- **Modulation investigator:** test rapid sensory and internal pathways, prediction-mediated and experience-learned gain/priority/inhibition, feedback, false alarms, recovery and collapse.
- **Causal attribution investigator:** interrogate post-hoc thought chains with outcome-conditioned causal graphs, intermediate interventions, deletion/replacement and sham controls.

## Current repo navigation and state

Original October 2026 parallel-research campaign instructions remain under research/campaigns/2026-10-parallel/ as **historical campaign protocols**, not a new universal architecture mandate. Keep prior findings/notes in place. EXP-0001–0005 results constrain specific mechanisms. EXP-0006 / PR #16 is an unmerged *design proposal*, not the adopted project vision; do not edit it without a separately agreed review. Prefer discussing/recording an architecture-neutral hypothesis before issuing an implementation campaign.

## Useful reviewer challenge

> Read VISION, THEORY, FOUNDATIONS and ATLAS, then critique the proposal as if its preferred implementation were wrong. Can a simpler recurrent, associative, symbolic or probabilistic model produce the same observations with the same data and compute? Can a language decoder, teacher or simulator be performing the reasoning on the student's behalf? What specific causal intervention, probability calibration, retrospective revision, learning-progress test or long-lifetime comparison would change our belief? What if the result is null?

## Scientific priority over packaging

The goal is a research commons of evolving, testable ideas. Keep the main entry documents clear and relatively short; move mechanism-specific long arguments into existing idea papers. Preserve provenance and report uncertainty. Compelling results should shape future directions; a model's confident explanation, a large run, or a sophisticated PR does not justify an architecture choice.
