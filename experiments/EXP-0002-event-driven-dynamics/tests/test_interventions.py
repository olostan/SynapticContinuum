"""Tests for causal interventions and sham invariance."""
import numpy as np
import pytest
from src.interventions import InterventionType, apply_intervention
from src.queue import EventKind, EventQueue
from src.substrate import SubstrateConfig, SubstrateState


def test_sham_intervention_exact_invariance():
    """Verify that SHAM intervention preserves exact queue contents, order, and state."""
    config = SubstrateConfig(num_nodes=5)
    state = SubstrateState(config)
    queue = EventQueue()

    # Push mixture of events
    queue.push(1.0, source=-1, target=0, amplitude=1.0, kind=EventKind.EXTERNAL)
    queue.push(5.0, source=0, target=1, amplitude=0.5, kind=EventKind.SPIKE)
    queue.push(7.0, source=1, target=2, amplitude=0.8, kind=EventKind.SPIKE)
    queue.push(10.0, source=-1, target=3, amplitude=1.0, kind=EventKind.PROBE)

    initial_events = [(e.timestamp, e.target, e.amplitude) for e in queue.get_all_events()]

    # Apply SHAM at t=4.0
    info = apply_intervention(
        queue=queue,
        state=state,
        intervention_type=InterventionType.SHAM,
        current_time=4.0,
        t_probe=10.0,
        seed=42,
    )

    post_events = [(e.timestamp, e.target, e.amplitude) for e in queue.get_all_events()]
    assert initial_events == post_events
    assert info["events_affected"] == 2  # events at 5.0 and 7.0 were internal candidates


def test_event_deletion_intervention():
    """Verify event deletion removes candidate internal events while keeping external/probe."""
    config = SubstrateConfig(num_nodes=5)
    state = SubstrateState(config)
    queue = EventQueue()

    queue.push(1.0, -1, 0, 1.0, EventKind.EXTERNAL)
    queue.push(5.0, 0, 1, 0.5, EventKind.SPIKE)
    queue.push(6.0, 1, 2, 0.5, EventKind.SPIKE)
    queue.push(10.0, -1, 3, 1.0, EventKind.PROBE)

    # 100% deletion of candidate internal events
    info = apply_intervention(
        queue=queue,
        state=state,
        intervention_type=InterventionType.EVENT_DELETION,
        current_time=4.0,
        t_probe=10.0,
        deletion_fraction=1.0,
    )

    remaining = queue.get_all_events()
    assert len(remaining) == 2
    assert remaining[0].kind == EventKind.EXTERNAL
    assert remaining[1].kind == EventKind.PROBE
