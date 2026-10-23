# R01 — Literature, prior art and novelty boundary
Date: 2026-10-23. Status: independent literature review; **no local model experiments or reproductions performed**.

## Question and executive judgment

Can a persistent, endogenously evolving neural substrate, with irregular sensory/action events, connection-temporal history, and optional multi-timescale adaptation, exhibit **causally meaningful** self-initiated internal representation development that simpler recurrent, event-driven and memory-only models do not explain?

**Assessment [Hypothesized]:** This *combination and evaluation target* is a research program, **not** an established original neural primitive, proven artificial mind, nor an established superiority result. Time-dependent synapses, internal neural ticks, plastic connections, autonomous dynamics, streaming outputs and latent reasoning each have close precedent. A model can generate complex trajectories yet encode nothing useful. No evidence here supports consciousness claims.

### Evidence grades

- **[Primary verified]** Paper identity, publication/version information, author abstract and specified method passages read from original papers (does **not** imply reproduction).
- **[Author reported]** Experiment descriptions/performance in source; not locally verified.
- **[Analytical inference]** Technical comparison derived from reported mechanisms.
- **[Hypothesis]** Proposed mechanism or prediction; untested.
- **[Open/unchecked]** Incomplete implementation/methodology verification.
- **[Negative evidence]** Published counterexample or ablation, not a proof of impossibility.

## Closest-neighbor matrix

| Line | Mechanism already documented | Overlap | Possible remaining delta (untested) | Strongest alternative explanation |
|---|---|---|---|---|
| Continuous Thought Machines (Darlow et al., 2025), [paper](https://arxiv.org/html/2505.05522v4), [code](https://github.com/SakanaAI/continuous-thought-machines) | Internal neural ticks, shared synapse MLP, **private neuron history models**, synchrony readouts; includes RL interaction | **Very high** | Distinct **edge-specific** temporal kernels and persisted between-event self-activity | CTM, LSTM or structured trace state can realize same input-output map |
| Liquid Time-constant Networks (Hasani et al., 2020), [paper](https://arxiv.org/abs/2006.04439) | Gated continuous-time recurrent dynamics and adaptive time constants | High | Particular learned action/readout/plasticity integration | Classical continuous-time RNN with elapsed-time control already suffices |
| Neural CDEs (Kidger et al., 2020), [paper](https://arxiv.org/abs/2005.08926) | Continuous hidden dynamics driven by irregular observations | High | Independently generated internal hypotheses without input updates | Autonomous ODE drift or control interpolation accounts for state change |
| Neural Hawkes (Mei & Eisner, 2016), [paper](https://arxiv.org/abs/1612.09328) | Continuous-time event intensities and event-dependent hidden states | Medium-high | Rich shared latent computation with actuators | Gated event intensity attached to standard RNN |
| S4 / Mamba (Gu et al., 2021; Gu & Dao, 2023), [S4](https://arxiv.org/abs/2111.00396), [Mamba](https://arxiv.org/abs/2312.00752) | Long-memory recurrent state / input-conditioned selective update | High | Outcome-relevant autonomous processing between events | Compressed linear or gated state is enough |
| TTT layers / Titans (Sun et al., 2024; Behrouz et al., 2024), [TTT](https://arxiv.org/abs/2407.04620), [Titans](https://arxiv.org/abs/2501.00663) | Hidden state as mutable learned model / persistent neural memory | High | Separated activity, edge traces and long-term consolidation with autonomous dynamics | Test-time memory alone produces any gain |
| Coconut (Hao et al., 2024), [paper](https://arxiv.org/abs/2412.06769), [code](https://github.com/facebookresearch/coconut) | Last LM hidden state fed as next input embedding, no sampled intermediate words | High | Free-running irregular-event state persisting across interactions | Repeated latent steps are merely hidden tokens |
| Huginn (Geiping et al., 2025), [paper](https://arxiv.org/abs/2502.05171) | Recurrent-depth blocks trained to use variable test-time latent compute | High | External inputs/outputs interrupt a persistently evolving state | Extra depth before a readout explains benefits |
| Looped Transformers (Chen et al., 2026), [paper](https://arxiv.org/abs/2605.23872) | Frozen pretrained middle blocks looped with damping | High for retrofit | Stable unbounded state after irregular interventions | Pre-norm Euler refinement, not autonomous thought |
| T²MLR (Cai et al., 2026), [paper](https://arxiv.org/abs/2607.15178) | Cached prior-token middle representation fed into new token position | High for transfer | Token-position independent autonomous clock | Token-conditioned recurrence sufficient |
| LOTUS (Fan et al., 2026), [paper](https://arxiv.org/abs/2606.31779) | Parallel supervised latent loop with gold CoT-step signals | High for latent compute | Endogenous representations without gold intermediate steps | Gains due to privileged supervised reasoning traces |
| Growing Neural CA (Mordvintsev et al., 2020), [original](https://distill.pub/2020/growing-ca/) | Learned local recurrent pattern maintenance and regeneration | High for self-organization | Persistent semantic/event integration | Self-maintenance is spatial dynamical pattern memorization |
| Differentiable plasticity / e-prop, [Miconi 2018](https://proceedings.mlr.press/v80/miconi18a.html), [Bellec 2020](https://www.nature.com/articles/s41467-020-17236-y) | Trainable Hebbian fast connections; local eligibility with modulatory errors | Very high for adaptation | Interaction with autonomous recurrent process | Existing three-factor plasticity suffices |
| Moshi (Défossez et al., 2024), [paper](https://arxiv.org/abs/2410.00037) | Full-duplex parallel speech streams, turn overlaps/interruptions | High for streaming I/O | Non-token common evolving neural substrate | Stream RNN plus separate encoder and decoder |
| Deep Equilibrium / Universal Transformer, [DEQ](https://arxiv.org/abs/1909.01377), [UT](https://arxiv.org/abs/1807.03819) | Iterative tied-weight computation, fixed points/adaptive halting | Medium-high | Long-term non-equilibrium, event-continuous individual | Standard recurrence captures observed effects |

## CTM comparison at the equation level (not merely nomenclature)

**[Primary verified]** CTM method equations (arXiv:2505.05522v4, §3.2–3.4): at internal tick t, a shared synapse model computes
`a^t = f_syn([z^t, o^t])` in R^D; a sliding matrix `A^t ∈ R^(D×M)` retains M previous preactivations; each neuron d updates `z_d^(t+1)=g_d(A_d^t)`. Synchrony is derived from history of postsynaptic neuron activity and used for attention/output. **Synapse is a cross-unit mixing function; the temporal history is processed by neuron-local models.** Its method does not describe one learned kernel per ordered directed edge (i,j).

**[Hypothesis]** An edge kernel candidate is `m_ij(t) = ∫_0^∞ K_ij(τ) h_j(t-τ)dτ`, with `dh_i/dt=-λ_i h_i+φ_i(Σ_j w_ij m_ij + u_i)`. Unlike CTM, i and k can receive different filtered histories from the *same* j. But generic recurrence can absorb finite-kernel history into augmented hidden state: for exponential basis traces `q_jk'=-λ_k q_jk+h_j`, with `m_ij=Σ_k c_ijk q_jk`; this shares O(NK) traces rather than maintaining O(EK) per-edge traces. Thus **edge-specific parameterization is not inherently a distinct expressive class** for finite-dimensional realizable kernels. For arbitrary delays there are additional memory/approximation costs. Test capacity and inductive bias under equal runtime/parameters, not by labeling the architecture novel.

**[Negative evidence]** CTM's appendix G.6 RL experiments report similar performance to LSTM baselines on evaluated tasks. Appendix F reports variability across random seeds. Its continuous interaction with an environment means “CTM cannot interact continually” is **not defensible**. What is not established is long-lived autonomous *cross-episode* state with the claimed endogenous epistemic effects.

## Coconut vs Huginn vs genuinely time-evolving state

**[Primary verified]** Coconut feeds LM hidden outputs into embedding positions of a prescribed latent reasoning sequence, so latent steps remain position-advancing recurrent *reasoning phases*. Huginn repeats a learned recurrence block for variable **depth** before prediction. T²MLR passes state between successive **tokens**. A proposed always-on core instead obeys `dS/dt = F(S,t)` even while inputs are absent, and event arrival `S(t_i^+)=J(S(t_i^-),e_i)`; output decision can be a separate intensity `λ_out(t)=softplus(g(S(t)))`. Note that traditional continuous-time RNNs/point processes already allow exactly this formal construction. Novelty therefore requires distinct measurable phenomena, not a clock diagram.

## Five (plus) originality claims to reject pending proof

1. “Thought without intermediate language tokens is new” — contradicted by Coconut and Huginn.
2. “A neural internal-time axis decoupled from input tokens is new” — contradicted by CTM and older recurrent computation.
3. “Neuron activation history enables a new temporal computation primitive” — already CTM; edge-specific kernels also have historic synaptic-filter/delay precedents.
4. “Continuous state changing between irregular sensory events is new” — continuous-time RNNs, CDEs, LTC and point processes.
5. “Fast trainable synapses and delayed eligibility-based reward are new” — differentiable plasticity/e-prop.
6. “Real-time simultaneous listening and speaking is new” — Moshi is a direct practical counterexample.
7. “Self-organized persistent neural patterns show thought” — CA establishes pattern persistence, not cognition.
8. “A collection of known mechanisms is demonstrated superior simply by integration” — no outcome data.
9. “CTM lacks live environmental interaction” — CTM explicitly evaluates RL environments.

## Three falsifiable hypotheses

**H1 / edge-temporal specificity [Hypothesis].** At fixed recurrent-state capacity, parameters, training data, wall-time and FLOPs, target-specific history kernels improve generalization to **unseen mixtures of cross-source delays** relative to: (a) exponential source-shared trace bank with learned edge mixing, (b) GRU/LSTM elapsed-time baseline, (c) CTM-style per-neuron history model, and (d) LTC/SSM. **Refuted if** edge kernel does not outperform best size/cost-matched model across prespecified seeds and temporal OOD splits.

**H2 / idle causality [Hypothesis].** Autonomous hidden evolution during genuine no-input windows creates a stable, *counterfactually consequential* representation that yields better held-out prediction/adaptation than equal-compute paused-state, event-triggered, pre-readout recurrent-unroll, and generative-replay baselines. **Refuted if** all effects vanish upon equalizing compute/state or after swapping the supposedly endogenous interim trajectories.

**H3 / provenance-aware emission [Hypothesis].** A shared latent dynamics architecture with internally recorded action intent and separately observed environmental receipt distinguishes silently dropped, delayed, or corrupted outbound actions more robustly than a streaming RNN with action/acknowledgment channels. **Refuted if** ordinary tagged event-stream RNN matches calibration and recovery under blinded drop/corruption.

## Highest-value experiment: E-R01-1 / edge memory × idle compute factorial

**[Proposed, not executed]** Train synthetic generators with causally independent sources `x_j(t)`, hidden partner-specific impulse responses `K_ij`, irregular timestamps, delayed observations, and deceptive distractor event streams. Partition by unseen delay mixtures/timestamps, not random windows cut from one trajectory. Freeze test events and labels before tuning; use event-time **and** wall-time evaluation.

**Models:** (0) two-state / finite-state task-specific control for greeting variants; (1) time-aware GRU/LSTM; (2) source-shared exponential trace bank + linear/gated readout; (3) SSM or LTC; (4) CTM-history analog; (5) edge kernel. Independently vary temporal schedule: A sleep/preserve state; B zero-input idle ticks; C ticks only on events; D same additional ticks immediately before readout; E explicit learned replay. This factorial prevents “more compute” from being confused with “compute while silent.”

**Training:** common generated environments and holdouts; parameter-count bands with separate compute-matched Pareto curves rather than pretending equal parameters imply equal FLOPs. At least 10 independent seeds where practical; preregister primary metrics and bootstrap confidence intervals with environment as unit. Record train/test data exposure, number of internal updates, elapsed-time inputs, total MACs/FLOPs, peak trace memory, numerical solver tolerance, latency, idle energy (if accessible), gradients and stability. Apply perturbation and trace-exchange interventions (replace idle trajectory with another seed's at the same timestamp) while preserving external event history.

**Primary outcomes:** OOD latent-target error and calibrated future event predictions; counterfactual causal intervention delta between intact vs replaced hidden trajectory; ability to distinguish attempted from delivered action (secondary task). **Null:** no statistically repeatable improvement beyond best conventional state baseline; complex or oscillatory activity is *not* accepted as a positive finding. Report failure cases and incomplete runs. An apparent advantage isolated to privileged extra data or more operations is invalid.

## Competing explanations / adversarial critique

- **Memory, not autonomous thought:** a learned compressed sufficient statistic explains everything.
- **Compute scheduling, not new cognitive substrate:** extra recurrent updates just before an observation yield the same score.
- **Replay or attractor:** internal novelty scores can come from cycles, random wandering or memorized motifs; sequence novelty is not semantic novelty.
- **Feedback leakage:** gold labels, reward generators, frozen LLM judges or gold CoT supervision introduce information unavailable to independent processes.
- **Representation non-identifiability:** “neurons representing intentions” may vanish under invertible hidden-basis changes.
- **Hardware & numerical effects:** solver step size and clock speed can masquerade as dynamics advantages.

## Source-file corrections proposed only (shared files untouched)

- `SOURCES.md`: display **full** titles for Coconut, TTT, CTM, Neural CDE, Moshi; add version/first-posted metadata. Titans first arXiv submission Dec 31 2024, even if routinely cited 2025. Neural Hawkes first submitted 2016 and NIPS 2017 camera-ready version.
- `RESEARCH_LANDSCAPE.md`: explicitly note CTM **does** test continual RL interaction with an environment (Appendix G.6), though it does not establish autonomous, durable mind-like evolution; its RL performance is **similar to LSTM**, not general dominance.
- `RESEARCH_LANDSCAPE.md`: qualify “continuous hidden change” comparisons: Neural CDE controlled dynamics and LTC autonomous drift are different constructions, and an ODE with zero drive need not continue productively.
- `SOURCES.md`: title of latent RL counterpaper arXiv:2512.11816 is *Reinforcement Learning for Latent-Space Thinking in LLMs*, submitted **Nov 26 2025**, despite the 2512 arXiv identifier (original arXiv metadata reports this date).
- Add a searchable table with DOI/versions/status; mark papers verified only at identity/abstract level unless equations or repository implementation were actually read.

## Other tracks and overlap control

R02 kernel representations/ablation; R03 emission and interruptible communication; R04 online plasticity; R05 frozen LLM guardrails; R06 evolution and consolidation; R07 pretrained retrofit; R08 falsification; R09 greeting prototype; R10 stability and asynchronous updates. This R01 report audits literature and proposes comparisons; it **does not** assert findings of other unfinished tracks or modify their owned files. Peer PR contents not verified in this investigation.

## What changes / does not change

**Changes:** novelty language should emphasize a possible *experimentally distinct causal phenomenon* and specify rigorous baselines. CTM must be treated as having continuous RL interaction, and source-shared trace banks are essential edge-kernel controls. **Unchanged:** it is legitimate to pursue persistent dynamics for emergent thought-like activity as a research question even when immediate task accuracy or inference speed is not the project goal. No result licenses consciousness inference.

## Verification scope and remaining audit debt

Primary source landing pages were checked for CTM, CDE, TTT, Coconut, Huginn, Training-Free Looped Transformers, T²MLR, LOTUS, LTC, S4, Mamba, Titans, Neural Hawkes, Moshi, neural CA, differentiable plasticity, latent RL negative paper; CTM's detailed method and RL appendix were read. Authors' code for CTM was located/read at README level, **not run**; other paper implementations and individual supplementary numeric tables were **not** audited end-to-end. Remaining SOURCES.md entries (DEQ, UT, e-prop, crosscoders, echo-state edge-of-chaos journal article) are valid literature leads but not independently method-audited in this pass. **This is not a systematic or exhaustive novelty search**, a patent clearance, or a claim of local reproduction.

See [REFERENCES.md](REFERENCES.md) for machine-friendly per-item bibliography status.
