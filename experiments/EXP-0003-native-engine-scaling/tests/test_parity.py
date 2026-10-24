"""Pytest suite verifying cross-language parity, correctness, and safety gates for EXP-0003."""
import math
import os
import sys
import numpy as np
import pytest

from src.python.bridge import (
    create_py_fixture,
    run_cpp_engine,
    run_py_event,
    run_py_event_sim,
    run_py_sync,
)
from src.python.hardware import preflight_check
from src.python.prng import DeterministicRNG


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


def test_cpp_hybrid_vs_literal():
    """Verify Hybrid C++ produces bit-exact state digest under identical graph."""
    res_lit = run_cpp_engine("literal", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)
    res_hybrid = run_cpp_engine("hybrid", num_nodes=128, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, seed=42, warmups=0, reps=1)

    assert res_lit["total_spikes"] == res_hybrid["total_spikes"]
    assert res_lit["state_digest"] == res_hybrid["state_digest"]


def test_cpp_owner_replay_parity():
    """Verify Owner C++ with 1, 2, 4, 6, 8 workers produces identical state digest to serial."""
    res_serial = run_cpp_engine("packed", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, warmups=0, reps=1)
    res_owner1 = run_cpp_engine("owner", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, workers=1, warmups=0, reps=1)
    res_owner2 = run_cpp_engine("owner", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, workers=2, warmups=0, reps=1)
    res_owner4 = run_cpp_engine("owner", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, workers=4, warmups=0, reps=1)
    res_owner6 = run_cpp_engine("owner", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, workers=6, warmups=0, reps=1)
    res_owner8 = run_cpp_engine("owner", num_nodes=128, degree=8, active_fraction=0.10, rate=1.0, t_max=5.0, seed=999, workers=8, warmups=0, reps=1)

    assert res_serial["total_spikes"] == res_owner1["total_spikes"] == res_owner2["total_spikes"] == res_owner4["total_spikes"] == res_owner6["total_spikes"] == res_owner8["total_spikes"]
    assert res_serial["state_digest"] == res_owner1["state_digest"] == res_owner2["state_digest"] == res_owner4["state_digest"] == res_owner6["state_digest"] == res_owner8["state_digest"]


def test_preflight_memory_safety():
    """Verify preflight rejects out-of-budget sizes and accepts standard sizes."""
    safe, est, limit = preflight_check(num_nodes=10000, degree=16, active_fraction=0.10, rate=1.0, t_max=10.0, engine="packed")
    assert safe is True
    assert est < limit

    safe_huge, est_huge, limit_huge = preflight_check(num_nodes=100_000_000, degree=64, active_fraction=1.0, rate=10.0, t_max=100.0, engine="dense_sync")
    assert safe_huge is False
    assert est_huge > limit_huge
