"""Orchestration of staged benchmarks and metrics generation for EXP-0003."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

import numpy as np

from .bridge import create_py_fixture, run_cpp_engine, run_py_event_sim, run_py_sync_sim
from .hardware import discover_hardware, preflight_check


def get_git_commit_info() -> Dict[str, str]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        sha = "unknown"
    try:
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        dirty = False
    return {"commit_sha": sha, "is_dirty": dirty}


class BenchmarkRunner:
    def __init__(self, output_root: str = "runs"):
        self.output_root = output_root
        self.hw = discover_hardware()
        self.git_info = get_git_commit_info()
        os.makedirs(self.output_root, exist_ok=True)

    def run_repetition_cell(
        self,
        engine: str,
        num_nodes: int,
        degree: int,
        active_fraction: float,
        rate: float,
        t_max: float,
        seed: int,
        dt: float = 0.1,
        workers: int = 4,
        topology: str = "random",
        timing: str = "poisson",
        history_L: int = 0,
        trace_B: int = 0,
        warmups: int = 2,
        reps: int = 5,
    ) -> Dict[str, Any]:
        """Runs cell with warmups and repetitions, measuring pure simulation and e2e wall time."""
        safe, est_bytes, limit_bytes = preflight_check(
            num_nodes, degree, active_fraction, rate, t_max, engine, max_fraction=0.60
        )
        if not safe:
            return {
                "engine": engine,
                "status": "SKIPPED_MEMORY_PREFLIGHT",
                "estimated_memory_bytes": est_bytes,
                "limit_bytes": limit_bytes,
            }

        # Python execution
        if engine.startswith("py_"):
            # Construct fixture ONCE outside the timed simulation loop to isolate runtime/interpreter overhead
            t_fixture_start = time.perf_counter()
            config, graph, ext_events = create_py_fixture(
                num_nodes, degree, active_fraction, rate, t_max, seed
            )
            fixture_time = time.perf_counter() - t_fixture_start

            sim_times = []
            e2e_times = []
            last_res = {}

            for r in range(warmups + reps):
                t0_e2e = time.perf_counter()
                if engine == "py_event":
                    res = run_py_event_sim(config, graph, ext_events, t_max)
                elif engine == "py_sync_dense":
                    res = run_py_sync_sim(config, graph, ext_events, t_max, dt=dt, sparse=False)
                elif engine == "py_sync_sparse":
                    res = run_py_sync_sim(config, graph, ext_events, t_max, dt=dt, sparse=True)
                else:
                    raise ValueError(f"Unknown python engine: {engine}")
                e2e_elapsed = (time.perf_counter() - t0_e2e) + fixture_time

                if r >= warmups:
                    sim_times.append(res["wall_time_sec"])
                    e2e_times.append(e2e_elapsed)
                    last_res = res

            sim_times.sort()
            e2e_times.sort()
            median_sim = sim_times[len(sim_times) // 2]
            p95_sim = sim_times[int(len(sim_times) * 0.95)] if len(sim_times) > 1 else sim_times[0]
            median_e2e = e2e_times[len(e2e_times) // 2]

            return {
                "engine": engine,
                "status": "COMPLETED",
                "median_sim_wall_time_sec": median_sim,
                "median_e2e_wall_time_sec": median_e2e,
                "p95_sim_wall_time_sec": p95_sim,
                "min_sim_wall_time_sec": sim_times[0],
                "max_sim_wall_time_sec": sim_times[-1],
                "reps_count": reps,
                "total_events_processed": last_res.get("total_events_processed", 0),
                "total_edges_traversed": last_res.get("total_edges_traversed", 0),
                "total_spikes": last_res.get("total_spikes", 0),
                "peak_queue_size": last_res.get("peak_queue_size", 0),
                "estimated_memory_bytes": est_bytes,
                "peak_rss_bytes": est_bytes, # Python estimate
            }

        # C++ Native execution
        cpp_engine_name = engine
        if engine == "cpp_dense_sync":
            cpp_engine_name = "dense_sync"
        elif engine == "cpp_sparse_sync":
            cpp_engine_name = "sparse_sync"
        elif engine.startswith("cpp_"):
            cpp_engine_name = engine[4:]

        res = run_cpp_engine(
            engine=cpp_engine_name,
            num_nodes=num_nodes,
            degree=degree,
            active_fraction=active_fraction,
            rate=rate,
            t_max=t_max,
            seed=seed,
            dt=dt,
            workers=workers,
            topology=topology,
            timing=timing,
            history_L=history_L,
            trace_B=trace_B,
            warmups=warmups,
            reps=reps,
        )

        return {
            "engine": engine,
            "status": "COMPLETED",
            "median_sim_wall_time_sec": res["wall_time_sec"],
            "median_e2e_wall_time_sec": res.get("e2e_wall_time_sec", res["wall_time_sec"]),
            "total_events_processed": res["total_events_processed"],
            "total_edges_traversed": res["total_edges_traversed"],
            "total_spikes": res["total_spikes"],
            "peak_queue_size": res["peak_queue_size"],
            "state_digest": res["state_digest"],
            "peak_rss_bytes": res.get("peak_rss_bytes", res.get("rss_bytes", 0)),
            "estimated_memory_bytes": res.get("estimated_memory_bytes", est_bytes),
            "lock_waits": res.get("lock_waits", 0),
            "causal_stalls": res.get("causal_stalls", 0),
            "cross_region_events": res.get("cross_region_events", 0),
        }

    def run_standard_screening(self, seeds: List[int] = [11, 23, 37]) -> List[Dict[str, Any]]:
        """Runs preregistered standard shared cross-host screening benchmark."""
        sizes = [128, 1024, 10000]
        active_fractions = [0.01, 0.10, 1.00]
        degree = 16
        rate = 1.0
        t_max = 5.0

        engines = [
            "py_event",
            "py_sync_dense",
            "cpp_literal",
            "cpp_packed",
            "cpp_queue_binary",
            "cpp_queue_dary4",
            "cpp_queue_bucket",
            "cpp_dense_sync",
            "cpp_sparse_sync",
            "cpp_locked",
            "cpp_owner",
            "cpp_hybrid",
        ]

        results = []
        for n in sizes:
            for f in active_fractions:
                for seed in seeds:
                    for eng in engines:
                        # Skip slow python event runs at N=10000 f=1.0
                        if eng == "py_event" and n == 10000 and f > 0.10:
                            continue
                        if eng.startswith("py_sync") and n == 10000 and f > 0.10:
                            continue

                        print(f"[BENCH-STANDARD] N={n} f={f} seed={seed} eng={eng}...", flush=True)
                        cell = self.run_repetition_cell(
                            engine=eng,
                            num_nodes=n,
                            degree=degree,
                            active_fraction=f,
                            rate=rate,
                            t_max=t_max,
                            seed=seed,
                            workers=4,
                            warmups=2,
                            reps=5,
                        )
                        cell.update({
                            "num_nodes": n,
                            "degree": degree,
                            "active_fraction": f,
                            "rate": rate,
                            "t_max": t_max,
                            "seed": seed,
                            "profile": "standard",
                        })
                        results.append(cell)
        return results

    def run_primary_scaling(self, seeds: List[int] = [11, 23, 37, 41, 53]) -> List[Dict[str, Any]]:
        """Runs primary scaling benchmark matrix on Linux."""
        results = []

        # 1. Scaling N in {100000, 1000000} on native engines
        for n in [100000, 1000000]:
            for f in [0.001, 0.01]:
                for seed in seeds:
                    for eng in ["cpp_packed", "cpp_queue_binary", "cpp_queue_dary4", "cpp_queue_bucket", "cpp_dense_sync", "cpp_owner"]:
                        if eng == "cpp_dense_sync" and n == 1000000:
                            if seed != seeds[0]:
                                continue

                        print(f"[BENCH-SCALING] N={n} f={f} seed={seed} eng={eng}...", flush=True)
                        cell = self.run_repetition_cell(
                            engine=eng,
                            num_nodes=n,
                            degree=16,
                            active_fraction=f,
                            rate=1.0,
                            t_max=5.0,
                            seed=seed,
                            workers=6,
                            warmups=2,
                            reps=5,
                        )
                        cell.update({
                            "num_nodes": n,
                            "degree": 16,
                            "active_fraction": f,
                            "rate": 1.0,
                            "t_max": 5.0,
                            "seed": seed,
                            "profile": "scaling",
                        })
                        results.append(cell)

        # 2. Worker scaling study on N=100000 (workers in 1, 2, 4, 6, 8, 12)
        for w in [1, 2, 4, 6, 8, 12]:
            for eng in ["cpp_locked", "cpp_owner"]:
                for seed in [11, 23, 37]:
                    print(f"[BENCH-WORKERS] workers={w} eng={eng} seed={seed}...", flush=True)
                    cell = self.run_repetition_cell(
                        engine=eng,
                        num_nodes=100000,
                        degree=16,
                        active_fraction=0.01,
                        rate=1.0,
                        t_max=5.0,
                        seed=seed,
                        workers=w,
                        warmups=1,
                        reps=3,
                    )
                    cell.update({
                        "num_nodes": 100000,
                        "degree": 16,
                        "active_fraction": 0.01,
                        "rate": 1.0,
                        "t_max": 5.0,
                        "seed": seed,
                        "workers": w,
                        "profile": "worker_scaling",
                    })
                    results.append(cell)

        # 3. Queue comparison under arrival distribution (poisson, regular, bursty)
        for timing in ["poisson", "regular", "bursty"]:
            for q_eng in ["cpp_queue_binary", "cpp_queue_dary4", "cpp_queue_bucket"]:
                for seed in [11, 23]:
                    print(f"[BENCH-TIMING] timing={timing} eng={q_eng} seed={seed}...", flush=True)
                    cell = self.run_repetition_cell(
                        engine=q_eng,
                        num_nodes=100000,
                        degree=16,
                        active_fraction=0.01,
                        rate=1.0,
                        t_max=5.0,
                        seed=seed,
                        timing=timing,
                        warmups=1,
                        reps=3,
                    )
                    cell.update({
                        "num_nodes": 100000,
                        "degree": 16,
                        "active_fraction": 0.01,
                        "rate": 1.0,
                        "t_max": 5.0,
                        "seed": seed,
                        "timing": timing,
                        "profile": "timing_distribution",
                    })
                    results.append(cell)

        # 4. History depth and Trace bank scaling
        for L in [0, 16, 64, 256]:
            cell = self.run_repetition_cell(
                engine="cpp_packed",
                num_nodes=10000,
                degree=16,
                active_fraction=0.10,
                rate=1.0,
                t_max=5.0,
                seed=11,
                history_L=L,
                warmups=1,
                reps=3,
            )
            cell.update({"num_nodes": 10000, "history_L": L, "profile": "history_scaling"})
            results.append(cell)

        for B in [0, 4, 8]:
            cell = self.run_repetition_cell(
                engine="cpp_packed",
                num_nodes=10000,
                degree=16,
                active_fraction=0.10,
                rate=1.0,
                t_max=5.0,
                seed=11,
                trace_B=B,
                warmups=1,
                reps=3,
            )
            cell.update({"num_nodes": 10000, "trace_B": B, "profile": "trace_scaling"})
            results.append(cell)

        return results

    def save_metrics(self, all_results: List[Dict[str, Any]], run_id: Optional[str] = None) -> str:
        """Saves complete metrics bundle to runs/<run_id>/metrics.json."""
        if not run_id:
            now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            host_tag = f"{self.hw.platform_system.lower()}-{self.hw.machine}"
            run_id = f"{now_str}-{host_tag}"

        run_dir = os.path.join(self.output_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        metrics_file = os.path.join(run_dir, "metrics.json")

        bundle = {
            "schema_version": 1,
            "experiment_id": "EXP-0003",
            "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": self.git_info,
            "hardware": asdict(self.hw),
            "total_benchmark_cells": len(all_results),
            "results": all_results,
        }

        with open(metrics_file, "w") as f:
            json.dump(bundle, f, indent=2)

        return metrics_file
