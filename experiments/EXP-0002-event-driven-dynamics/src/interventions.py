"""Causal intervention operations on internal event queues and dynamical states.

Governed by SPEC.md Stage 3:
- Freeze, analytic passive decay, replay, randomized events, sham, matched-compute
- Event deletion, event delay, amplitude perturbation
- Measures state divergence ||Delta h(t_probe)|| and downstream outcome shift.
"""
from enum import Enum
import heapq
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from .queue import Event, EventKind, EventQueue
from .substrate import NeuralGraph, SubstrateConfig, SubstrateState


class InterventionType(str, Enum):
    NONE = "none"
    SHAM = "sham"
    FREEZE = "freeze"
    PASSIVE_DECAY = "passive_decay"
    EVENT_DELETION = "event_deletion"
    EVENT_DELAY = "event_delay"
    AMPLITUDE_PERTURBATION = "amplitude_perturbation"
    RANDOMIZED_EVENTS = "randomized_events"
    MATCHED_COMPUTE = "matched_compute"


def apply_intervention(
    queue: EventQueue,
    state: SubstrateState,
    intervention_type: InterventionType,
    current_time: float,
    t_probe: float,
    seed: int = 42,
    deletion_fraction: float = 0.5,
    delay_amount: float = 1.0,
    amplitude_scale: float = 0.5,
) -> Dict[str, Any]:
    """Apply declared causal intervention to the internal event queue at current_time."""
    rng = np.random.default_rng(seed)
    info: Dict[str, Any] = {"type": intervention_type.value, "events_affected": 0}

    # Extract all events currently in the queue
    all_events = queue.get_all_events()
    queue.clear()

    # Partition events into:
    # 1. Past/External/Probe events that should remain untouched
    # 2. Internal future events within [current_time, t_probe] that can be intervened upon
    preserved: List[Event] = []
    candidates: List[Event] = []

    for ev in all_events:
        if ev.timestamp < current_time or ev.kind in (EventKind.EXTERNAL, EventKind.PROBE):
            preserved.append(ev)
        else:
            candidates.append(ev)

    info["total_internal_candidates"] = len(candidates)

    if intervention_type == InterventionType.NONE:
        # Re-insert all events
        for ev in all_events:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)

    elif intervention_type == InterventionType.SHAM:
        # Re-insert exact same events in identical order
        for ev in all_events:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.FREEZE:
        # Discard all candidate internal events; state will be held constant
        for ev in preserved:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.PASSIVE_DECAY:
        # Discard all internal spikes; allow only passive decay
        for ev in preserved:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.EVENT_DELETION:
        # Delete randomly selected fraction of candidate events
        kept = []
        deleted_count = 0
        for ev in candidates:
            if rng.random() < deletion_fraction:
                deleted_count += 1
            else:
                kept.append(ev)
        for ev in preserved + kept:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = deleted_count

    elif intervention_type == InterventionType.EVENT_DELAY:
        # Shift timestamps by delay_amount
        for ev in preserved:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        for ev in candidates:
            new_t = ev.timestamp + delay_amount
            queue.push(new_t, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.AMPLITUDE_PERTURBATION:
        # Scale amplitude
        for ev in preserved:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        for ev in candidates:
            new_amp = ev.amplitude * amplitude_scale
            queue.push(ev.timestamp, ev.source, ev.target, new_amp, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.RANDOMIZED_EVENTS:
        # Match count and amplitude distribution, scramble times and targets
        for ev in preserved:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        N = state.num_nodes
        for ev in candidates:
            scrambled_t = float(rng.uniform(current_time, t_probe))
            scrambled_target = int(rng.integers(0, N))
            queue.push(scrambled_t, ev.source, scrambled_target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)

    elif intervention_type == InterventionType.MATCHED_COMPUTE:
        # Execute equal arithmetic operations without changing real queue
        dummy_sum = 0.0
        for ev in candidates:
            dummy_sum += ev.amplitude * np.sin(ev.timestamp)
        for ev in all_events:
            queue.push(ev.timestamp, ev.source, ev.target, ev.amplitude, ev.kind)
        info["events_affected"] = len(candidates)
        info["dummy_sum"] = float(dummy_sum)

    return info
