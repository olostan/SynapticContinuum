"""Main execution entry point for EXP-0002.

Governed by EXPERIMENTATION.md & PROMPT.md:
- Deterministic smoke tests first
- Staged execution: Stage 1 Crossover, Stage 2 Representation, Stage 3 Causal study
- Real host provenance recording (CPU, RAM, git commit, dirty tree)
- Output compact metrics JSON under runs/<run_id>/metrics.json
"""
import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict

import yaml
import numpy as np

from .benchmarks import run_stage1_screening_suite
from .causal_study import run_stage3_causal_suite
from .hardware import detect_environment
from .representation import run_stage2_representation_suite
from .tasks import run_task_a_analytic_parity, run_task_c_matched_observation


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to seamlessly handle NumPy types."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super().default(obj)


def run_stage0_smoke() -> Dict[str, Any]:
    """Stage 0: Correctness, smoke tests, and analytic parity validation."""
    start_smoke = time.perf_counter()

    # 1. Analytic parity check
    task_a_res = run_task_a_analytic_parity(tau_m=5.0, t_max=15.0)
    assert task_a_res["event_driven_abs_err"] < 1e-5, (
        f"Event-driven analytic error too high: {task_a_res['event_driven_abs_err']}"
    )

    # 2. Matched observation check
    task_c_res = run_task_c_matched_observation(
        num_nodes=32, trace_bases_B=4, history_capacity_L=8, seed=42
    )
    assert task_c_res["discriminable"], "Task C sequences could not be discriminated by trace memory!"

    wall_sec = time.perf_counter() - start_smoke
    return {
        "status": "PASSED",
        "wall_time_sec": wall_sec,
        "task_a_parity": task_a_res,
        "task_c_discrimination": task_c_res,
    }


def main():
    parser = argparse.ArgumentParser(description="EXP-0002 Event-Driven Dynamics Runner")
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(
            os.path.dirname(__file__), "..", "configs", "default.yaml"
        ),
        help="Path to YAML configuration file",
    )
    parser.add_argument("--smoke-only", action="store_true", help="Run only Stage 0 smoke tests")
    parser.add_argument("--stage1-only", action="store_true", help="Run only Stage 1 crossover")
    parser.add_argument("--stage2-only", action="store_true", help="Run only Stage 2 representation")
    parser.add_argument("--stage3-only", action="store_true", help="Run only Stage 3 causal study")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory for runs")
    args = parser.parse_args()

    # Load configuration
    with open(args.config, "r") as f:
        config_data = yaml.safe_load(f)

    # Host environment provenance
    env_info = detect_environment()
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp_utc}-linux-x86_64"

    print("=" * 80)
    print(f"EXP-0002 Event-Driven Neural Dynamics — Run ID: {run_id}")
    print(f"Host: {env_info['os']['machine']} | CPU: {env_info['cpu'].get('model_name', 'Unknown')}")
    print(f"RAM Total: {env_info['ram'].get('total_gb')} GB | Avail: {env_info['ram'].get('available_gb')} GB")
    print(f"PyTorch: {env_info['torch'].get('version')} | CPU Instruction: {env_info['torch'].get('cpu_capability')}")
    print(f"Git Commit: {env_info['git'].get('commit_sha')} (dirty={env_info['git'].get('is_dirty')})")
    print("=" * 80)

    # Output run bundle
    run_record: Dict[str, Any] = {
        "experiment_id": config_data.get("experiment_id", "EXP-0002"),
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "environment": env_info,
        "config": config_data,
        "stages": {},
    }

    # Stage 0: Smoke
    print("\n[STAGE 0] Executing Smoke Tests & Analytic Parity...")
    stage0_res = run_stage0_smoke()
    run_record["stages"]["stage0_smoke"] = stage0_res
    print(f"Stage 0 PASSED in {stage0_res['wall_time_sec']:.3f}s. Event-driven analytic error: {stage0_res['task_a_parity']['event_driven_abs_err']:.2e}")

    if args.smoke_only:
        print("Smoke-only flag provided; terminating early.")
        return

    # Stage 1: Crossover
    if not (args.stage2_only or args.stage3_only):
        print("\n[STAGE 1] Executing Crossover Screening Matrix...")
        s1_conf = config_data.get("stage1", {})
        stage1_res = run_stage1_screening_suite(
            seeds=config_data.get("execution", {}).get("seeds_screening", [11, 23, 37]),
            sizes=s1_conf.get("sizes", [128, 512, 2048]),
            degrees=s1_conf.get("degrees", [16]),
            active_fractions=s1_conf.get("active_fractions", [0.01, 0.05, 0.25, 1.0]),
            t_max=config_data.get("execution", {}).get("t_max_stage1", 15.0),
            max_events_per_cell=config_data.get("execution", {}).get("max_events_per_cell", 500000),
        )
        run_record["stages"]["stage1_crossover"] = stage1_res
        print(f"Stage 1 COMPLETE in {stage1_res['total_wall_sec']:.2f}s across {stage1_res['num_cells']} cells.")

    # Stage 2: Temporal Representation
    if not (args.stage1_only or args.stage3_only):
        print("\n[STAGE 2] Executing Temporal Representation Analysis (Task B & C)...")
        s2_conf = config_data.get("stage2", {})
        stage2_res = run_stage2_representation_suite(
            sizes=s2_conf.get("sizes", [128, 512]),
            history_lengths=s2_conf.get("history_entries", [0, 1, 4, 16, 64, 256]),
            trace_bases_list=s2_conf.get("trace_bases", [0, 1, 4, 8]),
            seeds=config_data.get("execution", {}).get("seeds_screening", [11, 23, 37]),
            num_samples_task_b=s2_conf.get("num_task_b_samples", 300),
        )
        run_record["stages"]["stage2_representation"] = stage2_res
        print(f"Stage 2 COMPLETE in {stage2_res['total_wall_sec']:.2f}s across {stage2_res['num_evaluations']} evaluations.")

    # Stage 3: Endogenous Dynamics and Causal Study
    if not (args.stage1_only or args.stage2_only):
        print("\n[STAGE 3] Executing 5-Seed Endogenous Dynamics & Causal Study...")
        s3_conf = config_data.get("stage3", {})
        stage3_res = run_stage3_causal_suite(
            seeds=config_data.get("execution", {}).get("seeds_primary", [11, 23, 37, 41, 53]),
            sizes=s3_conf.get("sizes", [128, 512]),
            silence_gaps=s3_conf.get("silence_gaps", [1.0, 10.0, 50.0]),
            trace_bases_B=s3_conf.get("trace_bases_B", 4),
            history_capacity_L=s3_conf.get("history_capacity_L", 16),
        )
        run_record["stages"]["stage3_causal_study"] = stage3_res
        print(f"Stage 3 COMPLETE in {stage3_res['total_wall_sec']:.2f}s across {stage3_res['num_intervention_records']} intervention tests.")

    # Save compact metrics JSON
    runs_dir = args.output_dir or os.path.join(
        os.path.dirname(__file__), "..", "runs", run_id
    )
    os.makedirs(runs_dir, exist_ok=True)
    metrics_path = os.path.join(runs_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(run_record, f, indent=2, cls=NumpyEncoder)

    metrics_size_kb = os.path.getsize(metrics_path) / 1024
    print("\n" + "=" * 80)
    print(f"Run completed successfully! Metrics recorded at: {metrics_path} ({metrics_size_kb:.1f} KB)")
    print("=" * 80)


if __name__ == "__main__":
    main()
