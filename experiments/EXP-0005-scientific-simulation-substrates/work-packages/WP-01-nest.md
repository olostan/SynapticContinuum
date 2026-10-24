# WP-01 — NEST native hybrid scheduling and synapse-memory evaluation

**Prerequisite:** independently reviewed WP-00; G0 approval. **Owns:** EXP-0005/backends/nest/, tests/nest/, configs/nest/ and small runs/nest/. Separate PR. Goal: native NEST scheduling/precision/memory architecture; do not transplant EXP-0004 engine.

## Official sources / code
https://nest-simulator.readthedocs.io/en/stable/neurons/simulations_with_precise_spike_times.html ; https://nest-simulator.readthedocs.io/en/stable/nest_behavior/built-in_timers.html ; https://nest-simulator.readthedocs.io/en/stable/synapses/synapse_specification.html ; https://nest-simulator.readthedocs.io/en/main/models/stdp_synapse.html ; https://nest-simulator.readthedocs.io/en/main/model_details/flush_event_mechanism.html ; https://github.com/nest/nest-simulator. Inspect actual pinned tag's Python model names, thread controls, synapse timing rules and license BEFORE coding.

## Architecture plan required
Document neuron-update dt h, min-delay d_min, spike delivery batching, recording overhead, MPI rank/thread split, initial connection preparations, available precise cell family, built-in plasticity semantics. Explain why NEST grid spike and exact delta-LIF oracle may NOT have exact state parity. No e-prop claim unless actual supported model implemented.

## Milestones and explicit environment commands (pilot)
A. 'python3 --version; python3 -c "import nest; print(nest.__version__)"' and 'command -v nest-config || true'; record whether present. If missing, inspect official installation requirements, propose a pinned-user-env/isolated package installation, log package manifest; no unapproved system-wide installation or arbitrary pip version guessing.
B. Minimal native PyNEST spike_generator -> 1 iaf_psc_delta neuron -> spike_recorder, clock resolution 0.1ms, delays >=h, monitor one neuron. Use one of WP-00 fixtures with explicit ms/mV parameter mapping. Commit simple native script and proof of captured spike count/time. If native model cannot reproduce hand oracle exactly, report qualitative mismatch and expected tolerance; no bit parity.
C. Golden A/B/C model mapping, grid dt sweep where feasible, one 'precise' neuron if version supports it. Assert numerical error and controlled event count; check different default neuron model parameters and initialization before comparing.
D. Add small 128/1024/10k native networks, 1/2/4/6 OpenMP threads where supported (not automatically MPI), sparse vs sustained, disconnected/random/modular; 100ms then 10s. Measure built-in 'time_construction_create','time_construction_connect','time_simulate' and process RSS. Separate first 'Simulate' setup from subsequent portions; verify actual post-input spikes and events available; unknown internal event counts remain null.
E. Native STDP off vs on and _hom vs normal/_hpc variant only if version supports meaningfully comparable model; report that STDP precise-fraction support differs. Optional flush/history requires separate reviewer approval.

## Acceptance / evidence
Exact NEST version+upstream license, script+model defaults, h and d_min, adapted fixture checksum, golden error curves, built-in and external timing, cold-first and warm, all seeds/reps, RSS including construction, active neuron counts and spike histogram. Do not treat NEST spike counters as unique delivered edge events without evidence. Must pass >3 hand-reviewed native tests before benchmarks. Stop if installation fails or authoritative native model semantics cannot be mapped; report unsupported rather than approximate secretly.
