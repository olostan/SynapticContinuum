# Spontaneous Social Behavior in a Persistent Neural Substrate

**Status:** speculative research hypothesis, 2026-10-23. Not evidence of humanlike inner experience.

## Origin

The motivating scenario is **not** a request→response classifier. Imagine a continuously operating system in an otherwise empty room. Time passes and its latent state continues evolving; a visitor enters, and the system *might* spontaneously greet them, remark on the elapsed interval, or remain silent. It might also initiate an utterance before anyone arrives. A human analogy is “Oh, finally, I was so bored,” but generated text of that form does **not** establish boredom or subjective experience.

The research question: **can temporally extended neural activity, shaped by delayed positive/negative feedback over many interactions, acquire context-sensitive, sometimes spontaneous communication without making external prompts its operating clock?**

## Candidate loop

1. Run a persistent substrate, including stretches without input or output.
2. Inject occasional observations (people arriving/leaving, sound, changes in environment); mark their provenance.
3. Allow candidate communication actions to be initiated by internal state. Do not require a user turn or a fixed deadline.
4. Log action attempts separately from observed delivery and human response.
5. Obtain occasional reinforcement from human feedback, environment-grounded outcomes, or a *fallible* frozen LLM evaluator. Avoid assuming the reference's preference is ground truth.
6. Use a bounded, decaying eligibility mechanism to assign some of the delayed feedback to relevant prior activity or connections; test against reward applied only at output time.
7. Continue the substrate with no forced reset or predetermined response boundary.

## Distinguish several learning objectives

- **Contextual communication:** greeting when a person arrives; optionally initiating communication.
- **Timing and restraint:** not constantly speaking; learn when silence is appropriate.
- **Autonomous internal development:** maintain/revisit/recombine internal representations without external engagement.
- **Grounding:** statements about the room, time, or expectations correspond to observations and learned environmental regularities, not merely LLM-approved styles.
- **Adaptability:** behavior changes after genuine new experience, persists after the reference critic is withdrawn.

No single output like “I was bored” demonstrates any of these except the ability to emit text.

## First discriminating simulation

Build a simple synthetic environment with a room, entry/exit events, variable wait intervals and occasional human-feedback signals. Start with a compact fixed symbol vocabulary and independent emission gate; open-ended language comes later.

Compare:
- supervised reactive greeting classifier;
- recurrent system whose state is frozen during empty-room intervals;
- always-active recurrent substrate with no plasticity;
- persistent substrate with eligibility-modulated plasticity;
- identical system with conventional LLM feedback used as intermittent *scaffolding*.

Offer optional spontaneous utterances before the visitor arrives and after their departure. Measure grounded initiations, unnecessary interruptions, diversity beyond memorized scripts, stability of internal traces, attribution under delayed reinforcement, and behavior when the critic is removed. Random-text diversity, excessive speaking, and a script saying “bored” are failure modes, not emergence.

## Fundamental objections

1. The system may simply learn a timer-based greeting policy or a canned response.
2. Unbounded autonomous dynamics may settle into attractors or drift without learning anything.
3. A reference LLM may encourage imitation of familiar conversational conventions instead of distinct internal organization.
4. Reinforcement based on good final utterances may wrongly reward coincidental earlier neural activity.
5. No behavior-only experiment can prove subjective boredom, reflection, or consciousness.

**Research payoff:** establish whether context-sensitive *self-initiated* communication and persistent, causally consequential internal dynamics can coexist in one substrate, even if no claim of mind is justified.
