# E002 — Latent neural cellular automaton on formal tasks

**Status:** proposed, not executed · **Type:** small model trained from scratch · **Supports:** [H4/H7](../ATLAS.md#2-competing-core-hypotheses)

## Research question
Can interacting latent cells trained with local update rules solve graph problems beyond the depth seen in training and remain useful under perturbations?

## Baseline model
Generate small directed/undirected graphs (8–128 nodes). Assign each node a 32–64-dimensional latent vector and optional source/target markers. Share a small message/update network across nodes. Update synchronously or select a subset; intermediate outputs are **not language tokens**. Use a separate binary readout for reachability or other exact property.

One candidate step:
`m_i = mean_j M(s_i, s_j, edge_ij)`
`s_i <- LayerNorm(s_i + sigmoid(g(s_i,m_i)) * Delta(s_i,m_i))`.

## Training plan
Train on synthetic reachable/not-reachable graphs with variable unroll counts, e.g. 4–16 updates. Evaluate at 1, 2, 4, 8, 16, 32, 64, 128 updates on distinct graphs with held-out larger diameters. Monitor gradient truncation and stability.

## Required controls
1. BFS or constraint propagation oracle.
2. Matched standard message-passing GNN.
3. Same model with shuffled graph edges, random weights, and frozen readout.
4. Zero additional update model.
5. Synchronous and asynchronous updates with **matched node-update counts**.

## Success criteria and extensions
Plot accuracy against update steps, graph diameter, and active computation. Probe perturbation recovery and state collapse. A graph-reachability recurrent GNN isn't novel by itself. Only after a credible baseline should we inject frozen LLM embeddings and add snapshot language readout. Start background reading: https://distill.pub/2020/growing-ca/.
