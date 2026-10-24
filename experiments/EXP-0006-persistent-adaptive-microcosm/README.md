# EXP-0006 — Persistent Adaptive Microcosm

**Design proposal — NOT RUN.** This experiment is about the **student's evolving internal machinery**, NOT developing a clever mini-game, optimizing word predictions, watching attractive dynamical patterns, or evaluating an LLM's ability to answer questions.

**Central research question:** Can a bounded, persistent neural student learn to maintain, revise, extend and causally exploit internal relationships over time, with independent experience and occasional externally validated teaching, in a way not adequately explained by simpler memory systems / recurrent world models / extra compute?

### What is observed
A sequence of **the same student's** learning states: before learning, during training, across silent gaps, after interruption and restoration, before/after external teacher signals, when the teacher is removed, as rules and object sets change. Only *teacher-free held-out performance and interventions* can support positive claims. Retained activity or successful checkpointing alone is not cognition.

### Design package
- [SPEC.md](SPEC.md): hypotheses, null alternatives, controls, falsifiers and acceptance.
- [WORLD.md](WORLD.md): tiny generative causal world, independent truth and partial observations.
- [STUDENT.md](STUDENT.md): candidate continuous students and strong conventional baselines; reused C++ only as validated machinery.
- [TEACHER.md](TEACHER.md): local Ollama teacher as sparse, structured, validated feedback with paused simulated time and hard information boundaries.
- [MEASUREMENT.md](MEASUREMENT.md): longitudinal learning trajectories, all interruption types, parameter screens and causal interventions.
- [SCALING.md](SCALING.md): necessary evidence to attempt progressively more complex semantics or connect pretrained perceptual encoders.
- [manifest.yaml](manifest.yaml): explicit experimental and resource matrix.
- [WORKPACKAGES.md](WORKPACKAGES.md) and [PROMPT.md](PROMPT.md): bounded sequential implementation under independent review.
- [PRIOR_ART.md](PRIOR_ART.md): what earlier researchers already established.
- [REPORT.md](REPORT.md): **NOT RUN** until empirical evidence exists.
- [REVIEW.md](REVIEW.md): adversarial questions before approval.

The laborant is **not authorized** to run an implementation campaign from this design branch without a design GO and a separately approved first work package. Source of truth: ../../EXPERIMENTATION.md and ../../FOUNDATIONS.md.
