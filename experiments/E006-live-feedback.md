# E006 — Live delayed feedback without freezing the substrate

**State:** proposed · **Question:** can an external validator's delayed signals steer plastic connections and prevent regression without stopping neural dynamics or forcing imitation?

## Mechanism

Communication port emits \`e=(time,event_id,kind,payload,source)\`. Record a small eligibility/causal marker for the responsible recent activity, **not a whole-network snapshot**. The core keeps evolving and possibly accepting new input. Independent outcome tests or a frozen LLM validator produce later feedback keyed by \`event_id\`. Modulate eligible connections using decaying traces. Do not apply delayed negative feedback indiscriminately to whichever cells happen to be active on receipt.

A validator LLM can flag \`challenge\` or \`suspected_regression\` but may not punish a novel, objectively correct prediction merely for disagreeing. In the first experiment an exact simulator oracle is preferable to LLM judgment so truth can be measured.

## Conditions

- no feedback;
- immediate, ground-truth feedback;
- delayed, ground-truth feedback + eligibility;
- delayed feedback **without** event attribution (negative control);
- delayed noisy/inconsistent feedback;
- frozen language validator suggestions plus independent oracle checks (later);
- optional slow consolidation and evolution as *separate* factorial additions.

## Tasks

Timed symbol communication or online prediction in an environment that changes rules over time. Introduce hold-out tasks and previously mastered tasks to evaluate forgetting and preservation of plasticity. Test *actual external delivery* separately from *internally initiated output*.

## Measures

Continuous update throughput, response reward, false output rate, regression on old tasks, learning speed after rule change, state drift/collapse, ability to learn after long operation, cost of the validator, and latency from emitted event to applied feedback. Compare frozen-evolution/sleep controls.

## Important null hypotheses

- ordinary supervised online learning works as well;
- event attribution contributes no benefit;
- more feedback calls—not live feedback—explain gains;
- a stricter validator freezes adaptive capability;
- reward signals select pleasing outputs rather than truthful/useful information.

**Related:** [Adaptive plasticity paper](../ideas/adaptive-plasticity-and-guardrails.md), [Communication](../ideas/communication-as-activation.md).
