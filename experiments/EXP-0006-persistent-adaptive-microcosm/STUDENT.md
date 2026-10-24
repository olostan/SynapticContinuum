# EXP-0006 — Student substrate and transfer hypothesis

Do not choose a neural architecture by aesthetics. This document enumerates candidates with matching observable I/O and an explicit separation between runtime activity, adaptive memory and teacher training. Initial choice must stay compact enough to be challenged by conventional recurrence.

## Common state and API (proposal)
State S=(h,m,p,W,theta_opt,E,rng,version): fast activity h; slow learned state m; optional local plastic state p; weights W; optimizer or learning-state theta_opt; eligibility traces E; deterministic RNG streams and schema version. Environment has independent truth state; teacher has independent state/prompt cache.

student.observe(event,time); student.evolve(delta_ticks,policy); student.probe(query_type,entity_refs) -> nonlinguistic logits/belief features, **nonmutating**; student.feedback(validated_signal); student.snapshot(); student.restore(snapshot). No decoding generated language. If the student is queried, that operation must be read-only or an explicit experimental intervention.

Candidate P1: continuous recurrent dynamics with fast h and slow m, optional local eligibility traces; parameter/shared encoders support a variable number of entities and relational roles. Events inject observations; without events states may advance via a controlled transition. Adaptation can occur from world prediction error and bounded modulatory teacher feedback. Do not impose a hardcoded mapping from "container" to a designated neuron. Keep h/m/readout disentangled from graph oracle.
Candidate P2: event-driven/temporally asynchronous version, implemented *only after* P1 establishes a numerical baseline. Reuse EXP-0003/4 queue, CSR, deterministic PRNG, profiling or C++ execution techniques through independently justified interfaces; do not inherit LIF transitions or their semantics automatically.
Candidate A: learnable time-aware GRU or modest recurrent state-space world model using identical observation stream and comparable capacity; retain hidden state between episodes and include online adaptation or equal fine-tuning opportunities where comparable.
Candidate B: explicit symbolic or episodic belief-memory system observing exactly the same sensory events (no hidden truth). Record whether causal rules are hand-coded and do not compare it as a 'fair learned neural baseline' when privileged.
Candidate C: passive decay/frozen sleep/noise/replay/event-only dynamics; retain all other learning and data conditions.

## Structural growth strategy
Use shared event/type/role encoders, factorized entity embeddings, scalable working-memory slots allocated by mechanism rather than IDs, sparse pairwise or attention-like routing where justified. Vary *new instance count* and *new relationship compositions* with identical learned parameters; note that buffers might still grow with the number of seen entities. Record actual resident bytes per entity/relation and bound memory-history growth. Stable model does not mean constant memory forever; expose scaling curves and explicit eviction/consolidation.
A fixed output slot per object or fixed learned embedding for every test-world ID invalidates compositional growth claims. Consider teacher-defined relation types later, distinct from previously declared known types.

## Learning modes
- Training stage: short non-continuous supervised warmup to establish decodeability is allowed, but clearly stratified from claimed autonomous development. Train teacher/no-teacher groups on identical splits.
- Online stage: continue same weights/states across chronological experience; no episodic reset of h/m unless named baseline. Log every weight, optimizer and local plasticity update, its timestamp and feedback source.
- Teacher stage: apply only schema-validated, bounded training signals; verify that teacher-free held-out behavior changes after feedback.
- Continual novelty: unchanged topology and parameter shapes; new entity identities or rule variants learned from limited evidence without global full retraining. If reinitialization or global retraining becomes necessary, record as failure of H3/H5 rather than silently performing it.

## Why C++ is optional early
Python/PyTorch CPU or Mac is fine for a 128/256-dimensional reference and numerical diagnosis. Only move verified stepping/graph kernels to EXP-0003/4-style C++ once actual training/profiling bottleneck is observed. Optimizing a wrong learning rule is wasted engineering effort. Checkpoints, tests and learning-rule fidelity must precede speed optimization.
