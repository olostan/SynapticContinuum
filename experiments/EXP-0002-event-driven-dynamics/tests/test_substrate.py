"""Tests for SubstrateState, threshold emission, and refractory mechanics."""
import numpy as np
import pytest
from src.substrate import NeuralGraph, SubstrateConfig, SubstrateState


def test_analytic_passive_leak():
    """Verify passive membrane leak matches exponential law exactly."""
    config = SubstrateConfig(num_nodes=2, tau_m=4.0, threshold=10.0)
    state = SubstrateState(config)
    state.potentials[0] = 2.0
    state.last_update_times[0] = 1.0

    # Advance to t=5.0 (dt = 4.0 = tau_m)
    h_advanced = state.advance_node_potential(0, 5.0)
    expected = 2.0 * np.exp(-1.0)
    assert abs(h_advanced - expected) < 1e-6


def test_threshold_spiking_and_reset():
    """Verify threshold crossing emits spike and resets potential to v_reset."""
    config = SubstrateConfig(num_nodes=1, threshold=1.0, v_reset=0.0, refractory_period=2.0)
    state = SubstrateState(config)

    # Subthreshold impulse
    fired = state.receive_impulse(0, current_time=1.0, amplitude=0.8)
    assert not fired
    assert abs(state.potentials[0] - 0.8) < 1e-6

    # Suprathreshold impulse
    fired2 = state.receive_impulse(0, current_time=2.0, amplitude=0.5)
    assert fired2
    assert state.potentials[0] == 0.0
    assert state.spike_counts[0] == 1
    assert state.refractory_until[0] == 4.0


def test_refractory_period_clamping():
    """Verify impulses arriving during refractory period are clamped and do not trigger spikes."""
    config = SubstrateConfig(num_nodes=1, threshold=1.0, v_reset=0.0, refractory_period=2.0)
    state = SubstrateState(config)

    # Spike at t=1.0 -> refractory until t=3.0
    state.receive_impulse(0, current_time=1.0, amplitude=1.5)
    assert state.refractory_until[0] == 3.0

    # Large impulse at t=2.0 (inside refractory window)
    fired_during_ref = state.receive_impulse(0, current_time=2.0, amplitude=5.0)
    assert not fired_during_ref
    assert state.potentials[0] == 0.0  # clamped at reset

    # Impulse at t=3.1 (outside refractory window)
    fired_after_ref = state.receive_impulse(0, current_time=3.1, amplitude=1.2)
    assert fired_after_ref
    assert state.spike_counts[0] == 2
