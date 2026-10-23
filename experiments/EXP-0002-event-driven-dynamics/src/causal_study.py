"""Stage 3: Endogenous Dynamics and Causal Intervention Study.

Governed by SPEC.md Stage 3:
- Network sizes N in {128, 512}
- 5 fixed primary seeds {11, 23, 37, 41, 53}
- Silence gaps in {1.0, 10.0, 50.0}
- Model variants: external_only, delayed_feedback, intrinsic_oscillator, state_dependent_trigger, stability_controlled
- Causal interventions: sham, freeze, passive_decay, event_deletion, event_delay, amplitude_perturbation, randomized_events, matched_compute
- Metrics: state divergence ||Delta h||_2, decision flip rate, spike differences, stability, runaway/absorbing rates.
"""
import time
from typing import Any, Dict, List, Optional
import numpy as np

from .interventions import InterventionType
from .models import ModelVariant
from .tasks import run_task_d_silence_stability, run_task_e_causal_intervention_study


def run_stage3_causal_suite(
    seeds: Optional[List[int]] = None,
    sizes: Optional[List[int]] = None,
    silence_gaps: Optional[List[float]] = None,
    model_variants: Optional[List[str]] = None,
    interventions: Optional[List[InterventionType]] = None,
    trace_bases_B: int = 4,
    history_capacity_L: int = 16,
) -> Dict[str, Any]:
    """Execute Stage 3 5-seed endogenous activity and causal intervention study."""
    if seeds is None:
        seeds = [11, 23, 37, 41, 53]
    if sizes is None:
        sizes = [128, 512]
    if silence_gaps is None:
        silence_gaps = [1.0, 10.0, 50.0]
    if model_variants is None:
        model_variants = [
            ModelVariant.EXTERNAL_ONLY,
            ModelVariant.DELAYED_FEEDBACK,
            ModelVariant.INTRINSIC_OSCILLATOR,
            ModelVariant.STATE_DEPENDENT_TRIGGER,
            ModelVariant.STABILITY_CONTROLLED,
        ]
    if interventions is None:
        interventions = [
            InterventionType.SHAM,
            InterventionType.FREEZE,
            InterventionType.PASSIVE_DECAY,
            InterventionType.EVENT_DELETION,
            InterventionType.EVENT_DELAY,
            InterventionType.AMPLITUDE_PERTURBATION,
            InterventionType.RANDOMIZED_EVENTS,
            InterventionType.MATCHED_COMPUTE,
        ]

    start_wall = time.perf_counter()

    # Part 1: Task D Stability & Silence Dynamics
    stability_records: List[Dict[str, Any]] = []
    for N in sizes:
        for model in model_variants:
            for gap in silence_gaps:
                for s in seeds:
                    stab = run_task_d_silence_stability(
                        model_variant=model,
                        num_nodes=N,
                        silence_gap=gap,
                        seed=s,
                    )
                    stability_records.append({
                        "num_nodes": N,
                        "model_variant": model,
                        "silence_gap": gap,
                        "seed": s,
                        **stab,
                    })

    # Part 2: Task E Causal Interventions across shortlisted active models
    # Focus on active endogenous variants: DELAYED_FEEDBACK, INTRINSIC_OSCILLATOR, STABILITY_CONTROLLED
    active_variants = [
        ModelVariant.DELAYED_FEEDBACK,
        ModelVariant.INTRINSIC_OSCILLATOR,
        ModelVariant.STABILITY_CONTROLLED,
    ]

    intervention_records: List[Dict[str, Any]] = []
    for N in sizes:
        for model in active_variants:
            for gap in silence_gaps:
                for interv in interventions:
                    for s in seeds:
                        study_res = run_task_e_causal_intervention_study(
                            model_variant=model,
                            intervention_type=interv,
                            num_nodes=N,
                            silence_gap=gap,
                            seed=s,
                            trace_bases_B=trace_bases_B,
                            history_capacity_L=history_capacity_L,
                        )
                        intervention_records.append({
                            "num_nodes": N,
                            "model_variant": model,
                            "silence_gap": gap,
                            "intervention": interv.value,
                            "seed": s,
                            **study_res,
                        })

    total_wall = time.perf_counter() - start_wall

    return {
        "suite_name": "stage3_causal_study",
        "total_wall_sec": total_wall,
        "num_stability_records": len(stability_records),
        "stability_records": stability_records,
        "num_intervention_records": len(intervention_records),
        "intervention_records": intervention_records,
    }
