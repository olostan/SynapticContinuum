# R01 source verification ledger

Fields: key | authors (abbreviated) | exact original title | first submission / publication | primary URL | verification scope | result/evidence boundary.

| key | authors | title | date | primary | scope | important limitation |
|---|---|---|---|---|---|---|
| CTM | Darlow, Regan, Risi, Seely, Jones | Continuous Thought Machines | arXiv May 8 2025; v4 Oct 3 2025 | https://arxiv.org/html/2505.05522v4 | **Method equations + RL appendix + official code README** | Distinguish NLM neuron history from edge history; RL similar to LSTM |
| NCDE | Kidger, Morrill, Foster, Lyons | Neural Controlled Differential Equations for Irregular Time Series | arXiv May 18 2020 | https://arxiv.org/abs/2005.08926 | Identity/abstract | No local reproduction |
| TTT | Sun et al. | Learning to (Learn at Test Time): RNNs with Expressive Hidden States | arXiv July 5 2024; v4 Aug 31 2025 | https://arxiv.org/abs/2407.04620 | Identity/abstract | Token sequence TTT layers |
| Coconut | Hao et al. | Training Large Language Models to Reason in a Continuous Latent Space | arXiv Dec 9 2024; v4 Aug 23 2026 | https://arxiv.org/abs/2412.06769 | Identity/abstract | Hidden feedback is position/step scheduled |
| Huginn | Geiping et al. | Scaling up Test-Time Compute with Latent Reasoning: A Recurrent Depth Approach | arXiv Feb 7 2025 | https://arxiv.org/abs/2502.05171 | Identity/abstract | Recurrent depth, not indefinite persistence |
| Looped | L. Chen et al. | Training-Free Looped Transformers | arXiv May 22 2026 | https://arxiv.org/abs/2605.23872 | Identity/abstract | Authors report naive loops hurt |
| T2MLR | Cai et al. | T^2MLR: Transformer with Temporal Middle-Layer Recurrence | arXiv July 16 2026 | https://arxiv.org/abs/2607.15178 | Identity/abstract | Prior-token recurrence |
| LOTUS | Fan, Svete, Lee | Bridging the Gap Between Latent and Explicit Reasoning with Looped Transformers | arXiv June 30 2026 | https://arxiv.org/abs/2606.31779 | Identity/abstract | Gold CoT supervision, not autonomous cognition |
| LTC | Hasani et al. | Liquid Time-constant Networks | arXiv June 8 2020 | https://arxiv.org/abs/2006.04439 | Identity/abstract | Task-specific temporal processing |
| latentRL | Özeren, Aßenmacher | Reinforcement Learning for Latent-Space Thinking in LLMs | arXiv metadata: Nov 26 2025 | https://arxiv.org/abs/2512.11816 | Identity/abstract | Negative math-CoT evidence is task/approach-specific |
| S4 | Gu, Goel, Ré | Efficiently Modeling Long Sequences with Structured State Spaces | arXiv Oct 31 2021 | https://arxiv.org/abs/2111.00396 | Identity/abstract | Strong compressed temporal baseline |
| Mamba | Gu, Dao | Mamba: Linear-Time Sequence Modeling with Selective State Spaces | arXiv Dec 1 2023 | https://arxiv.org/abs/2312.00752 | Identity/abstract | Token/sequence driven |
| Titans | Behrouz, Zhong, Mirrokni | Titans: Learning to Memorize at Test Time | arXiv Dec 31 2024 | https://arxiv.org/abs/2501.00663 | Identity/abstract | Often cited 2025 |
| NHP | Mei, Eisner | The Neural Hawkes Process: A Neurally Self-Modulating Multivariate Point Process | arXiv Dec 29 2016; NIPS 2017 | https://arxiv.org/abs/1612.09328 | Identity/abstract | Event-time recurrence and intensity |
| Moshi | Défossez et al. | Moshi: a speech-text foundation model for real-time dialogue | arXiv Sep 17 2024 | https://arxiv.org/abs/2410.00037 | Identity/abstract | Full duplex still generated codec tokens |
| Plastic | Miconi, Stanley, Clune | Differentiable plasticity: training plastic neural networks with backpropagation | ICML 2018 | https://proceedings.mlr.press/v80/miconi18a.html | Publisher page/abstract | Fast synaptic learning prior art |
| NCA | Mordvintsev, Randazzo, Niklasson, Levin | Growing Neural Cellular Automata | Distill Feb 11 2020; DOI 10.23915/distill.00023 | https://distill.pub/2020/growing-ca/ | Original article and method description | Regeneration ≠ general cognition |
| DEQ | Bai et al. | Deep Equilibrium Models | 2019 | https://arxiv.org/abs/1909.01377 | Repository source lead, **not independently read here** | No method audit |
| UT | Dehghani et al. | Universal Transformers | 2018 | https://arxiv.org/abs/1807.03819 | Repository source lead, **not independently read here** | No method audit |
| eprop | Bellec et al. | A solution to the learning dilemma for recurrent networks of spiking neurons | 2020 | https://www.nature.com/articles/s41467-020-17236-y | Repository source lead, **not independently read here** | Do not equate a toy eligibility trace with full e-prop |
| Crosscoders | Lindsey et al. | Sparse Crosscoders | 2024 | https://transformer-circuits.pub/2024/crosscoders/index.html | Repository source lead, **not independently read here** | Feature study, not recurrent-agent evidence |
| Chaos | Gao | Edge of chaos in echo state networks (repository description) | 2025 | https://www.sciencedirect.com/science/article/pii/S0960077925013463 | **Unverified exact journal metadata/title** | Don't quote exact findings until checked |

Code links identified, not run: https://github.com/SakanaAI/continuous-thought-machines ; https://github.com/facebookresearch/coconut ; https://github.com/princeton-pli/T2MLR ; https://github.com/yingfan-bot/lotus ; https://github.com/locuslab/deq

**Audit methodology:** Reference identity/version claims from primary arXiv/publisher landing pages, specific CTM equations and appendices from arXiv HTML, authors' CTM code repository index/README. “Verified” here is not independent code execution, reproducibility, or endorsement of headline improvements. No measured results produced by R01.
