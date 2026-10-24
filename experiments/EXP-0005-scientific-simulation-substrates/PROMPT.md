# EXP-0005 — Delegation contract for execution agent

**DESIGN PR ONLY — NOT RUN.** Do not start benchmarking until Research Director explicitly approves the design and Principal Researcher assigns an approved single WP. See [LINUX-LABORANT-PROMPT.md](LINUX-LABORANT-PROMPT.md) for complete copy-paste version.

## Required initial response, before writing source
1. Identify **assigned WP identifier** and source branch/commit, confirm experiment design state.
2. Read ../../AGENTS.md, ../../EXPERIMENTATION.md, ../../FOUNDATIONS.md, SPEC.md, manifest.yaml, WORKLOADS.md, EVIDENCE.md, WORKPACKAGES.md, own WP and SOURCES.md. Inspect relevant EXP-0004 benchmark catalog, report and canonical configs.
3. Show actual Linux system discovery: CPU, cores, MemTotal/MemAvailable, swap, distro/kernel, compiler, CMake/Python/MPI availability, available disk, detected library and version, current background memory footprint; **no assumed 32 GB upgrade**.
4. Propose smallest native upstream example, semantic mapping table, 3 specific golden tests, actual build/install commands and version pin, branch isolation, expected memory/time upper bounds, commit checkpoints.
5. Flag uncertain API/library/precision/availability. Do not guess. Await review for expensive steps or semantic alteration.

## Mandatory implementation behavior
- Implement one work package at a time. Use upstream framework's own execution engine (NEST, Brian codegen, Arbor, ROSS), not a renamed EXP-0004 adapter. Cite exact upstream version/commit and docs.
- Never claim a second implementation is an independent oracle if it shares execution logic with the system under test. Ensure analytic formula or hand-derived expected values exist first.
- Keep graph fixture source paths, hashes and seed identities; preserve independent external historical baseline.
- Adopt appropriate strict/approx/native-only semantic classifications. Demonstrate why threshold, refractory, connection delay, precision and integration match or differ. Unsupported feature may remain unsupported.
- Do not alter preregistration after results; append date-justified AMENDMENTS.md for changes, demote impacted analysis to exploratory.
- Instrument end-to-end versus compile/setup/simulation/readout, peak measured RSS, active population and actual event/update counts. ROSS: distinguish processed/rollback/committed.
- Do not broaden scale before oracle and small-run review. Cancel on memory/swap/timeout safety breach; retain failure evidence.
- Store generated code, traces, binaries, graph dumps and checkpoint files **outside Git**, with SHA-256 manifest. No fabricated evidence or missing-data defaults. Only small metrics/configs/source/reports committed.
- Keep periodic isolated commits after prototype, tests, instrumentation and measured experiments, open **unmerged** implementation PR, with commands, full commit IDs, reproducible artifacts, failures, limitations and requested review decision.

## Required reporting packet
Exact source/build/install commands; version+license; native-code evidence (model definitions, generated project path+hash or C/MPI forward/reverse callbacks); input SHA-256 and adapted-input SHA-256; golden oracle results and tolerance; raw per-seed repetitions; timing and peak RSS; failure cases/unsupported fields; commit and branch; links to retained artifacts and checksum or truthful 'not retained'; scientific claims explicitly scoped; red flags requiring reviewer judgment.

**STOP / report:** compiler error, insufficient memory, ambiguous unit, inaccessible upstream source, inconsistent digest, non-reproducible behavior, ROSS rollback absent, NEST/Brian/Arbor model mismatch, or output stream not committed under optimistic PDES. Do not patch over with fabricated input, relaxed requirements, wrong library, or unreviewed numerical changes.
