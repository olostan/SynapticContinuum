# E001 — Frozen pretrained loops without intermediate token decoding

**Status:** proposed, not executed · **Type:** inference-only retrofit · **Supports:** [H1/H2](../ATLAS.md#2-competing-core-hypotheses)

## Research question
Can repeated hidden-state application of pretrained Transformer blocks, without sampling vocabulary tokens or updating pretrained weights, yield useful task improvements instead of drifting into unstable representations?

## Proposed mechanism
1. Encode the input once through early blocks, giving a state `h0`.
2. Reapply selected middle blocks `B` with a damped update such as `h[t+1] = h[t] + alpha * (B(h[t]) - h[t])`, with normalization variants.
3. Never sample tokens or extend the token sequence during recurrent iterations.
4. Probe at `t = 0, 1, 2, 4, 8, 16, 32`; probes must not modify state.
5. Compare alternative block selections and checkpoint structures.

**Important:** attention masks, RoPE positions, KV use, and residual stream statistics can invalidate this pseudocode if reused naively. First inspect the exact model implementation.

## Candidate setup
Start with a ~0.5–1.7B open-weight model (e.g. Qwen3-0.6B) on a machine with ~48GB unified memory. Verify model license, library versions, and layer access. Choose MLX or PyTorch/MPS based on measured support.

## Task and controls
Use deterministic formula checks, controlled graph reasoning, or exact-answer constraint tasks. Include unmodified inference, extra normal reasoning compute (reported separately), undamped vs damped recurrence, no-op normalization, shuffled block order, random feedback, and at least two held-out tasks. Match active FLOPs and measure wall-clock separately.

## Metrics
Accuracy by iteration count, state norms and rank, cosine drift, collapse/NaNs, energy or wall-clock, and long-run behavior at 64–256 steps. Plot full trajectories rather than selecting only the best step.

## Interpretive rule
Improvement only supports H1/H2 if it generalizes under meaningful controls; visually complex states with flat or worse accuracy are neutral or negative. Reproduce a slice of https://arxiv.org/abs/2605.23872 first.
