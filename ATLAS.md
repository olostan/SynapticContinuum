# Research Atlas: Persistent, Dynamically Routed Neural Computation

**Living document** · initial synthesis **2026-10-22** · exploratory, no single chosen architecture

> This atlas is not a specification to implement. It is a continually revised map of possibilities, confusions, known results, predictions, and experiments. Keep interesting alternatives alive long enough to test them.

## 0. Origin of the idea — preserve this accurately

The motivating intuition is **not** “let an LLM generate more hidden thought tokens.” It is not merely an agent repeatedly prompting an LLM, nor a chatbot with longer context.

A network could remain active without generating text. Its internal activations could propagate among neural regions repeatedly, potentially in a dynamic or asynchronous order. Some regions would influence or activate other regions. The activity might stabilize, oscillate, branch, reorganize, or react to new sensory inputs. A communication process could read this ongoing neural state *when triggered*, while the underlying activity continues. No spoken word, sampled vocabulary item, or decoder output is required for each state transition.

The analogy to **cellular automata, dynamical systems, complexity, and chaos** is about collective behavior emerging from local transitions—not a claim that complex behavior automatically implies intelligence or consciousness.

The pragmatic engineering question is whether an existing pretrained Transformer can be **reused** as a rich learned substrate, possibly with redesigned inference, feedback edges, trainable adapters, LoRA, or a separate dynamic system coupled to its representations. Fully retraining a large language model is not presumed feasible or necessary for first tests.

### Fundamental distinctions

| Conventional token-driven LM | Target concept |
|---|---|
| Prompt-to-response episode | Potentially persistent state across episodes |
| Autoregressive vocabulary sample is core outer loop | Neural-state transition is core loop |
| Hidden activations typically recomputed for each decoding position | Mutable latent state evolves on its own clock |
| Layer order mainly fixed | Dynamic graph / region routing is a hypothesis |
| Cached keys/values mostly preserve past token representations | Active recurrent state is updated over time |
| Communication is the routine product | Communication is a conditional readout |
| More computation usually entails tokens or dedicated latent steps | More computation need not produce symbols |

A qualification: conventional Transformers already perform rich hidden-space computation. The distinctive claim is about **persistent and controllable evolution of hidden neural states, decoupled from vocabulary generation**, not that LMs have no nonlinguistic internal representations.

## 1. Questions that precede any architecture

1. **State**: What persists? A few learned latent slots? A field of cells? Layer-residual streams? Sparse features? A graph of computational regions? A multi-timescale memory?
2. **Time**: Is the system truly event-driven, continuously integrated, synchronously stepped, or asynchronous with a scheduler? In practice all digital prototypes use discrete execution; continuous time can be numerically approximated.
3. **Topology**: Are neighbors spatial, learned semantic neighbors, attention-selected regions, or dynamic edges conditioned on state?
4. **Update semantics**: Does a region update residual-incrementally, replace its state, communicate messages, or perform a block of pretrained Transformer computation?
5. **Initialization**: How does input become a valid active state? Can a frozen pretrained model provide it? Must latent states be learned explicitly?
6. **Readout**: How does a language decoder interpret the state? Does it need an encoder or translator? Can speaking occur without stopping the state loop?
7. **Objective**: What trains the system to make *productive* transitions rather than useless patterns? Final-task reward, intermediate prediction, self-supervision, contrastive learning, distillation, TD learning, synthetic algorithmic tasks?
8. **Stability**: How can it avoid fixed-point collapse, limit cycles, exploding norms, catastrophic memory drift, and degenerate activity?
9. **Persistent memory**: Can the same state survive thousands of steps and new observations, or does it need slower and faster state tiers?
10. **Compute**: How much actual FLOP/latency/energy overhead is introduced? Does dynamic sparsity outperform dense GPU kernels in practice?
11. **Interpretability**: Are “regions” physically neurons, layers, sparse features, slots, or merely convenient engineering partitioning? Raw neurons may be polysemantic.
12. **Agency**: Should it decide to run or speak? What training signal prevents noise-driven spontaneous output?
13. **Evidence**: What results would distinguish useful autonomous latent reasoning from random recurrence plus a powerful frozen decoder?
14. **Novelty**: What do related approaches already establish, and what exact gap remains after reading original methods and code?
15. **Scaling**: Is the technique more compelling at toy scale, ~1B, or larger? Does additional recurrence improve or damage extrapolation?

## 2. Competing core hypotheses

These hypotheses need not all be true. They are deliberately formulated to conflict.

### H1 — Computation can improve in hidden-state loops without intermediate token sampling

**Prediction:** At a fixed input and with no sampled intermediate vocabulary tokens, selected latent recurrences improve accuracy as steps increase (at least over a bounded regime) versus an otherwise identical compute-matched nonrecurrent baseline.

**Threats:** trivial repeated computation, hidden changes unrelated to task, extra compute rather than recurrence, decoder-only leakage, benchmark overfitting.

**Test:** graph reachability, state tracking, modular arithmetic, small planning; step-count sweeps, shuffled feedback, random-weight feedback, and equal FLOPs.

### H2 — Pretrained Transformers can be retrofitted more economically than rebuilding from scratch

**Prediction:** Frozen reused blocks plus carefully damped feedback or a small adapter beat equally sized random dynamical modules on several tasks. Limited LoRA adaptation improves results and long-loop stability.

**Threats:** out-of-distribution feedback vectors; attention causal-mask/position assumptions; context cache semantics; layer interface incompatibility.

**Test:** compare (a) frozen-loop baseline; (b) frozen + trainable state adapters; (c) LoRA feedback; (d) trained-from-scratch small recurrence.

### H3 — Learned dynamic routing is advantageous over a fixed recurrent cycle

**Prediction:** State-dependent scheduling of regions improves accuracy-per-active-compute or generalization on heterogeneous tasks, with ablations fixing the same graph and execution budget.

**Threats:** sparse dispatch overhead dominates GPU gains; routing becomes a fixed schedule; unstable and hard-to-train credit assignment.

**Test:** variable graph tasks, multi-subproblem tasks, routing entropy and specialization analyses, wall-clock and FLOP comparisons.

### H4 — Local interaction rules can produce task-relevant global computation

**Prediction:** A learned graph/neural-cellular-automaton substrate initialized from semantic vectors solves tasks that require multiple propagations, generalizing to larger graphs or more iterations than trained on.

**Threats:** patterns may be visually interesting but semantically arbitrary; task labels may permit shortcut solutions; local models may fail long-range dependencies.

**Test:** seeded graph propagation, shortest path, logical consistency propagation, perturb-and-repair, topology shifts.

### H5 — Persistent state provides gains *across* input episodes

**Prediction:** Carrying forward active latent state aids delayed reasoning or nontrivial memory tasks, even after controlling for explicit context storage and token count.

**Threats:** hidden information leak across episodes; ordinary KV caching or a compact text note matches it; state drift or interference.

**Test:** segmented observation tasks, delayed cues, interruptions, checkpoint/restart, adversarial contradictory updates, retention horizon plots.

### H6 — Communication can be an independent readout

**Prediction:** The system can keep evolving while a frozen or adapted language decoder consumes a *snapshot* of its state, and the language output need not be fed back as cognition.

**Threats:** untrained states are not interpretable by the LM head; apparent gains arise entirely from the reader; speech-trigger thresholds are uncalibrated.

**Test:** read-only probe at steps t=0,4,8,...; inspect probe interference; compare output-trained state versus task-trained state; test conditional readout separately.

### H7 — Productive dynamics occupy a controlled regime between collapse and noise

**Prediction:** Useful performance correlates with robustness and memory capacity, possibly in a parameter range near—not necessarily at—a stability transition.

**Threats:** “edge of chaos” overgeneralization; Jacobian estimates misleading; high activity can be random.

**Test:** gain/coupling sweeps, perturbation response, Lyapunov-like local divergence estimates, task performance surfaces, long-horizon retention.

### H0 — Skeptical null hypothesis

Most observed benefits come from simply spending more compute, keeping larger context, or fitting benchmarks; frozen LM activations are poorly suited for perpetual recurrence, and token-decoded or externally managed reasoning remains more effective per FLOP.

**We actively want tests capable of supporting H0.**

## 3. The architecture landscape (not a decision)

### Family A: Frozen middle-block loops

```
text input -> embedding / early blocks -> h0
                      |                 |
                      +---- repeated middle stack with damping ---> hT
                                                          |
                                                 optional LM readout
```

Use a fixed repeated subset of Transformer blocks, with residual scaling, normalization, or interpolation. Cheapest retrofit to inspect; closest published analog is *Training-Free Looped Transformers* (2026), where naive looping often hurt and damped strategies helped in selected benchmarks. [Source](https://arxiv.org/abs/2605.23872).

**Open question**: Can frozen iteration produce improvement *without sampling more tokens* or changing prompt context? Does state collapse after 10–100 iterations?

### Family B: Learned feedback adapters + LoRA

Use frozen blocks, but learn projection, gating, and small recurrent edges among selected block interfaces. Examples:

```
h_i(t+1) = norm(h_i(t) + alpha_i * G_i(h_i(t), aggregate_j R_ji(h_j(t))))
```

with learned `G`/`R` and optional LoRA applied to reused blocks. Initialize feedback gains near zero so initialization approximates the normal pretrained computation. Distinguish **training a small recurrent controller** from training the pretrained LM itself. LoRA does not solve interface-distribution mismatch automatically.

**Open question**: Can adapters learn stable recurrent state with far less training than end-to-end model pretraining?

### Family C: Neural cellular automata over semantic latent slots

Initialize a set of learned slots/cells from encoder/LM hidden representations. Each slot updates using local or graph-neighbor information. Local update weights may be shared, or conditioned on region type. Inputs can modify a subset while remaining slots continue evolving.

```
s_i(t+1) = s_i(t) + update_theta(s_i(t), messages_from_neighbors(t))
```

Train on propagation and memory tasks before language. Later attach pretrained encoder/readout. Neural CA prior work proves learned local state can exhibit regeneration but **not** that it yields general semantic intelligence. [Source](https://distill.pub/2020/growing-ca/).

**Open question**: Do spatial neighborhoods make sense for semantic representations? What inductive bias should determine the graph?

### Family D: Dynamic asynchronous region graph

Each region has state, neighbors, update rule, and potential activation criterion. A scheduler chooses one or several regions; events/messages flow across directed edges. Crucially, no globally fixed layer order need be preserved.

```
ready-set <- events, surprise, state-change, priorities
while budget remains:
    select a region or a compatible batch
    region_state <- update(region_state, incoming messages)
    emit messages / activate neighbors
```

This is an **operational approximation**, not literal continuous biological spiking. It may be difficult to make faster than dense GPU computation. Benchmarks must include dispatch overhead and batching.

**Open question**: Can meaningful routing arise from local activation rules, or is a global learned scheduler essential?

### Family E: Continuous-time coupled dynamics

Model state as an ODE or stochastic differential system:

```
dh/dt = F_theta(h, observations, memory)
```

Use a numerical integrator, adaptive time steps, or piecewise event-driven updates. Neural ODEs supply mathematical and engineering tools, but their success on other tasks does not validate autonomous LLM cognition. [Source](https://arxiv.org/abs/1806.07366).

**Open question**: Do continuous-time dynamics add an advantage over discrete recurrence with equivalent compute?

### Family F: A two-system hybrid

Use a pretrained LM to *encode observations* and *decode occasional speech*, coupled to a compact persistent latent dynamical substrate that does most intervening updates. Later allow feedback through selected pretrained blocks.

```
observations -> LM encoder/projection -> [ persistent dynamical state ]
                                            <--> slow memory store
                                            <--> modular processors
                                            -> conditional readout -> LM decoder
```

This may be most realistic on consumer hardware. However, a frozen readout may not know how to interpret a novel latent representation; train a bridge or use probe labels. This architecture risks becoming merely an external agent controller unless the persistent substrate learns useful nonlinguistic neural computation.

### Family G: Equilibrium/attractor dynamics

Instead of endlessly traversing the state, learn a stable fixed point or family of attractors under observations. Deep Equilibrium Models are relevant; they solve for fixed points rather than necessarily maintaining autonomous ongoing cognition. [Source](https://arxiv.org/abs/1909.01377).

**Open question**: Perhaps useful persistent cognition needs controlled attractors and transitions rather than perpetual activity.

### Family H: Memory-first variants

Retain fast and slow latent states; attention/KV cache is only one form of passive context. Learned neural memory modules (Titans), recurrent state, external retrieval, and checkpointed latent memories can be compared fairly.

**Open question**: Is persistent latent *computation* essential, or is persistent latent *storage* enough?

## 4. Non-obvious engineering difficulties

### Existing weights assume a computation contract

A pretrained decoder-only LM is not a bag of independently activatable neurons. Its attention projections, rotary position encodings, normalization, residual pathways, MLPs, and KV caches are coordinated by training on a specific causal forward computation. Reusing block `L17` after block `L24` can feed it representations unlike its training distribution. Feedback needs normalization/projection and often training.

### A neural “feature” is not generally one neuron

Superposition and distributed representation studies caution against interpreting individual raw neuron activations as stable semantic modules. Candidate regions include layer blocks, attention heads, learned sparse features, low-rank subspaces, token-independent latent slots, or entire tiny networks. Routing among **features** and routing among **layers** are different hypotheses. [Toy Models of Superposition](https://transformer-circuits.pub/2022/toy_model/index.html).

### KV cache is not a perpetual thought store

A standard autoregressive cache holds past token-position keys/values for reuse. It does not ordinarily evolve while no new tokens are being processed. A recurrent latent state is a separate object; a hybrid may retain both.

### “Asynchronous” and “parallel” are not synonyms

Asynchronous scheduling may permit independently triggered region updates, but updates can be sequential and hardware-unfriendly. “Many neurons active simultaneously” at a conceptual level does not guarantee hardware-concurrent kernels or efficient memory bandwidth. Measure real execution.

### Stability vs capability

A fixed point can be a useful working solution or premature cognitive collapse. Chaotic activity can encode rich dynamics or be mere noise. Measure the relationship of stability to *correct task performance*, not to attractive visualizations alone.

### Continuous activity does not automatically mean persistent personhood or consciousness

The laboratory makes no claim that ongoing state implies awareness, subjective experience, or autonomous agency. Consciousness-inspired metaphors are allowed as hypothesis-generating devices, not evidence.

### Training objectives are the crux

Possible objectives:

- Supervised final-answer correctness after latent iteration.
- Multi-step state transition prediction on formal environments.
- Distillation of intermediary computations from a stronger reference, without requiring textual inner monologue at inference.
- Contrastive losses separating correct/incorrect latent configurations.
- Recurrent state persistence and reconstruction after perturbation.
- Sparse routing costs / compute regularization.
- Self-prediction of observation change; avoid optimizing for state activity itself.

Each objective can introduce shortcuts. Final-answer supervision may rely entirely on the readout; state reconstruction may reward static memorization; activity/diversity regularizers may reward noise; teacher distillation may bake in token-based structure. A good experiment isolates these.

## 5. Experimental principles and controls

**Always distinguish** ordinary text CoT, latent tokens in a serial Transformer pass, genuinely recurrent hidden states, and an external LLM agent loop. They solve related but nonidentical problems.

### Minimum baselines

1. Standard pretrained forward/generation without added internal compute.
2. Same model with equivalent extra compute using simple repeated passes or token-based reasoning.
3. Frozen recurrence with random/shuffled/zero feedback control.
4. Small trainable recurrent module with *no* pretrained weights, matched parameters and training data.
5. Same model with extra context/KV memory but no continually evolving state (when evaluating persistence).

### Important measures

- **Task success**: exact accuracy; pass@1 when appropriate; correctness under depth shift.
- **Compute**: effective active FLOPs, wall time, memory peak, tokens generated, energy proxy if reliable.
- **Improvement with latent time**: curve of accuracy versus internal steps, not a single endpoint.
- **State health**: norm histograms, NaN/Inf rate, cosine similarity through time, state-rank/diversity, convergence rates.
- **Robustness**: behavior after random perturbation, missing inputs, stale memories, long idle iterations, checkpoint/restore.
- **Causality**: ablate feedback edges; freeze/reinitialize gates; intervene on nodes; test whether state changes predict downstream improvements.
- **Routing**: activated regions, event counts, entropy/concentration, fairness of compute comparisons, dispatch overhead.
- **Readout separation**: state-evolution graph must not call an LM head or sample a token during thought updates.
- **Uncertainty**: multiple seeds, confidence intervals or distributions, not cherry-picked traces.

### Initial tasks

- `T1 Graph reachability`: one-bit answer, varied graph sizes/diameters; no implicit text reasoning needed.
- `T2 Path selection`: shortest path/maze; test depth generalization.
- `T3 Constraint propagation`: variable assignment and contradiction detection.
- `T4 Delayed symbol memory`: temporally segmented observations, no readout between segments.
- `T5 Perturb-and-recover`: damage some latent slots then measure exact task recovery.
- `T6 Novel observation after idle`: inject evidence into already evolved state and measure adaptation.

Later: code reasoning / debugging could be relevant, but introduces confounds from model knowledge and tool use. Do not start there.

### Failure criteria worth documenting

- Performance never improves over frozen first-step baseline at matched compute.
- Additional iterations help only when the readout is repeatedly invoked.
- Improvement disappears under equal FLOPs or extra-context baseline.
- Recurrent state rapidly collapses or becomes unstable on longer horizons.
- Dynamic routing is measurably slower and no more accurate than fixed recurrence.
- Small adaptation only memorizes training graph sizes and fails out-of-distribution tasks.
- Apparent intelligence is attributable entirely to pretrained encoder/decoder rather than the recurrent substrate.

## 6. A portfolio of first explorations

These are **parallel probes**, not sequential milestones:

| Probe | Core question | Smallest useful artifact | Follow-on |
|---|---|---|---|
| P1 Frozen reuse | Can pretrained blocks improve a fixed latent state through repeated passes? | Layer-hook script + step sweep | Damped loops, layer-subset search |
| P2 Local dynamics | Can a neural CA solve propagation problems with persistent activations? | Recurrent graph-cell trainer | Couple to LM embeddings |
| P3 Adaptive routing | Can a scheduler learn which regions to update next? | Sparse graph scheduler in toy model | Apply to pretrained blocks |
| P4 Feedback adaptation | Can LoRA/gates make recurrence stable without full retraining? | Controlled adapter ablation | Train longer-horizon dynamics |
| P5 Persistent memory | Is evolving state better than frozen memory across new observations? | Delayed-cue benchmark | Hybrid fast/slow memories |
| P6 Optional readout | Can a language head read evolving state without shaping each step? | Read-only probes | Learned communication gate |
| P7 Skeptical analysis | Are we merely reinventing recurrent depth / agent loops? | Comparative literature matrix and counterexperiments | Refine central claim |

See `experiments/` for first proposed protocols and `ideas/` for alternatives to challenge.

## 7. Data, training, and hardware tradeoffs

- Target **a local Apple Silicon system with ~48 GB unified memory**. Start with NumPy or a lightweight graph/CA implementation; move to MLX or PyTorch/MPS based on actual autograd and hidden-state hook support.
- For pretrained retrofits start with a small open-weight model around 0.5–1.7B parameters. A specific candidate is Qwen3-0.6B, pending architecture inspection and license/model access.
- Do not assume existing `mlx-lm` generation APIs expose the hidden-state update semantics we require. A custom model forward or layer-level hooks may be necessary.
- Start from fp16/bf16 where numerical behavior can be inspected; quantization changes norms and may confound dynamical stability.
- Record backend + exact framework/model revision, hardware, tokenization settings, random seed, dtype and numerical precision.
- For training through hundreds of recurrent steps, watch gradient explosion/vanishing and memory. Compare truncated BPTT, checkpointing, implicit differentiation, or short-run curricula as separate choices.
- Dynamic sparse routing may improve theoretical FLOPs but lose on wall-clock overhead. Optimize for scientific clarity before speed.
- Avoid large GPU checkpoint binaries in Git; retain reproducible scripts, metadata, and external artifact identifiers instead.

## 8. Research tensions worth assigning to opposing agents

**Tension 1:** fixed pretrained geometry vs trainable new latent representation. If the frozen decoder can read a state, are we making the latent system too text-aligned? If it cannot, how much bridge training is required?

**Tension 2:** spontaneous ongoing activity vs compute-aware event-driven sleep. Is persistence a property of retained state or actual uninterrupted numerical evolution? Would sparse wake-on-input provide the same benefits?

**Tension 3:** fixed stable recurrence vs unconstrained dynamical routing. Is a fixed computational circuit a useful inductive bias, or does routing unlock valuable specialization?

**Tension 4:** feature-level nodes vs block-level modules. Does a learned sparse feature basis make meaningful communication graphs possible, or just add interpretability complexity?

**Tension 5:** stable attractors vs long-running exploration. Do we need controlled oscillations/near-critical regimes, or simply a learned contractive recurrent computation with input-conditioned transitions?

**Tension 6:** LoRA vs small standalone latent system. When does adapting pretrained blocks beat using them only for semantic encoding/readout?

**Tension 7:** endogenous speaking gate vs explicit external request. How to define useful, calibrated communication without training a noisy interrupt generator?

**Tension 8:** training supervision vs emergence. How much behavior can emerge from local learning, and how much requires direct task objectives?

## 9. Discovery cycles (not project sprints)

### Round 0 — Sharpen the questions

Parallel agents review the atlas and contribute: missing related work, three best attack points, three reasons the thesis might fail, and one decisive test. The integrator maps disagreements without enforcing consensus.

### Round 1 — Get falsifiable evidence cheaply

Run a small recurrent CA on a formal task and a frozen pretrained loop on a formal language-friendly task. Include two strong controls for each. At this point no persistent autonomous “brain” needs to exist.

### Round 2 — Cross ideas

Design experiments joining the most promising fragments (e.g., pretrained block + trainable feedback, or language embeddings + neural CA). Ask whether cross-component communication is genuinely improving task performance.

### Round 3 — Demonstrate a continuous-state behavior

Create a live state process that takes observations at irregular times, updates when there is no output, and produces an occasional readout from a state snapshot. Prove that the hidden update path contains **zero token samples**. Evaluate it against a sleeping baseline and context-carrying baseline.

### Round 4 — Reassess the thesis

Are we learning a general architectural principle, a narrow engineering trick, or mostly rediscovering established recurrent models? Update claims, do not automatically expand scope.

## 10. Epistemic protocol / living synthesis

Every substantial claim should carry one of these in prose or notes:

- **Observed** — measured locally with linked experiment, code revision, seeds, controls.
- **Reported** — supported by linked paper; identify its setting, limits, and whether reproduced.
- **Hypothesized** — falsifiable prediction awaiting investigation.
- **Speculative** — useful idea, not yet operationalized.
- **Contradicted** — evidence against a prior idea; retain why the belief changed.

Cite paper versions and exact links. Do not turn abstract claims into measured conclusions. Avoid “paper X proves consciousness/AGI” or “complexity is intelligence.” Keep negative results visible.

The atlas should change only when there is something worth synthesizing: new paper evidence, new experiment, clarified concept, or resolved disagreement. Its job is memory with judgement, not a status dashboard.

## 11. Open questions for the next synthesis

- Is there a principled way to define a latent *region* in a pretrained Transformer without assuming individual neurons correspond to concepts?
- Does variable update order introduce harmful race-like nondeterminism, or productive diversity?
- Can a latent state be decodable **and** remain unconstrained enough for more efficient reasoning?
- Can we detect when extra internal computation is still productive without repeatedly decoding candidate answers?
- What is the simplest task demonstrating multi-timescale memory that ordinary context caching cannot match under equal cost?
- How should new observations inject energy/information into an otherwise stable state?
- Could a frozen model plus learned adapters discover new loops that do not correspond to any original layer ordering?
- Can we experimentally distinguish dynamic memory maintenance from autonomous cognition?
- Are different subnetworks actually essential, or can an unexpectedly small, shared recurrent operator match them?
- What would make us *stop* this line of research, or pivot to ordinary recurrent-depth methods?

## 12. Starting bibliography

This is an **entry point**, not an exhaustive review. See [SOURCES.md](SOURCES.md) for limitations and agent assignments.

- Hao et al., *Training Large Language Models to Reason in a Continuous Latent Space (Coconut)* (2024/2025): https://arxiv.org/abs/2412.06769
- Geiping et al., *Scaling up Test-Time Compute with Latent Reasoning* (Huginn, 2025): https://arxiv.org/abs/2502.05171
- Darlow et al., *Continuous Thought Machines* (2025): https://arxiv.org/abs/2505.05522
- Chen et al., *Training-Free Looped Transformers* (2026): https://arxiv.org/abs/2605.23872
- Cai et al., *T²MLR: Transformer with Temporal Middle-Layer Recurrence* (2026): https://arxiv.org/abs/2607.15178
- Fan et al., *Bridging the Gap Between Latent and Explicit Reasoning with Looped Transformers (LOTUS)* (2026): https://arxiv.org/abs/2606.31779
- Mordvintsev et al., *Growing Neural Cellular Automata* (2020): https://distill.pub/2020/growing-ca/
- Bai et al., *Deep Equilibrium Models* (2019): https://arxiv.org/abs/1909.01377
- Chen et al., *Neural Ordinary Differential Equations* (2018): https://arxiv.org/abs/1806.07366
- Dehghani et al., *Universal Transformers* (2018): https://arxiv.org/abs/1807.03819
- Behrouz et al., *Titans: Learning to Memorize at Test Time* (2025): https://arxiv.org/abs/2501.00663
- Elhage et al. / Transformer Circuits, *Toy Models of Superposition* (2022): https://transformer-circuits.pub/2022/toy_model/index.html
- Özeren & Aßenmacher, *Reinforcement Learning for Latent-Space Thinking in LLMs* (2025): https://arxiv.org/abs/2512.11816

---

**Editorial instruction to future synthesizers:** Keep the motivating intuition near the top intact. Add links to supporting and contradicting findings rather than rewriting the thesis to match whichever experiment ran last. Leave exploratory trails visible.
