# EXP-0001 — Does temporal synaptic memory add causal value?

**Status: DESIGN ONLY — NO EXPERIMENT RUN.** Related: E005, R02 PR #4. Read root EXPERIMENTATION.md.

## Question
Does learned sparse edge-specific temporal history improve irregular event understanding or subsequent state-dependent behavior compared with simpler time-aware recurrence at matched resource budgets? Separate *physical elapsed time* from *number of internal update cycles*. Findings about timing-task accuracy are not evidence of emergent cognition.

## Preregistered data
Generate synthetic sequences of three symbols A,B,C, timestamped t=(0,d1,d1+d2), with d1,d2 positive real. Main label y=1[d2>1.5*d1]; choose continuous values, avoid equality boundary. Generate balanced labels by rejection sampling separately within each split. Train 10k, validation 2k, test 4k sequences (modifiable only by logged amendment). Train intervals uniform in [1,10] except remove d1 in [4,5]; test (i) fresh in-distribution, (ii) d1 in [4,5] (interpolation), (iii) both intervals in [12,20] (extrapolation), each with balanced labels where feasible. **Caution:** d1,d2 both [12,20] may make positive labels rare/impossible for threshold 1.5. Therefore construct extrapolation from d1 in [12,16] and d2 in [10,30], reject to balance, and log sampled support; comparison should not claim broad extrapolation outside generated support. Input symbols identical across examples; provide exact delta times to every time-aware model. Train/test split deterministically by generator substreams and verify disjoint tuple hashes. No future event/timestamp leakage before its arrival.

Negative controls: final-symbol label only with randomized final symbol and delay-independent label (requires extending alphabet at final step); event-order control with shuffled first two symbols and label by identity order independently of delay. All architectures see identical event streams.

## Models
1. Majority baseline.
2. Exact arithmetic ratio predictor and small MLP fed d1,d2 (sanity ceiling; not causally streaming).
3. Time-aware GRU (event input includes Δt; optional log1p Δt).
4. Event-driven diagonal-decay state-space model with elapsed-time transition.
5. Source-shared B=8 exponential leaky traces with learned recurrent coupling.
6. Sparse FIR with fixed random degree <=8 per node, K=8 taps, learned coefficients; disclose tick index/time binning and ensure no privileged timestamp information. If implementing continuous-time delays, use causal timestamp interpolation, document computation and missing-history handling.
7. Optional fixed random recurrent reservoir + readout.

Start hidden N=128, batch size 64, fixed random seeds [11,23,37,41,53]. Report parameter count, MAC estimate, update steps, training time, peak RSS, per-seed metrics, validation-selection criteria, failures, and extrapolation bin curves; no claim of compute matching unless actually verified. Use the same optimizer search and data access; document parameter/compute mismatch. Do not tune models against held-out test.

## Factorial experiment: silence vs computation
Cross elapsed gap short/long with inner update count J in {0,1,8,64}; for each trained model compare: (a) freeze state + analytic time decay, (b) scheduled free evolution, (c) equivalent J steps immediately before readout, and (d) randomized or replay controls. Importantly a computational step has a defined dt; if J=0 time-aware models still receive Δt to avoid cheating. Measure effects on predictions and internal-state vectors, then causally ablate trace history at matched current h. Report state perturbations **and** independently evaluated label effects. A minimal first implementation may postpone this section only with explicit NOT RUN status and PR disclosure; it must not claim the full hypothesis tested.

## Decision criteria
Primary: held-out balanced accuracy and cross-entropy by delay regime, mean/std across 5 seeds; provisional practical equivalence margin 1 percentage point of balanced accuracy, reported with uncertainty (5 seeds exploratory, expand to >=10 for confirmation). Reject preference for expensive edge-specific FIR if GRU/SSM/traces match it at lower memory or cost. Null result or simple clock predictor dominance is valuable. Causal evidence for endogenous development additionally requires state intervention effects beyond replay, noise and equal-compute controls.

## Deliverables
Committed reproducible source, tests, small per-run JSON metrics, detailed REPORT.md with limitations and exactly used commands, machine capabilities and failures. No large binary artifacts in Git. No training is authorized by simply committing this design.
