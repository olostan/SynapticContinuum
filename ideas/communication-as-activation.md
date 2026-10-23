# Communication as Activity in a Shared Neural Field

**Hypothesis** · no separate token-based inference episode is required for the substrate.

## The idea

Incoming sensory symbols, internal neural events, outgoing speech/action commands and modulatory feedback are **events injected into or emitted from the same evolving network**. A conventional encoder or text renderer may translate between discrete external media and continuous activation; *the core does not wait to generate a vocabulary token to continue computing*.

An event can be described as \`e = (t, port, payload, provenance)\`. Time and source are important: an observed word, an internally imagined word and an attempted utterance need not carry identical epistemic status even when they trigger similar feature activations.

The internal action that results in "HELLO" can remain in the network as recurrent activity, so the system can retain a trace of **what it attempted to communicate**, without reparsing its own output. This is not the same as knowing that the external world received the message. Actual delivery needs observation/acknowledgment through an input port. Compare this with efference-copy or corollary-discharge mechanisms, without equating the model with human speech production.

## Bidirectional communication without whole-state snapshots

- **Input port** maps externally observed \`H\` then \`I\` (possibly separated by silence) into neural activation pulses. Updates proceed between and after them.
- **Communication region/port** continuously receives internal influence; a learned gate or event threshold may trigger a token, phoneme, action or symbol. For an early experiment, discrete labeled output ports are acceptable; state precisely that this is *classification/events*, not open-vocabulary language.
- **Outgoing event feedback** injects intended communication back through a dedicated feedback channel. Avoid uncontrolled self-excitation / repeated HELLO loops with refractory/reset gating.
- **Validator** can observe *emitted communication events* without freezing the full state. Delayed feedback is associated with the originating event and eligible connections; validation need not run every tick.
- **Independent observation** confirms what was actually said/heard, keeping action different from evidence.

A live readout is not free of synchronization: a validator still receives a finite event record or streaming projection, while the core continues. This is different from a full-state snapshot. The observer can be wrong; its uncertainty must not silently become weight updates.

## Attention and token sequences

Keep attention as a candidate *mechanism* for retrieving information from prior activations. It need not be the control clock of the system. Conventional prefix-based Transformers already begin computing before a sentence is complete; the testable additions are **timed gaps as information**, between-event recurrent evolution, persistence across utterances, and shared activity/feedback.

Timing experiments must factor:
1. identical symbols, different wall-time intervals;
2. identical available compute, different timing metadata;
3. identical timing, additional internal steps;
4. reordered symbols;
5. silence / truncated input / interruption.

Without these controls, a gain attributed to continuous time could just be more compute or a normal sequence feature.

## Output port choices

**A. Dedicated readout region** (easiest to train), **B. observer on distributed features**, **C. learned synchronization/workspace** (most speculative). A learned output protocol may emit discrete events eventually, but the substrate does not require discrete tokens for each state transition.

## What 'knowing what it said' means

A network can have an internal trace of initiating an output event (action copy). It does **not** necessarily know the semantic meaning, delivery outcome or correctness of that event. Test these separately with dropped, delayed, modified and contradicted outputs.

## Minimal falsifiable task

See [E004](../experiments/E004-timed-greeting.md): receive timed HI and emit a learned greeting event after a delay; remain silent for H alone, noise and silence; inject the intended output event internally and test whether it resists immediate repetition. Then extend to communication sequence of H/E/L/L/O events rather than a fixed HELLO class.

## Relevant references

- [Moshi: a speech-text foundation model for real-time dialogue](https://arxiv.org/abs/2410.00037)
- [Neural Hawkes Processes](https://arxiv.org/abs/1612.09328)
- [Neural Controlled Differential Equations](https://arxiv.org/abs/2005.08926)
- [Continuous Thought Machines](https://arxiv.org/abs/2505.05522)
