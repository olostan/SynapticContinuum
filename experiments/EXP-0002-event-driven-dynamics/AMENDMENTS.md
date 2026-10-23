# EXP-0002 Protocol Amendments Log

**Status:** NO AMENDMENTS REQUIRED.  
**Date:** 2026-10-23  
**Experiment:** EXP-0002 Event-Driven Dynamics and Temporal Memory  
**Governed by:** [EXPERIMENTATION.md](../../EXPERIMENTATION.md) and [SPEC.md](SPEC.md)

---

## 1. Protocol Adherence Summary

All experimental stages (Stage 0, Stage 1, Stage 2, Stage 3) and tasks (Tasks A, B, C, D, E) executed in strict adherence to the preregistered specification in `SPEC.md` and constraints in `manifest.yaml`.

- **SPEC.md Integrity:** `SPEC.md` was preserved immutable-first and untouched.
- **Resource Constraints:** Peak memory RSS remained under 600 MB (well below the 10 GiB limit). Total campaign execution time was 232.04 seconds (~3.9 minutes, well below the 360-minute budget).
- **Parity & Controls:**
  - Evaluated exact mathematical parity between Event-Driven (lazy decay), Event-Driven (eager), Dense Synchronous ($dt \in \{0.2, 0.1, 0.05\}$), and Sparse Synchronous ($dt \in \{0.2, 0.1, 0.05\}$).
  - Explicit $[\Delta t, \log(1+\Delta t)]$ clock features were strictly withheld from Task B readout models.
  - Negative controls (SHAM intervention, matched-compute arithmetic, external-only passive decay) were fully evaluated across all 5 primary seeds.
- **No exploratory deviations or post hoc metric redefinitions were introduced.**
