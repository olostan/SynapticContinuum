# Idea: Persistent hidden activity with optional communication

**Status:** system-level hypothesis · **Related:** [Atlas H5 and H6](../ATLAS.md#2-competing-core-hypotheses)

## Fundamental separation
Internal state changes must **not** require generating intermediate language tokens. Language is a conditional readout, not the internal compute scheduler. Repeating an LLM API call with textual memory does not test this hypothesis.

```text
new observation --> encoder / injection adapter
                           |
                           v
       +--------------------------------------+
       | recurring latent state / region graph|
       | updates continue without token output|
       +--------------------------------------+
               |                    |
          memory policy        optional readout gate
               |                    |
        persistent storage   snapshot -> language decoder
```

A recurrent network can evolve activations while its weights stay fixed. Persistent memory is different from online weight learning.

## The speech-gating problem
A simple `sigmoid(g(state)) > threshold` does not establish that communication is warranted. Train gating only after demonstrating useful state. First use an **externally triggered read-only probe** of snapshots, then compare triggered communication against carefully labeled opportunities where interruptions are helpful or harmful.

## Snapshot semantics
Output can operate from a versioned immutable copy while dynamics continue. The latest state may change before the decoder finishes; consider consistency and staleness rather than assuming simultaneous output and thinking are trivial.

## Counterhypothesis: sleep is better
Compare (1) idle active evolution, (2) frozen state during idle periods, and (3) event-driven or budgeted updates. If the same task performance arises with far less compute, perpetual GPU activity has no established advantage.

## Persistent-state test
Inject partial evidence, let state evolve or pause, then inject a new clue; test whether it integrates information better than explicit context storage. Include resets, randomization, long delays, and whether improvement survives equal-compute comparisons.

## Avoid anthropomorphic conclusions
Unprompted text generation is not proof of a self, subjective awareness, intentions, or consciousness. Measure objective information use and causal impact of internal states.


## 2026-10-22 alternative: continuous communication as neural activity

**Important research update:** the periodic snapshot/readout model above is now one baseline, **not** the current preferred architecture. The more recent hypothesis treats outgoing communication as activity in the same field as incoming input and other internal events. It retains an internal action trace while live output ports render the event externally; delayed observer feedback modulates eligible pathways rather than requiring a full-state snapshot.

See [Communication as activation](communication-as-activation.md) and [Foundations](../FOUNDATIONS.md). Compare both approaches empirically; don't erase the older alternative solely because a newer idea seems more elegant.
