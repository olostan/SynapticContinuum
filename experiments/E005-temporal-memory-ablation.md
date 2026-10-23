# E005 — Temporal weights versus ordinary recurrence

**State:** proposed · **Hypothesis:** learnable temporal response functions add useful information beyond instantaneous connections and equivalent standard recurrent memory.

## Setup

Generate a classification/prediction world where symbol identity, order and *inter-event delay* each sometimes determine the correct target. Include negative controls where interval length is irrelevant. Stream events and allow the substrate to evolve in all conditions.

Compare:
- A: instantaneous recurrent weights;
- B: A plus timestamp/delta-time input (critical control);
- C: B plus K-tap learned temporal connection kernels;
- D: B plus shared B-timescale leaky traces;
- E: C or D with optional *plastic* temporal coefficients (follow-up).

Match trainable parameters and update counts where feasible, and separately report real wall-time/FLOPs. A fully connected kernel has O(N²K) parameters; include sparse and low-rank alternatives.

## Confound disentanglement

Independently vary (1) semantic meaning of delays, (2) number of internal updates allowed during pauses, (3) explicit time encoding, and (4) order. A network given 100 idle iterations vs one given 2 does not isolate timing information.

For each pair/triple of identical symbols, inject randomized irregular intervals into held-out ranges, and measure generalization to durations longer than seen in training.

## Outcomes

Accuracy, calibration, memory horizon, response latency, parameter/MAC cost, activation-state stability and robustness to minor timing jitter. Plot per-delay performance, not just pooled accuracy. Include tests where the right answer changes if delays change but symbols do not.

## Falsification

If a timestamp-conditioned plain RNN or shared trace model performs as well at lower cost, an edge-specific temporal kernel is not justified by these tasks. If accuracy depends only on extra update count, it is not evidence about time representation.

**Related:** [Temporal connection memory](../ideas/temporal-connection-memory.md).
