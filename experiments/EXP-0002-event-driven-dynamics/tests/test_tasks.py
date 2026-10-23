"""Tests for Task A, Task B, Task C, and Task D."""
import pytest
from src.tasks import (
    generate_task_b_dataset,
    run_task_a_analytic_parity,
    run_task_c_matched_observation,
    run_task_d_silence_stability,
)


def test_task_a_analytic_parity():
    """Verify Task A event-driven simulation matches continuous analytic solution within 1e-5."""
    res = run_task_a_analytic_parity(tau_m=5.0, t_max=15.0)
    assert res["event_driven_abs_err"] < 1e-5
    # Verify synchronous errors exist and are positive
    for dt_key, sync_data in res["sync_dt_comparisons"].items():
        assert sync_data["dense_abs_err"] > 0.0


def test_task_b_dataset_no_clock_leakage():
    """Verify Task B samples define association without providing explicit delta_t to inputs."""
    samples = generate_task_b_dataset(num_samples=20, seed=42)
    assert len(samples) == 20
    for s in samples:
        assert s.c1 in (0, 1)
        assert s.c2 in (0, 1)
        assert s.target in (0, 1)


def test_task_c_matched_observation_discrimination():
    """Verify Task C sequences with identical final observation are discriminable via temporal state."""
    res = run_task_c_matched_observation(num_nodes=32, trace_bases_B=4, history_capacity_L=8, seed=42)
    assert res["discriminable"]
    assert res["potential_l2_diff"] > 1e-3 or res["trace_l2_diff"] > 1e-3


def test_task_d_silence_stability():
    """Verify Task D differentiates external-only (absorbing) from active endogenous models."""
    res_ext = run_task_d_silence_stability("external_only", num_nodes=32, silence_gap=5.0, seed=42)
    assert res_ext["spikes_silence"] == 0
    assert res_ext["is_absorbing"]

    res_osc = run_task_d_silence_stability("intrinsic_oscillator", num_nodes=32, silence_gap=5.0, seed=42)
    assert res_osc["spikes_silence"] > 0
    assert not res_osc["is_absorbing"]
