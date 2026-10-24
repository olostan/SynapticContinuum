"""
EXP-0004 Campaign Orchestrator.
Coordinates C++ native benchmarks, biological connectome pilot, and results aggregation.
"""

import os
import sys
import json
import time
import subprocess
import platform
import shutil
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

from .generators import fetch_or_load_celegans_connectome
from .metrics import compute_networkx_graph_metrics


def get_git_info() -> Dict[str, str]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        dirty = bool(status)
        return {"commit": commit, "branch": branch, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "branch": "unknown", "dirty": False}


def run_campaign(profile: str = "standard", out_base_dir: str = "runs") -> str:
    exp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    build_dir = os.path.join(exp_dir, "build")
    bin_path = os.path.join(build_dir, "bin", "exp0004_bench")

    if not os.path.exists(bin_path):
        print(f"[Orchestrator] Binary {bin_path} not found. Building with cmake...")
        os.makedirs(build_dir, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
        subprocess.check_call(["cmake", ".."], cwd=build_dir, env=env)
        subprocess.check_call(["cmake", "--build", ".", "-j6"], cwd=build_dir, env=env)

    # Generate timestamped run directory
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arch = platform.machine()
    run_id = f"{timestamp}-linux-{arch}"
    run_dir = os.path.join(exp_dir, out_base_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    metrics_path = os.path.join(run_dir, "metrics.json")

    print(f"\n========================================================")
    print(f" SynapticContinuum EXP-0004 Benchmark Campaign")
    print(f" Run ID:   {run_id}")
    print(f" Profile:  {profile}")
    print(f" Out Path: {metrics_path}")
    print(f"========================================================\n")

    # 1. Execute C++ native benchmark suite
    cmd = [bin_path, "--profile", profile, "--out", metrics_path]
    subprocess.check_call(cmd)

    # 2. Execute Stage 5 Biological Connectome Pilot
    print("\n[Orchestrator] Executing Stage 5: Biological Connectome Pilot (C. elegans)...")
    celegans_data = fetch_or_load_celegans_connectome()
    print(f"  Connectome Nodes: {celegans_data['num_nodes']}, Total Edges: {celegans_data['num_edges']}")
    print(f"  Layer Counts: {celegans_data['layer_counts']}")

    # Compute network metrics on biological graph
    part_celegans = [u % 6 for u in range(celegans_data["num_nodes"])]
    bio_metrics = compute_networkx_graph_metrics(
        celegans_data["num_nodes"],
        celegans_data["edges"],
        part_celegans
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
        "metrics": bio_metrics
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n[Orchestrator] Campaign completed successfully. Metrics written to {metrics_path}\n")
    return metrics_path


if __name__ == "__main__":
    profile_arg = "standard"
    out_arg = "runs"
    for i, arg in enumerate(sys.argv):
        if arg == "--profile" and i + 1 < len(sys.argv):
            profile_arg = sys.argv[i + 1]
        elif arg == "--out" and i + 1 < len(sys.argv):
            out_arg = sys.argv[i + 1]

    run_campaign(profile=profile_arg, out_base_dir=out_arg)
