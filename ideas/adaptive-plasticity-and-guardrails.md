# Live Plasticity, Consolidation and Guarded Evolution

**Status:** candidate mechanisms, not demonstrated in SynapticContinuum.

Our goal is not teacher/student language imitation. The evolving substrate explores its own representational space. A conventional, frozen LLM is a **fallible guardrail** that can identify possible semantic regressions, not a source of target thoughts or a universal reward oracle.

## Three kinds of change

- **Current state:** \`h,z\` (fast activation and temporal-memory traces) change while the network runs. This is inference-time state evolution, not necessarily weight training.
- **Local plastic state:** \`P_ij\` adjusts a connection's *effective* response through experience. It can be transient, reversible and reward-modulated.
- **Durable parameters/topology:** LoRA-like adapters \`BA\`, stable kernels and connectivity evolve on slower timescales. Candidate modifications should be evaluated independently before promotion. LoRA is parameter efficient but not inherently safe against drift or forgetting.

A simplified optional local update uses an eligibility trace \`E_ij(t+1)=λE_ij(t)+f(h_i(t),h_j(t))\` and delayed modulation \`ΔP_ij(t)=ηm(t)E_ij(t)\`. This is an illustrative three-factor plasticity rule, **not** the exact e-prop gradient equation. Delayed feedback needs event attribution and/or traces with appropriate timescales; current activity at feedback-arrival time may be unrelated.

## What counts as 'good thinking'?

**Not** activity level, oscillations, low entropy, surprise, agreement with a conventional LLM or confident outputs. Candidate value signals:
- change in proper-scoring-rule loss on independently observed *future* outcomes, with the same information available before/after extra latent steps;
- success on externally verifiable tasks or effects of actions;
- maintained previously verified capability under delayed/interrupted input;
- future adaptability on *held-out* environment changes (plasticity retention);
- bounded compute and robust performance under small perturbations.

An independent readout or fixed validator can itself be insufficient or biased. Reward the actual tested consequences whenever possible. A noisy unpredictable observation should not be intrinsically rewarding merely because it remains surprising.

## LLM guardrail, precisely limited

A normal frozen LLM may receive **communication events, structured predictions or short behavior summaries** (not arbitrary raw hidden vectors) and issue:
- \`challenge\` — request an independent check;
- \`suspected_regression\` — run a remembered capability test;
- \`inconclusive\` — no weight update;
- \`supported_regression\` — *only* after an external check confirms failure.

Disagreement with the LLM alone never automatically punishes a novel pathway. Its role is to spend scarce evaluation budget where the system looks inconsistent; verifiable evidence decides. Avoid feeding the validator's own generated judgments back as unquestioned environmental truth.

## Evolution: select robust adaptation, not maximal chaos suppression

Explore mutations to temporal kernels, trace timescales, routing edges, plasticity rules or adapter parameters in separate candidate branches. Promotion requires a **multi-objective** comparison: utility, retained old skills, ability to learn new skills, dynamical stability, and resource cost. Perturbation robustness is helpful but cannot prove correctness.

Do not evolve millions of dense weights each neural tick. Favor compact candidate variations and explicit evaluations on holdout cases. Preserve useful variation: too much regression protection can freeze learning and eliminate beneficial novelty.

## Objections to investigate

1. Feedback arrives too late for trace-based credit assignment.
2. The 'communication region' learns to flatter the validator instead of reflecting useful internal state.
3. Local plasticity reinforces coincidental activity or self-generated misinformation.
4. LoRA promotion improves a small regression suite but destroys unmeasured skills.
5. Evolution optimizes robust stagnation rather than productive adaptability.
6. A simpler ordinary recurrent network plus independent evaluation is equally effective and cheaper.

## Experimental bridge

- [E006: Delayed live feedback](../experiments/E006-live-feedback.md)
- [E005: Temporal memory](../experiments/E005-temporal-memory-ablation.md)
- [E003: Feedback and LoRA](../experiments/E003-feedback-adapters.md)

## Research starting points

- [Differentiable Plasticity](https://proceedings.mlr.press/v80/miconi18a.html)
- [e-prop / online learning in recurrent spiking networks](https://www.nature.com/articles/s41467-020-17236-y)
- [Titans: neural memory](https://arxiv.org/abs/2501.00663)
- [Constitutional AI: AI feedback](https://arxiv.org/abs/2212.08073) — provides contrast; **we do not propose imitation by default**.
