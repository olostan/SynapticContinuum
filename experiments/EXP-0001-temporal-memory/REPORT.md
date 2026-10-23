# EXP-0001 Execution Report — Temporal Synaptic Memory

**Date:** 2026-10-23  
**Status:** CONFIRMATORY RERUN EXECUTED (Addressing Scientific Review on PR #6)  
**Latest Confirmatory Run ID:** `20261023T180806Z-linux-amd-x86_64-confirmatory`  
**Superseded Exploratory Run ID:** `20261023T171033Z-linux-amd-x86_64`  
**Protocol Amendments:** [AMENDMENTS.md](AMENDMENTS.md)  
**Design Spec:** [SPEC.md](SPEC.md) (preregistered, unchanged)  
**PR:** #6 (`experiment/exp-0001-temporal-memory`)  

---

## 1. Executive Summary & Core Scientific Findings

We implemented protocol corrections requested during independent review of PR #6 and re-executed the full 5-seed benchmark on the Linux AMD Ryzen machine.

### Key Empirical Findings

1. **Explicit Timestamp Features Dominate Synaptic Traces (Diagnostic Ablation)**:
   - When explicit $[\Delta t, \log(1+\Delta t)]$ input features were ablated to zero at inference time, accuracy across **all** recurrent architectures (`TraceBank`, `DiagonalDecaySSM`, `TimeAwareGRU`, `SparseFIR`) collapsed from ~100% to **51.0% (chance)**, with large mean absolute logit shifts of **19.0 to 26.1**.
   - Conversely, boundary and interval trace ablations ($z \leftarrow 0$) at matched $h$ caused **zero perturbation** ($\|\Delta h\|_2 = 0.0, \Delta \text{logit} = 0.0$).
   - **Crucial Inference**: When explicit $\Delta t$ features are injected at each event, standard gradient optimization routes timing information through the direct input projection rather than relying on continuous synaptic trace filters. The model learns to read the explicit clock features.

2. **Negative Controls Confirm Timing Independence**:
   - When independent instances were trained specifically on the negative control tasks (`control_symbol`: final token identity; `control_order`: initial token order), **all** recurrent models (`Reservoir`, `TimeAwareGRU`, `DiagonalDecaySSM`, `TraceBank`, `SparseFIR`) achieved **100.00% ± 0.00%** accuracy.
   - Non-temporal tabular oracles (`ArithmeticOracle`, `MLPOracle`), which only observe $(d_1, d_2)$, remained at chance (~50%).
   - **Conclusion**: Temporal models easily learn standard sequence identity and order tasks, but temporal connection kernels confer **no advantage** over simpler recurrent models when the target semantics are timing-independent.

3. **Qualified Model Comparison (Inductive Bias, Not Cognition)**:
   - On the temporal ratio task ($y = \mathbf{1}[d_2 > 1.5 d_1]$), `TraceBank` achieved 99.88% in-distribution, 100.00% interpolation ($d_1 \in [4, 5]$), and 87.22% extrapolation ($d_1 \in [12, 16], d_2 \in [10, 30]$), slightly ahead of `TimeAwareGRU` (84.83%) and `DiagonalDecaySSM` (83.59%).
   - However, training `TraceBank` on CPU required **30.1s** per seed compared with **6.8s** for `TimeAwareGRU`, due to tensor scatter operations across the sparse graph. Parameter efficiency (10,826 vs 57,025) does not translate directly into training wall-clock speed.
   - Tabular oracles (`MLPOracle`) reached 99.14% extrapolation without any streaming recurrence. This synthetic benchmark isolates inductive bias for ratio arithmetic, not emergent cognitive thought.

4. **Symmetrical Silence $\times$ Computation Factorial (Negative Finding)**:
   - Under exact time conservation ($\sum \delta t = \Delta$ with $\Delta t_{\text{final}} = 0$), scheduling free-running internal evolution ($J \in \{1, 8, 64\}$) during long inter-event gaps ($\Delta = 10.0$) degraded accuracy across all continuous models:
     - `TraceBank`: 99.7% ($J=0$) $\to$ 41.9% ($J=8$) $\to$ 52.7% ($J=64$)
     - `DiagonalDecaySSM`: 99.1% ($J=0$) $\to$ 38.1% ($J=8$) $\to$ 41.9% ($J=64$)
     - `SparseFIR`: 99.7% ($J=0$) $\to$ 41.9% ($J=8$) $\to$ 41.9% ($J=64$)
     - `TimeAwareGRU`: 99.8% ($J=0$) $\to$ 41.9% ($J=8, 64$)
   - Uncalibrated internal state propagation during long silence drifts toward asymptotic attractors, eroding relative timing representations.

---

## 2. Environment & Machine Discovery

- **Host & Architecture**: `lenobox` (Linux 7.0.0-31-generic #31-Ubuntu x86_64)
- **CPU**: AMD Ryzen 5 PRO 5650GE with Radeon Graphics (6 cores, 12 logical threads)
- **Host RAM**: 14.50 GB total (3.61 GB free at startup)
- **Python**: CPython 3.12.14 via `.venv`
- **Framework**: PyTorch 2.14.1+cpu with AVX2 instruction set (`torch.is_vulkan_available() = False`)
- **Execution Resource Footprint**:
  - Confirmatory run total wall time: 850.93 seconds (~14.2 minutes)
  - Peak RSS: 547.63 MB (well within 12 GB host limit)

---

## 3. Dataset Generation & Auditing

Datasets were generated across 5 preregistered seeds (`[11, 23, 37, 41, 53]`) using independent `np.random.SeedSequence` streams:

1. **Task 1 (Main Temporal Ratio)**:
   - $y = \mathbf{1}[d_2 > 1.5 d_1]$, margin $|d_2 - 1.5 d_1| \ge 0.05$.
   - Splits: Train (10,000), Val (2,000), Test In-Distribution (4,000), Test Interpolation ($d_1 \in [4, 5]$, 4,000), Test Extrapolation ($d_1 \in [12, 16], d_2 \in [10, 30]$, 4,000).
   - Rejection sampled for exact 50.0% positive / 50.0% negative balance.
2. **Task 2 (Control: Symbol Identity)**:
   - $y = \mathbf{1}[\text{event}_2 == D]$, independent of delays $(d_1, d_2)$.
   - Independent Train (10,000), Val (2,000), Test (4,000) splits.
3. **Task 3 (Control: Event Order)**:
   - $y = \mathbf{1}[\text{event}_0 == A]$, independent of delays $(d_1, d_2)$.
   - Independent Train (10,000), Val (2,000), Test (4,000) splits.
4. **Leakage Verification**: SHA-256 tuple hash audits confirmed **0 shared tuples** between any train, val, or test split across all tasks.

---

## 4. Model Architectures & Resource Accounting

| Model | Total Params | Trainable Params | Fixed Params | Weight (MiB) | MACs / Step | Train Time / Seed (s) | Eval Latency (ms/sample) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Majority** | 1 | 0 | 1 | 0.000 | 0 | 0.0 | 0.006 |
| **ArithmeticOracle** | 1 | 0 | 1 | 0.000 | 1 | 0.0 | 0.007 |
| **MLPOracle** (tabular ceiling) | 17,281 | 17,281 | 0 | 0.066 | 17,024 | 4.0 ± 0.6 | 0.007 |
| **Reservoir** ($N=128, \rho=0.95$) | 19,137 | 129 | 19,008 | 0.073 | 18,688 | 3.9 ± 0.3 | 0.010 |
| **TimeAwareGRU** | 57,025 | 57,025 | 0 | 0.218 | 56,064 | 6.8 ± 0.7 | 0.012 |
| **DiagonalDecaySSM** | 19,137 | 19,137 | 0 | 0.073 | 18,816 | 7.3 ± 0.8 | 0.012 |
| **TraceBank** ($B=8$, degree $\le 8$) | 10,826 | 10,826 | 0 | 0.041 | 11,648 | 30.1 ± 1.6 | 0.038 |
| **SparseFIR** ($K=8$, degree $\le 8$) | 10,825 | 10,825 | 0 | 0.041 | 14,592 | 26.0 ± 2.1 | 0.041 |

*Note on Pareto Trade-offs*: While `TraceBank` has 5.2× fewer parameters and 4.8× fewer analytical MACs than `TimeAwareGRU`, its training time is ~4.4× higher on CPU due to Python/PyTorch tensor gather and scatter operations across sparse edge indices.

---

## 5. Preregistered Benchmark Results (5 Seeds)

Reported as **Mean ± Std** on 4,000 held-out samples per regime across seeds `[11, 23, 37, 41, 53]`.

### 5.1 Main Temporal Ratio Task Balanced Accuracy (%)

| Model | In-Distribution (ID) | Interpolation ($d_1 \in [4, 5]$) | Extrapolation ($d_1 \in [12, 16]$) |
|---|:---:|:---:|:---:|
| **Majority** | 50.00 ± 0.00 | 50.00 ± 0.00 | 50.00 ± 0.00 |
| **ArithmeticOracle** | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00 |
| **MLPOracle** | 100.00 ± 0.01 | 100.00 ± 0.00 | 99.14 ± 0.52 |
| **Reservoir** | 98.50 ± 0.48 | 99.11 ± 0.70 | 78.70 ± 1.67 |
| **TimeAwareGRU** | 99.86 ± 0.10 | 99.91 ± 0.20 | 84.83 ± 1.43 |
| **DiagonalDecaySSM** | 99.91 ± 0.08 | 99.93 ± 0.11 | 83.59 ± 1.73 |
| **TraceBank** | **99.88 ± 0.10** | **100.00 ± 0.00** | **87.22 ± 0.87** |
| **SparseFIR** | 99.65 ± 0.14 | 98.60 ± 0.88 | 81.07 ± 1.63 |

### 5.2 Task-Specific Trained Negative Controls Balanced Accuracy (%)

When independent instances are trained specifically on timing-independent objectives:

| Model | Control: Symbol ($y = \mathbf{1}[\text{sym}_2 == D]$) | Control: Order ($y = \mathbf{1}[\text{sym}_0 == A]$) |
|---|:---:|:---:|
| **Majority** | 50.00 ± 0.00 | 50.00 ± 0.00 |
| **ArithmeticOracle** (tabular $d_1, d_2$) | 50.54 ± 0.87 | 50.49 ± 0.67 |
| **MLPOracle** (tabular $d_1, d_2$) | 49.69 ± 0.86 | 50.17 ± 0.73 |
| **Reservoir** | 100.00 ± 0.00 | 100.00 ± 0.00 |
| **TimeAwareGRU** | 100.00 ± 0.00 | 100.00 ± 0.00 |
| **DiagonalDecaySSM** | 100.00 ± 0.00 | 100.00 ± 0.00 |
| **TraceBank** | 100.00 ± 0.00 | 100.00 ± 0.00 |
| **SparseFIR** | 100.00 ± 0.00 | 100.00 ± 0.00 |

*Scientific Interpretation*: Every recurrent model achieves perfect 100% accuracy on timing-independent sequence tasks. Temporal connection mechanisms do not impair non-temporal learning, but provide zero advantage over simple standard recurrence when timing is non-causal.

---

## 6. Silence $\times$ Computation Factorial Analysis

Evaluated across physical gap ($\Delta \in \{1.0, 10.0\}$) and silent internal steps ($J \in \{0, 1, 8, 64\}$) under exact time conservation ($\delta t = \Delta / J, \Delta t_{\text{final}} = 0$):

```text
Condition                TimeAwareGRU   DiagonalDecaySSM   TraceBank   SparseFIR
--------------------------------------------------------------------------------
Gap = 1.0:
  J = 0 (direct event)      100.0%          100.0%         100.0%      100.0%
  J = 1 (scheduled)         100.0%           91.6%          86.5%      100.0%
  J = 8 (scheduled)          99.2%          100.0%          87.4%      100.0%
  J = 64 (scheduled)        100.0%          100.0%          88.3%      100.0%
  Condition (a) Decay-only  100.0%           36.8%          24.3%      100.0%
  Condition (c) Clumped      89.0%          100.0%         100.0%      100.0%
--------------------------------------------------------------------------------
Gap = 10.0:
  J = 0 (direct event)       99.8%           99.1%          99.7%       99.7%
  J = 1 (scheduled)          41.9%           54.8%          70.0%       58.3%
  J = 8 (scheduled)          41.9%           38.1%          41.9%       41.9%
  J = 64 (scheduled)         41.9%           41.9%          52.7%       41.9%
  Condition (a) Decay-only   41.9%           41.9%          41.9%       58.3%
  Condition (c) Clumped      64.2%           99.1%          99.7%       58.1%
```

### Analysis of the Negative Result
1. At short gaps ($\Delta = 1.0$), recurrent models largely preserve their representations across substeps.
2. At long gaps ($\Delta = 10.0$), partitioning the interval into free silent steps ($J=8, 64$) degrades performance to near-chance (~42%) across **all** recurrent architectures.
3. This degradation occurs because ungrounded recurrent state evolution without external drive accumulates drift away from the trained manifold. The hypothesis that autonomous internal recurrent cycles generically enhance memory is **falsified** in this setting.

---

## 7. Multi-Point Diagnostic Ablation Analysis

| Ablation Condition | Model | Post-Ablation Acc (%) | Mean $|\Delta \text{logit}|$ | Prediction Flip Rate (%) |
|---|---|:---:|:---:|:---:|
| **Explicit $\Delta t$ Feature Zeroing** | TimeAwareGRU | 51.0% | 19.07 | 49.0% |
| **Explicit $\Delta t$ Feature Zeroing** | DiagonalDecaySSM | 51.0% | 22.67 | 49.1% |
| **Explicit $\Delta t$ Feature Zeroing** | TraceBank | 51.0% | 26.10 | 49.1% |
| **Explicit $\Delta t$ Feature Zeroing** | SparseFIR | 52.6% | 21.11 | 47.4% |
| **Boundary Trace Ablation ($z_2 \leftarrow 0$)** | TraceBank | 99.9% | 0.00 | 0.0% |
| **Interval Trace Ablation ($z_1 \leftarrow 0$)** | TraceBank | 99.9% | 0.00 | 0.0% |

### Key Diagnostic Discovery
The network relies overwhelmingly on the explicit $[\Delta t, \log(1+\Delta t)]$ input features injected into `in_proj(x)`. Because explicit timestamp features provide an uncorrupted scalar clock signal, the optimizer drives the weights to read this clock directly, bypassing causal reliance on continuous-time synaptic trace decay $z$.

---

## 8. Epistemic Status: Observed vs. Inferred vs. Open

- **Directly Observed**:
  - `TraceBank` achieves superior extrapolation (87.22% vs 84.83% GRU) with 5.2× fewer parameters, but requires 4.4× more CPU training time.
  - Tabular MLP oracle reaches 99.14% extrapolation without any recurrence or temporal synapses.
  - Zeroing explicit $\Delta t$ input features collapses accuracy to 51.0% across all models.
  - Symmetrical free-running silent updates degrade long-interval accuracy from 99.7% to ~42%.
- **Inferred**:
  - The performance advantage of `TraceBank` on extrapolation is an **inductive bias** for smooth exponential decay functions over large intervals, rather than dynamic edge-specific computation.
  - Standard gradient training on discrete-event sequences with explicit delta times disincentivizes the use of continuous synaptic trace state.
- **Not Established / Open**:
  - Whether a strictly continuous-time loss (e.g. Neural ODE/CDE training without explicit $\Delta t$ input features) would force the model to rely exclusively on synaptic traces.
  - Whether edge-specific delays outperform traces in large-scale, densely recurrent spiking substrates.

---

## 9. Artifact Manifest

- **Committed in Git**:
  - `src/` (hardware detection, data generators, models, training, evaluation, factorial suite)
  - `tests/` (17 passed unit, smoke, and property tests)
  - `configs/default.yaml`
  - `requirements.txt`
  - `runs/20261023T171033Z-linux-amd-x86_64/metrics.json` (128 KiB exploratory run)
  - `runs/20261023T180806Z-linux-amd-x86_64-confirmatory/metrics.json` (161 KiB confirmatory run)
  - `AMENDMENTS.md` (preregistered protocol adjustments)
- **Local Only (Excluded via .gitignore)**:
  - Virtual environment (`.venv/`)
  - Intermediate checkpoints and activations (discarded post-evaluation)

---

## 10. Conclusion and Next Steps

EXP-0001 confirmatory results refute the hypothesis that sparse edge-specific delay lines confer an inherent advantage over continuous state-space models on irregular timing tasks, and demonstrate that free internal recurrence during silence degrades stored representations without stabilizing feedback.

Future research (e.g., potential EXP-0002) should investigate **continuous-time training without explicit input clock injection** to test whether persistent synaptic traces can support autonomous temporal computation when explicit timestamp bypass is impossible.
