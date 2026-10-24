# WP-03 — Arbor native cell groups, recipes and morphological integration

**Prerequisites:** WP-00, numerical semantics review. **Owned:** EXP-0005/backends/arbor/, tests/arbor/, configs/arbor/, compact runs/arbor/. Separate PR.

## Upstream references
https://docs.arbor-sim.org/en/stable/concepts/ ; https://docs.arbor-sim.org/en/latest/concepts/lif_cell.html ; https://docs.arbor-sim.org/en/latest/concepts/domdec.html ; https://docs.arbor-sim.org/en/latest/dev/communication.html ; https://github.com/arbor-sim/arbor. Pin version/commit and verify actual available Python or C++ installation, CPU/GPU context and MPI support.

## Key architecture question
Arbor's recipe specifies cell kind/description/connections and domain decomposition assigns whole cell groups to CPU/GPU; its lif_cell has a fixed single-compartment impulse model and **cannot** carry arbitrary channel mechanisms. Compare point-LIF with numerical tolerance first. Only in separately reviewed stage introduce a *real cable cell* with documented morphology, compartments, channel mechanism, solver dt and state samples. Never label 100 compartments as 100 independent neurons.

## Milestones / commands
A. Discover 'python3 -c "import arbor; print(arbor.__version__)"' (if native binding available) and 'cmake --version; c++ --version; mpirun --version' if installed; propose pinned native build/install after reviewing actual docs and library license.
B. Implement one source-cell feeding a native lif_cell via recipe using documented spike_source_cell and connection; record source spike, target spike, simple membrane probe; commit smallest native example and unit tests.
C. Hand-oracle A/B/C cases with delay and refractory, document Arbor lif differential equation units and impulse conversion. Check timestamp resolution/solver defaults. Compare error curves without bit parity. Test known cell source/target labels, avoid accidental disconnected model.
D. Recipe-generated 128/1024/10k native lif network with injected sparse and sustained activity, disconnected/random/modular, CPU 1/2/4/6 threads if API; measure graph construction, domain decomposition, spike-exchange, solver, output and RSS if measurable. Count spikes, actual active cells and deliveries if public API exposes them; otherwise null.
E. Separately approved cable-native minimal 2/4 compartment passive-dendrite model and one synapse, independent small numerical convergence test, then short native cell-group performance. Record *compartment* count, mechanism count, integration steps, memory, dt/error and longer horizon. GPU deferred.

## Acceptance and traps
Prove truly native arbor::simulation / recipe or API equivalents, not standalone C++ reimplementation. Document context and partition. LIF can be compared observably to impulse oracle; cable is native-only scientific capability until matched physical model validated. No cross-system throughput conclusion based on identical neuron count alone. All output and memory phase boundaries reproducible. If Arbor package missing on Linux and build cost exceeds budget, stop after installation feasibility and report blocker.
