# R02 — Temporal kernels and synaptic memory

**Date:** 2026-10-23. **Status:** independent theoretical investigation; **no model training, benchmarking, or local reproduction conducted**. Owner: R02. Literature statements are tagged **[Published]**, deductions **[Derived]**, proposed mechanisms **[Hypothesis]**, and tests **[Proposed]**. No result in this report is evidence of intelligence or consciousness.

## Executive conclusion

**[Derived]** A fixed per-edge finite impulse response (FIR) temporal kernel is *not* a new class of computation: it is a multichannel finite convolution / delay-line recurrent system. Its N-by-N-by-K parameterization is expensive, but not exponentially expensive. Any K-tap linear FIR can be represented by an ordinary augmented recurrent state carrying a shift register of the last K source activations; conversely a small state-space system implements constrained infinite impulse responses. The potential value of **edge individuality** is an inductive bias for target-specific delays, not exclusive ability to remember the past. **[Hypothesis]** In a persistently active network, edge-specific timescales plus separately bounded fast plasticity could support unusual causal internal trajectories. No published work reviewed here establishes that this combination creates self-originating thought-like representations.

**Recommendation:** do not implement dense 4096×4096×64 kernels. First compare (1) exact-delay sparse FIR and (2) source-shared exponential trace bank against a time-aware GRU, an exact timestamp-conditioned SSM, and a non-evolving event cache. Add plasticity only after a fixed-kernel effect survives.

## Scope and cross-track state

Read the campaign COMMON.md and README.md, R02-PROMPT.md, README.md, FOUNDATIONS.md, ATLAS.md, RESEARCH_LANDSCAPE.md, SOURCES.md, AGENTS.md, ideas/temporal-connection-memory.md, E005, and R01 SUMMARY (already present on main). R01's summary distinguishes mechanistic prior art from the goal of internally initiated, causally consequential persistent activity; R01 is informative, not binding. Adjacent: R10 covers stability/asynchrony; R03 live emission; R09 controlled greeting; R08 adversarial falsification. R04 plasticity, R05 guardrail, R06 consolidation, R07 transfer, R01 prior art complete the ten-track map. The GitHub PR search at investigation time returned no open PRs, so no provisional peer PR conclusions are assumed; the R01 briefing references PR #1 and earlier work integrated into main.

## Precise models and semantics

Let a(t) in R^N be the presynaptic activity, h(t) in R^N persistent hidden state, x(t) external event injection, and Δt actual elapsed wall/environment time. **Distinguish simulation ticks from physical time.**

### A — Discrete-time full FIR synapses (tensor choice 1)

For step index n and K lags,
```text
u_i[n] = b_i + sum_(j=1..N) sum_(k=0..K-1) M_ij W_ijk a_j[n-k]
h[n+1] = (1-alpha) h[n] + alpha phi(u[n] + U x[n])
a[n+1] = h[n+1]  (or a separate bounded activity nonlinearity)
```
M is a fixed sparse adjacency mask. W in R^(N,N,K), ring buffer A in R^(K,N); u_i = einsum('ijk,kj->i',M*W,A) is executable in common tensor frameworks. With bounded K, exact old samples are lost after K steps. K represents **ticks**, NOT elapsed seconds, unless sampling cadence is fixed; a naive FIR trained on variable-step streams conflates durations and compute cycles. A proper irregular-time variant uses elapsed-time interpolated delays:
```text
u_i(t) = sum_j sum_k w_ijk a_j(t - tau_ijk)
```
with causal interpolation and an explicit history retention policy (event history may grow with event rate). For sparse edges (source[e], target[e], lag[e]):
```text
messages[e] = weight[e] * history[lag[e], source[e]]
u = zeros(N).scatter_add(target, messages)
```
The sparse code has O(E) parameters for *one selected delay per edge*, O(EK) for K taps per edge. Timestamp interpolation can require 2 values per sampled delay, plus indexing/search overhead.

**[Derived]** A full FIR equals a linear readout of a shift-register state q[n]=[a[n],...,a[n-K+1]] in R^(NK): q[n+1]=Shift(q[n],a[n+1]). Consequently a generic RNN with adequate state and readout capacity can implement it; any claimed expressivity advantage must hold under explicit resource limits.

### B — Source-shared continuous-time trace bank (tensor choice 2)

For B timescales τ_b>0 per source, let z_jb(t) be the exponential activity filter:
```text
dz_jb/dt = (a_j(t)-z_jb(t))/tau_b
z_jb(t+Δ) = exp(-Δ/tau_b) z_jb(t)
           + [1-exp(-Δ/tau_b)] a_j(t)
u_i(t) = sum_j sum_b M_ij C_ijb z_jb(t)
h(t+Δ) = h(t) + gamma(Δ) [phi(u(t)+Ux(t)) - h(t)]
```
This exact trace update assumes presynaptic activity is **piecewise constant** over the interval; if a(t) evolves freely during silence it is NOT exact, and the coupled ODE must be integrated or approximated (Euler/RK/analytic local approximation). For an input pulse modeled as an instantaneous impulse rather than a held value, use z_jb(t+) = z_jb(t-) + amplitude/τ_b and free decay; do not silently equate impulses with held activations. Code (PyTorch-like, unexecuted):
```python
decay = torch.exp(-dt[..., None, None] / tau[None, None, :])
z = decay * z + (1.0 - decay) * a[..., :, None]
u = torch.einsum("ijb,...jb->...i", C * mask[..., None], z)
h = h + gate_dt * (torch.tanh(u + input_proj(x)) - h)
```
Here z shape [batch,N,B], C [N,N,B], dt [batch], tau [B], h [batch,N]. For a batch-level dt with shape [batch], broadcast as dt[:,None,None]. **[Derived]** The bank is a low-order diagonal continuous-time SSM; a general SSM with state dimension NB can reproduce its linear filtering. Its B exponentials restrict the allowed convolution kernels to span{exp(-t/τ_b)}. Decaying exponentials cannot precisely realize arbitrary delayed narrow impulses without signed coefficients/cancellation, many bases, and potentially ill-conditioned learning.

### C — Edge-local dynamic state and plasticity (distinct mechanisms)

An edge-local state r_ijb can obey `dr_ijb/dt = -r_ijb/τ_ijb + g_ijb(a_j,h_i)`; incoming current is `u_i = sum_(j,b) v_ijb r_ijb`. **Cost:** O(EB) *mutable inference state*, versus O(NB) shared traces; it can depend on postsynaptic activity and thus is not always replaceable by source-only traces.

Fixed temporal coefficients C/W are parameters θ learned across episodes. Fast synaptic plasticity p_ij is a separate state updated within an episode, e.g.
```text
p_ij[n+1] = clip((1-rho)p_ij[n]
              + eta * modulator[n] * pretrace_j[n] * post_i[n],
              -pmax, pmax)
effective_ijb[n] = C_ijb + v_ijb*p_ij[n]
```
Its eligibility/modulator law is only a proposal, NOT a validated reward-learning algorithm. A full rapidly plastic p_ijk demands O(EK) extra mutable state, separate from static θ and historical activations. Plasticity/credit assignment belongs also to R04. Storing yesterday's weights is not required to build temporal response to yesterday's activations.

### D — Low-rank temporal basis

Write `W_ijk ≈ sum_(r=1..R) A_ir B_jr D_kr` (CP-factorized tensor); parameters R(2N+K) dense rather than N²K, intermediate `s_r[n]=sum_j B_jr sum_k D_kr a_j[n-k]`, output `u_i=sum_r A_ir s_r`. Per tick naive MAC ~ RNK+NR, and history NK; factorization restricts rank and cannot exactly represent arbitrary N×N×K tensors at small R. Alternatively use `W_ijk=sum_b C_ijb q_b(k)` with shared time basis q and E B coupling weights, allowing edge-specific mixtures but constraining timing functions. For irregular intervals use q_b(Δ), not index-based q_b(k).

## Cost model — exact counting conventions

Assume one scalar activation per unit, full directed graph including self-loops, sparsity 10% fixed mask with E=round(0.1 N²), K taps per present edge, fp32 weights and fp32 history, Adam mixed **not** assumed: weights+grad+2 Adam moments = 16 bytes/parameter; parameter-memory figures exclude allocator fragmentation, masks, indices, recurrent state, and layer/optimizer overhead. One multiply-accumulate (MAC) per tap; FLOPs ≈2×MACs (implementation-dependent). No sparsity speedup is guaranteed on GPU because indexing and gathers cost bandwidth/dispatch. Ring buffer storage = 4NK bytes, irrespective of density.

| N | K | Connectivity | Kernel weights | Weight MiB | Weight+grad+Adam MiB | History MiB | MAC/update |
|---:|---:|:---|---:|---:|---:|---:|---:|
| 128 | 8 | dense | 131,072 | 0.50 | 2.00 | 0.00 | 131,072 |
| 128 | 8 | 10% | 13,104 | 0.05 | 0.20 | 0.00 | 13,104 |
| 128 | 64 | dense | 1,048,576 | 4.00 | 16.00 | 0.03 | 1,048,576 |
| 128 | 64 | 10% | 104,832 | 0.40 | 1.60 | 0.03 | 104,832 |
| 512 | 8 | dense | 2,097,152 | 8.00 | 32.00 | 0.02 | 2,097,152 |
| 512 | 8 | 10% | 209,712 | 0.80 | 3.20 | 0.02 | 209,712 |
| 512 | 64 | dense | 16,777,216 | 64.00 | 256.00 | 0.13 | 16,777,216 |
| 512 | 64 | 10% | 1,677,696 | 6.40 | 25.60 | 0.13 | 1,677,696 |
| 4096 | 8 | dense | 134,217,728 | 512.00 | 2048.00 | 0.13 | 134,217,728 |
| 4096 | 8 | 10% | 13,421,776 | 51.20 | 204.80 | 0.13 | 13,421,776 |
| 4096 | 64 | dense | 1,073,741,824 | 4096.00 | 16384.00 | 1.00 | 1,073,741,824 |
| 4096 | 64 | 10% | 107,374,208 | 409.60 | 1638.40 | 1.00 | 107,374,208 |

**Training tape:** naive BPTT through T updates stores at least O(TN) hidden activations per sample and, if intermediates are materialized, can require O(T E K) intermediate multiplication products; actual frameworks may fuse kernels and checkpoint/recompute. An activation history buffer of size NK does **not** account for the full autograd graph across T. For event-indexed irregular times, gradient through interpolated history and dt needs additional saved values. Inference memory for a dense full FIR scales θ O(N²K), history O(NK); sparse FIR θ O(EK). Source trace variant parameters O(EB), inference state O(NB), MAC O(EB); edge-local B-filter variant state O(EB) and coupling O(EB). Full kernel bandwidth lower bound ~4EK bytes read per update absent on-chip cache, plus state reads/writes; e.g. dense 4096/64 scans 4 GiB of weights per tick, before output accumulation and memory traffic. These are *analytical estimates*, not measured runtime.

**Fair reference budgets:** vanilla N-wide simple RNN has ≈N² recurrent weights, ≈N hidden state, ≈N² MAC/update; a 3-gate GRU uses ≈3N² recurrent matrices plus input matrices and nonlinearities. An SSM with H state scalars, diagonal decay, N-to-H input and H-to-N readout has ~2NH+H trainable coefficients and ~2NH+H MAC/event (dense projections; more for gated/selective recurrence); a full unconstrained H×H SSM costs H². Compare equal *total* parameters, FLOPs, measured wall time, state memory, and training steps separately: exact equality on every axis is generally impossible. A timestamp-aware GRU or event-only SSM must receive Δt or absolute timestamps of the same precision as temporal models; do not handicap baselines.

## Stability, perturbation and causal dynamics

**[Derived]** For a fixed-delay linear recurrence `h[n+1]=sum_k W_k h[n-k]`, stability is governed by the spectral radius of its **NK×NK companion matrix**, not by the spectral radius of each W_k separately or solely of `sum W_k`. For the scalar one-lag recurrence `h[n+1]=g h[n]`, |g|<1 gives decay, g>1 runaway, g=-1 a period-two orbit; |g|=1 is marginal. A nonlinear saturating phi can bound activations while still producing cycles/chaos, so boundedness ≠ contraction nor useful memory.

**[Derived, sufficient only]** For `h[n+1]=(1-α)h[n]+α φ(Wh[n]+b)` with α in (0,1], Lipschitz(φ)≤L in induced norm and ||W||L<1, the map is contractive with upper bound (1-α)+α L||W||<1; this implies convergence under fixed input but rules out autonomous multi-attractor or persistent oscillatory dynamics in that regime. For multi-delay FIR, an easy sufficient condition with a weighted history norm may demand `L sum_k ||W_k||<1` plus careful companion-state shift weighting; it is not a universal necessary criterion. Stable exponential traces with τ>0 in isolation do not guarantee stability after feedback through C and h. Adaptive p may move the system outside a previously verified bound.

**[Proposed diagnostics]** Measure norm and singular-value growth of perturbations `δh(t)`, Jacobian-vector products, Lyapunov estimates with numerical-error bars, autocorrelation/periodic orbits, gradient norm, bifurcations under gain sweeps, and competence under perturbation. Compare no activity, stable fixed point, periodic cycle, apparently chaotic state, and meaningful task-relevant evolving states. Instrument output dependence by replacing or permuting trace banks during silence and measuring changes to withheld predictions; causal effect is not yet semantic importance. R10 should independently scrutinize numerical integration, scheduler-induced attractors and asynchronous stability claims.

## Closest primary prior art and counterevidence

| Source (original link) | What is actually reported | Relevance and limit |
|---|---|---|
| Gu, Goel & Ré, **S4**, ICLR 2022, https://arxiv.org/abs/2111.00396 | **[Published]** structured SSMs allow long sequence modeling and efficient convolution/recurrent views | Strong compressed memory competitor; no evidence about endogenous cognition |
| Gu & Dao, **Mamba**, 2023/2024, https://arxiv.org/abs/2312.00752 | **[Published]** input-dependent selective SSM parameters and efficient scan | Selection can compete with adaptable edge memory, but not identical to plastic p |
| Kidger et al., **Neural CDEs**, NeurIPS 2020, https://arxiv.org/abs/2005.08926 | **[Published]** irregularly sampled time series driven by observed control paths | A grounded rival for irregular events; interpolation policy is integral to model |
| Hasani et al., **LTC**, AAAI 2021, https://doi.org/10.1609/aaai.v35i9.16936 and https://arxiv.org/abs/2006.04439 | **[Published]** variable time-constant continuous-time RNN, bounded dynamics for its assumptions | Not equivalent to arbitrary learned per-edge delay; boundedness is model-specific |
| Darlow et al., **CTM**, 2025, https://arxiv.org/abs/2505.05522 | **[Published]** neuron-specific processing of activation histories and synchronization; selected tasks and adaptive internal steps | Close history-based mechanism, albeit neuron-local rather than arbitrary edge kernels; does not prove cognition |
| Miconi, Stanley & Clune, **Differentiable Plasticity**, ICML 2018, https://proceedings.mlr.press/v80/miconi18a.html | **[Published]** learnable Hebbian plastic coefficients in RNNs and experimental tasks | Strong precedent for dynamic connection-local state; current p rule is simplified |
| Mei & Eisner, **Neural Hawkes Process**, NeurIPS 2017, https://arxiv.org/abs/1612.09328 | **[Published]** continuous-time LSTM for irregular event histories and future event intensities | A simple timestamp/event-state null may be much stronger than assumed |
| Synaptic filter precedent: https://pmc.ncbi.nlm.nih.gov/articles/PMC8047134/ | **[Published]** double-exponential synaptic filters used for spike trains (building on prior work) | Exponential filtering is not a novelty claim; per-synapse biological analogy not evidence of cognition |

The S4/Mamba titles, dates and authors, CTM description, Neural CDE and differentiable plasticity claims were checked against primary paper landing pages. The full papers' numerical results were not independently replicated. Citation to a paper's claims does not mean those claims generalize to our setting.

**Counterargument 1 (equivalence):** a shift-register RNN can exactly realize every finite-tap FIR. A sufficiently capacious recurrent/SSM or an event cache with timestamp comparisons may be cheaper and equally accurate. **Counterargument 2 (OOD):** learned timing filters can interpolate within seen τ yet fail badly on durations exceeding train support; exact arithmetic comparisons against Δt may generalize better. **Counterargument 3 (clock confounding):** idle updates introduce extra nonlinear computation, not necessarily informative physical-time memory. **Counterargument 4 (semantics):** periodic activation, novel trajectories and susceptibility to interventions are compatible with noise, replay, or unstable attractors. **Counterargument 5 (optimization):** negative/oscillating temporal coefficients can cause ill-conditioned gradients; dense FIR may consume bandwidth without new predictive capability.

## Decisive experiments — pre-registration proposal (no runs performed)

### E-R02-1: identical symbols, disjoint delay labels

Generate sequences of **identical visible symbols A,B,C**, with times (0,d1,d1+d2), and label `y = 1[d2 > 1.5*d1]` or a delayed causal cue `1[d1 in [2,4] and d2 in [7,9]]` under stochastic jitter. All models receive equal symbols and accurate elapsed Δt. Train with continuous d1,d2 sampled from [1,10] plus intentionally withheld strips [4,5] and [7,8]; test in-distribution, withheld interpolations and extrapolation [12,20]. Avoid OOD-only task where absolute threshold makes extrapolation logically impossible without assumption. Split by **delay tuples**, not only randomly by samples; balance labels in every timing stratum, control total duration, and prevent position/padding/mask leakage. Vary K so maximum discrete lag actually encompasses selected examples; specify time-unit mapping.

Baselines: (0) last-symbol/majority label; (1) exact timestamp comparison via small MLP on [d1,d2] or hand-coded elapsed time (ceiling); (2) persistent fixed random RNN + readout; (3) timestamp-aware GRU; (4) event-driven diagonal SSM with Δt; (5) shared exponential trace bank B=4/8/16; (6) sparse FIR taps/learned delayed edges; optional (7) edge-local state. Keep data, seeds (at least 10), optimizer search, training updates and token/event access equal. Present Pareto front against parameters, MAC, peak memory, measured device time, and generalization error. **A loss to the elapsed-time MLP is informative, not a failed experiment.**

### E-R02-2: independent silence duration × computation budget

Factorial between-event delay `Δ∈{short,long}` crossed with internal updates `J∈{0,1,8,64}`. Compare (a) frozen state/sleep with analytic elapsed-time decay, (b) J evenly spaced integrations through silence, (c) J immediate pre-readout operations with same event inputs, and (d) random/noise-driven evolution. Record actual simulated physical-time propagation, and control dt supplied to every model. Do not equate 64 numerical Euler substeps with 64 units of extra independent physical duration. A time-aware **one-step** analytic trace may predict just as well as 64 continuous updates. When long-vs-short labels differ, J held fixed isolates elapsed time; when Δ fixed, J variation isolates compute. Train and test independently on each cell. Stop if instability prevents matched measurement; count failures.

### E-R02-3: negative-control tasks and emergent-state probes

Negative: label determined solely by final symbol, and a separate task determined solely by order but NOT Δ. Additional challenge: reset temporal state without changing most recent h, permute edge-local histories at matched h, freeze all idle activity, replay cached prior states, randomize temporal phases, and apply equal-amplitude state noise. Test withheld future responses/predictions and autonomous candidate generation with an external objective, avoiding LLM-as-truth semantics. For genuine *causally useful* endogenous states, interventions during silence must alter future behavior on a predeclared independent metric beyond changes caused by replay/random activity. Significant state differences alone are insufficient.

**Primary decision rule:** if shared traces, timestamp-aware GRU/SSM, or exact event cache match edge kernels within a prespecified practical equivalence margin (propose ≤1 percentage point accuracy and ≤0.02 cross-entropy difference, intervals across ≥10 seeds), at substantially lower memory/FLOPs, reject edge-specific FIR as preferred mechanism for this task family. For a broader claim of distinctive *endogenous development*, require reproducible, task-grounded intervention effects that persist after replay/sleep/equal-compute controls. The accuracy equivalence band should be set **before** data inspection and may need adjustment for task noise.

**Reporting:** dataset-generation commit, deterministic split files, seed list, hardware/backend versions, curves vs delay and idle steps, calibration, matched resource ledger, failure/NaN rate, confidence intervals with per-seed and per-task variability, sample audits for timestamp leakage. Zero training results currently exist in R02.

## Minimal high-value next experiment and stop conditions

Implement E-R02-1 and E-R02-2 in one deterministic tensor-only harness at N=128, B=8, sparse degree 8 and K=8 (plus matched GRU/SSM and a trivial exact-time predictor). Prefer *source-shared traces first*, because they encode elapsed time without E×B mutable state. Run the fixed-clock, frozen-idle control first; only then add free-running endogenous activity. **Decisive negative:** edge-specific delay adds no reproducible gain on delay-dependent held-out tuples, or any gain vanishes after matching exact Δt access/compute. **Decisive positive for further investigation (not consciousness):** reproducible causal advantage on delay-dependent OOD and held-out intervention outcomes at defensible compute/memory cost, where matched timestamp-aware recurrent and event-cache alternatives fail.

No edit to the shared vision is warranted. Synthesis may later incorporate the equivalence limitation and resource ledger into FOUNDATION/ATLAS; R02 does not edit those files.
