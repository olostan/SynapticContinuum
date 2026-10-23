# Idea space: Stability, chaos, and the skeptical case

**Status:** competing hypotheses; not a claim that chaos produces intelligence.

## Stability and computation are not opposites
A useful neural dynamical system might need attractor-like stability to preserve concepts while retaining sensitivity to informative new evidence. Convergence, oscillation, sensitive dependence, and chaotic-looking traces are not intrinsically useful.

## Diagnostics
- Norms and numerical exceptions across hundreds of updates.
- Effective state rank, feature diversity, and pairwise cosine similarity.
- Response to small perturbations and time to recovery.
- Approximate Jacobian singular values or Lyapunov measures (with interpretation limits).
- Dependency on iteration count and training horizon.
- Task accuracy and compute efficiency, not just visual activity complexity.

## Adversarial explanations
1. More compute alone explains any apparent benefit.
2. The pretrained model alone already encoded the correct answer.
3. A recurrent GNN or external memory achieves the same task result.
4. Scheduled updates are as good as learned dynamic activation.
5. Continuous state simply memorizes, without reasoning.
6. An implicit equilibrium solver achieves similar computation with better stability.
7. Extra cycles cause distribution drift rather than improvement.

## Negative-results culture
Publish clear failures: collapse to fixed points, chaotic explosion, no benefit from extra cycles, no transfer beyond training steps, inferior compute-efficiency, and inability to read latent states coherently.

## A serious competing research program
Perhaps progress in reasoning comes chiefly from training objectives, better verifiable rewards, and adaptive allocation of compute—not from persistent activation. Design compute-matched tests that could prefer this interpretation.

## Pointers
- Naive frozen looping can degrade quality: https://arxiv.org/abs/2605.23872
- Deep equilibrium models: https://arxiv.org/abs/1909.01377
- Counterevidence in latent reasoning: https://arxiv.org/abs/2512.11816
