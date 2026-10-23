# P0 — Event-driven greeting (reproducible toy)

This is a **supervised** experiment, not a learned general language model and not evidence of self-directed thought. The original prototype was written during research brainstorming and verified again on 2026-10-22 with PyTorch 2.10.0+cpu.

```bash
python -m pip install torch
python prototypes/continuous-greeting/demo.py --steps 420
```

The program seeds the RNG, trains a 48-unit recurrent neural field on synthetic labeled event patterns, and prints thresholded output events. Characters are *timed input pulses*, and the hidden state continues updating on silent ticks with two memory traces. Its two predefined communication classes are **HELLO** and **GOODBYE**. Training uses supervised event targets. During inference, output is event-gated and fed back to the next neural tick; it is not a next-token language decoder.

## Reproduced results (single run, not a statistical claim)

- `HI` at t=2,4 → `HELLO` t=7, score 0.789
- `BYE` at t=2,4,6 → `GOODBYE` t=10, score 0.945
- `H` alone → silence
- no input → silence
- `HI` at t=2,8 → `HELLO` t=12, score 0.882

Run uses seed 13, CPU PyTorch 2.10.0, 420 training batches; these are hand-selected probes from training-like patterns, **not held-out generalization estimates**. The network resets each example, so it does **not yet** demonstrate persistent cognition across separate conversations. No per-edge temporal kernel, online reward plasticity, LoRA, evolution or external LLM validator is implemented.

To evaluate the real hypothesis, see [E004](../../experiments/E004-timed-greeting.md), [E005](../../experiments/E005-temporal-memory-ablation.md) and [E006](../../experiments/E006-live-feedback.md): require held-out timing, long idle periods, recurrent/state-space baselines and true cross-episode persistence.
