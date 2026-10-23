"""Preregistered benchmark tasks A, B, C, D, E.

Governed by SPEC.md:
- Task A: Analytically soluble impulse response & delayed propagation error curves.
- Task B: Delayed association WITHOUT explicit delta-time input features.
- Task C: Matched final observation sequences requiring distinct event histories.
- Task D: Post-stimulus evolution, stability, and pathological cascade screening.
- Task E: Causal intervention and post-silence task utility.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from .interventions import InterventionType, apply_intervention
from .memory import BoundedEventHistory, ExponentialTraceBank
from .models import ModelVariant, create_neural_model, inject_endogenous_pacemaker_events
from .queue import Event, EventKind, EventQueue
from .schedulers import (
    DenseSynchronousScheduler,
    EventDrivenScheduler,
    SimulationResult,
    SparseSynchronousScheduler,
)
from .substrate import NeuralGraph, SubstrateConfig, SubstrateState


# ---------------------------------------------------------------------------
# Task A: Analytically Soluble Impulse Response & Timing Error
# ---------------------------------------------------------------------------

def run_task_a_analytic_parity(
    tau_m: float = 5.0,
    impulses: Optional[List[Tuple[float, float]]] = None,
    t_max: float = 20.0,
    dt_list: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate exact analytic continuous trajectory vs Event-Driven and Synchronous simulations.
    Subthreshold single-node impulse response:
    h*(t) = sum_{k: t_k <= t} a_k * exp(-(t - t_k) / tau_m)
    """
    if impulses is None:
        impulses = [(1.0, 0.4), (4.5, 0.3), (10.2, 0.5), (14.0, -0.2)]
    if dt_list is None:
        dt_list = [0.2, 0.1, 0.05]

    def analytic_h(t: float) -> float:
        val = 0.0
        for t_k, a_k in impulses:
            if t >= t_k:
                val += a_k * np.exp(-(t - t_k) / tau_m)
        return float(val)

    # 1. Event-driven simulation
    config = SubstrateConfig(num_nodes=1, tau_m=tau_m, threshold=100.0)  # subthreshold
    graph = NeuralGraph(1, [np.empty((0,), dtype=np.int32)], [np.empty((0,), dtype=np.float32)], [np.empty((0,), dtype=np.float32)])
    ext_events = [(t, 0, amp) for t, amp in impulses]

    ed_scheduler = EventDrivenScheduler(config, graph, lazy_decay=True)
    ed_res = ed_scheduler.run(ext_events, t_max)
    h_ed = float(ed_res.final_potentials[0])
    h_true = analytic_h(t_max)
    ed_abs_err = abs(h_ed - h_true)

    sync_results = {}
    for dt in dt_list:
        dense_sched = DenseSynchronousScheduler(config, graph, dt=dt)
        dense_res = dense_sched.run(ext_events, t_max)
        h_dense = float(dense_res.final_potentials[0])
        dense_err = abs(h_dense - h_true)

        sparse_sched = SparseSynchronousScheduler(config, graph, dt=dt)
        sparse_res = sparse_sched.run(ext_events, t_max)
        h_sparse = float(sparse_res.final_potentials[0])
        sparse_err = abs(h_sparse - h_true)

        sync_results[f"dt_{dt}"] = {
            "dt": dt,
            "dense_pot": h_dense,
            "dense_abs_err": dense_err,
            "dense_wall_sec": dense_res.wall_time_sec,
            "sparse_pot": h_sparse,
            "sparse_abs_err": sparse_err,
            "sparse_wall_sec": sparse_res.wall_time_sec,
        }

    return {
        "t_max": t_max,
        "analytic_truth": h_true,
        "event_driven_pot": h_ed,
        "event_driven_abs_err": ed_abs_err,
        "event_driven_wall_sec": ed_res.wall_time_sec,
        "sync_dt_comparisons": sync_results,
    }


# ---------------------------------------------------------------------------
# Task B: Delayed Association WITHOUT Explicit Clock Features
# ---------------------------------------------------------------------------

@dataclass
class DelayedAssociationSample:
    c1: int  # 0 or 1
    c2: int  # 0 or 1
    t1: float
    t2: float
    delta_t: float
    target: int  # 0 or 1


def generate_task_b_dataset(
    num_samples: int,
    seed: int = 42,
    tau_crit: float = 6.0,
    delta_t_range: Tuple[float, float] = (1.0, 15.0),
) -> List[DelayedAssociationSample]:
    """
    Generate delayed association dataset:
    Target: y = (c1 ^ c2) if delta_t <= tau_crit else 1 - (c1 ^ c2)
    Crucial constraint: timestamps are NOT provided as readout features.
    """
    rng = np.random.default_rng(seed)
    samples: List[DelayedAssociationSample] = []

    for _ in range(num_samples):
        c1 = int(rng.integers(0, 2))
        c2 = int(rng.integers(0, 2))
        t1 = 1.0
        delta_t = float(rng.uniform(delta_t_range[0], delta_t_range[1]))
        t2 = t1 + delta_t

        xor_val = c1 ^ c2
        target = xor_val if delta_t <= tau_crit else (1 - xor_val)

        samples.append(
            DelayedAssociationSample(
                c1=c1,
                c2=c2,
                t1=t1,
                t2=t2,
                delta_t=delta_t,
                target=target,
            )
        )
    return samples


def evaluate_task_b_model(
    samples: List[DelayedAssociationSample],
    num_nodes: int = 128,
    trace_bases_B: int = 4,
    history_capacity_L: int = 16,
    seed: int = 42,
    train_fraction: float = 0.7,
) -> Dict[str, Any]:
    """
    Evaluate delayed association without feeding explicit delta_t to readout.
    Features extracted at t2:
    - Node potentials h(t2)
    - Traces z(t2) (if B > 0)
    - History kernel convolution features (if L > 0)
    Readout is trained using ridge regression / linear classifier on train split.
    """
    config, graph = create_neural_model(
        variant=ModelVariant.DELAYED_FEEDBACK,
        num_nodes=num_nodes,
        seed=seed,
        history_capacity_L=history_capacity_L,
        trace_bases_B=trace_bases_B,
    )

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    kernel_power = lambda dt: (1.0 + dt / 5.0) ** (-1.5)

    for s in samples:
        state = SubstrateState(config)
        queue = EventQueue()

        # Cue 1 at t1: inject into node 0 (if c1=0) or node 1 (if c1=1)
        src_node_c1 = 0 if s.c1 == 0 else 1
        queue.push(s.t1, source=-1, target=src_node_c1, amplitude=1.2, kind=EventKind.EXTERNAL)

        # Cue 2 at t2: inject into node 2 (if c2=0) or node 3 (if c2=1)
        src_node_c2 = 2 if s.c2 == 0 else 3
        queue.push(s.t2, source=-1, target=src_node_c2, amplitude=1.2, kind=EventKind.EXTERNAL)

        # Simulate until t2 + 0.1
        t_eval = s.t2 + 0.1
        while not queue.is_empty():
            ev = queue.pop()
            if ev.timestamp > t_eval:
                break
            fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
            if fired:
                targets = graph.adj_targets[ev.target]
                weights = graph.adj_weights[ev.target]
                delays = graph.adj_delays[ev.target]
                for i in range(len(targets)):
                    arr_t = ev.timestamp + float(delays[i])
                    if arr_t <= t_eval:
                        queue.push(arr_t, ev.target, int(targets[i]), float(weights[i]), EventKind.SPIKE)

        # Advance state to t_eval
        state.advance_all_potentials(t_eval)

        # Construct feature vector:
        # 1. potentials h (N,)
        feats = [state.potentials.copy()]

        # 2. traces z (N * B) if B > 0
        if trace_bases_B > 0:
            traces = state.trace_bank.get_all_values(t_eval)
            feats.append(traces.flatten())

        # 3. history kernel features if L > 0
        if history_capacity_L > 0:
            hist_feats = np.zeros(num_nodes, dtype=np.float32)
            for n in range(num_nodes):
                hist_feats[n] = state.history.query_kernel(n, t_eval, kernel_power)
            feats.append(hist_feats)

        feature_vector = np.concatenate(feats)
        X_list.append(feature_vector)
        y_list.append(s.target)

    X = np.stack(X_list, axis=0)  # (N_samples, D_feats)
    y = np.array(y_list, dtype=np.int32)

    # Train / Test split
    num_train = int(len(samples) * train_fraction)
    X_train, X_test = X[:num_train], X[num_train:]
    y_train, y_test = y[:num_train], y[num_train:]

    # Standardize
    mean = np.mean(X_train, axis=0, keepdims=True)
    std = np.std(X_train, axis=0, keepdims=True) + 1e-6
    X_train_norm = (X_train - mean) / std
    X_test_norm = (X_test - mean) / std

    # Add bias
    X_train_ext = np.hstack([X_train_norm, np.ones((len(X_train), 1))])
    X_test_ext = np.hstack([X_test_norm, np.ones((len(X_test), 1))])

    # Ridge regression solution: w = (X^T X + lambda I)^-1 X^T y_signed
    y_signed = 2.0 * y_train - 1.0
    reg = 1.0
    A = X_train_ext.T @ X_train_ext + reg * np.eye(X_train_ext.shape[1])
    w = np.linalg.solve(A, X_train_ext.T @ y_signed)

    # Predictions
    preds_train = (X_train_ext @ w >= 0.0).astype(np.int32)
    preds_test = (X_test_ext @ w >= 0.0).astype(np.int32)

    acc_train = float(np.mean(preds_train == y_train))
    acc_test = float(np.mean(preds_test == y_test))

    # Balanced accuracy on test
    pos_mask = y_test == 1
    neg_mask = y_test == 0
    tpr = float(np.mean(preds_test[pos_mask] == 1)) if np.any(pos_mask) else 0.5
    tnr = float(np.mean(preds_test[neg_mask] == 0)) if np.any(neg_mask) else 0.5
    balanced_acc_test = float(0.5 * (tpr + tnr))

    # Memory accounting
    trace_bytes = state.trace_bank.storage_bytes
    history_bytes = state.history.storage_bytes

    return {
        "num_nodes": num_nodes,
        "trace_bases_B": trace_bases_B,
        "history_capacity_L": history_capacity_L,
        "train_acc": acc_train,
        "test_acc": acc_test,
        "test_balanced_acc": balanced_acc_test,
        "trace_bytes": trace_bytes,
        "history_bytes": history_bytes,
        "total_memory_bytes": trace_bytes + history_bytes,
    }


# ---------------------------------------------------------------------------
# Task C: Matched Final Observation Sequences
# ---------------------------------------------------------------------------

def run_task_c_matched_observation(
    num_nodes: int = 128,
    trace_bases_B: int = 4,
    history_capacity_L: int = 16,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Test discrimination of sequences with identical final observation:
    Seq 0: Pulse at t=1.0, quiet at t=8.0, final probe pulse at t=15.0.
    Seq 1: Quiet at t=1.0, pulse at t=8.0, final probe pulse at t=15.0.
    """
    config, graph = create_neural_model(
        variant=ModelVariant.DELAYED_FEEDBACK,
        num_nodes=num_nodes,
        seed=seed,
        history_capacity_L=history_capacity_L,
        trace_bases_B=trace_bases_B,
    )

    t_eval = 15.1
    # Run Seq 0
    s0 = SubstrateState(config)
    q0 = EventQueue()
    q0.push(1.0, -1, 0, 1.5, EventKind.EXTERNAL)
    q0.push(15.0, -1, 5, 1.0, EventKind.PROBE)

    while not q0.is_empty():
        ev = q0.pop()
        if ev.timestamp > t_eval:
            break
        fired = s0.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
        if fired:
            for j in range(len(graph.adj_targets[ev.target])):
                arr_t = ev.timestamp + float(graph.adj_delays[ev.target][j])
                if arr_t <= t_eval:
                    q0.push(arr_t, ev.target, int(graph.adj_targets[ev.target][j]), float(graph.adj_weights[ev.target][j]))

    s0.advance_all_potentials(t_eval)

    # Run Seq 1
    s1 = SubstrateState(config)
    q1 = EventQueue()
    q1.push(8.0, -1, 0, 1.5, EventKind.EXTERNAL)
    q1.push(15.0, -1, 5, 1.0, EventKind.PROBE)

    while not q1.is_empty():
        ev = q1.pop()
        if ev.timestamp > t_eval:
            break
        fired = s1.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
        if fired:
            for j in range(len(graph.adj_targets[ev.target])):
                arr_t = ev.timestamp + float(graph.adj_delays[ev.target][j])
                if arr_t <= t_eval:
                    q1.push(arr_t, ev.target, int(graph.adj_targets[ev.target][j]), float(graph.adj_weights[ev.target][j]))

    s1.advance_all_potentials(t_eval)

    # Measure Euclidean distance between final states
    pot_diff = float(np.linalg.norm(s0.potentials - s1.potentials))
    trace_diff = (
        float(np.linalg.norm(s0.trace_bank.get_all_values(t_eval) - s1.trace_bank.get_all_values(t_eval)))
        if trace_bases_B > 0
        else 0.0
    )

    return {
        "num_nodes": num_nodes,
        "trace_bases_B": trace_bases_B,
        "history_capacity_L": history_capacity_L,
        "potential_l2_diff": pot_diff,
        "trace_l2_diff": trace_diff,
        "discriminable": (pot_diff > 1e-3 or trace_diff > 1e-3),
    }


# ---------------------------------------------------------------------------
# Task D: Post-Stimulus Evolution & Stability Across Silence
# ---------------------------------------------------------------------------

def run_task_d_silence_stability(
    model_variant: str,
    num_nodes: int = 128,
    silence_gap: float = 10.0,
    seed: int = 42,
    max_events: int = 50_000,
) -> Dict[str, Any]:
    """
    Measure stability and event production during sensory silence:
    - Stimulus phase: t in [0, 5.0]
    - Silence phase: t in [5.0, 5.0 + silence_gap]
    """
    t_stim = 5.0
    t_max = t_stim + silence_gap

    config, graph = create_neural_model(
        variant=model_variant,
        num_nodes=num_nodes,
        seed=seed,
    )

    state = SubstrateState(config)
    queue = EventQueue(max_capacity=max_events)

    # Injected stimulus: 10 initial pulses in [0, 3.0]
    rng = np.random.default_rng(seed)
    for _ in range(15):
        t_in = float(rng.uniform(0.5, 3.5))
        node_in = int(rng.integers(0, num_nodes))
        queue.push(t_in, -1, node_in, 1.2, EventKind.EXTERNAL)

    # If intrinsic oscillator, inject pacemaker events
    if model_variant == ModelVariant.INTRINSIC_OSCILLATOR:
        inject_endogenous_pacemaker_events(
            queue, num_nodes, start_time=t_stim, end_time=t_max, seed=seed
        )

    events_stim = 0
    events_silence = 0
    spikes_silence = 0
    runaway = False
    absorbing = False

    try:
        while not queue.is_empty():
            ev = queue.pop()
            if ev.timestamp > t_max:
                break

            if ev.timestamp < t_stim:
                events_stim += 1
            else:
                events_silence += 1

            fired = state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
            if fired:
                if ev.timestamp >= t_stim:
                    spikes_silence += 1
                targets = graph.adj_targets[ev.target]
                weights = graph.adj_weights[ev.target]
                delays = graph.adj_delays[ev.target]
                for i in range(len(targets)):
                    arr_t = ev.timestamp + float(delays[i])
                    if arr_t <= t_max:
                        queue.push(arr_t, ev.target, int(targets[i]), float(weights[i]), EventKind.SPIKE)

            if events_stim + events_silence >= max_events:
                runaway = True
                break
    except Exception:
        runaway = True

    # Check absorbing state: did firing die out to 0 during silence?
    if spikes_silence == 0:
        absorbing = True

    is_sustained = (spikes_silence > 0) and not runaway

    return {
        "model_variant": model_variant,
        "num_nodes": num_nodes,
        "silence_gap": silence_gap,
        "events_stim": events_stim,
        "events_silence": events_silence,
        "spikes_silence": spikes_silence,
        "is_sustained": is_sustained,
        "is_absorbing": absorbing,
        "is_runaway": runaway,
        "peak_queue": queue.peak_size,
    }


# ---------------------------------------------------------------------------
# Task E: Causal Intervention & Post-Silence Task Utility
# ---------------------------------------------------------------------------

def run_task_e_causal_intervention_study(
    model_variant: str,
    intervention_type: InterventionType,
    num_nodes: int = 128,
    silence_gap: float = 10.0,
    seed: int = 42,
    trace_bases_B: int = 4,
    history_capacity_L: int = 16,
) -> Dict[str, Any]:
    """
    Execute full causal intervention pipeline:
    1. Stimulus phase: [0, 4.0]
    2. Silence phase: [4.0, 4.0 + silence_gap]
    3. At t_int = 4.0 + silence_gap / 2: apply intervention.
    4. At t_probe = 4.0 + silence_gap: inject probe and measure state divergence ||Delta h||_2
       and downstream task decision compared to intact control.
    """
    t_stim = 4.0
    t_int = t_stim + silence_gap / 2.0
    t_probe = t_stim + silence_gap

    config, graph = create_neural_model(
        variant=model_variant,
        num_nodes=num_nodes,
        seed=seed,
        trace_bases_B=trace_bases_B,
        history_capacity_L=history_capacity_L,
    )

    # 1. First run intact simulation (NONE intervention)
    intact_state = SubstrateState(config)
    intact_queue = EventQueue(max_capacity=500_000)

    # External inputs
    rng = np.random.default_rng(seed)
    for _ in range(12):
        t_in = float(rng.uniform(0.5, 3.5))
        node_in = int(rng.integers(0, num_nodes))
        intact_queue.push(t_in, -1, node_in, 1.2, EventKind.EXTERNAL)

    if model_variant == ModelVariant.INTRINSIC_OSCILLATOR:
        inject_endogenous_pacemaker_events(
            intact_queue, num_nodes, start_time=t_stim, end_time=t_probe, seed=seed
        )

    # Probe event at t_probe
    intact_queue.push(t_probe, -1, 0, 1.0, EventKind.PROBE)

    while not intact_queue.is_empty():
        ev = intact_queue.pop()
        if ev.timestamp > t_probe + 0.1:
            break
        fired = intact_state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
        if fired:
            for j in range(len(graph.adj_targets[ev.target])):
                arr_t = ev.timestamp + float(graph.adj_delays[ev.target][j])
                if arr_t <= t_probe + 0.1:
                    intact_queue.push(arr_t, ev.target, int(graph.adj_targets[ev.target][j]), float(graph.adj_weights[ev.target][j]))

    intact_state.advance_all_potentials(t_probe)
    h_intact = intact_state.potentials.copy()
    spikes_intact = intact_state.total_spikes

    # 2. Second run with intervention at t_int
    test_state = SubstrateState(config)
    test_queue = EventQueue(max_capacity=500_000)

    # Re-inject identical external inputs
    rng_re = np.random.default_rng(seed)
    for _ in range(12):
        t_in = float(rng_re.uniform(0.5, 3.5))
        node_in = int(rng_re.integers(0, num_nodes))
        test_queue.push(t_in, -1, node_in, 1.2, EventKind.EXTERNAL)

    if model_variant == ModelVariant.INTRINSIC_OSCILLATOR:
        inject_endogenous_pacemaker_events(
            test_queue, num_nodes, start_time=t_stim, end_time=t_probe, seed=seed
        )

    test_queue.push(t_probe, -1, 0, 1.0, EventKind.PROBE)

    intervention_applied = False
    interv_info: Dict[str, Any] = {}
    frozen_potentials: Optional[np.ndarray] = None

    while not test_queue.is_empty():
        # Check if reached t_int and intervention not yet applied
        peek_ev = test_queue.peek()
        if peek_ev is not None and peek_ev.timestamp >= t_int and not intervention_applied:
            test_state.advance_all_potentials(t_int)
            frozen_potentials = test_state.potentials.copy()
            interv_info = apply_intervention(
                queue=test_queue,
                state=test_state,
                intervention_type=intervention_type,
                current_time=t_int,
                t_probe=t_probe,
                seed=seed,
            )
            intervention_applied = True
            if test_queue.is_empty():
                break

        ev = test_queue.pop()
        if ev.timestamp > t_probe + 0.1:
            break

        # If FREEZE was applied, we clamp potentials and don't emit spikes
        if intervention_type == InterventionType.FREEZE and intervention_applied and frozen_potentials is not None:
            test_state.potentials = frozen_potentials.copy()
            continue

        fired = test_state.receive_impulse(ev.target, ev.timestamp, ev.amplitude, ev.kind)
        if fired:
            # If PASSIVE_DECAY was applied, do not propagate downstream spikes
            if intervention_type == InterventionType.PASSIVE_DECAY and intervention_applied:
                continue
            for j in range(len(graph.adj_targets[ev.target])):
                arr_t = ev.timestamp + float(graph.adj_delays[ev.target][j])
                if arr_t <= t_probe + 0.1:
                    test_queue.push(arr_t, ev.target, int(graph.adj_targets[ev.target][j]), float(graph.adj_weights[ev.target][j]))

    test_state.advance_all_potentials(t_probe)
    h_test = test_state.potentials.copy()
    spikes_test = test_state.total_spikes

    # Causal metrics
    state_divergence = float(np.linalg.norm(h_test - h_intact))
    max_state_diff = float(np.max(np.abs(h_test - h_intact)))
    spike_diff = abs(spikes_test - spikes_intact)

    # Decision probe: sign of mean activation across first 10 readout nodes
    decision_intact = int(np.mean(h_intact[:10]) >= 0.0)
    decision_test = int(np.mean(h_test[:10]) >= 0.0)
    decision_flipped = (decision_intact != decision_test)

    return {
        "model_variant": model_variant,
        "intervention": intervention_type.value,
        "num_nodes": num_nodes,
        "silence_gap": silence_gap,
        "state_divergence_l2": state_divergence,
        "max_state_diff": max_state_diff,
        "spikes_intact": spikes_intact,
        "spikes_test": spikes_test,
        "spike_diff": spike_diff,
        "decision_flipped": decision_flipped,
        "intervention_info": interv_info,
    }
