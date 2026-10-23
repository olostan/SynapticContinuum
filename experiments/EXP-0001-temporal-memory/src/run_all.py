"""Main orchestration script for EXP-0001 (Confirmatory Revised Run).

Conducts preregistered comparison across 5 seeds, all models, regimes,
task-specific trained negative controls, resource accounting, time-conserving
factorial analysis, and multi-point diagnostic ablation.
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
    return f"{utc_str}-linux-amd-x86_64-confirmatory"


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

    print(f"=== Starting EXP-0001 Confirmatory execution: run_id={run_id} ===")
    print(f"Host: {env_info['cpu'].get('model_name', 'CPU')}, RAM: {env_info['ram'].get('total_gb')} GB")
    print(f"Torch: {env_info['torch'].get('version')} (CPU AVX2: {env_info['torch'].get('cpu_capability')})")

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

        suites, audits = generate_all_datasets(
            seed=seed,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
            epsilon=cfg["data"]["epsilon"],
        )

        temporal_ds = suites["temporal"]
        sym_ds = suites["control_symbol"]
        ord_ds = suites["control_order"]

        # Temporal loaders
        temp_tr_loader = DataLoader(temporal_ds["train"], batch_size=batch_size, shuffle=True)
        temp_va_loader = DataLoader(temporal_ds["val"], batch_size=batch_size, shuffle=False)
        temp_eval_loaders = {
            "test_id": DataLoader(temporal_ds["test_id"], batch_size=batch_size, shuffle=False),
            "test_interpolation": DataLoader(temporal_ds["test_interpolation"], batch_size=batch_size, shuffle=False),
            "test_extrapolation": DataLoader(temporal_ds["test_extrapolation"], batch_size=batch_size, shuffle=False),
        }

        # Control loaders (task-specific training and test)
        sym_tr_loader = DataLoader(sym_ds["train"], batch_size=batch_size, shuffle=True)
        sym_va_loader = DataLoader(sym_ds["val"], batch_size=batch_size, shuffle=False)
        sym_te_loader = DataLoader(sym_ds["test"], batch_size=batch_size, shuffle=False)

        ord_tr_loader = DataLoader(ord_ds["train"], batch_size=batch_size, shuffle=True)
        ord_va_loader = DataLoader(ord_ds["val"], batch_size=batch_size, shuffle=False)
        ord_te_loader = DataLoader(ord_ds["test"], batch_size=batch_size, shuffle=False)

        seed_model_metrics: Dict[str, Any] = {}

        for model_name, factory in MODEL_FACTORIES.items():
            print(f"  [Task 1: Temporal] Training & evaluating {model_name}...")
            torch.manual_seed(seed)
            model_temp = factory(cfg, seed)

            # Record model accounting once
            if model_name not in model_accounting:
                params_info = count_parameters(model_temp)
                macs = estimate_macs_per_step(
                    model_name,
                    hidden_dim=cfg["models"]["hidden_units"],
                    trace_bases=cfg["models"]["trace_bases"],
                    fir_taps=cfg["models"]["fir_taps"],
                    max_degree=cfg["models"]["sparse_max_degree"],
                )
                params_info["macs_per_step"] = macs
                model_accounting[model_name] = params_info

            # Train on temporal ratio task
            trained_temp, stats_temp = train_model(
                model=model_temp,
                train_loader=temp_tr_loader,
                val_loader=temp_va_loader,
                lr=cfg["models"]["learning_rate"],
                max_epochs=max_epochs,
                patience=cfg["models"]["early_stopping_patience"],
                device=device,
            )

            # Measure inference latency on test_id
            t_eval_start = time.time()
            id_results = evaluate_model(trained_temp, temp_eval_loaders["test_id"], device=device)
            eval_latency_ms = round((time.time() - t_eval_start) * 1000.0 / len(temporal_ds["test_id"]), 3)
            stats_temp["inference_latency_ms_per_sample"] = eval_latency_ms

            temp_regimes = {"test_id": id_results}
            for rname in ["test_interpolation", "test_extrapolation"]:
                temp_regimes[rname] = evaluate_model(trained_temp, temp_eval_loaders[rname], device=device)

            # Zero-shot out-of-task test (retaining for historical comparison)
            temp_regimes["zero_shot_control_symbol"] = evaluate_model(trained_temp, sym_te_loader, device=device)
            temp_regimes["zero_shot_control_order"] = evaluate_model(trained_temp, ord_te_loader, device=device)

            # Task 2: Negative Control Symbol (Train separate model instance)
            print(f"  [Task 2: Control Symbol] Training {model_name}...")
            torch.manual_seed(seed)
            model_sym = factory(cfg, seed)
            trained_sym, stats_sym = train_model(
                model=model_sym,
                train_loader=sym_tr_loader,
                val_loader=sym_va_loader,
                lr=cfg["models"]["learning_rate"],
                max_epochs=max_epochs,
                patience=cfg["models"]["early_stopping_patience"],
                device=device,
            )
            res_sym = evaluate_model(trained_sym, sym_te_loader, device=device)

            # Task 3: Negative Control Order (Train separate model instance)
            print(f"  [Task 3: Control Order] Training {model_name}...")
            torch.manual_seed(seed)
            model_ord = factory(cfg, seed)
            trained_ord, stats_ord = train_model(
                model=model_ord,
                train_loader=ord_tr_loader,
                val_loader=ord_va_loader,
                lr=cfg["models"]["learning_rate"],
                max_epochs=max_epochs,
                patience=cfg["models"]["early_stopping_patience"],
                device=device,
            )
            res_ord = evaluate_model(trained_ord, ord_te_loader, device=device)

            seed_model_metrics[model_name] = {
                "training_stats": stats_temp,
                "temporal_regimes": temp_regimes,
                "trained_control_symbol": res_sym,
                "trained_control_order": res_ord,
            }

            # Factorial & ablation analysis on final seed
            if seed == seeds[-1] and model_name in ["TimeAwareGRU", "DiagonalDecaySSM", "TraceBank", "SparseFIR"]:
                print(f"    Running updated factorial/ablation for {model_name}...")
                fact_res = run_factorial_and_ablation(
                    trained_temp,
                    model_name,
                    temporal_ds["test_id"],
                    gaps=cfg["factorial"]["gaps"],
                    update_counts=cfg["factorial"]["update_counts"],
                    device=device,
                    max_eval_samples=200 if smoke_test else 1000,
                )
                factorial_results[model_name] = fact_res

        all_seed_results[f"seed_{seed}"] = {
            "wall_time_sec": round(time.time() - seed_start, 2),
            "audits": audits,
            "models": seed_model_metrics,
        }

    total_wall_time = round(time.time() - start_total_time, 2)
    peak_rss = get_peak_rss_mb()

    # Aggregate summaries across seeds
    aggregate_summary: Dict[str, Any] = {}
    for model_name in MODEL_FACTORIES.keys():
        aggregate_summary[model_name] = {
            "temporal_regimes": {},
            "trained_controls": {},
            "resource_profiles": {
                "train_time_sec": compute_aggregate_stats([
                    all_seed_results[f"seed_{s}"]["models"][model_name]["training_stats"]["train_time_sec"]
                    for s in seeds
                ]),
                "inference_latency_ms": compute_aggregate_stats([
                    all_seed_results[f"seed_{s}"]["models"][model_name]["training_stats"]["inference_latency_ms_per_sample"]
                    for s in seeds
                ]),
            },
        }

        # Temporal regimes
        for reg in ["test_id", "test_interpolation", "test_extrapolation", "zero_shot_control_symbol", "zero_shot_control_order"]:
            accs = [all_seed_results[f"seed_{s}"]["models"][model_name]["temporal_regimes"][reg]["balanced_accuracy"] for s in seeds]
            losses = [all_seed_results[f"seed_{s}"]["models"][model_name]["temporal_regimes"][reg]["loss"] for s in seeds]
            aggregate_summary[model_name]["temporal_regimes"][reg] = {
                "balanced_accuracy": compute_aggregate_stats(accs),
                "loss": compute_aggregate_stats(losses),
            }

        # Trained controls
        for ctrl in ["trained_control_symbol", "trained_control_order"]:
            accs = [all_seed_results[f"seed_{s}"]["models"][model_name][ctrl]["balanced_accuracy"] for s in seeds]
            losses = [all_seed_results[f"seed_{s}"]["models"][model_name][ctrl]["loss"] for s in seeds]
            aggregate_summary[model_name]["trained_controls"][ctrl] = {
                "balanced_accuracy": compute_aggregate_stats(accs),
                "loss": compute_aggregate_stats(losses),
            }

    final_report = {
        "metadata": {
            "experiment_id": "EXP-0001",
            "run_id": run_id,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "confirmatory",
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

    run_dir = os.path.join(output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    metrics_path = os.path.join(run_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n=== EXP-0001 Confirmatory completed in {total_wall_time}s. Peak RSS: {peak_rss} MB ===")
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
