# SynapticContinuum — Living Foundations

**Status:** research hypotheses, not an implemented architecture. **Last synthesis:** 2026-10-22.

> Thinking changes state. Experience may change connections. Feedback may change behavior. Evolution may change organization. Input and output are events in the same evolving neural dynamics—not the boundaries of an inference call.

This is a research question, **not** a claim about achieved intelligence or consciousness. It is possible that simpler recurrent/state-space architectures or ordinary stream processing outperform it.

## Research intent — artificial mind, not faster inference

The primary objective is to investigate the *possibility* of a constantly operating artificial mind: an endogenous neural process that may sustain internal activity, self-monitor or revisit its own internal states, form associations, and potentially produce novel thought-like trajectories in the absence of new external prompts. Input and output are peripheral interactions, not the system's principal purpose, update clock, or primary reward source. External communication is useful for observing and probing the system, but conversational fluency is not the definition of success.

This is an exploration, **not a claim that such a mind, genuine self-reflection, consciousness, or thinking beyond statistical learning has been achieved**. The phrase “not pattern matching like normal inference” should be treated as a challenge to investigate: learned neural models inherently use learned statistical structure; a researchable distinction is whether internally generated state trajectories yield new, causally consequential, persistent representations or hypotheses without being directly prompted, rather than simply replaying learned associations.

Efficiency, FLOPs, matched compute and sleeping baselines remain crucial *controls* for causal attribution and practical feasibility, **not optimization goals or go/no-go requirements**. Even an inefficient prototype is scientifically interesting if its endogenous dynamics reveal a genuinely new measurable phenomenon.

### Specific questions arising from that goal

- What maintains endogenous activity when no new sensory event or reward is supplied?
- Can the system create and revisit internal candidate representations without a prompt, while separating self-generated content from observations?
- What operational tests distinguish self-reflection from recurrent noise, attractor cycles, replay and an externally programmed self-prompt loop?
- Can unexpected internal trajectories causally alter later learning, anticipation or action on withheld probes?
- What keeps long-lived dynamics neither trivial nor destructive, without forcing them toward task completion?

## Pretrained weights as a seed, not an inference engine

**Design intent (2026-10-23):** existing pretrained models are candidates for initializing rich representations, associations, and world knowledge. They are **not** intended to remain the governing autoregressive text-generation mechanism. A pretrained model's learned structure may provide initial weights or a source of representation transfer; whether that structure survives a fundamentally different recurrence and learning regime is unknown and must be tested.

The proposed *operating system* is a persistent, temporally structured neural dynamical process: activations influence later activations through histories, delays, state-dependent couplings and possibly local plasticity. There may be autonomous activity with no external input and no commitment to producing output. Communication is an optional consequence of internal state, not an objective enforced at each step.

**Learning and selection are open research questions rather than supervised response correctness.** A candidate substrate might adapt through endogenous prediction, consistency, self-modeling, environmental feedback, local homeostasis, or longer-term selection, with competing mechanisms tested separately. Do not silently replace the research goal with RLHF, next-token accuracy, conversational helpfulness, fast responses, or agreement with a frozen language model. Slow, irregular, incomplete or less structured outward behavior is compatible with the research intent; it is not itself evidence of mental activity.

**Necessary distinction:** pretrained weights cannot be assumed to encode portable, accessible knowledge independent of their original architecture, normalization, tokenization and training objective. Simply running an LLM's weights recurrently may produce collapse or meaningless dynamics. Research should compare (a) native pretrained weights with altered recurrence; (b) pretrained features transferred through learned interfaces into a separately trained dynamical substrate; and (c) dynamical systems trained from scratch. Avoid presenting a technical method as settled prematurely.

**Evaluation should be epistemic, not conversational:** look for causal continuity of endogenous state, durable internally initiated representations, reproducible effects of self-revisitation, adaptation after environmental change, and robust distinctions between internal conjecture and observed reality. Use controls for replay, random recurrence, trivial attractors and externally authored prompts. No measurement can automatically certify a subjective mind.

## Founding propositions

1. **Continuous core:** a mutable neural state persists while external observations arrive at irregular times and while nothing arrives. Digital implementations have discrete update steps; 'continuous' here means that updates aren't necessarily driven by vocabulary tokens.
2. **Common event semantics:** sensory input, internally propagated signals, feedback, and outgoing motor/communication commands affect the same dynamical substrate. Modality-specific encoders and actuators still exist; source labels distinguish observation from imagination and action.
3. **Time-resolved connections:** the influence of neuron/region j on i depends on a history of j's activity, not only its instantaneous value. Delay kernels, leaky memory traces and connection-local state are candidates, not mandatory implementations.
4. **Output remains internal:** outgoing activity is part of the dynamics; a communication event can also be externally rendered. Internal intent is not proof of successful external transmission; observed delivery is a separate event.
5. **Learning is multi-timescale:** activity changes rapidly, transient synaptic state changes more slowly, durable weights/adapters change more slowly still, and connectivity/evolution may change at a longer cadence. Those are architectural hypotheses, not fixed biological times.
6. **Feedback is mostly protective, not prescriptive:** a conventional frozen LLM may *flag* semantic regressions; independently checkable outcomes have higher evidential status. We do not optimize for imitation of the reference LLM.
7. **Productive computation is an empirical question:** nonzero and complex activity is not equivalent to useful reasoning. Equal-compute and sleeping-state baselines are mandatory.
8. **Parallel investigation:** no single architecture wins by declaration; agents can challenge any idea and publish negative results.

## An abstract model

Represent live state as \`S(t) = (h(t), z(t), p(t), W_s, G(t))\`:
- \`h\`: active units/regions;
- \`z\`: short- and long-timescale traces of past activity;
- \`p\`: optional fast plastic state;
- \`W_s\`: relatively stable learned structure, perhaps including low-rank adapters;
- \`G\`: connectivity / routing; may be fixed initially.

Between events, \`dh/dt = F(h,z,p,W_s,G)\`; traces obey decay-and-drive dynamics. An arriving event \`e=(time,source,payload)\` induces an injection \`h^+ = h^- + I(e,h^-)\`. An outgoing communication event is generated from activity, rendered by an actuator, and recorded as **internal action information**. Independent outcome observation may arrive later.

This does **not** require continuous gradient descent. Learnable parameters, temporarily plastic connection states and active neural state must be represented and measured separately.

## Working research questions

- Can a trainable temporal kernel over previous activations outperform a simpler recurrent state at matched parameters, FLOPs, and wall time?
- Does idle-time evolution create useful state changes, or could the system simply preserve its state and sleep?
- Can an output event be produced by thresholded/gated communication activity **without** autoregressive inner token sampling?
- Can delayed feedback target the responsible activity through eligibility traces, without needing full-state snapshots?
- Can a fixed LLM guardrail detect semantic regression without penalizing valuable disagreement?
- Can slow LoRA-like consolidation and evolutionary selection prevent forgetting *without* freezing learning capacity?
- What is the smallest falsifiable experiment, including null cases and negative examples?

## Design papers (independent, not sequential)

- [Temporal connection memory](ideas/temporal-connection-memory.md)
- [Communication as activation](ideas/communication-as-activation.md)
- [Adaptive plasticity and guarded evolution](ideas/adaptive-plasticity-and-guardrails.md)
- [Pretrained retrofit](ideas/pretrained-retrofit.md)
- [Neural cellular automata](ideas/latent-cellular-automata.md)
- [Dynamic routing](ideas/dynamic-routing.md)

## Experiments and baseline

- [E004 Timed greeting and silence](experiments/E004-timed-greeting.md)
- [E005 Temporal connection ablation](experiments/E005-temporal-memory-ablation.md)
- [E006 Live delayed feedback](experiments/E006-live-feedback.md)
- Existing [E001–E003](experiments/README.md) remain viable competing lines.

**Research restraint:** nothing about receiving HI and emitting HELLO demonstrates general linguistic competence. The goal is a measurable, correctly controlled communication *mechanism*.

## Change without bureaucracy

Any agent adds a unique note, idea, code sample, or experiment file. Synthesis changes FOUNDATIONS/ATLAS only when evidence or a clarified conceptual distinction merits it. Record counterclaims alongside claims. Don't demand PRs or issue templates while the lab is exploratory.

## Related foundations

See [SOURCES.md](SOURCES.md) for annotated literature on recurrent depth, CTM, learned temporal dynamics, eligibility traces, online plasticity, liquid networks, neural ODEs and memory. Conceptual similarity does not establish experimental novelty.
