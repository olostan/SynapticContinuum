# EXP-0006 — Minimal generative universe / exact truth contract

The world is **an instrument to falsify neural hypotheses**, not an emulated human reality, game or benchmark leaderboard. Prefer 8 meaningful entities to 800 inert ones. Phase 0 world must be independently checkable by hand and deterministic without an LLM.

## Version 0: minimal factorized causal universe
**Geometry:** two regions R0/R1, each with four addressable cells (location encoding remains a vector, no natural-language names). Optional barrier only in later extension.
**Entities:** immutable opaque IDs with type: 2 containers C, 2 movable tokens X, 1 mover A (scripted actor), optional third token. Sampling permutes labels per episode; do not rely on a fixed one-hot vocabulary indexed by ID.
**State:** tick integer t; for every entity its type and parent ID (a container if nested) OR free cell location; for containers an open flag; actor region/cell; optional exogenous event queue; versioned world-rule ID. Ground truth tree must be acyclic: no object inside itself or its descendants; exact one parent or location per entity. Nested containers at depth <=2 in phase 0.
**Relations derived from state:** direct_inside(x,c) from parent; transitive_inside(x,c) via ancestry; at_region(x,r) via ancestor location; accessible(x) depends on open flags; open(c); co_located(x,y); moved_since_last_visible(x). Relational direction is critical: inside(X,C) != inside(C,X). Distinguish direct vs inferred/transitive. Do not hand a relation vector to the student as a hidden observation.

## Deterministic transitions (minimal)
- PUT(x,c): if x is a movable token or a movable container, container c open and accessible, neither would create an ancestry cycle, set parent(x)=c; else no-op with an observable failure flag only when actor can witness.
- TAKE(x,c): if parent(x)=c and c open, remove x from c into cell at c's outermost position; otherwise no-op.
- MOVE(x,dest): if x is free movable object or container and not obstructed, change its outermost cell to dest; all nested descendants change **derived effective location**, not their parent IDs. Movement of a contained item independently is invalid until TAKE.
- OPEN(c)/CLOSE(c): change flag if reachable; hiding contents is observation policy, not destruction of object existence.
- WAIT: advance one tick only; no stipulated new sensory input.
- HIDDEN_MOVE/DELAYED_TRANSFER: optional scripted exogenous events, never silently counted as student actions; version 1 only after v0 validation.
- Simultaneous events ordered by (world_tick, action_priority, actor_id, sequence_ordinal), exact rule specified in code and documented per fixture. Invalid actions are recorded; don't silently re-roll them to 'successful' actions.

**Observation channel:** at permitted observation ticks, emit visible entities in currently observed region plus relative cell, type and appearance token; closed-container contents remain occluded. Opaque IDs may be matched across sightings through appearance, but never encode ground-truth parent or hidden location. v0 view has controlled identity cues; harder variant masks IDs and randomizes appearances. During a gap no observation array is emitted (not an all-zero observation pretending to be seen). Labels of hidden-state probes are held by evaluator and cannot enter student's runtime.

**Action channel:** phase 0 scripted world events establish clean causal sequences; optional student actions in later gate. Student makes predictions/belief updates without a language interface. Predictive probes are passive read-only to primary neural state; do not give a new observation or gradient update from probe until scheduled learning point.

## Pilot tasks and independent oracle examples
P0. Identity/role: X inside C versus C inside X (second must be invalid by type); direction must not be confused. Include label permutations and reversible action order.
P1. Compositional location: PUT(X,C), CLOSE(C), MOVE(C,R1), hidden gap -> inferred region of X is R1 despite no visible X; version with TAKE before MOVE gives a different outcome.
P2. Nested containment: PUT(X,C0), PUT(C0,C1), MOVE(C1,R1) -> X in R1, direct_inside(X,C1)=false, transitive_inside(X,C1)=true. Only introduce once basic v0 is valid.
P3. Partial evidence conflict: hidden action or observation contradicts previously likely location; student should update belief without overwriting unrelated relation.
P4. Rule shift: from epoch E onward, scripted unusual container behavior (e.g. contents remain at old cell when special carrier moves); rule shift must be a *new explicitly encoded world_rule_version* and observations permit detecting it. Do NOT secretly change the simulator and claim autonomous new intelligence.
P5. World-pause vs ongoing unseen world: identical observation gaps but in one family world waits and in the other scripted exogenous event executes; compare prediction vs remembering, separate effects of elapsed time.

## Procedural splits and leakage controls
Train / validation / held-out are disjoint **causal templates**, not only seeds: withhold relation-chain depth, action permutations, identity renaming and new rule family combinations; all use independent random seeds and immutable rule hashes. Predefine fixed calibration probes; adaptively selected LLM episodes stay train-only. On novel labels, ensure embeddings use shared reusable encoders and student does not receive an expanded fixed one-hot slot count.
Recommended 3 layers:
- S0 sanity: 2 objects+1 container, unoccluded, short sequence, deterministic labels; if GRU cannot learn, world/feedback bug.
- S1 main: 2 rooms, 2 containers, 2 movable items, occlusion and composition, no hidden rule shifts; train different ordering/identities; held-out compositions.
- S2 after gate: new objects, nesting, adversarial hidden moves and rule shifts; same model parameterization, vary true complexity one axis at a time.

## Complexity axes (NOT a full Cartesian product)
Objects N=3/5/8 (later 12/24); max containment depth=1/2 (later 3/4); gaps=0/8/32/128 ticks; observation dropout=0/25/50%; hidden event rate=0/0.05/0.2 per tick; rule versions=1 then 2; ambiguity none then matching-appearance confounds. No unbounded proliferation. World must remain tractable for an independent symbolic oracle and for exact enumeration of small scenarios.

## World acceptance tests
- Exhaustive small-state transition check where feasible: acyclic ancestry, conservation of IDs, no cross-room teleport except explicit MOVE, no hidden visibility leakage, deterministic reset/replay, valid/invalid actions.
- Hand-computed P1/P2 oracles and semantic sign tests: swapping relationship arguments changes truth; changing action order changes final state; moving container moves contained descendants; closed container hides but does not destroy.
- Equal initial observable history can correspond to different hidden worlds (partial observability); no predictor can be expected to always infer the unknowable. Score calibrated belief distributions rather than demand impossible 100% accuracy.
- World simulator emits exact transition trace and truth separately from per-student observation tape. Hash world spec, transition recipe, observation tape and held-out truth; student sees observation tape only.
- Altering object count, rule versions or time-gap does not require replacing model input schema: observations are variable-length encoded events/sets with mask, not fixed identity-indexed input slots.
