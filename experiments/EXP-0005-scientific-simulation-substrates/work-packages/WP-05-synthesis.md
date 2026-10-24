# WP-05 — Independent validation, interpretation and atlas synthesis

**Owner:** Principal Researcher or independent specialist, NOT implementation laborant. Start after >=2 audited backend WPs and continue as remaining tracks complete. Owns EXP-0005/synthesis/ and reviewed REPORT.md updates; propose atlas v2 integration separately. No automatic main merge.

## Inputs and tests
Read SPEC/manifest/EVIDENCE, original upstream docs/source, code for each native backend, raw compact records + verifiable external artifact manifests, EXP-0004 v1 historical catalog. Independently regenerate golden B and at least one cross-backend fixture from *its raw bytes*; do not accept code's own reference output as truth. Audit implementation correctness of each native API, time grid/delay semantics and optimistic rollback proof.

## Work stages
1. Build semantic capability matrix (A analytic micro; B aligned with tolerance; C native-only; unsupported) for each backend/mode/dt/plasticity/horizon. Explicitly refuse fake direct rankings.
2. Validate v2 records vs actual raw sample outputs and subprocess memory, see rejected/null cells. Compare runs only within exact workload bytes, model equivalence, hardware and fidelity strata; one category may remain non-comparable.
3. Check cold total and steady sim separately, each seed and repetitions (>=5 for primary), variance/CI, process vs child RSS, activity during duration not just allocation. Require ROSS committed rates and rollback overhead.
4. Construct a **phase diagram** indexed by actual spike traffic, solver cost, dt/accuracy, history depth, topology locality, simulated horizon and active population; identify Pareto-optimal (not merely fastest) native capabilities.
5. Retain ALL failures, scope limitations and model mismatches; explicitly contrast EXP-0004 10M low-activity allocation result with **measured** sustained activity.
6. Produce research decision: which native mechanism to prototype independently next (e.g. multirate integration, reversible short-term plasticity, trace flush, generated state kernels) with matched null controls; avoid declaring cognition.

## Acceptance
Reviewed REPORT claims link to actual v2 record IDs and exact source/build hashes. At least one independently reproduced microfixture, peer-reviewed semantic map, clear error bars, stop/failure ledger, source references, active vs allocated distinction and three prioritized next tests. Post GO/CHANGES REQUESTED/NO-GO as a comment on each implementation PR; only owner merges.
