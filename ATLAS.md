# SynapticContinuum — Research Atlas: Questions Before Mechanisms

**Reframed 2026-10-24 · living critical map · not an architecture specification.**
The earlier 2026-10-22 neural-recurrence-focused version is preserved at [archive/ATLAS-2026-10-22.md](archive/ATLAS-2026-10-22.md). Start from [VISION.md](VISION.md) and [FOUNDATIONS.md](FOUNDATIONS.md). No result currently establishes the full vision.

## A. What phenomenon are we trying to demonstrate?

A **persistent, open-ended inner process** that can generate and revisit multiple nonlinguistic possibilities, analogically recompose past experience, estimate alternative past/current/future states, and discover relevance before being externally asked a question. The process allocates finite computation through state-dependent and perhaps learnable significance signals, may investigate the world by acting, and changes its subsequent learning and exploration through experience.

A single correct prediction, a promptless sentence, complex oscillation, a graph walk, or a trained decoder labeling hidden features is **not sufficient**. We want to know whether one *internally initiated* development causes another and leaves a lasting, externally testable trace in how the learner learns or acts. It is valid for the system sometimes to do nothing.

## B. Open scientific questions (do not collapse into one hypothesis)

**Q1: Representation and emergent meaning.** Are useful categories, object identities, roles and causal relations better supported by distributed temporal population codes, learned latent embeddings, dynamic object slots, explicit symbolic graphs, mixed architectures or others? How do we preserve two same-looking individuals and relation direction without imposing word nodes?

**Q2: Causal analogy and completion.** Can a partial activation history trigger several past trajectories, share *only transferable causal structure*, and create possibilities absent from any stored episode? Vase-on-table -> falling risk may generalize to animal-on-table; fragile glass -> breaking need not transfer to animal. Compare mere similarity, retrieval, generative continuation, relational composition and explicit structure mapping.

**Q3: Epistemic time.** Can one system preserve an observed past, maintain uncertainty about the present, reconstruct possible earlier causes, imagine several futures and run counterfactuals without treating imagination as new evidence? Can a later word or sensor observation revise historical interpretation without rewriting history?

**Q4: Autonomy and recursion.** What permits thought-like latent trajectories to develop after stimuli end and influence yet later trajectories, without a question, fixed output budget or scripted sequence? Distinguish productive internal exploration from attractor loops, replay, noise, self-prompting or merely giving a model more compute.

**Q5: Significance, 'feelings' and attention.** Can multidimensional, time-varying, possibly distributed appraisal variables (interest, reducible uncertainty, expected learning progress, urgency, anticipated harm, relevance, boredom, cost) govern the *probability of exploring* a possibility separately from the *probability it is true*? Can the system learn what to care about? Do gradients toward one scalar objective destroy useful diversity?

**Q6: Self-directed interaction.** Do exploratory sensory actions, waiting, touching or intervening improve knowledge beyond passive observations with matched access? Can internal simulations guide actions without direct external task instructions? Distinguish value of information from physical reward.

**Q7: Memory, change, continuity.** What persists across long time: state, residual traces, episodic memories, learned weights, adaptive routing or learned interest? When does internal imagination change future learning without implanting false memories? Can the system expand without preallocating one node for each future fact?

**Q8: Criticism and selective elimination.** Could a weak retrospective critic suppress invalid causal patterns while preserving uncertain imagination? How does delayed feedback identify eligible earlier activity? When do negative-only correction or positive reinforcement cause silence, overconfidence, drift or repetitive gaming?

**Q9: Semantic interpretation and language.** Can meaningful prediction/action arise in a system with no words? Can a separate, fallible decoder attach, revise and later change human labels without becoming the engine that performs inference? How do we test decoder leakage and confidence?

**Q10: What would make the phenomena genuinely nontrivial?** Which measurements, falsifying interventions and competitive baselines distinguish a new mechanism from established recurrent neural inference, Copycat/NARS-like stochastic search, explicit world-model simulation, probabilistic belief propagation or static episodic retrieval?

## C. Mechanism families: candidates, not priorities

| Family | Potential role | Strongest caution / baseline |
| --- | --- | --- |
| Temporal activation kernels, traces, spiking/synchrony, CTM | Residual history affects future transitions and delayed eligibility | GRU/SSM, clock shortcut, frozen/decay/replay, history ablation at fixed current state |
| Distributed learned embeddings, predictive/self-supervised sensory representations | Similarity and partial pattern completion without word nodes | Cosine similarity does not guarantee causal roles, temporal order or calibration |
| Modern Hopfield/associative memory, episodic replay, generative memory | Restore partial histories, recombine alternative trajectories | Nearest-neighbor lookup, mere replays, replay-induced false evidence |
| Explicit probabilistic graphical models and belief-state filtering/smoothing | Truth-conditioned uncertainty in past, present and future | Hand-coded variables/relations vs learned structure; compare fair information access |
| Recurrent generative world models, simulation-based planning | Sample alternative future and counterfactual trajectories | Fixed tasks/rewards; may only run at externally specified query times |
| Graph/hypergraph inference, GNN attention, relational binding, analogy models | Preserve relational roles; learned contextual traversals | One-node-per-word assumptions, prescribed search, rule/ontology leakage |
| Copycat/Metacat/NARS-style stochastic codelets, slipnets, agendas | Open-ended priority sampling, self-monitoring, fluid analogy | Existing mechanisms are strong prior art; not evidence of neural emergence |
| Active inference, intrinsic motivation, homeostasis, affect/appraisal, empowerment | Allocate finite computation/actions based on significance and information | Hand-authored utilities, reward hacking, risk paralysis, noise attraction |
| Online plasticity, local elimination/inhibition, three-factor learning, consolidation | Learn which causal histories to preserve or suppress | Bad credit assignment; catastrophic forgetting and activity collapse |
| Dynamic attractors, neural CA, asynchronous/event-driven execution, LoRA retrofit | Possible computational substrates or scaling strategies | Stability/throughput is not autonomously meaningful development |

A hybrid may combine complementary mechanisms, but complexity is a cost requiring causal justification. A small explicit symbolic system may reproduce many behaviors and must remain a respected baseline, not a straw man.

## D. Candidate synthesis — a design *lens* only

At time t we may think abstractly of:
- X(t): distributed and context-dependent internal activity, multiple time scales;
- H(t): structured or latent history and learned memory (history is not necessarily an external database);
- B(t): uncertain and potentially branching beliefs/imagined continuations about past, present and future;
- V(t): changing multidimensional significance influencing attention and optional actions;
- P(t): learning/plasticity, possibly including organization and exploration policy.

A new observation changes X/H/B/V; partial matches can generate candidate continuations; V allocates a bounded processing budget among those candidates, including lower-probability high-information or high-consequence possibilities; candidates can influence other candidates; future observations update beliefs without turning simulated events into witnessed truth; experience may alter P and V. There is no requirement that X, H, B, V or P be separate modules, nor that the student represent 'thoughts' as discrete entities. This lens should be discarded if data favor another decomposition.

## E. Falsifiable phenomena, not benchmark theater

**E1 Partial analogy:** separately encounter vases breaking after falls and animals landing safely. Test new animal-on-elevated-surface scenario after no direct example. Does the learner generate several warranted continuations with appropriate differences in fragility, instead of 'animal breaks'? Baseline explicit analogical/probabilistic inference, replay and recurrent world model.

**E2 Temporal belief revision:** a state observed at t0 should remain historical evidence while present-location distribution spreads when no observation arrives. Later evidence should update plausible pasts, not silently rewrite old observations. Compare temporal-history and current-state models under same elapsed-time data.

**E3 Spontaneous multistep development:** following one observation with no task, does a novel internally generated possibility cause another later useful possibility, without a privileged decoder or required output? Clone state and surgically disrupt intermediate histories; test later held-out adaptation or action.

**E4 Learned significance:** with the same world and fixed compute budget, compare frozen, shuffled and learned appraisal signals. Do they improve *value of information and retained generalization* rather than simply increasing event count, danger avoidance or novelty seeking? Separate belief probability from exploration sampling.

**E5 Active sensing:** permit the same sensory budget with agent-directed actions versus passive/replayed observations. Does information-seeking emerge and improve calibrated beliefs when external reward is absent?

**E6 Delayed naming:** learn environment dynamics without labels, later present new words and instance evidence; test revisable interpretation of prior experience and unchanged nonlinguistic prediction ability with language disconnected.

**E7 Critic ablations:** where a rule oracle exists, compare no feedback, positive, negative, temporary inhibition, plausibility-only LLM, random/shuffled and delayed eligibility. Track both valid discoveries and suppressed useful alternatives.

**E8 Lifelong retention/growth:** repeatedly introduce new motifs, sensor remaps and changing laws while preserving the same student. Does learning itself improve or is the system only accumulating a database? Measure memory/CPU per additional episode and knowledge age, forgetting, capacity and interest drift.

Each of these is an experimental *question*, not an authorized new EXP campaign. First build baselines and leakage tests, then only extend if findings distinguish mechanisms.

## F. Scientific observation contract

For a positive claim require, proportionate to claim: (1) independent world/observation truth and heldout compositions; (2) multiple independently seeded developing individuals; (3) available alternative hypotheses and uncertainty quality; (4) teacher/decoder blinded to test truth; (5) causal intervention at intermediate state with sham and compute-matched alternatives; (6) ability to distinguish replay from new inference; (7) learning/retention beyond one answer; (8) reported resource cost, total failures and ambiguous outcomes.

Do not conflate simulator reality with what the learner observes; event-sourced provenance is an optional necessary laboratory discipline for debugging but not the student's thinking mechanism. An internal representation cannot be declared 'fear', 'cat', or 'consciousness' simply because a decoder found a matching phrase. Calibrated read-only probes and downstream causal effects are essential.

## G. Actual evidence so far and its limits (no inventions)

- **EXP-0001 temporal memory:** its rerun report found strong reliance on explicit time features; trace ablation often did not alter outputs in that setup; excessive idle-time computation degraded tested performance. An instructive failed shortcut, not proof temporal history is useless.
- **EXP-0002 event-driven dynamics:** the report found bounded history and multiscale traces distinguish some delayed-event sequences, and homeostatic dynamics can sustain activity. The limited delayed-association trace bank reached approximately 57.8% balanced accuracy versus 51.5% memoryless; far from concept or continual imagination. Activity persisted, semantic autonomy not established.
- **EXP-0003/0004:** measured performance/representation of native execution and topology; potentially reusable engineering, no evidence of emerging meaning.
- **EXP-0005:** validated fixture/oracle work and simulator-substrate plans, not proof of the cognitive vision.
- **EXP-0006 design branch / PR #16:** a preregistered tiny causal world and teacher-student interpretation; **design only** and explicitly not accepted as the new project's conceptual north star. Re-evaluate its ontological and teacher assumptions before executing. Do not alter that branch as part of this vision-only revision.
- **R01 literature study:** closest mechanisms already have substantial published precedents; the question is what causal, lifelong autonomous phenomenon remains to be demonstrated.

See actual reports for exact methods, seeds, caveats and whether claims were independently reproduced.

## H. Research strategy under limited resources

Do not build a comprehensive world, indefinite autonomous simulation or multigigabyte neural rig to prove that an algorithm can wander. The fastest research path uses tiny controlled sensory worlds, a handful of discriminating hypotheses, serious classical baselines and careful ablations. Simulators provide objective truth for evaluation but not student-accessible symbolic answers.

Prototype one *mechanism comparison* per approved run. Review what it would falsify **before** coding; use simple CPU reference implementations; only reuse EXP-0003/4 kernels when a measured bottleneck actually matters. Allow the results to favor explicit probabilistic models, distributed dynamics, emergent slots or hybrids. Leave enough budget for surprise and exploratory observation but never convert surprise into an unearned cognition claim.

## I. Closest intellectual relatives and novelty boundary

- Hofstadter/Mitchell **Copycat** and Marshall **Metacat**: fluid analogies, stochastic competing processes, priority, metacognitive reflection.
- Bach **MicroPsi/Psi** and Oudeyer **intrinsic motivation**: motivated cognition, internal drives, exploration and adaptive development.
- Schacter/Addis **constructive episodic simulation** and generative memory models: overlap of memory, imagining and reinterpretation.
- Rigotti et al. **mixed selectivity**, Smolensky **variable binding**: distributed semantic and role-bearing representations.
- Modern Hopfield networks, **CTM**, predictive encoders/world models, active inference, GFlowNets, and probabilistic graph reasoning: mathematical and engineered components already available.

Existing work makes blanket novelty claims inappropriate. The project would be interesting if it established a new **causal organization of persistent, experience-shaped, significance-steered internal exploration**, not merely if it uses familiar terms differently. The [bibliography](SOURCES.md) names primary sources; the [historical atlas](archive/ATLAS-2026-10-22.md) retains previously surveyed architecture families and open objections.

## J. Continue the conversation

Preserve uncomfortable objections and contradictory design ideas. If a new thought changes the north star, update VISION with explicit rationale and previous-history reference, then re-evaluate the active atlas. Never allow a short-term benchmarking project, a local laborant implementation or a favorite neural mechanism to redefine the aim by inertia.
