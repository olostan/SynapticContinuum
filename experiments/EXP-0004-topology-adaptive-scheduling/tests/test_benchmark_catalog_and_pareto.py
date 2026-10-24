import json
from pathlib import Path
import pytest
import jsonschema
from scripts.pareto_query import (
    get_benchmark_schema,
    validate_record_strictly,
    load_json_records,
    filter_records,
    compute_pareto_frontier,
)

def make_valid_record(
    benchmark_id: str = "exp0004_stage3_modular_sbm_N100000_D16_f0.0100_seed42",
    run_id: str = "run_001",
    build_id: str = "znver3_o3",
    semantic_class: str = "exact",
    engine_id: str = "cpp_persistent_pool",
    num_workers: int = 6,
    num_nodes: int = 100000,
    total_events: int = 50000,
    wall_sim_sec: float = 0.010,
    peak_rss_bytes: int = 100 * 1024 * 1024,
    parity_with_serial: bool = True,
):
    return {
        "schema_version": "1.0.0",
        "benchmark_id": benchmark_id,
        "run_id": run_id,
        "build_id": build_id,
        "semantic_class": semantic_class,
        "hardware_environment": {
            "os": "Linux 6.6.87.2-microsoft-standard-WSL2",
            "cpu_model": "AMD Ryzen 5 5600X 6-Core Processor",
            "physical_cores": 6,
            "logical_threads": 12,
            "total_ram_bytes": 16777216000,
            "compiler": "GCC 13.3.0",
            "compiler_flags": "-O3 -march=znver3 -mtune=znver3 -DNDEBUG",
        },
        "graph_configuration": {
            "num_nodes": num_nodes,
            "num_edges": num_nodes * 16,
            "topology_type": "modular_sbm",
            "graph_checksum": "0xabcdef0123456789",
            "input_events_checksum": "0x9876543210fedcba",
        },
        "execution_configuration": {
            "engine_id": engine_id,
            "algorithm_family": "conservative_pdes",
            "num_workers": num_workers,
            "num_regions": 12,
        },
        "workload_metrics": {
            "total_events_processed": total_events,
            "total_spikes": 12000,
            "total_edges_traversed": 192000,
        },
        "timing_breakdown": {
            "wall_time_sim_sec": wall_sim_sec,
            "wall_time_total_sec": wall_sim_sec + 0.001,
            "events_per_sec": total_events / wall_sim_sec,
        },
        "resource_metrics": {
            "peak_rss_bytes": peak_rss_bytes,
            "hardware_perf_counters_available": False,
        },
        "validation": {
            "state_digest": "0x123456789abcdef0",
            "reference_serial_digest": "0x123456789abcdef0",
            "parity_with_serial": parity_with_serial,
        },
    }

def test_benchmark_schema_structure():
    """Verify that benchmark_schema.json exists and requires all canonical properties."""
    schema = get_benchmark_schema()
    assert schema.get("version") == "1.0.0"
    for req in [
        "schema_version",
        "benchmark_id",
        "run_id",
        "build_id",
        "semantic_class",
        "hardware_environment",
        "graph_configuration",
        "execution_configuration",
        "workload_metrics",
        "timing_breakdown",
        "resource_metrics",
        "validation",
    ]:
        assert req in schema["required"]

def test_strict_schema_rejects_incomplete_or_arithmetic_mismatch():
    """Verify that missing fields or arithmetically inconsistent throughput raise errors."""
    bad_missing = {"benchmark_id": "incomplete_legacy_record", "W": 6}
    with pytest.raises(jsonschema.ValidationError):
        validate_record_strictly(bad_missing)

    bad_math = make_valid_record(total_events=2550, wall_sim_sec=0.00058)
    # Intentionally corrupt events_per_sec to 10.9M instead of 2550 / 0.00058 = 4.396M
    bad_math["timing_breakdown"]["events_per_sec"] = 10900000.0
    with pytest.raises(ValueError, match="Arithmetic inconsistency"):
        validate_record_strictly(bad_math)

def test_pareto_query_refuses_unverified_records_on_exact_frontier():
    """Verify that records with parity_with_serial=False or None are excluded from exact Pareto frontiers."""
    r_valid_fast = make_valid_record(
        run_id="r_valid_fast",
        num_workers=6,
        total_events=50000,
        wall_sim_sec=0.010, # 5.0M ev/s
        peak_rss_bytes=100 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_valid_dominated = make_valid_record(
        run_id="r_valid_dominated",
        num_workers=2,
        total_events=50000,
        wall_sim_sec=0.050, # 1.0M ev/s
        peak_rss_bytes=200 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_valid_lean = make_valid_record(
        run_id="r_valid_lean",
        engine_id="cpp_serial",
        num_workers=1,
        total_events=50000,
        wall_sim_sec=0.025, # 2.0M ev/s
        peak_rss_bytes=50 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_unverified_cheater = make_valid_record(
        run_id="r_unverified_cheater",
        semantic_class="exact",
        num_workers=6,
        total_events=50000,
        wall_sim_sec=0.001, # 50.0M ev/s, 10 MB RSS, but parity_with_serial is False!
        peak_rss_bytes=10 * 1024 * 1024,
        parity_with_serial=False,
    )

    records = [r_valid_fast, r_valid_dominated, r_valid_lean, r_unverified_cheater]
    # Note: all 4 share the exact same canonical benchmark_id across W=1, 2, 6!
    assert len({r["benchmark_id"] for r in records}) == 1

    filtered_exact = filter_records(records, semantic_class="exact")
    assert len(filtered_exact) == 3
    assert all(r["validation"]["parity_with_serial"] is True for r in filtered_exact)

    pareto = compute_pareto_frontier(records, require_exact_parity=True)
    run_ids = [r["run_id"] for r in pareto]
    assert "r_valid_fast" in run_ids
    assert "r_valid_lean" in run_ids
    assert "r_valid_dominated" not in run_ids
    assert "r_unverified_cheater" not in run_ids

def test_proof_chain_and_no_cross_workload_pareto_dominance():
    """Verify:
    1. Data-layout or quantized/procedural records cannot claim parity_with_serial=True if state_digest != reference_serial_digest or semantic_class != exact.
    2. Pareto frontier never allows a small 10k-node workload to dominate and prune a large 10M-node workload.
    """
    # 1. False parity=True with mismatched digest is rejected
    bad_digest_claim = make_valid_record(run_id="bad_digest_claim", parity_with_serial=True)
    bad_digest_claim["validation"]["state_digest"] = "0xdeadbeef00000001"
    bad_digest_claim["validation"]["reference_serial_digest"] = "0x123456789abcdef0"
    with pytest.raises(ValueError, match="Proof-chain violation"):
        validate_record_strictly(bad_digest_claim)

    # 2. Quantized/procedural semantic class claiming parity_with_serial=True is rejected
    bad_quant_claim = make_valid_record(
        run_id="bad_quant_claim",
        semantic_class="quantized-approx",
        parity_with_serial=True,
    )
    with pytest.raises(ValueError, match="cannot claim parity_with_serial=True"):
        validate_record_strictly(bad_quant_claim)

    # 3. Cross-workload isolation: 10k-node fast/tiny run must NOT dominate 10M-node run
    r_10k = make_valid_record(
        benchmark_id="exp0004_stage0_disconnected_N10000_D16_seed11",
        run_id="r_10k_w6",
        num_nodes=10000,
        total_events=32249,
        wall_sim_sec=0.001, # 32.2M ev/s
        peak_rss_bytes=46 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_10k["graph_configuration"]["graph_checksum"] = "0x1111111111111111"

    r_10m_w6 = make_valid_record(
        benchmark_id="exp0004_stage3d_scale_N10000000_D16",
        run_id="r_10m_w6",
        num_nodes=10000000,
        total_events=1572432,
        wall_sim_sec=0.117, # 13.4M ev/s
        peak_rss_bytes=6491 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_10m_w6["graph_configuration"]["graph_checksum"] = "0x9999999999999999"

    r_10m_w1_dominated = make_valid_record(
        benchmark_id="exp0004_stage3d_scale_N10000000_D16",
        run_id="r_10m_w1",
        num_nodes=10000000,
        total_events=1572432,
        wall_sim_sec=0.727, # 2.16M ev/s
        peak_rss_bytes=6491 * 1024 * 1024,
        parity_with_serial=True,
    )
    r_10m_w1_dominated["graph_configuration"]["graph_checksum"] = "0x9999999999999999"

    frontier = compute_pareto_frontier([r_10k, r_10m_w6, r_10m_w1_dominated], require_exact_parity=True)
    frontier_ids = [r["run_id"] for r in frontier]
    assert "r_10k_w6" in frontier_ids
    assert "r_10m_w6" in frontier_ids
    assert "r_10m_w1" not in frontier_ids

