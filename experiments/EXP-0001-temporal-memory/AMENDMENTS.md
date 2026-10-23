# EXP-0001 — Protocol Amendments

**Date:** 2026-10-23  
**Status:** PREREGISTERED REVISION (Addressing Review Feedback on PR #6)  
**Governing Documents:** root `EXPERIMENTATION.md`, `SPEC.md`

Pursuant to Section 2 of `EXPERIMENTATION.md`, this document preregisters indispensable protocol and implementation corrections identified during independent scientific review of PR #6. The initial execution (`run_id: 20261023T171033Z-linux-amd-x86_64`) is retained as superseded exploratory evidence. All subsequent executions incorporating these amendments are designated confirmatory for the amended criteria.

---

## Amendment 1: Task-Specific Negative Control Training (P0)

- **Prior Defect**: In the exploratory run, models trained on the temporal ratio task ($y = \mathbf{1}[d_2 > 1.5 d_1]$) were directly evaluated on `control_symbol` and `control_order` without training on those objectives. The resulting chance-level accuracy reflected semantic task mismatch, not a true negative control.
- **Correction**: 
  - Independent instances of all 8 model architectures are trained specifically on `control_symbol` ($y = \mathbf{1}[\text{event}_2 == D]$) and `control_order` ($y = \mathbf{1}[\text{event}_0 == A]$).
  - Each control task uses independent deterministic train (10,000), validation (2,000), and test (4,000) splits with identical input event streams, 50/50 balanced sampling, and early stopping.
  - **Hypothesis under test**: When trained on timing-independent tasks, temporal memory architectures should successfully learn the identity/order rules, but temporal connection kernels (TraceBank, SparseFIR) will confer no inductive advantage over standard recurrent baselines.

---

## Amendment 2: Unified, Time-Conserving Silent Dynamics Factorial (P0)

- **Prior Defect**: The exploratory factorial test applied silent updates only to `TraceBank` using an ad-hoc formula (`h += gamma * (tanh(h)-h)`), while passing `gap/J` to the final event after simulating the interval, double-counting elapsed time.
- **Correction**:
  - Unified continuous-time silent transition interface across all recurrent models (`TraceBank`, `DiagonalDecaySSM`, `TimeAwareGRU`, `SparseFIR`).
  - During silent steps, no external token is injected ($x = 0$ / held drive); internal states evolve according to each model's learned recurrent coupling and decay parameters over sub-step $\delta t = \Delta / J$.
  - **Exact Time Conservation**: Total physical time across the interval is $\Delta = \sum_{j=1}^J \delta t$. At the arrival of the final event at timestamp $t_2$, the elapsed time since the last update is $\Delta t_{\text{last}} = 0$ (if propagated up to $t_2$), completely eliminating double-counting.
  - Four matched conditions tested at short ($\Delta = 1.0$) and long ($\Delta = 10.0$) gaps across $J \in \{0, 1, 8, 64\}$:
    1. Condition (a): Freeze state + analytic time decay.
    2. Condition (b): Scheduled free evolution ($J$ even steps of $\delta t = \Delta / J$).
    3. Condition (c): Clumped compute ($J$ steps immediately before readout with $\delta t = 0$).
    4. Condition (d): Noise / state perturbation control.
  - The previous 41.9% result is labeled an exploratory custom intervention.

---

## Amendment 3: Multi-Point Diagnostic Trace and Feature Ablation (P0)

- **Prior Defect**: The exploratory trace ablation zeroed $z$ immediately before the final event while $h$ was held, while the final event still received explicit $\Delta t$ features, rendering the ablation non-diagnostic.
- **Correction**:
  - Multi-point causal ablation comparing:
    1. **Interval Trace Ablation**: Zeroing or perturbing $z$ after event 1 and propagating through the silent interval to event 2.
    2. **Explicit $\Delta t$ Input Feature Ablation**: Zeroing the $[\Delta t, \log(1+\Delta t)]$ input features at inference time to measure dependence on explicit timestamps versus internal recurrence/trace dynamics.
    3. **Boundary Trace Ablation**: Zeroing $z$ strictly at event 2.
  - Tracking continuous logit perturbation $|\Delta \text{logit}|$, state L2 distance $\|\Delta h\|_2$, and prediction flip rates.

---

## Amendment 4: Pareto Qualification and Inductive Bias Framing (P1)

- In the updated report, claims of "Pareto dominance" are qualified: wall-clock training time, inference latency, and peak memory are reported alongside parameter and MAC counts.
- The task is explicitly characterized as an evaluation of *inductive bias for continuous-time ratio comparison*, not evidence of emergent cognitive thought.
- `SparseFIR` results are framed as specific to the tested sparse topology and 8-tap configuration, not a universal falsification of all temporal kernel mechanisms.
