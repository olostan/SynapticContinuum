# EXP-0006 — Persistent Adaptive Microcosm: preregistered scientific design

**Status: DESIGN ONLY / NOT RUN.** 2026-10-24. Research Director must approve the design; independent Principal Researcher review before implementation and before major expansions. Follow ../../EXPERIMENTATION.md. This is separate from E006-live-feedback (a proposal) and EXP-0005 (simulation-substrate research).

## Scientific purpose and scope
Study whether a small neural system can accumulate, maintain, revise and *expand* causally useful internal representations through irregular experiences, silent internal dynamics and sparse external guidance. The world is an experimental instrument, NOT a game/product or target of research. We do **not** claim thought, subjective experience, consciousness, nonverbal human cognition or human-brain similarity. A constant nonzero activation trace, animation, high simulator score, teacher agreement, or checkpoint restoration alone is not a success.

**One sentence test:** after training and then withdrawing the teacher, can a continuously maintained student integrate a genuinely new relation/rule, preserve old learning, and exploit its *own* elapsed-time dynamics more effectively than serious compute-, data- and parameter-aware alternatives?

### Terms defined operationally
- **Persistent operational identity:** episodes and teacher interruptions continue from the same student activity h, slow state m, adaptive parameter p, plastic weights W, optimizer/eligibility/RNG (when applicable), without re-encoding an accumulating narrative. Storage checkpoint is permitted to persist process state; its correctness must be independently tested.
- **Autonomous evolution:** transition of student h/m (and, if explicitly enabled, local plasticity) on a simulated time step with NO incoming observation or teacher guidance. Sleeping or doing nothing is a valid learned policy, not a failure.
- **Experience-based development:** training changes generalizable representations, predictive beliefs or learning capability in a measurable direction. Do not equate weight norm/entropy/oscillation with learning.
- **Semantic meaning (operational):** role-sensitive, recombinable regularities between entities, their identities, hidden locations, time and causal consequences, measured on disjoint held-out structures rather than correctness of text.
- **Teacher:** an optional local Ollama model making structured suggestions/reward/curriculum interventions at paused simulation checkpoints. It does not own truth, choose labels for held-out tests, directly rewrite source/weights, or inject text to the student.
- **Continuity under interruption:** distinct phenomena: (i) silent simulated time with evolution; (ii) wall-clock teacher pause with simulated time stopped; (iii) crash-restart preserving exact saved state; (iv) teacher outage while student continues under predefined deterministic fallback.

## Competing preregistered hypotheses
- **H0 null / strong alternative:** GRU/SSM, explicit symbolic state tracker, replay, static memory or frozen student can match all meaningful gains with the same information. Any apparent benefit disappears after controlling additional operations/updates, trainable parameters, teacher curriculum, timestep and evaluation leakage.
- **H1 relational induction:** factorized student trained on a restricted world predicts unseen role permutations and compositions better than a memoryless model, but has no presumed advantage over a strong recurrent baseline. *Falsifier:* no held-out composition generalization beyond memorization, or only success when true relation labels are supplied as input.
- **H2 endogenous utility:** for matching experienced observations, simulated elapsed time and available pre-probe compute, autonomous h/m evolution provides repeatable improvement in later predictive calibration, causal-relation inference or adaptation, versus freeze/decay/noise/event-only/replay and conventional recurrent controls. *Falsifier:* no benefit after controlled compute, or only more spikes/entropy with no functional advantage.
- **H3 continual adaptation:** while teacher is absent, student integrates new rule families or novel objects with bounded additional experience and avoids catastrophic forgetting of earlier tested families. *Falsifier:* only memorizes fixed IDs/rules, requires model architecture reset, or old tasks collapse outside the predefined retention budget.
- **H4 sparse teacher improves development:** checkpointed local LLM critique/curriculum or validated reward leads to more teacher-free held-out acquisition/retention than matched oracle-only, random/shuffled and fixed curriculum, across seeds and budgets. *Falsifier:* benefit disappears with equal exposure/evaluation/compute or rewards merely mimic teacher judgments.
- **H5 growing capability without fixed slot hack:** student transfers to larger object sets, longer relation chains or longer gaps **without changing its architecture/parameter count**, within a predeclared feasibility band. *Falsifier:* only fixed-size indices/lookup table, fails on capacity expansion or increasing temporal horizon.
- **H6 interruption semantics:** a lossless crash+resume reproduces an uninterrupted deterministic CPU run (or documented tolerance for nondeterministic kernels); pausing for the teacher has no effect until a validated feedback message is applied. *Falsifier:* hidden state/optimizer/eligibility lost or divergence not accounted for. H6 is reliability, not cognition.

## Experimental design: minimal discriminating comparisons
Phase 0 validate independent world transitions/observation masks and leak-proof train/test splits (see WORLD.md). Build hand-worked causal oracles. No LLM initially.
Phase 1 validate task learnability with a symbolic oracle, non-oracle symbolic memory, memoryless learner and time-aware GRU/SSM (sufficient task signal, no hidden-world truth leaked).
Phase 2 compare a NEW persistent recurrent substrate (fast h, slow m, optional locally adaptive p/W; see STUDENT.md) with frozen/decay/noise/event-triggered/replay and recurrent controls. Same exposure and observation schedule; cross perturbation at mid-silence; separate simulated time from internal update count.
Phase 3 compare teacher modes using identical pre-teacher checkpoints and held-out episodes, cached prompts/feedback and matched curriculum budgets. Ollama only after local feasibility and LLM-feedback schema/rubric approved.
Phase 4 evaluate rule updates, context/knowledge growth and transfer without resetting student. Only after scientific evidence supports extending; do not attempt scaling for its own sake.

**Experimental unit:** entire independently seeded student training trajectory, not correlated checkpoints. Primary seeds [11,23,37,41,53] and validation/tuning seeds [101,103]. Holdout world seeds [211,223,227,229,233]. Report each trajectory, all failures, not just best checkpoint. Primary paired comparisons reuse world seed/episode schedule; stochastic student RNG remains independent, recorded. Tune only on train/validation; freeze protocols before held-out scoring. No using LLM on private evaluation labels.

### World / intervention contracts
See WORLD.md for small finite world, hidden states and observation/action channels. Evaluate (a) static relations, (b) compositional hidden-state updates, (c) withheld relation direction and entity roles, (d) changed rules without label leaks, (e) long silence with world frozen vs world advancing unseen. Teacher-free held-out probes include location inference, calibrated belief distribution, prediction of next observation and consequences of a chosen nonlinguistic action. Probes are **measurement**, not primary training output. Do not evaluate by generated word tokens.

A useful event during silence must be causally established: freeze/replace/rewind/noise/phase-shift internal state while holding world stream/RNG/exposure fixed; map effect on later generalization and calibration. Negative sham state copy and matched-compute arithmetic required. Probes should not inject hidden ground-truth state into the student.

## Primary metrics, baselines, and decision rules
Primary: teacher-free held-out relational composition accuracy and log loss/Brier score on balanced probes (two distinct outcomes, no trivial class skew), measured at matched experience counts; AUC of learning curve (not merely final success), retention of old family after new learning, transfer sample efficiency on unseen relation/rule. Secondary: epistemic calibration, hidden-state linear probe transfer (read-only, trained on non-heldout data), causal intervention effect with sign/control, growth curve vs relation depth/object count, teacher request/success cost, RSS, elapsed compute per episode, and simulated years/steps.
Formal hypotheses must report uncertainty: >=5 primary independent trajectories; paired score differences + bootstrap 95% CI over **seeds**, not individual correlated events; per-family breakdown; no claim of superiority from a non-significant difference. Exploratory threshold for a promising follow-up: improvement >=5 percentage points on prespecified held-out composition *and* nonnegative old-family retention relative to strongest matched learned baseline, CI compatible with a reproducible benefit; **not** a proof of novelty/cognition. Substantial negative results and inconclusive tests are valid outcomes.

Baselines:
1. deterministic ground-truth oracle (ceiling; has privileged world state and must NOT count as fair competing learner);
2. legitimate symbolic belief/state tracker limited to exactly the same observations and causal rules available to students; mark hand-coded domain knowledge explicit;
3. memoryless tabular/MLP readout;
4. time-aware GRU or simple SSM recurrent latent world model; training/probe budget matched;
5. proposed autonomous student with no teacher, all ablations; 
6. proposed student + deterministic simulator feedback;
7. proposed student + LLM teacher; random/shuffled teacher feedback and fixed curriculum negative controls.
No comparison under mismatched simulator versions, teacher tokens, information, training examples, update count, teacher latency or checkpoint policy without flagging non-equivalence. Include wall-clock and useful-scientific-result-per-CPU-hour as **cost**, not success.

## Crucial confound isolation
- **Extra work:** control internal update count independently from *elapsed world time* and available compute; do not conclude that more internal thought is good when extra model steps are unaccounted.
- **World transition:** held-out truth derives only from deterministic simulator; no LLM as oracle; student never receives world hidden state/teacher explanation or evaluator target.
- **Reward leakage:** LLM observes train-only diagnostics and permitted world facts; no hidden test probes. Censor test labels, traces and unpermitted future world information.
- **Permanent state:** no resetting h/m/weights/eligibilities between continual episodes unless explicitly indicated as a control. Keep environment resets distinct from student identity.
- **Architecture changes:** new object counts and relation depth must use same shapes/weights in transfer test. Expansion by adding slots invalidates 'same-model' transfer claim.
- **Teacher benefits:** cache fixed feedback and replay across subjects; compare equal labels/budgets and teacher outputs validated against simulator.
- **Representations:** high decoding accuracy alone may result from probe overfitting; use cross-episode heldout probes, state swap intervention, probe-capacity control and causal timing.
- **Selection:** no post-hoc favorable seed/rule/gap selection. Changes after evidence recorded in AMENDMENTS.md and related claims demoted exploratory.

## Scientific stopping and future scale relevance
Stop early if a world generator leaks labels, baselines cannot learn even easy tasks, checkpoint resumes corrupt hidden state, or teacher feedback is systematically inconsistent. If no measurable H2 benefit in a diagnostic pilot, investigate an alternative mechanism or stop; don't buy compute to make bigger dynamics. If H3 fails, prioritize plasticity/forgetting over adding objects.
Scaling beyond Microcosm demands (i) shared entity/role encodings, (ii) incremental learning without a fixed concept table, (iii) bounded per-event state/history growth or explicit capacity-performance trade-off, (iv) robustness to noisy observations and changed rules, (v) a pathway to pretrained encoders/teachers for external semantic signals, not language inside the core. A toy success is NOT proof of real-world understanding or consciousness.
Links: WORLD.md, STUDENT.md, TEACHER.md, MEASUREMENT.md, WORKPACKAGES.md, manifest.yaml, PRIOR_ART.md, ../../FOUNDATIONS.md. EXP-0001 silence degradation and EXP-0002 persistence/intervention are the most directly relevant prior results; EXP-0003/4 kernels are external performance references. EXP-0005 atlas is optional reusable evidence infrastructure, not a prerequisite simulator. 
