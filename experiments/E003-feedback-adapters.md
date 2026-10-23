# E003 — Learn feedback connections and LoRA for pretrained models

**Status:** proposed, not executed · **Type:** lightweight post-training · **Supports:** [H2/H3](../ATLAS.md#2-competing-core-hypotheses)

## Research question
Can a small number of trainable feedback parameters turn frozen pretrained Transformer blocks into a stable, useful recurrent system? Does low-rank adaptation help more than a comparably sized new network?

## Prerequisite
Use E001 to identify a meaningful frozen baseline or clearly document its failure. Never assume that LoRA automatically makes arbitrary cross-layer interfaces compatible.

## Compare these variants
- V0: ordinary frozen forward pass.
- V1: frozen recurrence with prescribed damping.
- V2: frozen blocks plus trained low-rank projections and feedback gate.
- V3: V2 plus LoRA on one or two reused blocks.
- V4: new recurrent network with matched extra trainable parameters.
- V5: fixed versus sparse learned routing, only after the earlier variants are working.

One possible rule: `h_next = normalize(h + gate(h) * P_out(B(P_in(h))))`. Initialize near an identity transition.

## Training and measurement
Use objective graph/constraint tasks with held-out higher problem depths. Start with short recurrence lengths and evaluate longer lengths. Test final-answer supervision, latent-step distillation, and auxiliary stability losses independently before mixing objectives.

Compare trainable parameter count, training examples, active FLOPs, and readout capacity. Include random/frozen feedback controls. Measure both extrapolation and whether the base model loses existing capabilities.

## Interpretation
Success requires an advantage over both frozen recurrence and a parameter/compute-matched small recurrent model. Training only the feedback matrices is weight adaptation; the target phenomenon is still **inference-time latent state evolution without token sampling**.

Sources: https://arxiv.org/abs/2607.15178 · https://arxiv.org/abs/2606.31779 · https://arxiv.org/abs/2605.23872
