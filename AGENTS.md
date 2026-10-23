# Parallel Research Agents — Minimal Operating Guide

This repo is a **research commons**, not a software delivery organization. The purpose of agents is to expand the idea space, attack assumptions, and generate *testable* knowledge.

## Invariants worth preserving

1. The central proposal is **neural-state evolution without requiring intermediate language-token generation**. Do not silently substitute text-based agents or ordinary chain-of-thought.
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
