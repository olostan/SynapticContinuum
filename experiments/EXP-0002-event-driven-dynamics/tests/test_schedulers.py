"""Tests for Event-Driven, Sparse Sync, and Dense Sync schedulers."""
import numpy as np
import pytest
from src.schedulers import (
    DenseSynchronousScheduler,
    EventDrivenScheduler,
    SparseSynchronousScheduler,
)
from src.substrate import NeuralGraph, SubstrateConfig


def test_schedulers_single_branch_parity():
    """Verify event-driven and synchronous simulation parity on a 3-node feedforward chain."""
    config = SubstrateConfig(
        num_nodes=3,
        tau_m=5.0,
        threshold=1.0,
        refractory_period=1.0,
        min_delay=1.0,
        max_delay=1.0,
    )
    # Node 0 -> Node 1 (delay 1.0, weight 1.5)
    # Node 1 -> Node 2 (delay 1.0, weight 1.5)
    adj_targets = [np.array([1], dtype=np.int32), np.array([2], dtype=np.int32), np.empty((0,), dtype=np.int32)]
    adj_weights = [np.array([1.5], dtype=np.float32), np.array([1.5], dtype=np.float32), np.empty((0,), dtype=np.float32)]
    adj_delays = [np.array([1.0], dtype=np.float32), np.array([1.0], dtype=np.float32), np.empty((0,), dtype=np.float32)]
    graph = NeuralGraph(3, adj_targets, adj_weights, adj_delays)

    # External event at t=1.0 targeting node 0 with amp 1.5
    ext_events = [(1.0, 0, 1.5)]
    t_max = 5.0

    # 1. Event-driven
    ed_sched = EventDrivenScheduler(config, graph)
    ed_res = ed_sched.run(ext_events, t_max)
    assert ed_res.total_spikes == 3  # node 0 at 1.0, node 1 at 2.0, node 2 at 3.0

    # Check spike timestamps: (1.0, 0), (2.0, 1), (3.0, 2)
    assert ed_res.spike_records[0] == (1.0, 0)
    assert ed_res.spike_records[1] == (2.0, 1)
    assert ed_res.spike_records[2] == (3.0, 2)

    # 2. Dense synchronous with dt=0.05
    dense_sched = DenseSynchronousScheduler(config, graph, dt=0.05)
    dense_res = dense_sched.run(ext_events, t_max)
    assert dense_res.total_spikes == 3

    # 3. Sparse synchronous with dt=0.05
    sparse_sched = SparseSynchronousScheduler(config, graph, dt=0.05)
    sparse_res = sparse_sched.run(ext_events, t_max)
    assert sparse_res.total_spikes == 3


def test_dt_refinement_error_scaling():
    """Verify that finer dt reduces potential error compared to event-driven reference."""
    config = SubstrateConfig(num_nodes=5, tau_m=5.0, threshold=100.0)  # linear subthreshold
    graph = NeuralGraph.create_random(5, mean_out_degree=2, seed=42, weight_scale=0.2)
    ext_events = [(1.0, 0, 0.5), (3.0, 1, 0.8), (6.0, 2, 0.6)]
    t_max = 10.0

    ed_sched = EventDrivenScheduler(config, graph)
    ed_res = ed_sched.run(ext_events, t_max)
    ref_pot = ed_res.final_potentials

    errors = []
    for dt in [0.2, 0.1, 0.05]:
        dense_sched = DenseSynchronousScheduler(config, graph, dt=dt)
        dense_res = dense_sched.run(ext_events, t_max)
        err = float(np.linalg.norm(dense_res.final_potentials - ref_pot))
        errors.append(err)

    # Errors should decrease monotonically as dt decreases
    assert errors[0] > errors[1] > errors[2]
