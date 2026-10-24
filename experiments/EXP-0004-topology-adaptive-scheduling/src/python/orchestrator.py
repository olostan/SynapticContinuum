"""
EXP-0004 Campaign Orchestrator.
Coordinates C++ native benchmarks (both portable -O3 and Zen3 -march=znver3 builds),
external partitioner baselines (pymetis & igraph Leiden), biological connectome pilot,
and strict schema validation.
"""

import os
import sys
import json
import subprocess
import platform
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from .generators import fetch_or_load_celegans_connectome
from .metrics import compute_networkx_graph_metrics


def get_git_info() -> Dict[str, Any]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        dirty = bool(status)
        return {"commit": commit, "branch": branch, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "branch": "unknown", "dirty": False}


def run_campaign(profile: str = "standard", out_base_dir: str = "runs", build_id: str = "znver3_o3") -> str:
    exp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    build_dir = os.path.join(exp_dir, "build")
    bin_name = "exp0004_bench_native" if build_id == "znver3_o3" else "exp0004_bench"
    bin_path = os.path.join(build_dir, "bin", bin_name)

    if not os.path.exists(bin_path):
        print(f"[Orchestrator] Binary {bin_path} not found. Building with cmake...")
        os.makedirs(build_dir, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
        subprocess.check_call(["cmake", ".."], cwd=build_dir, env=env)
        subprocess.check_call(["cmake", "--build", ".", "-j6"], cwd=build_dir, env=env)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arch = platform.machine()
    run_id = f"{timestamp}-linux-{arch}-{build_id}"
    run_dir = os.path.join(exp_dir, out_base_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    metrics_path = os.path.join(run_dir, "metrics.json")

    py_exe = os.path.join(exp_dir, ".venv", "bin", "python")
    if not os.path.exists(py_exe):
        py_exe = sys.executable
    ext_script = os.path.join(exp_dir, "scripts", "compute_external_partitions.py")

    print(f"\n========================================================")
    print(f" SynapticContinuum EXP-0004 Benchmark Campaign")
    print(f" Run ID:   {run_id}")
    print(f" Build ID: {build_id} ({bin_name})")
    print(f" Profile:  {profile}")
    print(f" Out Path: {metrics_path}")
    print(f"========================================================\n")

    # 1. Execute C++ native benchmark suite
    cmd = [
        bin_path,
        "--profile", profile,
        "--build-id", build_id,
        "--python-bin", py_exe,
        "--ext-script", ext_script,
        "--out", metrics_path,
    ]
    subprocess.check_call(cmd, cwd=exp_dir)

    # 2. Execute Stage 5 Biological Connectome Pilot
    print("\n[Orchestrator] Executing Stage 5: Biological Connectome Pilot (C. elegans)...")
    celegans_data = fetch_or_load_celegans_connectome()
    print(f"  Connectome Nodes: {celegans_data['num_nodes']}, Total Edges: {celegans_data['num_edges']}")
    print(f"  Layer Counts: {celegans_data['layer_counts']}")

    part_celegans = [u % 6 for u in range(celegans_data["num_nodes"])]
    bio_metrics = compute_networkx_graph_metrics(
        celegans_data["num_nodes"],
        celegans_data["edges"],
        part_celegans,
    )
    print(f"  Biological Clustering C: {bio_metrics['clustering_coefficient']:.4f}")
    print(f"  Biological Path Length L: {bio_metrics['path_length_largest_scc']:.4f}")
    print(f"  Biological Edge Cut (6-part): {bio_metrics['edge_cut_fraction']:.4f}")

    # 3. Read and enrich metrics.json
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    metrics["run_id"] = run_id
    metrics["git"] = get_git_info()
    metrics["stage5_biological_connectome_pilot"] = {
        "dataset_name": celegans_data["dataset_name"],
        "source_url": celegans_data["source_url"],
        "sha256": celegans_data["sha256"],
        "num_nodes": celegans_data["num_nodes"],
        "num_edges": celegans_data["num_edges"],
        "layer_counts": celegans_data["layer_counts"],
        "metrics": bio_metrics,
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # 4. Strictly validate every emitted record against schemas/benchmark_schema.json
    sys.path.insert(0, exp_dir)
    from scripts.pareto_query import load_json_records
    validated = load_json_records(Path(metrics_path), strict=True)
    print(f"\n[Orchestrator] Strictly validated {len(validated)} schema-v1.0.0 records in {metrics_path}\n")
    return metrics_path


if __name__ == "__main__":
    profile_arg = "standard"
    out_arg = "runs"
    build_arg = "znver3_o3"
    for i, arg in enumerate(sys.argv):
        if arg == "--profile" and i + 1 < len(sys.argv):
            profile_arg = sys.argv[i + 1]
        elif arg == "--out" and i + 1 < len(sys.argv):
            out_arg = sys.argv[i + 1]
        elif arg == "--build-id" and i + 1 < len(sys.argv):
            build_arg = sys.argv[i + 1]

    run_campaign(profile=profile_arg, out_base_dir=out_arg, build_id=build_arg)
