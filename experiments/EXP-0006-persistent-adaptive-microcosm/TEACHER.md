# EXP-0006 — Local LLM teacher protocol (non-authoritative, sparse, paused)

**First pilot requires NO LLM** until WORLD + conventional student baseline are scientifically accepted. Teacher is an experimental variable, never ground truth, simulator, student memory or language model inside runtime.

## Who can see what
- World oracle: complete causal state/rules and held-out truth, used for objective automated scoring.
- Student: observation stream, its own history/state and occasional numeric/structured teaching signal, NOT the world oracle, teacher prompt or generated language.
- Ollama teacher: only *training episodes*, authorized diagnostic probe summaries, intervention comparison, trainee uncertainty, known public world rules, active learning constraints; it must NOT see reserved held-out evaluation labels, future transitions, full simulator truth for blind test, or privileged states presented as student-visible evidence.
- Researcher: may inspect all only after frozen tests; no retuning test protocol after seeing heldout results.

## Teacher phases
T0 deterministic oracle feedback and uniform scripted curriculum (golden baseline).
T1 same reward/curriculum budget with random/shuffled feedback; negative control.
T2 local LLM suggests curriculum family and factual tests, but deterministic simulator supplies reward; isolates curriculum benefit.
T3 local LLM additionally supplies validated bounded reinforcement or critique mapped onto pre-existing supported feedback channels; compare to oracle-only and same curriculum. No direct freeform neural weight edits.
T4 only later: investigate learned internal self-evaluator, with teacher removed for independent assessment.

## Exact feedback API (candidate JSON schema v0)
A teacher proposal is parsed, checked, and converted into validated structured data with fields:
schema_version="sc06-teacher-v0"; reviewed_train_run_id; curriculum_family one of {identity,containment,composition,occlusion,rule_shift,temporal_gap}; optional episode_recipe_seed; claim list entries {probe_id,expected_relation_type,expected_boolean,confidence in [0,1]}; feedback targets {named_probe_id,score in [-1,1],source}; explanation is for the *human lab record only* and is NEVER injected to student. If teacher is uncertain or schema fails, abstain, record and choose deterministic fallback; no fabricated correction.
The deterministic simulator checks every claim/test precondition; rejects contradictory/impossible rule proposals. Teacher can select but not modify core simulator physics. A claim can be validated *only on training world snapshots*. Reward is applied through a predetermined learning rule with clipping and trace eligibility; the source tag is recorded.

## Controlled checkpoint protocol
- At designated student simulated tick t and after a complete event transaction, write a **complete** versioned checkpoint: h/m/p/W, optimizer and eligibility E, RNG states, queued student events and their timestamps, student world-observation cursor; plus independent world truth state, world event queue, rule version, seed; separately teacher policy state and teacher interaction index. Hash files.
- **Pause simulation time** entirely. External wall-clock time may elapse while teacher uses CPU/RAM; do not advance decay, environment physics, hidden student work, or reward eligibility by wall-clock seconds.
- Generate a immutable teacher request from bounded train-only data and a versioned rubric. Include hashes for student checkpoint, world/observation tape, prompt template, model tag+digest and sampling options. Cache response exact bytes, latency, retries, errors.
- Validate response; if accepted apply bounded reinforcement to the saved student with a declared simulated event timestamp. The resumed model state differs from an uninterrupted model **only because of valid recorded feedback**.
- Resume with a distinct branch of the same checkpoint for each comparison (same student/world RNG) and record any non-equivalence from stochastic implementation.

## Teacher outages and other interruption experiments
A. Paused teacher latency 0/30 seconds or as observed: simulation state must not move; compare no-feedback pause with continuous uninterrupted run bitwise on deterministic CPU when supported.
B. Actual crash/restart from checkpoint: must restore student + world + training/optimizer/eligibility + random streams, not just final neuron vectors.
C. Teacher unavailable: predeclared fallback NO TEACHER signal or deterministic oracle feedback (different experimental groups); never silently substitute another model/updated prompt.
D. Stop teacher at 25/50/75% of learning sequence and evaluate teacher-free trajectories before/after withdrawal with same world schedule; distinguish direct teacher dependence from learned autonomous capability.
E. Delay feedback by 0/8/32 simulated ticks with eligibility trace depth fixed/swept; determine whether assignment survives delay, replay or missing traces.

## Local resource policy and budget
- Discover installed Ollama and models via 'ollama --version' and 'ollama list'; do not assume a given quantization fits 16GB. Pin actual model digest and exact prompt version.
- Linux lab 16GB *shared* with student. Prefer **sequential** student/checkpoint/teacher calls; unload local model after use when Ollama API supports it; measure actual RSS, MemAvailable and swap before both phases. Stop if memory headroom uncertain. No cloud API required or authorized by default. Mac M4 Pro ~48GB is an optional separately validated runner.
- Pilot budget (proposal): <=16 teacher consultations per independent seed; <=4096 input tokens and <=256 output tokens per consultation; <=2 retries per malformed response; deterministic small curated train-only episodes. Cache first, compare fixed teacher-feedback trace to random/shuffled feedback on replay. Teacher token/time budget recorded, not hidden.
- Teacher version, context sampling temperature and seed pinned where backend supports; zero temperature is NOT proof of deterministic output. Do not conflate model output variability with learning randomness.
- Report valid response %, abstain %, contradiction/error %, reward overrides, per-call wall latency, peak memory, token counts if supported, student learning effects and all missing-response episodes.
- Avoid LLM judging 'quality of neural thoughts' from raw activation arrays. Critique observable predictions, interventions and independently verified training facts. Never reward resemblance to a predefined hidden neuron pattern.
