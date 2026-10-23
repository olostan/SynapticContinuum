# SynapticContinuum

*A lightweight, parallel research space on persistent neural computation beyond token-by-token generation.*

**Status:** exploration, not a validated architecture · **Initial snapshot:** 2026-10-22 · **Repository:** SynapticContinuum

## North star

> Can a neural system operate as a persistent artificial mind, continuously developing its own internal activity and potentially self-originating new thoughts, with external input and output serving as occasional interactions rather than the purpose or clock of cognition?

**Primary research goal:** explore the possibility of a continuously operating artificial mind with endogenous dynamics, self-reflection, and internally emerging thought-like structures. Optimizing token efficiency, answer accuracy, or hardware throughput is **not** the research objective; these are feasibility constraints or diagnostic comparisons. We do not assume that the resulting activity is conscious, intelligent, or qualitatively free of learned statistical patterns. Those interpretations require operational definitions and evidence.

We are not trying to build another text-based agent loop and call it continuous thought. The central object of study is **latent neural state that changes without generating tokens and without requiring external stimulation**.

## Current research focus (2026-10-22)

The latest discussion extends the original latent-recurrence thesis into a **shared, temporally expressive neural substrate**. Inputs, internal activity, communication output and feedback are interacting neural events; connections may remember earlier activations. Faster plasticity, slower LoRA-style consolidation, evolutionary selection, and an optional conventional-LLM **guardrail** remain separate hypotheses rather than prescribed mechanisms.

**Read [Living Foundations](FOUNDATIONS.md) first** for the current working principles. The original atlas remains a broad hypothesis map, not a frozen architecture. Recent independent papers: [temporal connection memory](ideas/temporal-connection-memory.md), [communication as activation](ideas/communication-as-activation.md), [adaptive plasticity and guardrails](ideas/adaptive-plasticity-and-guardrails.md). Initial experimental entry point: [timed HI → HELLO](experiments/E004-timed-greeting.md). A [runnable supervised toy prototype](prototypes/continuous-greeting/README.md) is available as a baseline, not as validation of the full architecture.

## How to navigate

- **[FOUNDATIONS.md](FOUNDATIONS.md)** — concise current hypotheses and invariants; start here for the newest conceptual synthesis.
- **[ATLAS.md](ATLAS.md)** — the main evolving research map: hypotheses, alternatives, technical constraints, discriminating tests, open tensions, and possible trajectories. Start here for understanding.
- **[AGENTS.md](AGENTS.md)** — short operating guidance and ready-to-use prompts for parallel research agents. Start here when delegating.
- **[SOURCES.md](SOURCES.md)** — annotated research bibliography, with relevance and caveats.
- **[RESEARCH_LANDSCAPE.md](RESEARCH_LANDSCAPE.md)** — independent prior-art comparison, novelty boundaries, competing explanations, citation audit, and discriminating research priorities.
- **[ideas/](ideas/)** — competing architectures; agents can propose contradictory ideas.
- **[experiments/](experiments/)** — executable proposals; no obligation to implement them in order.
- **[notes/](notes/)** — independent agent notes, negative results, rebuttals, surprising observations.
- **[results/](results/)** — machine-readable experiment results, figure metadata, and short summaries; avoid large binary checkpoints in Git.

## The research loop (deliberately light)

1. **Explore**: any agent chooses a question and creates one self-contained note, idea, or experiment proposal on its own branch.
2. **Challenge**: another agent may write a counterargument or contradictory prediction. Do not erase disagreement.
3. **Test**: formulate the smallest experiment that would distinguish competing explanations. Record baselines and negative results.
4. **Synthesize**: occasionally update ATLAS.md to reflect what has changed, linking the original evidence. The atlas is a map, not a gatekeeper.

For now, work directly on `main`: no required PRs or issue tracking. Parallel agents should each write new, uniquely named files to avoid collisions; coordinate before editing shared atlas or bibliography. Branches can be introduced later if needed.

**Writing boundaries**: every agent may add its own files under `notes/`, `ideas/`, or `experiments/`. The integrator is the normal editor of `ATLAS.md` and `SOURCES.md`. Exceptions are fine when no other agent is touching them.

## Suggested parallel starts

- **Scout**: survey recurrent depth, latent reasoning, neural CA, equilibrium networks, dynamic routing, and counterevidence since 2024.
- **Architect**: develop a neuron/region-level update rule that is actually executable without autoregressive decoding.
- **Retrofit investigator**: assess where existing pretrained Transformer blocks can be reused, and which interfaces fail under feedback.
- **Skeptic**: argue why apparently intelligent activity could be mere unstable dynamics; propose discriminating controls.
- **Experimentalist**: design an equal-compute benchmark with non-token latent updates and repeatability.
- **Synthesizer**: reconcile findings *without erasing competing hypotheses*.

See [AGENTS.md](AGENTS.md) for copy-paste prompts.

## First machine and feasibility

Target experiments that can begin on a personal Apple Silicon laptop with about 48 GB unified memory. Prefer tiny synthetic systems and ~0.5–1.7B open-weight models before attempting larger runs. We should benchmark memory, speed, training support, and actual backend feature access before choosing MLX vs PyTorch/MPS. This is a feasibility constraint, not a prescribed framework.

## What counts as progress?

- A falsifiable hypothesis with a clear prediction.
- A faithful reproduction or refutation of a paper's central result.
- A surprising **negative** finding that closes an unproductive branch.
- An implementation that actually updates a persistent hidden state *without emitting an intermediate vocabulary token*.
- A controlled task where more internal computation increases accuracy under matched budgets.
- A strong alternative explanation, supported by an experiment.

**Not progress by itself**: visually exciting activation patterns, output fluency, mere repeated LLM calls, or unsupported analogies to biological awareness.

## Publication stance

This is a **public** exploratory research repository. Do not commit private notes, credentials, copyrighted datasets, restricted checkpoints, or findings presented as verified without evidence. Apache-2.0 is the repository license; external models, papers, and data retain their own licenses.
