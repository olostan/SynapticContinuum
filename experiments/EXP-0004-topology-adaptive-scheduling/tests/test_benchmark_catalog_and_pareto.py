import json
from pathlib import Path
import pytest
from scripts.pareto_query import filter_records, compute_pareto_frontier

def test_benchmark_schema_structure():
    """Verify that benchmark_schema.json exists and contains required properties."""
    schema_path = Path(__file__).parent.parent / "schemas" / "benchmark_schema.json"
    assert schema_path.exists(), "benchmark_schema.json missing!"
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    assert schema.get("version") == "1.0.0"
    assert "required" in schema
    assert "benchmark_id" in schema["required"]
    assert "semantic_class" in schema["required"]
    assert "resource_metrics" in schema["required"]
    assert "validation" in schema["required"]

def test_pareto_query_filtering_and_dominance():
    """Verify Pareto frontier correctly prunes dominated configurations."""
    dummy_records = [
        {
            "benchmark_id": "fast_and_lean",
            "semantic_class": "exact",
            "graph_configuration": {"num_nodes": 100000, "topology_type": "modular_sbm"},
            "execution_configuration": {"engine_id": "cpp_persistent_pool", "num_workers": 6},
            "timing_breakdown": {"events_per_sec": 5000000.0},
            "resource_metrics": {"peak_rss_bytes": 100 * 1024 * 1024},
            "validation": {"parity_with_serial": True}
        },
        {
            "benchmark_id": "slow_and_heavy", # Strictly dominated by fast_and_lean
            "semantic_class": "exact",
            "graph_configuration": {"num_nodes": 100000, "topology_type": "modular_sbm"},
            "execution_configuration": {"engine_id": "cpp_owner_static", "num_workers": 2},
            "timing_breakdown": {"events_per_sec": 1000000.0},
            "resource_metrics": {"peak_rss_bytes": 200 * 1024 * 1024},
            "validation": {"parity_with_serial": True}
        },
        {
            "benchmark_id": "slow_but_leanest", # Not dominated because it uses even less memory
            "semantic_class": "exact",
            "graph_configuration": {"num_nodes": 100000, "topology_type": "modular_sbm"},
            "execution_configuration": {"engine_id": "cpp_serial", "num_workers": 1},
            "timing_breakdown": {"events_per_sec": 2000000.0},
            "resource_metrics": {"peak_rss_bytes": 50 * 1024 * 1024},
            "validation": {"parity_with_serial": True}
        }
    ]

    filtered = filter_records(dummy_records, topology="modular", min_nodes=50000, semantic_class="exact")
    assert len(filtered) == 3

    pareto = compute_pareto_frontier(filtered)
    assert len(pareto) == 2
    pareto_ids = [r["benchmark_id"] for r in pareto]
    assert "fast_and_lean" in pareto_ids
    assert "slow_but_leanest" in pareto_ids
    assert "slow_and_heavy" not in pareto_ids, "Dominated point was not pruned!"
