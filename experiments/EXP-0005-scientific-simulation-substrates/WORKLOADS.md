# Canonical workload identity & portability map

## Existing canonical material
EXP-0004 owns fixtures at ../EXP-0004-topology-adaptive-scheduling/configs/ and the workload registry ../EXP-0004-topology-adaptive-scheduling/BENCHMARK_CATALOG.md. Reference **config JSON path, raw bytes SHA-256, generator commit, seed and graph/input checksum**. These configs are *definitions*, not complete graph fixtures: independently regenerate and inspect the actual directed edges, weight/delay/timestamp arrays and hashes. Historical 64-bit checksums by themselves do not verify cross-language byte identity. Do not silently assume the generated graph is equivalent.

## EXP-0005 identifiers
Use workload IDs 'sc05/analytic-leak/v1', 'sc05/analytic-threshold/v1', 'sc05/replay/v1', 'sc05/disconnected/v1', 'sc05/random/v1', 'sc05/smallworld/v1', 'sc05/modular/v1', 'sc05/hierarchical/v1', 'sc05/plastic/v1', 'sc05/long-silence/v1', 'sc05/recurrent-sustained/v1', 'sc05/ross-causality/v1'. Each **workload_instance_id** is SHA-256 of canonical UTF-8 config serialization plus fixture files and seed (record recipe, canonicalization rule, and fixture file hashes). Backend, compiler, threads, numerical_dt and model_semantics are RUN variant attributes and must not change the identity of the workload's intended stimulus. If adapting stimulus (quantization/rounding), record adapted_input_sha256 as separate field.

## Golden self-contained fixtures (independent hand-oracle)
A. passive decay: V(0)=0.8 mV, E_L=0, tau=10 ms, sample V at 0/10/20 ms: 0.8, 0.8/e, 0.8/e² mV. No spikes.
B. threshold/reset: V(0)=0, inputs [(1,0.4),(3,0.4),(4,0.4)] in (ms,mV), tau 10ms, threshold 1 mV, reset 0, refractory 2 ms. Analytic V(3+)≈0.72749 mV; V(4+)≈1.05825 mV triggers one spike at 4 ms under exact event processing. If a simulator enforces end-step threshold checks report its model-specific spike time / error. Same-time events test is separate; do not rely on ambiguous tie order.
C. causality chain: A -> B -> C directed, delay 2 ms per link, A emits at 1 ms; B/C receive no earlier than 3/5 ms. No negative time, duplicate or loss. Map to cell-specific external spike generators carefully; spike threshold optional for delivery-only oracle.
D. optimistic rollback fixture: two LPs, LP0 computes a later event then receives a lower-time message; reverses previous state, RNG changes and child messages. Require explicit proof of rollback and replay against a sequential independent committed-event trace, plus --synch=6 or version-supported rollback-check mode.

## Graph and stimulus transport
Plan a versioned, backend-neutral *small* JSON/CSV fixture export with sorted (src_id,dst_id,delay_ms,weight_mV) rows, explicit duplicates/self-edge rules, and sorted external (t_ms,target_id,weight_mV,ordinal) rows. 128/1024 fixture files may live in Git within size policy; larger **generated** data stays external with hashes, regeneration code and opt-in retention. Avoid importing a prebuilt EXP-0004 in-memory CSR engine as a native backend. A single fixture emitter (or two independent emitters under audit) may be reused for comparability. Unit conversion MUST be explicit.

## Comparability vs availability matrix
'Analytic delta-LIF', 'native grid-LIF', 'plastic traces', 'multi-compartment', 'Time Warp LP' are **different semantic capabilities**. A backend row is classified as: equivalent-exact (rare, proven), aligned-with-tolerance, different-neural-model, native-only, or unsupported. The validation agent must approve classification before a cross-backend chart. Synthetic spikes alone do not establish cognitive emergence.

## Scale matrix and stopping
Pilot: N=128/1024, D=4/16, time=0.1s; then N=10k,D=16,horizon=10s for random/modular/disconnected and sparse/dense, including fixed silent interval. Advance to 100k, D 4/16 and horizon=100s only after G1–G3 plus 60%-available RAM gate. Scale axes **independently**: (i) allocation-only network N/M with 0 stimuli, (ii) externally driven spike trains with feedback off, (iii) recurrent activity and actual updates per biological second, (iv) plastic and long-history costs. Optional hour-long wall run is a discrete owner-approved experiment. No full Cartesian sweep.
