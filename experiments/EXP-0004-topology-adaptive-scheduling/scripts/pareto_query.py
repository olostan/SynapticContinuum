#!/usr/bin/env python3
"""
SynapticContinuum Pareto Query CLI & Strict Schema Validator
EXP-0004 Cross-Experiment Benchmark Query Tool

Strictly validates canonical benchmark records against `schemas/benchmark_schema.json`,
enforces arithmetic consistency (`events_per_sec == total_events_processed / wall_time_sim_sec`),
rejects unverified or non-parity records for exact frontier queries, and computes the
non-dominated Pareto scaling frontier (Events/sec vs Peak RSS Bytes).
"""

import sys
import json
import math
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "benchmark_schema.json"

def get_benchmark_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_record_strictly(record: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> None:
    """
    Validates a canonical benchmark record against `benchmark_schema.json` and checks:
      1. Required schema fields and types.
      2. Arithmetic consistency: `events_per_sec` must equal `total_events_processed / wall_time_sim_sec`
         within 0.5% relative tolerance whenever `wall_time_sim_sec > 0`.
      3. `benchmark_id` must NOT encode worker count (`_W1`, `_W6`) so that scaling curves share
         an immutable workload identifier across workers and engines.
    Raises ValueError or jsonschema.ValidationError on any violation.
    """
    if schema is None:
        schema = get_benchmark_schema()

    jsonschema.validate(instance=record, schema=schema)

    tb = record["timing_breakdown"]
    wm = record["workload_metrics"]
    sim_sec = float(tb["wall_time_sim_sec"])
    ev_s = float(tb["events_per_sec"])
    total_ev = int(wm["total_events_processed"])

    if sim_sec > 0.0 and total_ev > 0:
        expected_ev_s = total_ev / sim_sec
        rel_err = abs(ev_s - expected_ev_s) / max(expected_ev_s, 1e-9)
        if rel_err > 0.005:
            raise ValueError(
                f"Arithmetic inconsistency in record '{record.get('run_id', record.get('benchmark_id'))}': "
                f"events_per_sec={ev_s:.2f} != total_events_processed ({total_ev}) / wall_time_sim_sec ({sim_sec:.6f}) = {expected_ev_s:.2f} "
                f"(rel_err={rel_err:.4%})"
            )

def load_json_records(path: Path, strict: bool = True) -> List[Dict[str, Any]]:
    """
    Loads canonical benchmark records from a JSON file or directory.
    Does NOT fabricate missing fields, default graph sizes, or synthetic `parity_with_serial: True`.
    """
    schema = get_benchmark_schema()
    records: List[Dict[str, Any]] = []

    def _extract_from_obj(data: Any, src_path: Path):
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    validate_record_strictly(item, schema)
                    records.append(item)
                elif strict:
                    raise ValueError(f"Non-dict element at index {idx} in {src_path}")
        elif isinstance(data, dict):
            if "benchmark_records" in data and isinstance(data["benchmark_records"], list):
                for idx, item in enumerate(data["benchmark_records"]):
                    validate_record_strictly(item, schema)
                    records.append(item)
            elif "schema_version" in data and "benchmark_id" in data:
                validate_record_strictly(data, schema)
                records.append(data)
            elif strict:
                raise ValueError(
                    f"File {src_path} does not contain canonical 'benchmark_records' or a valid schema-v1.0.0 record."
                )

    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _extract_from_obj(data, path)
    elif path.is_dir():
        for p in sorted(path.glob("**/*.json")):
            if "schema" in p.name.lower() or "config" in str(p).lower():
                continue
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and ("benchmark_records" in data or ("schema_version" in data and "benchmark_id" in data)):
                _extract_from_obj(data, p)
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "schema_version" in data[0]:
                _extract_from_obj(data, p)
            elif strict:
                raise ValueError(f"Unrecognized or non-canonical JSON file in run directory: {p}")
    else:
        raise FileNotFoundError(f"Benchmark path not found: {path}")

    return records

def filter_records(
    records: List[Dict[str, Any]],
    max_memory_gib: Optional[float] = None,
    topology: Optional[str] = None,
    min_nodes: Optional[int] = None,
    semantic_class: Optional[str] = None,
    engine: Optional[str] = None,
    build_id: Optional[str] = None,
    benchmark_id: Optional[str] = None,
    require_serial_parity: bool = False
) -> List[Dict[str, Any]]:
    schema = get_benchmark_schema()
    filtered = []
    for r in records:
        validate_record_strictly(r, schema)

        if max_memory_gib is not None:
            rss_bytes = r["resource_metrics"]["peak_rss_bytes"]
            if rss_bytes > max_memory_gib * (1024**3):
                continue

        if topology:
            topo = r["graph_configuration"]["topology_type"]
            if topology.lower() not in topo.lower():
                continue

        if min_nodes is not None:
            nodes = r["graph_configuration"]["num_nodes"]
            if nodes < min_nodes:
                continue

        if semantic_class:
            s_class = r["semantic_class"]
            if semantic_class.lower() != s_class.lower():
                continue

        if engine:
            eng = r["execution_configuration"]["engine_id"]
            if engine.lower() not in eng.lower():
                continue

        if build_id:
            b_id = r["build_id"]
            if build_id.lower() != b_id.lower():
                continue

        if benchmark_id:
            if benchmark_id != r["benchmark_id"]:
                continue

        # When filtering for exact semantic class or when require_serial_parity is True,
        # strictly require validation.parity_with_serial == True!
        if require_serial_parity or (semantic_class and semantic_class.lower() == "exact"):
            if r["validation"].get("parity_with_serial") is not True:
                continue

        filtered.append(r)
    return filtered

def compute_pareto_frontier(
    records: List[Dict[str, Any]],
    require_exact_parity: bool = True
) -> List[Dict[str, Any]]:
    """
    Computes 2D Pareto frontier: Maximize events_per_sec, Minimize peak_rss_bytes.
    If `require_exact_parity` is True (default), any record whose `validation.parity_with_serial`
    is not strictly `True` (or whose `semantic_class == 'exact'` lacks verified parity) is refused.
    """
    schema = get_benchmark_schema()
    valid = []
    for r in records:
        validate_record_strictly(r, schema)
        if require_exact_parity or r.get("semantic_class") == "exact":
            if r["validation"].get("parity_with_serial") is not True:
                continue
        ev_s = float(r["timing_breakdown"]["events_per_sec"])
        rss = int(r["resource_metrics"]["peak_rss_bytes"])
        if ev_s > 0.0 and rss > 0:
            valid.append((ev_s, rss, r))

    pareto = []
    for i, (ev_s_a, rss_a, r_a) in enumerate(valid):
        dominated = False
        for j, (ev_s_b, rss_b, _) in enumerate(valid):
            if i == j:
                continue
            if (ev_s_b >= ev_s_a and rss_b <= rss_a) and (ev_s_b > ev_s_a or rss_b < rss_a):
                dominated = True
                break
        if not dominated:
            pareto.append(r_a)

    pareto.sort(
        key=lambda x: x["timing_breakdown"]["events_per_sec"],
        reverse=True
    )
    return pareto

def main():
    parser = argparse.ArgumentParser(description="Query SynapticContinuum benchmark catalog and compute Pareto frontiers")
    parser.add_argument("--path", type=str, default="runs", help="Path to JSON run file or directory")
    parser.add_argument("--max-memory-gib", type=float, default=None, help="Filter: Maximum peak RSS in GiB")
    parser.add_argument("--topology", type=str, default=None, help="Filter: Topology type substring")
    parser.add_argument("--min-nodes", type=int, default=None, help="Filter: Minimum number of nodes")
    parser.add_argument("--semantic-class", type=str, default=None, help="Filter: exact, fixed-dt-approx, relaxed-model, trace-replay-only")
    parser.add_argument("--engine", type=str, default=None, help="Filter: Engine identifier")
    parser.add_argument("--build-id", type=str, default=None, help="Filter: portable_o3 or znver3_o3")
    parser.add_argument("--benchmark-id", type=str, default=None, help="Filter: Exact canonical benchmark_id")
    parser.add_argument("--allow-non-parity", action="store_true", help="Include relaxed/unverified records in Pareto frontier")
    parser.add_argument("--pareto", action="store_true", help="Output only Pareto-optimal configurations")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table")

    args = parser.parse_args()
    records = load_json_records(Path(args.path), strict=True)
    filtered = filter_records(
        records,
        max_memory_gib=args.max_memory_gib,
        topology=args.topology,
        min_nodes=args.min_nodes,
        semantic_class=args.semantic_class,
        engine=args.engine,
        build_id=args.build_id,
        benchmark_id=args.benchmark_id,
        require_serial_parity=(not args.allow_non_parity and args.semantic_class == "exact")
    )

    if args.pareto:
        result = compute_pareto_frontier(filtered, require_exact_parity=not args.allow_non_parity)
    else:
        result = filtered

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\n[SynapticContinuum Pareto Query] Found {len(result)} matching benchmark records (Total validated: {len(records)})")
    print("-" * 128)
    print(f"{'Benchmark ID':<28} | {'Build':<11} | {'Engine':<22} | {'Nodes':<8} | {'W':<3} | {'Events/s':<12} | {'RSS (MB)':<9} | {'Parity':<6}")
    print("-" * 128)
    for r in result:
        b_id = str(r["benchmark_id"])[:27]
        b_cfg = str(r["build_id"])[:10]
        eng = str(r["execution_configuration"]["engine_id"])[:21]
        nodes = r["graph_configuration"]["num_nodes"]
        workers = r["execution_configuration"]["num_workers"]
        ev_s = r["timing_breakdown"]["events_per_sec"]
        rss_mb = r["resource_metrics"]["peak_rss_bytes"] / (1024 * 1024)
        p_val = r["validation"].get("parity_with_serial")
        parity = "YES" if p_val is True else ("NO" if p_val is False else "NULL")
        print(f"{b_id:<28} | {b_cfg:<11} | {eng:<22} | {nodes:<8} | {workers:<3} | {ev_s:<12.1f} | {rss_mb:<9.2f} | {parity:<6}")
    print("-" * 128 + "\n")

if __name__ == "__main__":
    main()
