"""Main orchestration script for EXP-0001.

Conducts preregistered comparison across 5 seeds, all models, regimes,
resource accounting, factorial analysis, and trace ablation.
"""
import argparse
import datetime
import json
import os
import time
from typing import Any, Dict, List
import yaml
import numpy as np
import torch
from torch.utils.data import DataLoader

from src.hardware import detect_environment
from src.accounting import count_parameters, estimate_macs_per_step, get_peak_rss_mb
from src.data import generate_all_datasets
from src.models import (
    MajorityModel,
    ArithmeticOracle,
    MLPOracle,
    ReservoirModel,
    TimeAwareGRU,
    DiagonalDecaySSM,
    TraceBankModel,
    SparseFIRModel,
)
from src.train import train_model
from src.eval import evaluate_model
from src.factorial import run_factorial_and_ablation


MODEL_FACTORIES = {
    "Majority": lambda cfg, seed: MajorityModel(prior=0.5),
    "ArithmeticOracle": lambda cfg, seed: ArithmeticOracle(),
    "MLPOracle": lambda cfg, seed: MLPOracle(hidden_dim=cfg["models"]["hidden_units"]),
    "Reservoir": lambda cfg, seed: ReservoirModel(
        hidden_dim=cfg["models"]["hidden_units"], seed=seed
    ),
    "TimeAwareGRU": lambda cfg, seed: TimeAwareGRU(
        hidden_dim=cfg["models"]["hidden_units"]
    ),
    "DiagonalDecaySSM": lambda cfg, seed: DiagonalDecaySSM(
        hidden_dim=cfg["models"]["hidden_units"]
    ),
    "TraceBank": lambda cfg, seed: TraceBankModel(
        hidden_dim=cfg["models"]["hidden_units"],
        trace_bases=cfg["models"]["trace_bases"],
        max_degree=cfg["models"]["sparse_max_degree"],
        seed=seed,
    ),
    "SparseFIR": lambda cfg, seed: SparseFIRModel(
        hidden_dim=cfg["models"]["hidden_units"],
        fir_taps=cfg["models"]["fir_taps"],
        max_degree=cfg["models"]["sparse_max_degree"],
        seed=seed,
    ),
}


def build_run_id() -> str:
    utc_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{utc_str}-linux-amd-x86_64"


def compute_aggregate_stats(values: List[float]) -> Dict[str, float]:
    arr = np.array(values, dtype=np.float64)
    return {
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
    }


def run_experiment(
    config_path: str = "configs/default.yaml",
    smoke_test: bool = False,
    output_dir: str = "runs",
) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    env_info = detect_environment()
    run_id = build_run_id()
    if smoke_test:
        run_id += "-smoke"

    print(f"=== Starting EXP-0001 execution: run_id={run_id} ===")
    print(f"Host: {env_info['cpu'].get('model_name', 'CPU')}, RAM: {env_info['ram'].get('total_gb')} GB")
    print(f"Torch: {env_info['torch'].get('version')} (CPU AVX2: {env_info['torch'].get('cpu_capability')})")

    # Configure seeds and sizes
    seeds = [11] if smoke_test else cfg["seeds"]
    train_size = 200 if smoke_test else cfg["data"]["train_size"]
    val_size = 50 if smoke_test else cfg["data"]["validation_size"]
    test_size = 50 if smoke_test else cfg["data"]["test_size_per_regime"]
    max_epochs = 3 if smoke_test else cfg["models"]["max_epochs"]
    batch_size = 32 if smoke_test else cfg["models"]["batch_size"]
    device = cfg["models"].get("device", "cpu")

    all_seed_results: Dict[str, Any] = {}
    model_accounting: Dict[str, Any] = {}
    factorial_results: Dict[str, Any] = {}

    start_total_time = time.time()

    for seed in seeds:
        print(f"\n--- Running Seed {seed} ---")
        seed_start = time.time()

        # Deterministic dataset generation
        datasets, audit = generate_all_datasets(
            seed=seed,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
            epsilon=cfg["data"]["epsilon"],
        )

        train_loader = DataLoader(datasets["train"], batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(datasets["val"], batch_size=batch_size, shuffle=False)

        eval_loaders = {
            "val": val_loader,
            "test_id": DataLoader(datasets["test_id"], batch_size=batch_size, shuffle=False),
            "test_interpolation": DataLoader(datasets["test_interpolation"], batch_size=batch_size, shuffle=False),
            "test_extrapolation": DataLoader(datasets["test_extrapolation"], batch_size=batch_size, shuffle=False),
            "control_symbol": DataLoader(datasets["control_symbol"], batch_size=batch_size, shuffle=False),
            "control_order": DataLoader(datasets["control_order"], batch_size=batch_size, shuffle=False),
        }

        seed_model_metrics: Dict[str, Any] = {}

        for model_name, factory in MODEL_FACTORIES.items():
            print(f"  Training & evaluating {model_name}...")
            # Set seed for model initialization
            torch.manual_seed(seed)
            model = factory(cfg, seed)

            # Record model resource accounting once
            if model_name not in model_accounting:
                params_info = count_parameters(model)
                macs = estimate_macs_per_step(
                    model_name,
                    hidden_dim=cfg["models"]["hidden_units"],
                    trace_bases=cfg["models"]["trace_bases"],
                    fir_taps=cfg["models"]["fir_taps"],
                    max_degree=cfg["models"]["sparse_max_degree"],
                )
                params_info["macs_per_step"] = macs
                model_accounting[model_name] = params_info

            # Train model
            trained_model, train_stats = train_model(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                lr=cfg["models"]["learning_rate"],
                max_epochs=max_epochs,
                patience=cfg["models"]["early_stopping_patience"],
                device=device,
            )

            # Evaluate on all regimes
            regime_results = {}
            for regime_name, loader in eval_loaders.items():
                regime_results[regime_name] = evaluate_model(trained_model, loader, device=device)

            seed_model_metrics[model_name] = {
                "training": train_stats,
                "regimes": regime_results,
            }

            # Run factorial and trace ablation on final seed
            if seed == seeds[-1] and model_name in ["TimeAwareGRU", "DiagonalDecaySSM", "TraceBank", "SparseFIR"]:
                print(f"    Running factorial/ablation for {model_name}...")
                fact_res = run_factorial_and_ablation(
                    trained_model,
                    model_name,
                    datasets["test_id"],
                    gaps=cfg["factorial"]["gaps"],
                    update_counts=cfg["factorial"]["update_counts"],
                    device=device,
                    max_eval_samples=200 if smoke_test else 1000,
                )
                factorial_results[model_name] = fact_res

        all_seed_results[f"seed_{seed}"] = {
            "wall_time_sec": round(time.time() - seed_start, 2),
            "audit": audit,
            "models": seed_model_metrics,
        }

    total_wall_time = round(time.time() - start_total_time, 2)
    peak_rss = get_peak_rss_mb()

    # Aggregate statistics across seeds for each model and regime
    aggregate_summary: Dict[str, Any] = {}
    regimes = ["test_id", "test_interpolation", "test_extrapolation", "control_symbol", "control_order"]

    for model_name in MODEL_FACTORIES.keys():
        aggregate_summary[model_name] = {"regimes": {}}
        for reg in regimes:
            accs = [
                all_seed_results[f"seed_{s}"]["models"][model_name]["regimes"][reg]["balanced_accuracy"]
                for s in seeds
            ]
            losses = [
                all_seed_results[f"seed_{s}"]["models"][model_name]["regimes"][reg]["loss"]
                for s in seeds
            ]
            aggregate_summary[model_name]["regimes"][reg] = {
                "balanced_accuracy": compute_aggregate_stats(accs),
                "loss": compute_aggregate_stats(losses),
            }

    final_report = {
        "metadata": {
            "experiment_id": "EXP-0001",
            "run_id": run_id,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "smoke_test": smoke_test,
            "seeds": seeds,
            "total_wall_time_sec": total_wall_time,
            "peak_rss_mb": peak_rss,
        },
        "environment": env_info,
        "config": cfg,
        "model_accounting": model_accounting,
        "aggregate_summary": aggregate_summary,
        "factorial_and_ablation": factorial_results,
        "seed_runs": all_seed_results,
    }

    # Write metrics to runs/<run_id>/metrics.json
    run_dir = os.path.join(output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    metrics_path = os.path.join(run_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n=== EXP-0001 completed in {total_wall_time}s. Peak RSS: {peak_rss} MB ===")
    print(f"Metrics written to: {metrics_path}")

    return final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--smoke", action="store_true", help="Run tiny smoke test")
    parser.add_argument("--output-dir", default="runs")
    args = parser.parse_args()

    run_experiment(
        config_path=args.config,
        smoke_test=args.smoke,
        output_dir=args.output_dir,
    )
