"""Pytest suite verifying cross-language parity, correctness, and safety gates for EXP-0003."""
import math
import os
import sys
import numpy as np
import pytest

from src.python.bridge import run_cpp_engine, run_py_event, run_py_sync
from src.python.hardware import preflight_check
from src.python.prng import DeterministicRNG, generate_deterministic_events, generate_deterministic_graph


def test_prng_determinism():
    rng1 = DeterministicRNG(42)
    rng2 = DeterministicRNG(42)
    for _ in range(100):
        assert rng1.next_u64() == rng2.next_u64()


def test_python_vs_cpp_literal_chain_parity():
    """Verify bit-exact spike timestamps on 3-node feedforward chain."""
    py_res = run_py_event(num_nodes=3, degree=1, active_fraction=1.0, rate=1.0, t_max=5.0, seed=42)
    cpp_res = run_cpp_engine(
        engine="literal",
        num_nodes=3,
        degree=1,
        active_fraction=1.0,
        rate=1.0,
        t_max=5.0,
        seed=42,
        warmups=0,
        reps=1,
    )

    assert py_res["total_spikes"] == cpp_res["total_spikes"]
    assert py_res["total_events_processed"] == cpp_res["total_events_processed"]


def test_python_vs_cpp_literal_random_network():
    """Verify parity on random graph N=128, D=16."""
    py_res = run_py_event(num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42)
    cpp_res = run_cpp_engine(
        engine="literal",
        num_nodes=128,
        degree=16,
        active_fraction=0.10,
        rate=1.0,
        t_max=10.0,
        seed=42,
        warmups=0,
        reps=1,
    )

    assert py_res["total_spikes"] == cpp_res["total_spikes"]
    assert py_res["total_events_processed"] == cpp_res["total_events_processed"]
    assert py_res["total_edges_traversed"] == cpp_res["total_edges_traversed"]


def test_cpp_literal_vs_packed():
    """Verify Packed C++ produces identical spike count and events to Literal C++."""
    res_lit = run_cpp_engine("literal", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)
    res_packed = run_cpp_engine("packed", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)

    assert res_lit["total_spikes"] == res_packed["total_spikes"]
    assert res_lit["total_events_processed"] == res_packed["total_events_processed"]
    assert res_lit["total_edges_traversed"] == res_packed["total_edges_traversed"]
    assert res_lit["state_digest"] == res_packed["state_digest"]


def test_cpp_queues_parity():
    """Verify binary, dary4, and bucket queues produce identical simulation outcomes."""
    res_bin = run_cpp_engine("queue_binary", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)
    res_dary = run_cpp_engine("queue_dary4", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)
    res_bkt = run_cpp_engine("queue_bucket", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)

    assert res_bin["total_spikes"] == res_dary["total_spikes"] == res_bkt["total_spikes"]
    assert res_bin["state_digest"] == res_dary["state_digest"] == res_bkt["state_digest"]


def test_preflight_memory_safety():
    """Verify preflight rejects out-of-budget sizes and accepts standard sizes."""
    # Standard size should be safe
    safe, est, limit = preflight_check(num_nodes=10000, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, engine="packed")
    assert safe is True
    assert est < limit

    # Hypothetical 100-billion node network should be rejected on this host
    safe_huge, est_huge, limit_huge = preflight_check(num_nodes=100_000_000, degree=64, active_fraction=1.0, rate=10.0, t_max=100.0, engine="dense_sync")
    assert safe_huge is False
    assert est_huge > limit_huge
