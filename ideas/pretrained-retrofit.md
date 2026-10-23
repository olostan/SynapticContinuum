# Idea: Retrofit existing pretrained Transformer weights

**Status:** exploratory engineering hypothesis · **Related:** [Atlas H1/H2](../ATLAS.md#2-competing-core-hypotheses) and [E001](../experiments/E001-frozen-block-loops.md)

## Motivation
Pretrained Transformer weights encode useful structure. Training a foundation model from scratch is expensive, so first determine what these weights can contribute to token-free hidden-state recurrence.

## Candidate paths
- **Frozen mid-layer loop:** apply selected existing blocks repeatedly, with damping.
- **Trainable low-rank feedback:** learn low-rank projections and gates between compatible layers while freezing base weights.
- **LoRA-adapted recurrence:** train adapters on a small number of reused blocks to stabilize shifted hidden-state distributions.
- **Latent slot bank:** retain K independent latent vectors, update them through pretrained submodules, and use language heads only for probes.
- **Reusable block library:** use a dynamic router to invoke different pretrained blocks in flexible order.

## The tensor-level trap
A Transformer block does not necessarily accept arbitrary activations safely. Validate residual-stream distribution, normalization, RoPE positions, attention masks, KV-cache assumptions, causal dependencies, device support, and compatibility of hidden tensors with the final readout head.

A "loop" that appends sampled or hidden pseudo-tokens changes the hypothesis; record which path actually occurs.

## Questions to answer
Which pretrained model provides the cleanest hooks? Can loops improve any held-out task without training? What magnitude of state drift occurs after 8, 32, or 256 updates? Does LoRA fix distribution mismatch or merely fit the finite training horizon?

## Falsification
If frozen looping underperforms direct inference and minimal adapters offer no gain over a matched small recurrent network, it may be cheaper and more capable to train a new recurrence module from scratch.

## Next action
Reproduce a minimal published frozen-loop result, then test the exact same checkpoint on longer run lengths and controls. See [SOURCES.md](../SOURCES.md).
