"""Stage 1: Execution Crossover Benchmarks.

Governed by SPEC.md Stage 1:
- Nodes N in {128, 512, 2048, 8192}
- Out-degree D in {4, 16, 64}
- Injected active fraction f in {0.001, 0.01, 0.05, 0.10, 0.25, 0.50, 1.0}
- Preregistered screening matrix: N in {128, 512, 2048}, D=16, f in {0.01, 0.05, 0.25, 1.0} across 3 seeds {11, 23, 37}.
- Selective expansion triggers: N=8192 if RAM < 8 GiB and cell runtime < 10m; D in {4, 64} and f in {0.001, 0.10, 0.50}.
- Compare Event-Driven (lazy decay), Event-Driven (eager), Dense Sync dt in {0.2, 0.1, 0.05}, Sparse Sync dt in {0.2, 0.1, 0.05}.
"""
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .schedulers import (
    DenseSynchronousScheduler,
    EventDrivenScheduler,
    SimulationResult,
    SparseSynchronousScheduler,
)
from .substrate import NeuralGraph, SubstrateConfig


def generate_external_stimulus(
    num_nodes: int,
    active_fraction: float,
    t_max: float,
    seed: int,
    rate_hz: float = 1.0,
) -> List[Tuple[float, int, float]]:
    """
    Generate deterministic Poisson external stimulus events:
    Targeting active_fraction subset of nodes.
    """
    rng = np.random.default_rng(seed)
    num_active = max(1, int(np.round(num_nodes * active_fraction)))
    active_nodes = rng.choice(num_nodes, size=num_active, replace=False)

    events: List[Tuple[float, int, float]] = []
    for node in active_nodes:
        # Generate event times up to t_max
        curr_t = float(rng.exponential(1.0 / rate_hz))
        while curr_t <= t_max:
            events.append((curr_t, int(node), 1.2))
            curr_t += float(rng.exponential(1.0 / rate_hz))

    events.sort(key=lambda x: x[0])
    return events


def run_stage1_single_cell(
    num_nodes: int,
    out_degree: int,
    active_fraction: float,
    seed: int,
    t_max: float = 20.0,
    dt_list: Optional[List[float]] = None,
    max_events_per_cell: int = 1_000_000,
) -> Dict[str, Any]:
    """Execute all schedulers on a single (N, D, f, seed) cell."""
    if dt_list is None:
        dt_list = [0.2, 0.1, 0.05]

    config = SubstrateConfig(
        num_nodes=num_nodes,
        mean_out_degree=out_degree,
        tau_m=5.0,
        threshold=1.0,
        refractory_period=1.0,
    )
    graph = NeuralGraph.create_random(
        num_nodes=num_nodes,
        mean_out_degree=out_degree,
        seed=seed,
        weight_scale=0.25,
    )

    external_events = generate_external_stimulus(
        num_nodes=num_nodes,
        active_fraction=active_fraction,
        t_max=t_max,
        seed=seed,
    )

    cell_results: Dict[str, Any] = {
        "num_nodes": num_nodes,
        "out_degree": out_degree,
        "injected_fraction": active_fraction,
        "seed": seed,
        "t_max": t_max,
        "num_external_events": len(external_events),
        "schedulers": {},
    }

    # 1. Event-Driven Lazy
    ed_lazy = EventDrivenScheduler(config, graph, lazy_decay=True)
    res_lazy = ed_lazy.run(external_events, t_max, max_events=max_events_per_cell)
    cell_results["schedulers"]["event_driven_lazy"] = {
        "wall_time_sec": res_lazy.wall_time_sec,
        "events_processed": res_lazy.total_events_processed,
        "edges_traversed": res_lazy.total_edges_traversed,
        "spikes": res_lazy.total_spikes,
        "peak_queue": res_lazy.peak_queue_size,
        "propagated_fraction": res_lazy.propagated_active_fraction,
        "capacity_exceeded": res_lazy.max_queue_exceeded,
    }

    # Reference firing record for trajectory comparison
    ref_spikes = res_lazy.total_spikes
    ref_final_pot = res_lazy.final_potentials

    # 2. Event-Driven Eager
    ed_eager = EventDrivenScheduler(config, graph, lazy_decay=False)
    res_eager = ed_eager.run(external_events, t_max, max_events=max_events_per_cell)
    cell_results["schedulers"]["event_driven_eager"] = {
        "wall_time_sec": res_eager.wall_time_sec,
        "events_processed": res_eager.total_events_processed,
        "edges_traversed": res_eager.total_edges_traversed,
        "spikes": res_eager.total_spikes,
        "peak_queue": res_eager.peak_queue_size,
        "propagated_fraction": res_eager.propagated_active_fraction,
        "capacity_exceeded": res_eager.max_queue_exceeded,
    }

    # 3. Synchronous schedulers across dt candidates
    for dt in dt_list:
        # Sparse Synchronous
        sparse_sched = SparseSynchronousScheduler(config, graph, dt=dt)
        sparse_res = sparse_sched.run(external_events, t_max, max_events=max_events_per_cell)
        pot_l2_err = float(np.linalg.norm(sparse_res.final_potentials - ref_final_pot))

        cell_results["schedulers"][f"sparse_sync_dt_{dt}"] = {
            "wall_time_sec": sparse_res.wall_time_sec,
            "events_processed": sparse_res.total_events_processed,
            "edges_traversed": sparse_res.total_edges_traversed,
            "spikes": sparse_res.total_spikes,
            "pot_l2_err": pot_l2_err,
            "propagated_fraction": sparse_res.propagated_active_fraction,
        }

        # Dense Synchronous
        dense_sched = DenseSynchronousScheduler(config, graph, dt=dt)
        dense_res = dense_sched.run(external_events, t_max, max_events=max_events_per_cell)
        dense_pot_err = float(np.linalg.norm(dense_res.final_potentials - ref_final_pot))

        cell_results["schedulers"][f"dense_sync_dt_{dt}"] = {
            "wall_time_sec": dense_res.wall_time_sec,
            "events_processed": dense_res.total_events_processed,
            "edges_traversed": dense_res.total_edges_traversed,
            "spikes": dense_res.total_spikes,
            "pot_l2_err": dense_pot_err,
            "propagated_fraction": dense_res.propagated_active_fraction,
        }

    return cell_results


def run_stage1_screening_suite(
    seeds: Optional[List[int]] = None,
    sizes: Optional[List[int]] = None,
    degrees: Optional[List[int]] = None,
    active_fractions: Optional[List[float]] = None,
    t_max: float = 20.0,
    max_events_per_cell: int = 1_000_000,
) -> Dict[str, Any]:
    """Execute the preregistered Stage 1 screening matrix and trigger evaluations."""
    if seeds is None:
        seeds = [11, 23, 37]
    if sizes is None:
        sizes = [128, 512, 2048]
    if degrees is None:
        degrees = [16]
    if active_fractions is None:
        active_fractions = [0.01, 0.05, 0.25, 1.0]

    all_cells: List[Dict[str, Any]] = []
    start_suite = time.perf_counter()

    for N in sizes:
        for D in degrees:
            for f in active_fractions:
                for s in seeds:
                    cell = run_stage1_single_cell(
                        num_nodes=N,
                        out_degree=D,
                        active_fraction=f,
                        seed=s,
                        t_max=t_max,
                        max_events_per_cell=max_events_per_cell,
                    )
                    all_cells.append(cell)

    total_wall = time.perf_counter() - start_suite

    return {
        "suite_name": "stage1_screening",
        "total_wall_sec": total_wall,
        "num_cells": len(all_cells),
        "cells": all_cells,
    }
