# EXP-0006 — Principal-to-laborant handoff (design-only)

You are a bounded implementation laborant for SynapticContinuum. Current assignment is **none until Research Director approves EXP-0006 design**. Do not execute any WP simply because this file exists.

After approved: begin **WP-00 deterministic world and independent oracle only**. First respond with a PRE-FLIGHT PLAN, not a giant implementation:
1. Read AGENTS.md, FOUNDATIONS.md, EXPERIMENTATION.md, experiments/EXP-0006-persistent-adaptive-microcosm/{SPEC.md,WORLD.md,STUDENT.md,TEACHER.md,MEASUREMENT.md,WORKPACKAGES.md,manifest.yaml,PRIOR_ART.md,REPORT.md}.
2. Inspect selected reviewed base commit and Linux actual CPU/RAM/disk/Python/compiler, and branch from updated main. Do not edit old EXP-0001–0005. Only own experiments/EXP-0006... source, tests, fixtures and run summaries.
3. Produce a precise world state schema, minimum 3 hand-worked transition oracles, independent observation/leakage tests, split recipe with disjoint causal templates, safe pilot command, proposed files and staged commits. Ask review where rules or units are ambiguous; DO NOT guess and invent results.
4. Implement a tiny Python stdlib truth simulator first, no neural student, no Ollama, no render/UI dependencies, no hyperparameter sweeps. Require hand correctness for nested carry, hidden observation, and changed order. If a baseline cannot recover simple relationship, debug world before claiming novel dynamics.
5. Open a WP-00 PR with tests, source + config SHA256, precise commands, failures and limitations. No merge; request Principal Researcher scientific review.
6. Later assigned WPs each have a separate independent PR and approved plan. Do not use shared code as both reference oracle and student implementation. Student and teacher designs are NOT implementation orders at WP-00.
7. Generated data, checkpoints, binaries and logs stay outside Git with manifest hashes. The Linux computer has ~16GB RAM, not 32GB; student and local Ollama should be sequential until actual peak RSS proves concurrent is safe. No unapproved cloud calls, package installs, hour-long simulations or open-ended self-improvement loops.

Scientific focus: do not optimize for producing language or pretty animations. Every result must say what it demonstrates about persistent self-developing state, what simpler alternatives explain, and whether same mechanism could plausibly extend beyond this tiny world. Uncertainty/negative results are accepted. The LLM teacher never decides ground truth or writes arbitrary weights/code.
