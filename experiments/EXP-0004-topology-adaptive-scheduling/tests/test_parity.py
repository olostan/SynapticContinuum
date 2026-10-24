"""
Pytest suite for EXP-0004 correctness and parity verification.
"""

import os
import subprocess
import json
import pytest

from src.python.generators import fetch_or_load_celegans_connectome
from src.python.metrics import compute_networkx_graph_metrics


def test_native_cxx_test_suite():
    """Verify that the full C++ native test suite passes with 100% success."""
    exp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bin_path = os.path.join(exp_dir, "build", "bin", "topology_tests")

    assert os.path.exists(bin_path), f"Native test binary {bin_path} not found"
    res = subprocess.run([bin_path], capture_output=True, text=True)
    print(res.stdout)
    assert res.returncode == 0, f"topology_tests failed:\n{res.stderr}\n{res.stdout}"
    assert "ALL EXP-0004 TESTS PASSED SUCCESSFULLY" in res.stdout


def test_biological_connectome_loader():
    """Verify C. elegans connectome dataset loader and structure."""
    data = fetch_or_load_celegans_connectome()
    assert data["num_nodes"] >= 279
    assert data["num_edges"] > 0
    assert 1 in data["layer_counts"]  # Electrical gap junctions
    assert 2 in data["layer_counts"]  # Monadic synapses
    assert 3 in data["layer_counts"]  # Polyadic synapses


def test_networkx_metrics_sanity():
    """Verify NetworkX graph metrics computation on a small ring lattice."""
    num_nodes = 10
    edges = [(i, (i + 1) % num_nodes) for i in range(num_nodes)]
    metrics = compute_networkx_graph_metrics(num_nodes, edges)
    assert metrics["num_nodes"] == 10
    assert metrics["num_edges"] == 10
    assert 0.0 <= metrics["clustering_coefficient"] <= 1.0


def test_benchmark_smoke_execution(tmp_path):
    """Verify that exp0004_bench runs in smoke mode and produces valid JSON metrics."""
    exp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bin_path = os.path.join(exp_dir, "build", "bin", "exp0004_bench")

    assert os.path.exists(bin_path), f"Benchmark binary {bin_path} not found"
    out_json = str(tmp_path / "smoke_metrics.json")
    cmd = [bin_path, "--profile", "smoke", "--out", out_json]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Benchmark execution failed:\n{res.stderr}\n{res.stdout}"

    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["experiment"] == "EXP-0004"
    assert "stage0_disconnected_control" in data
    assert "stage1_topology_sweep" in data
    assert "stage2_partition_strategies" in data
    assert "stage3_schedulers" in data
    assert "stage4_relaxed_ordering" in data
