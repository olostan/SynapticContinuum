# EXP-0002 — Event-driven neural dynamics and temporal memory

**Status: PREREGISTERED DESIGN ONLY — NOT RUN.** Date: 2026-10-23. Governed by [EXPERIMENTATION.md](../../EXPERIMENTATION.md). Reference: merged EXP-0001 and Linux Vulkan feasibility PR #7.

## Scientific purpose and limitations

Evaluate whether sparse event-driven propagation plus temporal-state representations can sustain **causally consequential** neural activity between observations, and at what computational cost. We do **not** equate classification, oscillation, novelty, speed, or persistence alone with cognition. EXP-0001's explicit elapsed-time shortcuts and untrained silent-step interventions motivate this design.

Primary hypotheses:
- **H1 / computational:** For identical dynamical laws and error tolerance, sparse event scheduling reduces processed edges and wall time at low activity; the advantage disappears or reverses as activity saturates. **Falsifier:** no measurable crossover or event execution slower throughout the tested sparse regime.
- **H2 / temporal representation:** Bounded event histories preserve selected non-exponential historical distinctions unavailable to an equal-size exponential trace bank, but analytic exponential traces achieve equivalent results for exponential impulse-response tasks at lower storage. **Falsifier:** no measured task discrimination or no memory/cost difference under capacity-matched comparisons.
- **H3 / persistence:** Conditioned endogenous event generation can produce activity following stimulus removal, but *utility* requires improvements on held-out delayed probes over frozen/decay-only, random activity, replay and matched-compute controls. **Falsifier:** sustained activity without positive downstream causal utility.
- **H4 / causal effect:** Intervening on selected internal events has measurable, reproducible downstream state and behavioral effects beyond randomized or sham intervention. This establishes causal participation, **not** cognition.

## Definitions and mathematical parity

A directed weighted graph G=(V,E), weights w, transmission delays d>=0, node state h_i and optional local memory m_i. External stimuli are timestamped. Event queue holds (timestamp, stable_sequence_id, source, target, amplitude, kind); order is timestamp then stable ID. For an impulse event at t, first advance the target's local state analytically under the declared between-event law, then add the impulse and apply the same activation/threshold/refractory rule for all scheduler variants. Define the initial reference dynamics as leaky integrate-and-fire-like with exact exponential passive leak and thresholded emission; declare reset, refractory, excitation/inhibition, delays, equality and simultaneous-event policy explicitly in configs. Do not quietly introduce autonomous oscillation in a baseline.

For exponential trace z with last observation t0 and decay tau>0: z(t)=z(t0) exp(-(t-t0)/tau) between impulses; at t add q. This is exact under the chosen impulse model, allowing lazy evaluation. Explicit bounded event-history queries may compute a declared causal kernel sum over events, with truncation defined; history=0 disables stored-history lookup, **not** baseline node state. Separate scheduler queue (future events), online memory (history/traces), and append-only experimental log (replay/provenance).

**Parity comparison:** event-driven exact or near-exact simulation versus synchronous fixed-step simulation of the *same* dynamics; compare trajectory and firing timestamps against a small analytic/event reference. Use dt grid refinement and discretization error curves; report dt, approximation error and compute. A dense synchronous baseline updates all nodes; sparse synchronous baseline uses sparse graph operations at each global dt, but must still advance eligible state semantics. Do not call architectural differences scheduler speedups. If no exact equivalence for a mechanism, label an *architecture comparison* separately.

## Preregistered experiments (staged; do not exhaust Cartesian product)

**Stage 0 — correctness/smoke:** 8–128 nodes, deterministic impulse, delay chain, branching graph, analytic leak, simultaneous events, cycle/refractory termination, bounded history, snapshot+replay. Compare timestamps and states with defined tolerances. Require property tests before performance work.

**Stage 1 — execution crossover (primary engineering test):** nodes N={128,512,2048,8192}; mean out-degree D={4,16,64}; external-seed active fraction f={0.001,0.01,0.05,0.10,0.25,0.50,1.0}. First screen N={128,512,2048}, D=16, f={0.01,0.05,0.25,1.0} across 3 seeds. Expand selectively to rest *by preregistered triggers*: add N=8192 if peak RAM <8 GiB and projected single-cell runtime <10 minutes; add degrees 4/64 and densities 0.001/0.10/0.50 where initial crossover bracketed or cost ordering changes. Do not select configurations based on task performance. Compare dense fixed-step, sparse fixed-step, event-driven adjacency/priority queue, and lazy-decay variants. For synchronous reference use dt={0.2,0.1,0.05} in simulated units where meaningful and chart error versus runtime. Match simulated horizon and external stimulus sequence; **record actual propagated active fraction**, not just injected f.

**Stage 2 — temporal representation:** N={128,512} and D=16 initially; compare bounded explicit history L={0,1,4,16,64,256} events per node, and 0/1/4/8 exponential traces. Additional windows by elapsed time where informative. Compare same exponential response (expected trace efficiency), and non-exponential/order-sensitive history queries where finite history may help. Provide capacity-matched storage comparison, memory accounting, effective horizon, queries/second, fidelity, and held-out delayed-history probes. Do not grant one candidate access to hidden timestamps/future input unavailable to another. If training is needed, train models specifically on task and silence behavior; no evaluation-only removal of expected time features as decisive evidence.

**Stage 3 — endogenous activity and causal utility:** N={128,512}; use 5 fixed seeds {11,23,37,41,53}; history L={0,16,64} and trace bases B={0,4,8} for shortlisted candidates from Stage 2; silence gaps={1,10,50} units (or calibrated to measured timescales, declared before run). Compare external-only, delayed-feedback, intrinsic oscillator, state-dependent trigger and a stability control (refractory/homeostasis). Evaluate freeze, analytic passive decay, replay, randomized events, sham intervention and matched-compute internal updates; align training with inference. Compare event deletion, delay and amplitude perturbation to sham/random interventions; hold external inputs, weights, seeds and pre-intervention state fixed. Measure downstream outcome and internal-state divergence by future time, not just immediate change. Report degenerate absorbing states, runaway cascades and censoring separately; do not optimize intervention selection on held-out tests.

## Tasks, metrics, and analysis

- **Task A:** analytically soluble impulse response/delayed propagation, timing and hidden-state error.
- **Task B:** delayed association without feeding explicit delta-time as a learned input feature; event timestamps are available only to the scheduler/kernel law, not as privileged readout features.
- **Task C:** matched-final-observation sequences requiring distinct histories, hold out time ranges and sequence families to probe generalization.
- **Task D:** post-stimulus evolution and stability (event counts, recurrent cascades, sustained fraction, pathological activity).
- **Task E:** causal intervention and post-silence task utility. Define task scoring before training and record random/sham controls.

Primary computational metrics: wall seconds, peak RSS, queue peak, processed events/edges, median/p95 event latency, initialization cost, events per simulated second, history bytes, and deterministic replay digest. Primary scientific metrics: task success and uncertainty, trajectory error, history-horizon retention, event counts during silence, intervention effect sizes and downstream task deltas, runaway/termination fraction. Report absolute numbers and uncertainty across seeds (screen 3; primary 5), not just speedup. Predefine meaningful tolerances in each config; compare accuracy with fixed baseline differences, plus a stability failure rate. Statistical claims at five seeds are exploratory; no strong significance or cognition claim.

## Reproducibility and failure gates

Use CPU first per PR #7; PyTorch/NumPy for correct references, efficient adjacency or CSR scheduler implementation if warranted. No GPU backend prerequisite; GPU resident batching not ruled out by PR #7. Capture true machine capability, commit SHA, execution commands, precision, versions and input hashes. Keep peak process RSS below 10 GiB, max 6 hours per primary run campaign, configurable per-cell time and max-event budgets; stop/censor pathological cascades and preserve censored counts. Cap queue size and simulated event depth; never silently discard events. Training budget must be reported, matched across trained candidates, and held-out test not used for tuning. An optional exploratory expansion requires AMENDMENTS.md.

**Acceptance:** all correctness properties pass; parity discrepancy quantified; at least the Stage 1 screening matrix, Stage 2 basic depth curve and Stage 3 five-seed controlled causal study actually execute, **or** label incomplete sections explicitly with reasons. No paper-like grand conclusions when stages were not run.

## Deliverables

Under this directory only: src/, tests/, configs/, runs/<run-id>/metrics.json, detailed REPORT.md, optional AMENDMENTS.md and .gitignore. Do not store checkpoints, raw event histories, binaries, generated datasets or huge logs in Git. Human-readable report must separate observed, inferred, unknown, failures and counterfactual limitations; include tables for N×f scheduler crossover, L×f history cost, and causal intervention versus control. Leave final execution PR open for independent review.
