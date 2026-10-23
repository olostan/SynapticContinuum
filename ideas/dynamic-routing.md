# Idea: Dynamic routing among computational regions

**Status:** speculative architecture · **Related:** [Atlas H3](../ATLAS.md#h3--learned-dynamic-routing-is-advantageous-over-a-fixed-recurrent-cycle)

## Core idea
Instead of a fixed stack or fixed recurrent cycle, stateful computational regions exchange messages. Current activity, novelty, and learned local conditions determine which regions run next. Language output is just one possible consumer of the state, never the clock governing the network.

A region has state `s_i`, an update operator `U_i`, an incoming message set, and optional activation priority. In a discrete simulator:

```python
active = select_regions(states, pending_messages, update_budget)
for i in active:
    next_state, outgoing = update(i, states[i], inbox[i])
    states[i] = next_state
    route(outgoing)
```

This approximates asynchronous activation with discrete events; it is not mathematically continuous physical time.

## Five routing mechanisms worth comparing
1. All regions update synchronously (strong baseline).
2. Fixed round-robin updates.
3. Event/novelty threshold updates.
4. Trainable gating network selecting active regions.
5. Local competition, where activations propagate through neighborhoods without a global scheduler.

Dynamic sparse computation may **increase** GPU latency because of dispatch overhead; distinguish update-count savings from measured wall time and energy.

## Specific research questions
- Can a region be revisited repeatedly without requiring every other region to execute?
- Does routing specialization emerge from training, rather than being designed into labels such as "memory" or "contradiction"?
- Can sparse updates retain or improve exact task correctness with fewer active FLOPs?
- Can a readout take a consistent snapshot while updates continue?
- When is sleep/event-driven wakeup as good as fully continuous activity?

## Failure modes
Starvation; routing collapse to one central hub; unbounded recurrent amplification; brittle scheduling; vanishing gradients through long event chains; complicated activity with no useful results.

## Decisive comparison
Compare dynamic routing with round-robin and synchronous recurrent models, matching active node-updates, parameters, and separate real-world timing measurements. Include scheduler ablation. If routing learns a fixed universal schedule or gains vanish under compute matching, the added complexity is unjustified.
