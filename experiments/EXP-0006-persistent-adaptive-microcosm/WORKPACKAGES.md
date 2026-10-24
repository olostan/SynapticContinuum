# EXP-0006 — Minimal research execution plan

Design is not authorization to run an expensive campaign. Keep each implementation to a separate PR and one bounded question, review at each scientific gate. The Linux laborant is a smaller model; Principal Researcher owns mathematical semantics, falsification, independent audit. Do not automatically launch all packages, even if the experiment design is merged.

| Stage | Task | Result and abort condition |
| --- | --- | --- |
| WP-00 | **World specification/oracle only** — Python stdlib deterministic generator, hand-checkable transitions, observations and heldout split contracts; simple symbolic reference | Full tests for causality/visibility; STOP if leakage, invalid state or train/test overlap |
| WP-01 | **Learnability baselines** — memoryless, fair symbolic belief tracker, time-aware GRU or simple SSM under identical observation stream | End-to-end small task learned / failure properly diagnosed; STOP if tasks impossible, too easy or evaluation unreliable |
| WP-02 | **Persistent student** — independent fast/slow activity, controllable idle updates, online adaptive memory/eligibility, consistent read-only probes and checkpoints | Oracle/comparison to control, deterministic interruption/restart; STOP if state not persistent or progress explained by compute |
| WP-03 | **Teacher protocol** — local Ollama model discovery+resource planning; validated JSON signal, logged teacher decisions, curriculum/reward ablations | Teacher-free gains under controlled budgets; STOP if failures, hallucinated truth, leakage or resource pressure |
| WP-04 | **Longitudinal synthesis** — learning/gap/forgetting/transfer curves, intervention test, parameter screen and growth extrapolation report | GO/NO-GO relative to explicit simpler baselines, next falsifiable experiment or stop recommendation |

**Independent effort:** one laborant at a time. WP-00 and WP-01 should work on Linux without LLM. WP-02 starts with portable CPU reference / PyTorch as needed; use validated C++ from EXP-0003/4 only where it helps, NOT as imported scientific semantics. WP-03 optional local teacher sequential with simulation on 16GB Linux or Mac 48GB after headroom check; no implied GPU support. No hour-long campaigns without director approval and a pilot showing scientific value. 5-minute pilot cell cap; Linux max incremental RSS min(60% MemAvailable, 6GiB); stop on swap/OOM/CPU contention.

**Mandatory checkpoints per WP:**
1. Read SPEC/WORLD/STUDENT/TEACHER/MEASUREMENT/manifest and predecessor evidence. Preflight plan lists exact files, legal dependency versions, sizes and golden test.
2. Minimal source prototype with standalone deterministic tests. One commit.
3. Independent heldout/oracle and adversarial correctness tests, including deliberate failure. One commit.
4. Run bounded screening cells, record raw evidence, all failures and provenance; no sweeping until Principal GO.
5. Write report section, PR to main, independent scientific GO/CHANGES REQUESTED/NO-GO, owner acceptance. No laborant self-merge or self-authorized redefinition.

**One-session handoff:** A fresh laborant session per complex WP after previous merge is preferred; transfer by immutable repository docs and source SHA, not chat summaries. If pausing a WP, hand off a pinned SHA, unfinished tests, blocked commands, environment and exact next small step, then stop.
