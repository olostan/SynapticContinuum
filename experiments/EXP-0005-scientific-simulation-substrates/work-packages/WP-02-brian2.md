# WP-02 — Brian 2 runtime and generated standalone C++

**Prerequisite:** WP-00 accepted. **Owned:** EXP-0005/backends/brian2/, tests/brian2/, configs/brian2/, small runs/brian2/. Native equations and generated project, not hand-written C++ copy.

## Sources
https://brian2.readthedocs.io/en/stable/user/computation.html ; https://brian2.readthedocs.io/en/stable/advanced/preferences.html ; https://brian2.readthedocs.io/en/stable/introduction/known_issues.html ; https://github.com/brian-team/brian2 (record source/version/license). Inspect 'NeuronGroup', 'Synapses', 'SpikeMonitor', 'StateMonitor', 'set_device', 'device.build' in pinned API.

## Scientific variant
Define dV/dt=-(V-E_L)/tau with threshold/reset/refractory explicitly in native Brian equations, weights + synaptic delay; initial V and units from WORKLOADS.md. Choose and justify integration method ('exact' if validated linear ODE, 'euler' numerical control) and network 'defaultclock.dt' with explicit time grid. Initial external SpikeGeneratorGroup -> tiny neuron; then one delayed recurrent fixture.
Separate **(1)** Python NumPy/Cython runtime, **(2)** cpp_standalone single-thread, **(3)** optional cpp_standalone OpenMP threads only after correctness. Plasticity follow-on: Synapses with trace dApre/dt=-Apre/tau : 1 (event-driven) and on_pre/on_post updates; carefully test eligibility update over silence against independent exponential analytical trace. No naive 'event-driven' marker on coupled nonlinear dynamics.

## Milestones / commands
A. Discover 'python3 -m pip --version; python3 -c "import brian2; print(brian2.__version__)"'; create user venv, propose exact pinned package and compiler; do not change system Python. Verify 'g++ --version', 'make --version', 'cmake --version' as applicable.
B. Minimal Brian runtime golden A/B, then standalone: 'set_device("cpp_standalone", directory=OUTSIDE_GIT_DIRECTORY, build_on_run=False)' and 'device.build(directory=..., compile=True, run=True)' using isolated output per seed; generated source and binary hashes manifest.
C. Three analytic tests + dt sweep 0.1/0.05/0.01 ms, against math oracle (not against own generated code). Record spike/state errors and threshold timing policy. Every compile generation must use unique directory; never run parallel jobs over same tree.
D. Test interpreted/compiled pair on same fixture, timers split into Python model graph generation, codegen, C++ compile, binary start, simulation, result read; no comparing warm runtime to cold end-to-end while hiding compiler.
E. Plasticity event-driven trace vs fixed-step trace sample; then staged N=128/1024/10k sparse/moderate/bursty; only then threads 2/4/6 if native generated OpenMP validated. Check docs' OpenMP caution with actual unit tests, no independent speed claims from a flag alone.

## Exact acceptance
Same equation and fixture-derived stimulus within each Brian variant; trace analytic checks, no spike emitted during prohibited refractory window, correct delay, generated C++ present and checksum retained outside Git, explicit integration policy and monitor config. Memory includes C++ child process, not just Python parent. Single-core and thread-run repetitions, seed/compile hashes, wall-sim/e2e. Any incompatibility with precise continuous-time oracle is a valid quantified finding, not an exact parity failure to hide.
