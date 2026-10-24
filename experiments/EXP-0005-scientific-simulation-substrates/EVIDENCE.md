# Scientific evidence, benchmark atlas and artifact retention

## Invariant: result ≠ claim
EXP-0004 retained schema v1.0.0 and its historical files must remain **unchanged**. EXP-0005 proposes a side-by-side 'atlas v2 extension' (JSON schema and validator to be written in WP-00), never casting fixed-dt or different models to exact EXP-0004 parity. Map shared fields losslessly where definitions match; include source_schema_version and provenance of original records; if semantics change, define a new metric, never overwrite a historical one. The canonical benchmark triple (benchmark_id, graph_checksum, input_events_checksum) from EXP-0004 remains valid for queries on historical data. EXP-0005 adds SHA-256 fixture identity and explicit semantic fingerprints, so historical same-name workloads are **not** assumed identical without byte confirmation.

## Compact per-run record contract (proposal, schema in WP-00)
Required: schema_version='2.0.0-sc05-proposal' until validator approved; unique run_id (UTC+host+seed+backend+build); experiment_id, branch, full git SHA, dirty flag, backend/source tag+SHA/license, build/compiler/CMake and flags, Python/package lock, OS/kernel/container, CPU model/core/SMT and physical memory, command+environment, lifecycle timing (install/compile/network construction/first call/steady simulation/readout), distinct simulated_horizon_ms and wall_time_s, seed + versioned RNG stream IDs, graph config/checksum, input config/checksum, adapted input hash, neuron count, directed edge count, cell compartment count where relevant, actual active neurons and participation definition, externally injected events, committed spikes, synapse deliveries, neuron integration steps, scheduler processed events and rolled-back events (if applicable), throughput with explicit denominator definition, peak process RSS, available memory at start/end, swap/OOM, full repetition array, warmup count, confidence method, failure/timeout/exit status, numerical model and solver/dt/precision, outcome trace checksum, validation status/tier, monitor policy, raw-evidence artifact refs and SHA-256, unsupported/null fields with explanation.

**No zeros for unmeasured fields:** absent/null + 'not-measured' reason. Counts across engines need explicit name and semantics. ROSS's processed events include undone work; report rolled_back, reexecuted and *committed* event rates separately. NEST may expose spikes but not every internal synaptic operation: mark unknown when no instrumentation.

## Proof of reproducibility
- Check exact primary source / dependency tags with Git SHAs when possible, release hashes, licenses, compiler version and ABI. Record build commands in a shell script with explicit versions; do not use moving 'latest' as reproducible identifier.
- Shell capture /usr/bin/time -v (maximum RSS, faults) and in-process timers if available; validate unit convention (KiB vs bytes, VmHWM vs /proc/self/statm), timing contamination, OS process-tree accounting. Use external memory sampler for child processes if needed, note undercount risks.
- Validation layer independently verifies timestamp monotonicity in **committed** event order when required, checksum of output, analytic oracle, numerical error at aligned readout timestamps; use native solver domain acceptance for mismatched models.
- Repeat >=5 when cell is a primary conclusion; store each seed/repetition and workload identity before aggregates; report all failed and excluded cases with reason.
- Attach audit trace or minimal fixture that reproduced surprising positive/negative outcomes, not only an agent-composed prose summary.

## Archiving
**Git:** design/specs/implementation, small fixtures and configuration, validation source, reports and compact json/csv metrics, optional diagrams (<=1MiB file and <=5MiB per-run checked-in evidence by EXPERIMENTATION.md). **Outside Git:** compiled binaries, NEST/Arbor/Brian outputs, Brian generated C++, ROSS builds and checkpoint dumps, full traces, graph exports > limit, profiler captures, MPI/OS logs, snapshots and time-series files. Recommended '$SC_ARTIFACT_ROOT/EXP-0005/<run_id>/' outside repo; include SHA-256, path/URI, byte count, privacy/licensing, create/reproduce command, retention_status {retained, deleted, missing} and a permanent descriptive manifest small enough for Git. Never claim deleted local files remain retrievable. No credentials/private data committed.

## Long-term atlas questions
For each backend identify **feasible allocation size** (N,M, RSS), **sustained useful activity** (active neurons+synaptic deliveries/simulated second, simulated horizon, activity stationarity), **fidelity frontier** (model dt/error/memory), **plasticity-history cost**, **parallel causality overhead**, **end-to-end reproducibility** and **unsupported mechanisms**. A run on Mac cannot share a Linux hardware Pareto frontier without hardware stratum. Never rank incompatible semantic classes on raw events/sec.

## Independent audit checklist
1. Can an independent run regenerate exact fixture bytes and numerical output reference?
2. Are all timing boundaries explicit, including generated compile and first simulation?
3. Are events actually committed and sustained, not just queued, allocated or repeatedly rolled back?
4. Are memory maxima measured including construction and child processes, not idealized payload only?
5. Are numerical discrepancies accepted, characterized, or unmeasured? Is the model mapping honest?
6. Are all seeds, failures, unsupported cases included? Is the raw proof archived or reproducible?
7. Does a claimed architectural advantage survive a backend-native control and feature-equivalent baseline?
8. Has an independent human/agent verified one smoke case without consuming implementation agent's own result generator as oracle?
