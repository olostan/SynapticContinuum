"""Stage 2: Temporal Representation Analysis.

Governed by SPEC.md Stage 2:
- Bounded explicit history L in {0, 1, 4, 16, 64, 256}
- Exponential trace bases B in {0, 1, 4, 8}
- Network sizes N in {128, 512}, degree D=16
- Capacity-matched storage comparison, effective horizon, query latency,
  and held-out delayed-history probes (Tasks B & C).
"""
import time
from typing import Any, Dict, List, Optional
import numpy as np

from .tasks import (
    evaluate_task_b_model,
    generate_task_b_dataset,
    run_task_c_matched_observation,
)


def run_stage2_representation_suite(
    sizes: Optional[List[int]] = None,
    history_lengths: Optional[List[int]] = None,
    trace_bases_list: Optional[List[int]] = None,
    seeds: Optional[List[int]] = None,
    num_samples_task_b: int = 400,
) -> Dict[str, Any]:
    """Execute Stage 2 temporal representation parameter sweep."""
    if sizes is None:
        sizes = [128, 512]
    if history_lengths is None:
        history_lengths = [0, 1, 4, 16, 64, 256]
    if trace_bases_list is None:
        trace_bases_list = [0, 1, 4, 8]
    if seeds is None:
        seeds = [11, 23, 37]

    start_wall = time.perf_counter()
    results_matrix: List[Dict[str, Any]] = []

    for N in sizes:
        for s in seeds:
            # Generate dataset for this seed
            dataset = generate_task_b_dataset(num_samples=num_samples_task_b, seed=s)

            # 1. Sweep trace bases B with L=0 (pure trace bank)
            for B in trace_bases_list:
                eval_res = evaluate_task_b_model(
                    samples=dataset,
                    num_nodes=N,
                    trace_bases_B=B,
                    history_capacity_L=0,
                    seed=s,
                )
                c_res = run_task_c_matched_observation(
                    num_nodes=N,
                    trace_bases_B=B,
                    history_capacity_L=0,
                    seed=s,
                )
                results_matrix.append({
                    "num_nodes": N,
                    "seed": s,
                    "type": "trace_bank",
                    "trace_bases_B": B,
                    "history_capacity_L": 0,
                    "task_b_test_acc": eval_res["test_acc"],
                    "task_b_balanced_acc": eval_res["test_balanced_acc"],
                    "task_c_potential_diff": c_res["potential_l2_diff"],
                    "task_c_trace_diff": c_res["trace_l2_diff"],
                    "task_c_discriminable": c_res["discriminable"],
                    "total_memory_bytes": eval_res["total_memory_bytes"],
                })

            # 2. Sweep history capacity L with B=0 (pure explicit history buffer)
            for L in history_lengths:
                if L == 0:
                    continue  # already evaluated in (B=0, L=0)
                eval_res = evaluate_task_b_model(
                    samples=dataset,
                    num_nodes=N,
                    trace_bases_B=0,
                    history_capacity_L=L,
                    seed=s,
                )
                c_res = run_task_c_matched_observation(
                    num_nodes=N,
                    trace_bases_B=0,
                    history_capacity_L=L,
                    seed=s,
                )
                results_matrix.append({
                    "num_nodes": N,
                    "seed": s,
                    "type": "explicit_history",
                    "trace_bases_B": 0,
                    "history_capacity_L": L,
                    "task_b_test_acc": eval_res["test_acc"],
                    "task_b_balanced_acc": eval_res["test_balanced_acc"],
                    "task_c_potential_diff": c_res["potential_l2_diff"],
                    "task_c_trace_diff": c_res["trace_l2_diff"],
                    "task_c_discriminable": c_res["discriminable"],
                    "total_memory_bytes": eval_res["total_memory_bytes"],
                })

    total_wall = time.perf_counter() - start_wall

    return {
        "suite_name": "stage2_representation",
        "total_wall_sec": total_wall,
        "num_evaluations": len(results_matrix),
        "results": results_matrix,
    }
