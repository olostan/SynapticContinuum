"""Neural network dynamical models and endogenous activity generators.

Governed by SPEC.md Stage 3:
1. External-only (passive decay control)
2. Delayed-feedback (recurrent delay network)
3. Intrinsic oscillator (pacemaker / subthreshold drive)
4. State-dependent trigger (threshold/bursting dynamics)
5. Stability control (homeostatic plasticity and refractory enforcement)
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from .queue import EventKind, EventQueue
from .substrate import NeuralGraph, SubstrateConfig, SubstrateState


class ModelVariant:
    EXTERNAL_ONLY = "external_only"
    DELAYED_FEEDBACK = "delayed_feedback"
    INTRINSIC_OSCILLATOR = "intrinsic_oscillator"
    STATE_DEPENDENT_TRIGGER = "state_dependent_trigger"
    STABILITY_CONTROLLED = "stability_controlled"


def create_neural_model(
    variant: str,
    num_nodes: int,
    mean_out_degree: int = 16,
    seed: int = 42,
    history_capacity_L: int = 0,
    trace_bases_B: int = 0,
) -> Tuple[SubstrateConfig, NeuralGraph]:
    """Factory creating config and graph for each preregistered model variant."""
    homeostasis = False
    weight_scale = 0.25

    if variant == ModelVariant.EXTERNAL_ONLY:
        # Zero recurrent weights
        weight_scale = 0.0
    elif variant == ModelVariant.DELAYED_FEEDBACK:
        # Recurrent connections with delays
        weight_scale = 0.35
    elif variant == ModelVariant.INTRINSIC_OSCILLATOR:
        # Recurrent connections with moderate weights
        weight_scale = 0.25
    elif variant == ModelVariant.STATE_DEPENDENT_TRIGGER:
        weight_scale = 0.30
    elif variant == ModelVariant.STABILITY_CONTROLLED:
        # Stronger recurrent connections paired with homeostatic threshold adaptation
        weight_scale = 0.40
        homeostasis = True
    else:
        raise ValueError(f"Unknown model variant: {variant}")

    config = SubstrateConfig(
        num_nodes=num_nodes,
        mean_out_degree=mean_out_degree,
        tau_m=5.0,
        threshold=1.0,
        v_reset=0.0,
        refractory_period=1.0,
        min_delay=0.2,
        max_delay=2.0,
        history_capacity_L=history_capacity_L,
        trace_bases_B=trace_bases_B,
        homeostasis=homeostasis,
        homeostasis_rate=0.10,
        homeostasis_tau=20.0,
    )

    graph = NeuralGraph.create_random(
        num_nodes=num_nodes,
        mean_out_degree=mean_out_degree,
        seed=seed,
        weight_scale=weight_scale,
        min_delay=config.min_delay,
        max_delay=config.max_delay,
    )

    return config, graph


def inject_endogenous_pacemaker_events(
    queue: EventQueue,
    num_nodes: int,
    start_time: float,
    end_time: float,
    rate_hz: float = 2.0,
    fraction_pacemakers: float = 0.05,
    seed: int = 42,
) -> int:
    """Inject endogenous pacemaker events during silence for intrinsic oscillator variant."""
    rng = np.random.default_rng(seed)
    num_pacemakers = max(1, int(num_nodes * fraction_pacemakers))
    pacemaker_nodes = rng.choice(num_nodes, size=num_pacemakers, replace=False)
    events_injected = 0

    duration = end_time - start_time
    if duration <= 0:
        return 0

    for node in pacemaker_nodes:
        # Generate Poisson or regular spike train
        curr_t = start_time + rng.exponential(1.0 / rate_hz)
        while curr_t < end_time:
            queue.push(
                timestamp=float(curr_t),
                source=-2,  # Pacemaker internal source
                target=int(node),
                amplitude=1.2,  # Sufficient to trigger spike
                kind=EventKind.PACEMAKER,
            )
            events_injected += 1
            curr_t += rng.exponential(1.0 / rate_hz)

    return events_injected
