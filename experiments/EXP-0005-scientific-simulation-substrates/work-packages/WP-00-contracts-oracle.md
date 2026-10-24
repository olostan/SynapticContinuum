# WP-00 — Workload transport, independent golden oracle and atlas v2 scaffolding

**Owner:** Linux laborant after G0 approval. **First and only initial implementation assignment.** Deliver separate reviewable PR; no framework installation or performance tests.

## Why
EXP-0004 defined extensive topology/workload records, but its v1 build_id enum is locked to 'portable_o3'/'znver3_o3' and its exact serial digest cannot certify cross-framework numerical equivalence. We need native fixture bytes, independent small mathematical oracle and new schema without mutating history.

## Inputs and owned files
Read EXP-0004 BENCHMARK_CATALOG.md, schemas/benchmark_schema.json, configs/canonical_modular_sbm_n100k.json, configs/canonical_disconnected_control_n100k.json, scripts/pareto_query.py (READ ONLY). Write ONLY under EXP-0005/fixtures/, EXP-0005/oracle/, EXP-0005/schemas/, EXP-0005/tests/, EXP-0005/scripts/ and small EXP-0005/runs/. No import of EXP-0004 source engines into oracle; may use historical configs as named data sources if translation documented.

## Source and mathematical contract
Use SPEC.md / WORKLOADS.md analytic delta-LIF definition and worked examples. Implement scalar Python standard-library oracle for passive analytic leak, *ordered* signed instantaneous arrivals, refractory clamp and threshold/reset; one connection delay; never use code from NEST/Brian/Arbor/ROSS or EXP-0004 engine for expected values. Derive hand results before implementation.
Golden A V(t)=0.8*exp(-t/10) at t=10,20 ms to 1e-12 for Python 64-bit.
Golden B 3 arrivals at 1,3,4 ms as specified; exactly one threshold crossing at 4ms under oracle; use explicit tolerance 1e-10 in analytic arithmetic.
Golden C causal A->B->C delay 2ms; earliest deliveries 3 and 5ms. Additional adversarial same-time arrivals: tie by (timestamp,target,src,ordinal), test explicit multiple arrival policy and clamp.

## Implementation milestones and commands
1. Inspect Python3 interpreter; use stdlib JSON, csv, hashlib, unittest for minimal dependency. 'python3 --version'; 'python3 -m unittest discover -s experiments/EXP-0005-scientific-simulation-substrates/tests -v' from repo root (create discoverable tests).
2. Commit original WORKLOADS format and tiny committed fixture export (<= 1MiB), deterministic sorted CSV/JSON bytes, SHA-256 manifest, units, direction, duplicate policy, generator CLI with --seed --output outside Git for large outputs. Never claim cross-language hash equality until independently read both.
3. Commit hand-verified oracle and falsification tests: wrong delay, negative time, corrupt checksums, altered weight, mixed unit, same-time event and refractory; at least three expected failures.
4. Add new 'schemas/sc05_benchmark_v2.json' JSON Schema without modifying v1, plus standalone validator and example **clearly marked synthetic validation sample NOT A RUN**. Required null/unsupported reasons and no default inference; validator must reject mismatched fixture/model identity and unsupported parity claims. If external jsonschema unavailable, mark schema validation unavailable instead of falsely using a substitute.
5. Commit report with actual tests, hashes, environment and limitations; no zero-cost benchmark claims. Open separate WP-00 PR.

## Review gates
Independent reviewer hand-computes golden B and checks source independence. Fixture byte identity reproducible on rerun. v1 remains unchanged. v2 captures solver, model semantic signature, warmed/cold times, active state, committed events, rollback, RSS, SHA-256 and missingness. Fail before cross-backend comparison if any collision or false exactness. Stop/ask on mismatched EXP-0004 generator/checksums or memory changes.
