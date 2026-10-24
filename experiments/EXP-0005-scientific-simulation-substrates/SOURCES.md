# EXP-0005 annotated original-source reading list (2026-10-24)

Sources were checked for **documented architectural behavior**; they were NOT independently reproduced on the laboratory hardware. Pin git tags/SHAs of actual installed libraries at implementation time; a documentation URL may describe a newer version.

## NEST
- https://www.nest-simulator.org/ (October 2026 site lists NEST 3.10; verify installed release)
- https://nest-simulator.readthedocs.io/en/stable/neurons/simulations_with_precise_spike_times.html — h vs d_min scheduling; precise vs grid.
- https://nest-simulator.readthedocs.io/en/stable/nest_behavior/built-in_timers.html — separate network construction, first-call prep and simulation timing.
- https://nest-simulator.readthedocs.io/en/stable/synapses/synapse_specification.html — homogeneous and HPC connection storage variants.
- https://nest-simulator.readthedocs.io/en/main/models/stdp_synapse.html — native STDP and precise timing caveat.
- https://nest-simulator.readthedocs.io/en/main/model_details/flush_event_mechanism.html — spike-silent event-driven plasticity trace-history memory pressure; promising lead, not evaluated here.
- Upstream code: https://github.com/nest/nest-simulator

## Brian 2
- https://brian2.readthedocs.io/en/stable/user/computation.html — compiler generation + cpp_standalone and OpenMP caution; differentiate runtime and native compiled runs.
- https://brian2.readthedocs.io/en/stable/advanced/preferences.html — standalone/OpenMP configuration.
- https://brian2.readthedocs.io/en/stable/introduction/known_issues.html — unique output directory for concurrent standalone runs.
- Upstream code: https://github.com/brian-team/brian2

## Arbor
- https://docs.arbor-sim.org/en/stable/concepts/ — cell recipe, groups, sim and recording.
- https://docs.arbor-sim.org/en/latest/concepts/lif_cell.html — LIF impulse differential equation and constraints.
- https://docs.arbor-sim.org/en/latest/concepts/domdec.html — CPU/GPU grouping.
- https://docs.arbor-sim.org/en/latest/dev/communication.html — communication between cell groups and spike exchange.
- Upstream code: https://github.com/arbor-sim/arbor

## ROSS
- https://ross-org.github.io/ — ROSS official documentation and release 8.1.0 announcement.
- https://ross-org.github.io/model-dev/lp-type-callbacks.html — forward/reverse/commit callbacks.
- https://ross-org.github.io/feature/checking-reverse-handler.html — --synch=6 validates reversibility including RNG.
- https://ross-org.github.io/feature/gvt-hook.html — GVT hook semantics and reversible triggers.
- https://github.com/ROSS-org/ROSS — official C/MPI code and run modes; inspect model examples from target tag.
- https://ross-org.github.io/setup/running-sim.html — synch modes 1/2/3/4 and memory options.

## Secondary/deferred
- https://www.neuronsimulator.org/en/latest/coreneuron/running-a-simulation.html — CoreNEURON as optimized NEURON backend.
- https://github.com/genn-team/genn — investigate only if GPU/build feasibility is established.
- https://doi.org/10.1162/neco.2007.19.1.47 — Morrison et al., precise spike propagation (NEST).
- https://doi.org/10.1109/ICPP.1985.42 — Jefferson's Time Warp foundational work (verify full bibliographic citation before formal publication).
- Internal historical evidence: [EXP-0004 REPORT](../EXP-0004-topology-adaptive-scheduling/REPORT.md), [EXP-0003 REPORT](../EXP-0003-native-engine-scaling/REPORT.md), [EXP-0002 REPORT](../EXP-0002-event-driven-dynamics/REPORT.md), [EXP-0001 REPORT](../EXP-0001-temporal-memory/REPORT.md).

**Licensing:** Repo is Apache-2.0; upstream NEST GPL and other licenses remain independent. Do not copy external source into this repo without license review; use native installed APIs/builds and short original adapters.
