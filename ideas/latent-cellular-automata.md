# Idea: Neural cellular automata over semantic latent states

**Status:** hypothesis · **Related:** [Atlas H4](../ATLAS.md#h4--local-interaction-rules-can-produce-task-relevant-global-computation) · [E002](../experiments/E002-latent-ca.md)

## Hypothesis
Learned local update rules operating over persistent latent vector "cells" could produce global task-relevant computation without generating vocabulary tokens. A pretrained LM could later initialize these cells, inject observations, or decode an immutable state snapshot.

## What counts as a neighbor?
- **Spatial:** adjacent grid cells, excellent for validating dynamics and path finding.
- **Task graph:** nodes tied by a problem's edges or constraints; good for falsifiable tests.
- **Learned semantic graph:** neighbors selected through latent similarity, gating, or learned relations.

Begin with task-graph neighbors. Learning update rules *and* topology simultaneously confounds the first results.

## Candidate local rule
For node `i`, neighbors `N(i)`:

```
message_i = aggregate(message_net(state_j, edge_ji) for j in N(i))
delta_i = update_net(state_i, message_i)
state_i = normalize(state_i + sigmoid(gate_net(state_i, message_i)) * delta_i)
```

This is a recurrent graph neural network / neural CA baseline, **not itself a novel architecture**.

## Experimental ladder
1. Synthetic graph reachability and constraint propagation with hidden-state updates only.
2. Evaluate generalization across graph diameters and extra recurrent cycles.
3. Inject embeddings from a frozen LM; compare against ordinary embedding classifiers and GNNs.
4. Attach readout/decoder without introducing token generation into the recurrent transition.
5. Explore persistent state across multiple observations and dynamic/sparse routing.

## Hard objections
Graph structure could encode the answer; the frozen LM might already solve the task; simple message passing might match performance; self-organized patterns might be computationally irrelevant.

## Smallest decisive result
On held-out longer graph paths, compare against a fixed-depth GNN, equal-parameter recurrent GNN, and exact BFS oracle. Plot accuracy vs graph diameter and *total node-update budget*. Preserve unsuccessful trajectories and interventions.
