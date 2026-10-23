# E004 — Timed greeting as an activation event

**State:** controlled extension proposed; an initial **single-seed supervised toy baseline** is runnable in [prototypes/continuous-greeting/](../prototypes/continuous-greeting/README.md). The baseline was reproduced once on CPU (PyTorch 2.10.0, seed 13) with HI → HELLO, BYE → GOODBYE and negative silence probes. This is **not** evidence of held-out generalization, continuous cross-episode state, per-edge temporal kernels, or reinforcement/evolution. The tests below remain proposed.

## Minimal claim

A persistent recurrent substrate receiving irregularly timed H then I pulses can learn to emit one HELLO event later, while staying silent for incomplete/noisy input and preserving internal activity in the intervening quiet ticks. No intermediate autoregressive vocabulary sampling is used.

## Why this is a useful toy, and what it does not prove

It tests event semantics, silence, timing, recurrent state and feedback of intended output. It does not prove intelligence, generative language, unsupervised communication, or that our temporal-kernel hypothesis is better than a standard RNN.

## Input/output contract

At each simulation tick input vector has one-hot pulses on alphabet channels and no event for silence. The network's latent state updates at **every** tick. A communication unit emits a discrete event when it crosses a threshold after a refractory/reset criterion; that outgoing event is re-injected as an action trace. Initially the label HELLO can be one event class. In a follow-up, train a true event sequence H-E-L-L-O from separate actuator channels without an autoregressive text decoder.

## Minimum cases

| Case | Expected |
|---|---|
| H @2, I @4 | One HELLO event after I |
| H @2, I @8 | One HELLO after I, without early output |
| H alone | Silence |
| Idle/no input | Silence |
| I before H | Silence or correctly distinguished pattern |
| H/I mixed with irrelevant pulses | No ungrounded HELLO unless learned task calls for it |
| Late contradictory event | Revised/aborted response if task defines it |
| Communication blocked externally | Internal action attempt ≠ observed delivery |

## Training options

- First: supervised event timing, BCE/CE to prove system wiring. This is **not** self-reinforced learning.
- Next: reward only task success, silence on negatives and correct ordering, with a delayed signal applied through eligibility traces.
- Later: learn output letters as a temporal sequence, then add LoRA-like consolidation or evolution in independent ablations.

## Rigorous measurements

Run multiple seeds and train/test timing splits; exact precision/recall of emitted events, latency from last relevant input, false activation per idle tick, failure at long pauses, feedback-induced echo loops, state norm/drift, FLOPs, wall-clock, and sensitivity to computational budget. Include nonrecurrent, ordinary RNN and explicit sequence-model baselines.

## Pass/fail criteria

*Passing* means the system reliably distinguishes complete patterns from partial/silent input and emits exactly one delayed event on held-out timing patterns. *No novelty claim* until it improves over the baselines in a larger task.

## Simple code

The following illustrative event loop is **pseudocode**, not a trained solution:

\`\`\`python
state, traces = init_state(), init_traces()
for tick in simulation_clock():
    pulses = sensory_port.poll(tick)  # may be all zeros
    state, traces = recurrent_update(state, traces, pulses, outgoing_feedback)
    proposed = communication_region(state)
    outgoing_feedback = event_gate(proposed)  # refractory suppression
    if outgoing_feedback:
        actuator.emit(outgoing_feedback)
\`\`\`

The key invariant is \`recurrent_update\` runs at silent ticks and does not need a tokenizer/LM head to create an intermediate output token.

See [communication paper](../ideas/communication-as-activation.md).
