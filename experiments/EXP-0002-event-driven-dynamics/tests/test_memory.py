"""Tests for ExponentialTraceBank and BoundedEventHistory."""
import numpy as np
import pytest
from src.memory import BoundedEventHistory, ExponentialTraceBank


def test_exponential_trace_partition_invariance():
    """Verify that multi-step lazy evaluation equals single combined decay."""
    bank = ExponentialTraceBank(num_nodes=2, num_bases=3, tau_list=[1.0, 5.0, 20.0])
    bank.advance_and_add(node=0, current_time=0.0, amplitude=1.0)

    # Step-by-step decay: t=0 -> t=2.0 -> t=5.0
    val_intermediate = bank.get_values(node=0, current_time=2.0)
    bank.advance_and_add(node=0, current_time=2.0, amplitude=0.0)
    val_final_stepwise = bank.get_values(node=0, current_time=5.0)

    # Direct single jump: t=0 -> t=5.0
    bank_direct = ExponentialTraceBank(num_nodes=2, num_bases=3, tau_list=[1.0, 5.0, 20.0])
    bank_direct.advance_and_add(node=0, current_time=0.0, amplitude=1.0)
    val_direct = bank_direct.get_values(node=0, current_time=5.0)

    np.testing.assert_allclose(val_final_stepwise, val_direct, rtol=1e-6, atol=1e-6)


def test_bounded_history_capacity_and_order():
    """Verify circular ring buffer discards oldest events beyond capacity L and preserves order."""
    L = 3
    hist = BoundedEventHistory(num_nodes=2, capacity_L=L)

    # Add 5 events: only last 3 should be retained
    for i in range(5):
        hist.record_event(node=0, timestamp=float(i), amplitude=float(i * 10), kind=1)

    events = hist.get_events(node=0)
    assert len(events) == L
    # Kept should be timestamps 2.0, 3.0, 4.0
    assert events[0] == (2.0, 20.0, 1)
    assert events[1] == (3.0, 30.0, 1)
    assert events[2] == (4.0, 40.0, 1)


def test_bounded_history_causal_kernel_no_future_leakage():
    """Verify causal kernel ignores future events where query_time < timestamp."""
    hist = BoundedEventHistory(num_nodes=2, capacity_L=4)
    hist.record_event(node=0, timestamp=2.0, amplitude=1.0)
    hist.record_event(node=0, timestamp=5.0, amplitude=1.0)

    # Query at t=3.0: event at t=5.0 must not contribute
    kernel_fn = lambda dt: np.ones_like(dt)
    conv_val = hist.query_kernel(node=0, query_time=3.0, kernel_fn=kernel_fn)
    assert conv_val == 1.0


def test_memory_storage_accounting():
    """Verify byte accounting formulas match array allocation."""
    N = 100
    B = 8
    L = 16
    trace_bank = ExponentialTraceBank(num_nodes=N, num_bases=B)
    assert trace_bank.storage_bytes == (N * B * 4 + N * 4 + B * 4)

    history = BoundedEventHistory(num_nodes=N, capacity_L=L)
    # 4 (timestamp) + 4 (amplitude) + 1 (kind) = 9 bytes per event * N * L
    # + 4 (head) + 4 (count) = 8 bytes per node * N
    expected_hist_bytes = N * L * 9 + N * 8
    assert history.storage_bytes == expected_hist_bytes
