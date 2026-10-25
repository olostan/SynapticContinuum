# Annotated Research Sources and Novelty Map

**Initial review:** 2026-10-22. All links are to identifiable primary papers, official author pages, or original research posts where possible. This is a curated starting set, not a systematic literature review. A published claim is not equivalent to an independently reproduced result.

## Nearest to our idea

### Continuous Thought Machines (Sakana AI; 2025)
- Paper: https://arxiv.org/abs/2505.05522
- Official explanation: https://sakana.ai/ctm/
- Code: https://github.com/SakanaAI/continuous-thought-machines
- **What it does:** introduces internal neural time, neuron-level history processing, and synchrony-based representations. Reports results across tasks including mazes, classification, and RL.
- **Why we care:** makes temporally unfolding neural activity part of the actual computation, not merely a text-generation metaphor.
- **What it does not establish:** a general-purpose pretrained-LLM retrofit running unbounded, self-organizing activation with an independently triggered speech pathway.
- **Agent question:** How are states initialized, updated, and read out? How does time scale? Does performance increase monotonically with extra updates?

### Training-Free Looped Transformers (Chen et al.; 2026)
- Paper: https://arxiv.org/abs/2605.23872
- **What it does:** loops contiguous mid-stack blocks of frozen pretrained Transformers at inference; reports naive looping usually degrades performance, while damped updates can help on selected benchmarks.
- **Why we care:** the closest accessible starting point for reusing trained weights without immediate retraining.
- **Missing relative to our thesis:** still repeated blocks in a prescribed arrangement and finite evaluation; not free-form dynamic region activation or persistent autonomous state.
- **Agent question:** Which looping strategy and normalization is safe under growing step counts? Is a token-free update path actually exposed by the reference code?

### Huginn — Scaling up Test-Time Compute with Latent Reasoning (Geiping et al.; 2025)
- Paper: https://arxiv.org/abs/2502.05171
- Research portal: https://www.recurrentdepth.org/research
- **What it does:** trains a recurrent-depth model that can increase test-time computation by repeating internal blocks; reports significant improvements in selected settings.
- **Why we care:** strong evidence that repeated latent computation is a real model design choice, not just prompting.
- **Missing:** not a completely order-free, asynchronous, persistent region network; significant pretraining effort.

### T²MLR — Temporal Middle-Layer Recurrence (Cai et al.; 2026)
- Paper: https://arxiv.org/abs/2607.15178
- Code: https://github.com/princeton-pli/T2MLR
- **What it does:** sends information from a deeper middle-layer representation of a prior token into an earlier middle-layer representation of the next token using a light gated recurrent pathway; includes pretrained-model retrofit with finetuning.
- **Why we care:** directly relevant to small trainable cross-layer feedback and preserving pretrained weights.
- **Missing:** recurrent mechanism is tied to token positions; differs from free-running no-token latent state.

### LOTUS — Bridging Latent and Explicit Reasoning (Fan et al.; 2026)
- Paper: https://arxiv.org/abs/2606.31779
- Code: https://github.com/yingfan-bot/lotus
- **What it does:** loops latent blocks with parallel supervision, reporting parity with explicit CoT on some math settings and lower thought-phase latency at 3B parameters.
- **Why we care:** a useful bridge between hidden-state looping, training signals, and readout interpretability.
- **Missing:** a finite reasoning phase followed by decoding, not autonomous continuously routed state.
- **Caution:** reported benefits depend on evaluated tasks, model size, and supervision setup; do not assume transfer to persistent cognition.

### Coconut — Chain of Continuous Thought (Hao et al.; 2024/2025)
- Paper: https://arxiv.org/abs/2412.06769
- Code: https://github.com/facebookresearch/coconut
- **What it does:** feeds hidden-state representations back as subsequent inputs rather than decoding intermediate reasoning words; reports benefits on certain reasoning tasks.
- **Why we care:** direct evidence for latent reasoning without intermediate sampled words.
- **Missing:** feedback is organized around a prescribed series of latent steps rather than a fully persistent dynamic activation graph.
- **Counterevidence:** https://arxiv.org/abs/2512.11816 reports limitations and difficulty matching conventional CoT on mathematical reasoning with some latent RL approaches. Avoid one-sided reading.

## Cellular automata, recurrent dynamics, and stability

### Growing Neural Cellular Automata (Mordvintsev et al.; 2020)
- Original interactive article: https://distill.pub/2020/growing-ca/
- **What it does:** trains differentiable local update rules to grow, persist, and regenerate visual patterns.
- **Why we care:** proof of principle that local learned interactions can create durable global structure.
- **Missing:** no evidence of general language understanding or long-horizon abstract reasoning.

### Universal Transformers (Dehghani et al.; 2018)
- Paper: https://arxiv.org/abs/1807.03819
- **What it does:** applies repeated self-attention transformations and adaptive per-position halting to sequences.
- **Why we care:** historical foundation for recurrent-depth computation and adaptive computation.
- **Missing:** not independent evolving neural regions nor unbounded persistent activity.

### Deep Equilibrium Models (Bai et al.; 2019)
- Paper: https://arxiv.org/abs/1909.01377
- Code: https://github.com/locuslab/deq
- **What it does:** models computation through a fixed point of a weight-tied network rather than an explicitly deep stack, allowing implicit gradients.
- **Why we care:** alternative to endlessly unrolling recurrent steps; provides a principled stability-oriented view.
- **Missing:** seeking a fixed point is not autonomous evolving cognition.

### Neural Ordinary Differential Equations (Chen et al.; 2018)
- Paper: https://arxiv.org/abs/1806.07366
- **What it does:** treats hidden state as a learned continuous-time differential system.
- **Why we care:** foundations for variable-time computation and adaptive numerical integration.
- **Missing:** not a pretrained LM reuse method and not a ready-made cognitive architecture.

### Edge of chaos in echo state networks (Gao; 2025)
- Publication: https://www.sciencedirect.com/science/article/pii/S0960077925013463
- **What it does:** analytically characterizes a critical regime in a specific class of continuous-time echo state networks, with empirical diagnostics.
- **Why we care:** tools for probing recurrence stability and local sensitivity.
- **Caution:** does not prove that operation “at the edge of chaos” maximizes intelligence in arbitrary Transformers or cellular automata.

## Memory, representation and alternative explanations

### Titans — Learning to Memorize at Test Time (Behrouz et al.; 2025)
- Paper: https://arxiv.org/abs/2501.00663
- **What it does:** integrates learnable neural memory with attention and test-time memorization.
- **Why we care:** powerful alternative baseline: perhaps memory and state update, rather than uninterrupted neural thought, explain gains.
- **Missing:** not the same proposition as free-running neural activity with language as conditional output.

### Toy Models of Superposition (Elhage et al.; 2022)
- Original research: https://transformer-circuits.pub/2022/toy_model/index.html
- **What it does:** studies distributed representations and superposition of features.
- **Why we care:** cautions against treating raw neurons as semantically separable computational units.
- **Missing:** does not construct a persistent agentic recurrent system.

### Sparse Crosscoders (Lindsey et al.; 2024)
- Original research: https://transformer-circuits.pub/2024/crosscoders/index.html
- **What it does:** investigates features across multiple layers/models.
- **Why we care:** a potential way to think about region-level routing in a learned feature basis.
- **Caution:** interpreting features is not the same as training useful recurrent feature interactions.

## Open research requests for future scouts

1. Survey **asynchronous event-driven neural computation** with learned selection of active modules and compare training schemes.
2. Survey **spiking neural networks and neuromorphic computation** but avoid assuming biological plausibility is essential for task success.
3. Survey **reservoir computing / criticality / attractor memory** and identify measured limits.
4. Survey **adaptive compute allocation**, recurrent-depth scaling failures, and OOD generalization.
5. Survey **latent-state persistent agents** and distinguish actual recurrent hidden vectors from externally stored text/state.
6. Inspect current Apple Silicon inference/training capabilities at the exact library version. Avoid using outdated blog setup instructions as API guarantees.
7. Search specifically for work that combines pretrained-LM latent representations with **neural CA** or **dynamically activated region graphs**; quantify closest overlaps.

## How to extend this bibliography

For each new source, record title, link, authors/year, method, training/inference budget if stated, what it establishes, what it does **not** establish, and which hypothesis or experiment it informs. Prefer the original paper and implementation to secondary summaries. Add contradictory sources rather than only confirming ones.


## Temporal communication, online learning and live feedback — added 2026-10-22

- [Neural Controlled Differential Equations](https://arxiv.org/abs/2005.08926) (2020): models irregularly sampled input driving continuous hidden dynamics. **Not** a persistent general cognitive substrate.
- [Neural Hawkes Process](https://arxiv.org/abs/1612.09328) (2016): event-triggered recurrent intensity modelling; useful for temporal events. **Not** a learned general reasoning system.
- [S4: Efficiently Modeling Long Sequences with Structured State Spaces](https://arxiv.org/abs/2111.00396) (2021): compact learnable long-term sequence dynamics; candidate baseline against per-edge delay kernels.
- [Mamba](https://arxiv.org/abs/2312.00752) (2023): selective recurrent state conditioned on incoming data; excellent baseline for streaming inputs, **not** an autonomous self-plastic neural field.
- [Moshi: a speech-text foundation model for real-time dialogue](https://arxiv.org/abs/2410.00037) (2024): full-duplex streaming speech handling; uses tokenized audio rather than the postulated shared activation substrate.
- [Differentiable Plasticity](https://proceedings.mlr.press/v80/miconi18a.html) (2018): trainable plastic connections in recurrent networks; relevant to connection-specific fast-changing state.
- [e-prop: A solution to the learning dilemma for recurrent networks of spiking neurons](https://www.nature.com/articles/s41467-020-17236-y) (2020): local eligibility and learning signals, a precedent for delayed modulation; our simplified trace equations are not the full method.
- [Constitutional AI](https://arxiv.org/abs/2212.08073) (2022): illustrates AI-generated feedback. In SynapticContinuum **the reference LLM is a fallible validator, not a teacher or a target to imitate**.

**New comparison questions:** What changes when timestamps are injected versus when extra neural cycles occur during silence? Can compressed source-traces match per-edge temporal kernels? Is an internally emitted communication command distinguishable from observed delivery? What validated outcome provides learning signals when the LLM validator is uncertain?


## 2026-10-24 — New vision: fluid concepts, motivated exploration and nonlinguistic meaning

These are **existing mechanism and theory precedents**, not papers claiming or proving SynapticContinuum's envisioned persistent open-ended inner process. Read [VISION.md](VISION.md) and [ATLAS.md](ATLAS.md) for the distinctions.

### Hofstadter / Mitchell — Copycat: fluid analogy and stochastic micro-agents
- Original cognitive architecture account (Hofstadter & Mitchell, 1995): https://melaniemitchell.me/PapersContent/HofstadterMitchellCopycat1995.pdf
- Historical MIT technical report (Hofstadter, 1984): https://dspace.mit.edu/entities/publication/f5c71f85-e38a-43f6-8897-8dfbb33dbd85
- **Relevance:** slipnet, workspace, stochastic codelets, dynamic temperature, partial analogy and selective attention. **Limit:** predetermined analogy microdomain and explicit conceptual components; do not claim it demonstrates general nonverbal spontaneous lifelong cognition.

### Bach — MicroPsi/Psi and Pei Wang — NARS
- Joscha Bach, *Principles of Synthetic Intelligence: PSI* (2009): https://doi.org/10.1093/acprof:oso/9780195370676.001.0001
- MIT Media Lab MicroPsi overview: https://www.media.mit.edu/projects/micropsi-an-architecture-for-motivated-cognition/overview/
- Pei Wang, NARS version 4.1 overview: https://aaai.org/papers/01135-AAAI00-204-non-axiomatic-reasoning-system-version-4-1/
- **Relevance:** internal drives, priority, context-sensitive processing, limited computation, uncertainty and autonomous behavior. **Limit:** rich prior art for functional goals; requires honest comparison, not a straw-man rule system.

### Oudeyer & Kaplan — intrinsic motivation and developmental exploration
- *What Is Intrinsic Motivation? A Typology of Computational Approaches* (2007): https://doi.org/10.3389/neuro.12.006.2007
- Oudeyer, Kaplan & Hafner, *Intrinsic Motivation Systems for Autonomous Mental Development* (2007): https://www.pyoudeyer.com/ims.pdf
- **Relevance:** curiosity/learning progress, reducible uncertainty, exploration without constant explicit external goals. **Risk:** seeking unpredictable noise; measuring more events does not prove better self-development.

### Schacter & Addis — constructive memory / past and future
- Schacter, Addis & Buckner, *Remembering the Past to Imagine the Future* (2007): https://doi.org/10.1038/nrn2213
- Computational generative reconstruction and replay (2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC10963272/
- **Relevance:** possible shared machinery for imagining future and reconstructing past; **risk:** imaginative trajectories can distort apparent memories. Do not import human neuroscience as proof of an artificial implementation.

### Gentner and distributed representation
- Gentner, *Structure-mapping* (1983): https://doi.org/10.1016/S0364-0213(83)80009-3
- Rigotti et al., *Mixed selectivity in complex cognitive tasks* (2013): https://www.nature.com/articles/nature12160
- Locatello et al., *Challenging Common Assumptions in the Unsupervised Learning of Disentangled Representations* (2019): https://proceedings.mlr.press/v97/locatello19a
- **Relevance:** role/relationship transfer without copying irrelevant attributes, distributed coding, and limits on discovering a privileged factorization with no inductive biases.

### Associative retrieval, diverse possibility generation, temporal neural time
- Ramsauer et al., *Hopfield Networks Is All You Need* (2020): https://arxiv.org/abs/2008.02217
- Bengio et al., *GFlowNet Foundations* (2023): https://www.jmlr.org/papers/v24/22-0364.html
- Sakana AI, *Continuous Thought Machines* (2025): https://arxiv.org/abs/2505.05522
- **Relevance:** partial retrieval, probabilistic candidate exploration, time-dependent population dynamics. **Limit:** retrieving or generating many candidates is not necessarily lifelong autonomous, meaningful development.

### Active inference, appraisal, epistemic action
- Review *Active inference as a theory of sentient behavior* (2024): https://doi.org/10.1016/j.biopsycho.2023.108741
- **Relevance:** alternative mathematical coupling of uncertain beliefs, preferred states and epistemic actions. **Limit:** often assumes generative factors and objectives, and must not be presented as uniquely resolving consciousness.

**Research gaps to assign:** context-dependent nonlinguistic semantic probes; learned significance and priority updating; distinguishing observation from internal imagination; teacher/decoder contamination; persistent cross-episode endogenous influence; analogical role transfer; meaningful self-directed sensing. Cite original works, not merely broad conceptual resemblances.
