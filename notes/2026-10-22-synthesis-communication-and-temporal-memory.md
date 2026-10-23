# Research synthesis — Shared activations, temporal connections, and guarded adaptation

**2026-10-22 · Discussion synthesis, not experiment results**

## What changed

The original thesis was persistent latent computation instead of token-driven inference. The latest discussion sharpens it in four ways:

1. **The same event substrate** should receive sensory activity and internally propagated activity; outgoing communication is an actuation event within it, not the objective of every forward pass.
2. **Temporal response at connections** is central: a connection transforms histories of activity, potentially with different response delays. Connection-local state and independently trainable kernel taps must not be conflated.
3. **Learning can occur while processing** through short-lived plastic state, with durable LoRA-like consolidation and slower topology/learning-rule changes investigated separately.
4. **An external conventional LLM is a guardrail, not a teacher**: it can flag suspected regressions in emitted behavior while externally verifiable outcomes remain the stronger criterion. It should not require global snapshots or teach the system to mimic its own thoughts.

## Precise central hypothesis

*A persistent neural dynamical system with temporally expressive connections can integrate external input, internal activation, communication, plasticity and delayed feedback as streams of interacting events. Selected slow adaptation and evolutionary mechanisms may improve capability while guarding against catastrophic decay; language decoding need not drive internal updates.*

This is **hypothesized**, not established by existing papers or local experiments.

## Deliberately unresolved

- Do shared temporal traces capture the benefit at lower complexity than edge-specific history kernels?
- How is useful state evolution distinguished from elaborate noise when nothing happens outside the system?
- Can action-copy feedback provide internal communication memory without generating self-excitation loops?
- How can delayed validation target relevant connections after thousands of neural updates?
- Does evolving while idle offer value over retaining state and sleeping?
- What external observations or verifiers are available when a conventional LLM cannot reliably judge correctness?
- When should the architecture use pretrained LLM weights at all, versus start from a novel small substrate?

## Recommended parallel tasks

Independent teams can investigate temporal-kernel ablations, live communication ports, event-attributed eligibility feedback, robust evolutionary selection, and strongest simpler-model counterexamples. Reconcile only after small falsifiable experiments.

## Provenance

This note records an exploratory design conversation and points to [Foundations](../FOUNDATIONS.md), [Temporal memory](../ideas/temporal-connection-memory.md), [Communication](../ideas/communication-as-activation.md), [Adaptation](../ideas/adaptive-plasticity-and-guardrails.md) and [Experiments](../experiments/README.md). No paper result or prior prototype run is claimed as reproduced by this repository.
