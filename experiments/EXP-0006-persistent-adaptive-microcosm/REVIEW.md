# EXP-0006 — Independent scientific design review prompts

Give **GO / CHANGES REQUESTED / NO-GO**, cite exact document sections, and require specific fixes for deficiencies. No pressure to implement just because design is extensive.

1. **Central falsification:** Would the proposed result truly test continually evolving internal neural computation, or only conventional memory/recurrent prediction with extra updates? Which null baseline is missing?
2. **World validity:** Can an independent human compute ground-truth nested containment and hidden-location outcomes from the specified rules? Are impossible cases rejected rather than resampled until favorable? Does observation leak a hidden relation?
3. **Data leakage:** Are train, validation and holdout disjoint in causal **templates**, not only RNG seeds? Are evaluation probes nonmutating and the LLM blind to heldout truth?
4. **Time semantics:** Distinguish no sensory input while world moves, student updates, no internal updates, teacher pause, process restart, teacher outage and teacher withdrawal. Which recorded fields establish they differ?
5. **Checkpoint exactness:** Do snapshots cover optimizer, local eligibility, RNG, queued events, world truth and observation cursor? Is no-feedback teacher pause equal to uninterrupted run?
6. **Teacher source:** Could a deterministic world oracle and fixed teacher curriculum yield the same gain? Are LLM scores checked against factual truth and capped? No human-readable thought traces as student targets by default.
7. **Controls/equity:** Comparable student/GRU/SSM access to timestamps, training examples, updates, capacity, CPU work, teacher-call counts and heldout data? If not, is the non-equivalence explicit?
8. **Statistical validity:** Are five student trajectories sufficient for a **screening** inference but not overclaimed; paired seed CI, failures, multiple parameter explorations, family-level effects reported; no validation-driven heldout overfitting?
9. **Causality:** State perturbation paired with sham and equal compute, on frozen environment and matched observation streams; is a correlated state probe mistakenly called cognitive meaning?
10. **Beyond toy world:** Does student architecture support variable ID count and relational depth without adding hardcoded slots or replacing trained weights? Are memory/compute tradeoffs recorded?
11. **Budget:** Is the pilot minimal enough for Linux 16GB and Mac 48GB without an assumed GPU or expensive Ollama co-residency? Are abort thresholds and large artifact policies binding?
12. **What if all null?** Does the plan specify a STOP or redirection instead of endless optimization? Should EXP-0005 native backends remain deferred?
13. **Prior-art honesty:** DreamerV3, recurrent liquid states, neural CA, RLAIF, small world benchmarks. Identify the precise potential difference, not 'we built dynamics'.

**Initial verdict requested for this PR:** scientific rigor and scope of the design only. REPORT remains NOT RUN; do not request simulator performance charts as a condition for design GO.
