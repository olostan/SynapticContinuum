# Parallel Research Agents — Minimal Operating Guide

This repo is a **research commons**, not a software delivery organization. The purpose of agents is to expand the idea space, attack assumptions, and generate *testable* knowledge.

## Research objective and quick orientation for LLM agents (2026-10-23)

**Goal:** investigate whether a persistent neural system can develop **internally initiated, lasting, causally consequential representations or behaviors** between irregular external events. The goal is *not* maximum answer correctness, speed, fluent conversation, or cheap inference. Performance and cost are controls to reject confounding explanations, not a definition of cognition. Neural complexity, spontaneous oscillation, and apparent novelty do **not** establish thought or consciousness.

**Read first:** [FOUNDATIONS.md](FOUNDATIONS.md), then the concise [R01 cross-track summary](https://github.com/olostan/SynapticContinuum/blob/research/r01-literature-novelty/research/findings/R01-literature-novelty/SUMMARY.md) ([full R01 report](https://github.com/olostan/SynapticContinuum/blob/research/r01-literature-novelty/research/findings/R01-literature-novelty/REPORT.md); [open PR](https://github.com/olostan/SynapticContinuum/pull/1)). **Note:** until PR #1 is merged, these links point to its branch, not `main`. R01 findings are provisional and must not dictate conclusions.

For every hypothesis distinguish **(A) prior-art mechanisms** from **(B) the emergent phenomenon under study**. Existing CTM, latent-reasoning, recurrent/continuous-time, memory and plasticity techniques may provide useful mechanisms without having investigated the *same objective*. Do not claim uniqueness merely because a paper optimizes accuracy; equally, do not dismiss a paper's relevant autonomous or self-organizing behavior because it reports accuracy benchmarks.

**Agent discipline:** preserve independent investigation, check original sources, document counterarguments, test simple memory-only/replay/event-driven baselines, use causal interventions on internal state, and report negative findings. For the current ten-track campaign, follow [COMMON.md](research/campaigns/2026-10-parallel/COMMON.md) and [track ownership](research/campaigns/2026-10-parallel/README.md): each track owns its assigned directory and PR; shared foundation changes require a separate coordinated change.

## Latest priority / orientation (2026-10-22)

Read [FOUNDATIONS.md](FOUNDATIONS.md) and the three newer idea papers before assuming that communication is a periodic whole-state snapshot. The current leading hypothesis treats incoming sensory pulses, internal activations, outgoing communication and feedback as events in **one evolving substrate**, with connections responding to historical activity. The original frozen-Transformer/CA proposals remain legitimate alternatives.

Research independently in these lanes: **temporal connection kernels vs state-space memory; live communication/outgoing action copy; delayed eligibility-based reward; LLM guardrail as non-authoritative validator; LoRA/evolutionary consolidation; skeptical controlled baselines**. No implementation is required by this update. Never describe the greeting experiment as verified unless runnable code and rerun evidence appear.

## Invariants worth preserving

1. The central proposal is **persistent neural-state evolution and temporal connection memory without requiring intermediate language-token generation**. Do not silently substitute text-based agents or ordinary chain-of-thought.
2. No default architecture. Keep frozen recurrence, feedback LoRA, dynamic routing, cellular automata, persistent memory, and skeptical alternatives alive until evidence discriminates among them.
3. Separate **published**, **reproduced**, **hypothesized**, and **speculative**. Attach exact URLs and describe the limits of cited work. Never invent paper findings, code behavior, benchmarks, or local measurements.
4. Optimize for insights, not volume. Every contribution should name what existing uncertainty it reduces or what new falsifiable question it opens.
5. Be skeptical of claims about consciousness or “emergence.” Complexity and time-varying activation do not by themselves establish reasoning.
6. On `main`, do not overwrite another agent's drafts. Preferred pattern: one agent, one unique new file. No PRs are required during initial exploration.
7. Never present a conceptual proposal as implemented or working. Code and performance claims require executable evidence.
8. Negative findings and disagreement are first-class contributions. Do not collapse diversity merely because one agent sounds more confident.

## Minimal file contract

Write a markdown note under `notes/YYYY-MM-DD-<agent>-<topic>.md`, or a distinct `ideas/<slug>.md` / `experiments/<slug>.md` when developing an alternative or experiment. Free form is fine, but try to answer:

- **Question / claim**: what specifically is being investigated?
- **Core insight**: one paragraph, without hype.
- **Mechanism**: enough detail to simulate, train, or falsify; diagrams/pseudocode welcome.
- **Closest prior work**: direct links, publication timing, and exact differences.
- **Critical objections and alternative explanations**: genuinely adversarial.
- **Smallest decisive experiment**: baselines, observable metric, expected outcomes under competing hypotheses.
- **Confidence and unknowns**: distinguish assumptions from evidence.
- **Next links**: related repo files and useful follow-up questions.

No mandatory template, labels, issue, owner, priority, or approval. A short insight note is fine when it contains a genuinely new idea.

## Parallelism protocol

- **Independence first:** agents read `README.md`, `ATLAS.md`, `SOURCES.md` and then pursue their assigned angle independently. They must not seek prior consensus.
- **Collision avoidance:** each agent writes only to a unique new file. Only the designated synthesis agent normally edits `ATLAS.md` and `SOURCES.md`.
- **Adversarial pairing:** for strong ideas, run a *builder* and a *skeptic* in parallel. Both create notes; neither can delete the other's view.
- **Synthesis:** occasionally merge results into the atlas by adding “supported,” “contradicted,” or “still open” annotations, linked to source notes. Preserve intellectual history.
- **Experiments:** record implementation commit, environment, model version, seed, evaluation set, compute measure, controls, and negative results. Small results can live in Git; model weights/datasets go to suitable external artifacts.
- **No standing deadlines:** this is exploratory research. Strong evidence should change direction.

## Recommended roles (choose any subset)

### Literature scout
Find closest prior research across recurrence, latent computation, neural CA, asynchronous activation, dynamical systems, and interpretability. Build a novelty matrix: *what exactly is similar and what exactly is missing*. Treat paper abstracts as claims until evaluated. Put findings in one new note.

### Architecture explorer
Invent one or more precise executable state-update mechanisms. Address state tensor shapes, positional encodings, normalization, routing, and trainable interfaces. Compare two alternatives, not just your favorite.

### Skeptic / falsification agent
Attack the strongest thesis. Find controls in which recurrence is equivalent to more compute, context, caching, or repeated calls. Specify *what observation would prove this line of investigation unpromising*.

### Toy-model experimentalist
Propose or build the smallest controlled experiment for one claim. No need for pretrained LLMs if the claim can be tested with a tiny graph dynamical model. Prefer reproducing a baseline first.

### Pretrained-LM retrofit investigator
Inspect viable model architectures and backend layer interfaces for genuine hidden-state looping. Verify, don't assume, specific MLX/PyTorch APIs. Identify where token positions and KV caching obstruct recurrence. Compare adapter/LoRA approaches.

### Dynamics specialist
Focus on Jacobian spectra, contraction/expansion, attractors, bifurcations, state rank, time constants, perturbation recovery, and numerical integration. Tie mathematical observations to useful task outcomes.

### Synthesizer
Read new notes, contrast competing claims, revise ATLAS.md where justified, and add a short changelog entry with references. Do not declare a winner just to create a clean narrative.

## Copy-paste master prompt for a multi-agent host (Antigravity, Cursor, or another system)

> You are running an **open-ended multi-agent research laboratory**, NOT implementing a predetermined product roadmap. Research question: can pretrained networks or novel small neural systems support persistent, dynamically routed latent activation whose evolution does not require intermediate output tokens, while communication is only an optional readout?
>
> Read `README.md`, `ATLAS.md`, `SOURCES.md`, and `AGENTS.md`. Independently launch these investigations if your environment supports parallel agents: (1) related-work/novelty scout, (2) pretrained-Transformer loop+LoRA retrofit researcher, (3) neural cellular-automaton / dynamic-region architect, (4) skeptic/falsification specialist, (5) benchmark/experiment designer. Agents must **not** converge early or rewrite each other's findings.
>
> Each agent writes one self-contained, evidence-linked note to a **unique** `notes/` filename or owns a new idea/experiment file; avoid simultaneous edits to central files. When research is complete, have an independent synthesizer review all results, identify contradictions, propose no more than 3 decisive next experiments, and *selectively* update `ATLAS.md` with provenance. No bureaucracy, sprint tickets, elaborate gates, or obligatory implementation. When the owner has authorized work in this repo, direct commits to `main` are allowed; never force-push or overwrite unrelated work. Coordinate central-document edits, and preserve each research contribution. Distinguish verified published claims from inferences and speculation. Report concrete discoveries and failures, not status fluff.

## Copy-paste adversarial follow-up

> Independently audit the most promising new idea from this research repo. Do not assume the core thesis is correct. First reconstruct it precisely and identify its closest existing published equivalent. Then give the strongest theoretical objection, the strongest implementation objection, and a carefully compute-matched experiment that would discriminate the claimed novel benefit from normal recurrence, KV memory, extra decoder steps, or random state evolution. Write a unique note. Do not modify the idea author's file.

## Copy-paste experiment planning follow-up

> Choose a narrow, falsifiable hypothesis from `ATLAS.md`. Design an experiment runnable on a ~48 GB Apple Silicon machine, favoring tiny synthetic tasks or a sub-2B open-weight model. Specify tensor shapes, forward/update pseudocode that **does not sample vocabulary tokens during internal transitions**, baseline conditions, matched compute, seeds, metrics, expected success/failure patterns, data contamination risks, and 1–3 day practical scope. Do not execute before verifying dependencies and hardware assumptions. Write `experiments/<new-name>.md` and a companion `notes/` note if needed.

## Copy-paste synthesis follow-up

> Review all research files modified since the last synthesis. Identify: new evidence, unresolved contradictions, abandoned hypotheses, missing baselines, and novel cross-connections. Revise `ATLAS.md` sparingly; cite exact note paths and sources. Keep independent alternatives visible. Produce a short synthesis note describing what changed and why, plus the 2–3 highest-information unanswered questions. Avoid project-management artifacts.

## Quick feedback checklist for a proposed contribution

- Is it genuinely about neural/latent computation, not merely orchestrating prompts?
- Is the difference from existing research stated precisely?
- Is there a falsifiable prediction?
- Are matched-compute baselines and a trivial null model considered?
- Does the idea survive skeptical scrutiny at the level of tensor/state semantics?
- Is it understandable and reproducible by a second independent agent?

That's enough process. Research quality should come from evidence and critical discussion, not workflow controls.


## Executable simulation laboratories (EXP-0005+): research roles

The open-ended research commons above stays non-hierarchical. For **resource-intensive executable experiments**, use the scoped three-role supervision protocol: **Research Director** (repo owner: decides vision, approvals and merges), **Principal Researcher** (designs scientific hypotheses, acceptance, independent audits and experiment direction), and **Linux Research Laborant** (smaller implementation model: one approved bounded WP, native code/tests/raw measured evidence, no self-validation of scientific conclusions or silent semantics changes). The experiment-specific design is in [EXP-0005](experiments/EXP-0005-scientific-simulation-substrates/SPEC.md), with [ordered WPs](experiments/EXP-0005-scientific-simulation-substrates/WORKPACKAGES.md), [laborant prompt](experiments/EXP-0005-scientific-simulation-substrates/LINUX-LABORANT-PROMPT.md) and [independent research prompts](experiments/EXP-0005-scientific-simulation-substrates/RESEARCH-AGENTS-PROMPTS.md). This does not grant blanket execution permission or replace [EXPERIMENTATION.md](EXPERIMENTATION.md). Prefer native independent substrate implementations; inherit reviewed fixture/provenance knowledge, not EXP-0004 scheduler code by default. Design PRs remain NOT RUN until implementation evidence exists.

## New architecture-first research design (EXP-0006, 2026-10-24)

The proposed [EXP-0006 Persistent Adaptive Microcosm](experiments/EXP-0006-persistent-adaptive-microcosm/README.md) tests **continuity, self-development and causal utility of persistent neural representations**; its tiny world and sparse Ollama teacher are instruments, not goals. Read [SPEC](experiments/EXP-0006-persistent-adaptive-microcosm/SPEC.md), [interruption/learning protocol](experiments/EXP-0006-persistent-adaptive-microcosm/MEASUREMENT.md), and [growth criteria](experiments/EXP-0006-persistent-adaptive-microcosm/SCALING.md). It is a DESIGN ONLY/NOT RUN proposal on a separate branch; do not conflate it with E006 or EXP-0005 and do not infer empirical progress. World truth is authoritative; LLM teaching is optional and bounded; teacher-free held-out effects versus serious memory/recurrent baselines are required. Historical EXP-0001–0005 evidence remains unchanged.
