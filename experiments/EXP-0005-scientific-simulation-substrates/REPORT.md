# EXP-0005 — Scientific Simulation Substrates: Results

**Status: NOT RUN — DESIGN ONLY.** 2026-10-24.

No EXP-0005 installations, native adapters, numeric results or benchmark runs have been performed or independently validated by this design submission. No relative simulator performance ranking exists. Preliminary architecture descriptions are literature/source documentation research only; see [ARCHITECTURES.md](ARCHITECTURES.md) and [SOURCES.md](SOURCES.md).

## Planned sections after execution
1. Approved design commit + amendment history.
2. Machine and pinned runtime/toolchain audit.
3. Backend native algorithm and numerical-semantic mapping table.
4. Golden oracle test results and cross-framework fidelity error curves.
5. Per-workload, per-seed timing (cold/warm), sustained activity and measured peak RSS.
6. Recurrent/plastic and long-horizon resource/fidelity curves.
7. ROSS optimistic rollback/GVT evidence (or a documented failure).
8. Cross-backend capability Pareto and historical EXP-0004 contextual comparison.
9. Limitations, negative evidence, artifacts with SHA-256 and reproducible commands.
10. Independent review record and scientifically justified next hypotheses.

**Historical evidence (not a result of EXP-0005):** EXP-0004 reported successful allocation/execution at N=10M,D=16, with approximately 1.57M processed events and ~6.49GB peak RSS; don't convert it into a sustained 10M-active-neuron claim.
