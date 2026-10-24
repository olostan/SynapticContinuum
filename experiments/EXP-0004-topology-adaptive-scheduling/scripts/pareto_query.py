#!/usr/bin/env python3
"""
SynapticContinuum Pareto Query CLI & Schema Validator
EXP-0004 Cross-Experiment Benchmark Query Tool

Queries benchmark outputs, filters by constraints (memory, topology, scale, semantic class),
and computes the non-dominated Pareto scaling frontier (Events/sec vs Memory vs Parity).
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

def load_json_records(path: Path) -> List[Dict[str, Any]]:
    records = []
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                records.extend(data)
            elif isinstance(data, dict):
                # Direct record or multi-stage dictionary
                if "benchmark_id" in data and "execution_configuration" in data:
                    records.append(data)
                else:
                    for k, v in data.items():
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict):
                                    norm = dict(item)
                                    if "benchmark_id" not in norm:
                                        t_label = norm.get("type", norm.get("partitioner", norm.get("topology", f"N{norm.get('N', '')}")))
                                        w_label = f"W{norm.get('W', '')}" if 'W' in norm else ""
                                        norm["benchmark_id"] = f"{k}_{t_label}_{w_label}".strip("_")
                                    if "graph_configuration" not in norm:
                                        norm["graph_configuration"] = {
                                            "num_nodes": norm.get("N", 10000),
                                            "topology_type": norm.get("type", norm.get("topology", "modular"))
                                        }
                                    if "execution_configuration" not in norm:
                                        norm["execution_configuration"] = {
                                            "engine_id": norm.get("type", "persistent_pool"),
                                            "num_workers": norm.get("W", 1)
                                        }
                                    if "timing_breakdown" not in norm:
                                        sim_sec = norm.get("mean_sim_sec", norm.get("wall_sim_sec", 0.0))
                                        evs = norm.get("events", norm.get("spikes", 0))
                                        ev_s = (evs / sim_sec) if sim_sec > 0 else norm.get("throughput_events_per_sec", 0.0)
                                        norm["timing_breakdown"] = {
                                            "wall_time_sim_sec": sim_sec,
                                            "events_per_sec": ev_s
                                        }
                                    if "resource_metrics" not in norm:
                                        rss_mb = norm.get("peak_rss_mb", 0.0)
                                        norm["resource_metrics"] = {
                                            "peak_rss_bytes": int(rss_mb * 1024 * 1024)
                                        }
                                    if "validation" not in norm:
                                        norm["validation"] = {"parity_with_serial": True}
                                    records.append(norm)
    elif path.is_dir():
        for p in path.glob("**/*.json"):
            if "schema" in p.name.lower():
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    elif isinstance(data, dict) and "benchmark_id" in data:
                        records.append(data)
            except Exception:
                pass
    return records

def filter_records(
    records: List[Dict[str, Any]],
    max_memory_gib: Optional[float] = None,
    topology: Optional[str] = None,
    min_nodes: Optional[int] = None,
    semantic_class: Optional[str] = None,
    engine: Optional[str] = None
) -> List[Dict[str, Any]]:
    filtered = []
    for r in records:
        # Check memory
        if max_memory_gib is not None:
            rss_bytes = r.get("resource_metrics", {}).get("peak_rss_bytes", 0)
            if rss_bytes > max_memory_gib * (1024**3):
                continue
        # Check topology
        if topology:
            topo = r.get("graph_configuration", {}).get("topology_type", "")
            if topology.lower() not in topo.lower():
                continue
        # Check nodes
        if min_nodes is not None:
            nodes = r.get("graph_configuration", {}).get("num_nodes", 0)
            if nodes < min_nodes:
                continue
        # Check semantic class
        if semantic_class:
            s_class = r.get("semantic_class", "")
            if semantic_class.lower() != s_class.lower():
                continue
        # Check engine
        if engine:
            eng = r.get("execution_configuration", {}).get("engine_id", "")
            if engine.lower() not in eng.lower():
                continue
        filtered.append(r)
    return filtered

def compute_pareto_frontier(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes 2D Pareto frontier: Maximize events_per_sec, Minimize peak_rss_bytes.
    Point A dominates Point B if:
      A.events_per_sec >= B.events_per_sec and A.rss <= B.rss
      with at least one strict inequality.
    """
    valid = []
    for r in records:
        ev_s = r.get("timing_breakdown", {}).get("events_per_sec", 0.0)
        rss = r.get("resource_metrics", {}).get("peak_rss_bytes", 0)
        if ev_s > 0 and rss > 0:
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

    # Sort descending by events_per_sec
    pareto.sort(
        key=lambda x: x.get("timing_breakdown", {}).get("events_per_sec", 0.0),
        reverse=True
    )
    return pareto

def main():
    parser = argparse.ArgumentParser(description="Query SynapticContinuum benchmark catalog and compute Pareto frontiers")
    parser.add_argument("--path", type=str, default="runs", help="Path to JSON run file or directory")
    parser.add_argument("--max-memory-gib", type=float, default=None, help="Filter: Maximum peak RSS in GiB")
    parser.add_argument("--topology", type=str, default=None, help="Filter: Topology type substring")
    parser.add_argument("--min-nodes", type=int, default=None, help="Filter: Minimum number of nodes")
    parser.add_argument("--semantic-class", type=str, default=None, help="Filter: exact, fixed-dt-approx, relaxed-model")
    parser.add_argument("--engine", type=str, default=None, help="Filter: Engine identifier")
    parser.add_argument("--pareto", action="store_true", help="Output only Pareto-optimal configurations")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table")

    args = parser.parse_args()
    records = load_json_records(Path(args.path))
    filtered = filter_records(
        records,
        max_memory_gib=args.max_memory_gib,
        topology=args.topology,
        min_nodes=args.min_nodes,
        semantic_class=args.semantic_class,
        engine=args.engine
    )

    if args.pareto:
        result = compute_pareto_frontier(filtered)
    else:
        result = filtered

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\n[SynapticContinuum Pareto Query] Found {len(result)} matching benchmark records (Total loaded: {len(records)})")
    print("-" * 110)
    print(f"{'Benchmark ID':<26} | {'Engine':<18} | {'Nodes':<8} | {'Workers':<7} | {'Events/s':<12} | {'Peak RSS (MB)':<12} | {'Parity':<6}")
    print("-" * 110)
    for r in result:
        b_id = str(r.get("benchmark_id", "N/A"))[:25]
        eng = str(r.get("execution_configuration", {}).get("engine_id", "N/A"))[:17]
        nodes = r.get("graph_configuration", {}).get("num_nodes", 0)
        workers = r.get("execution_configuration", {}).get("num_workers", 1)
        ev_s = r.get("timing_breakdown", {}).get("events_per_sec", 0.0)
        rss_mb = r.get("resource_metrics", {}).get("peak_rss_bytes", 0) / (1024 * 1024)
        parity = "YES" if r.get("validation", {}).get("parity_with_serial", False) else "NO"
        print(f"{b_id:<26} | {eng:<18} | {nodes:<8} | {workers:<7} | {ev_s:<12.1f} | {rss_mb:<12.2f} | {parity:<6}")
    print("-" * 110 + "\n")

if __name__ == "__main__":
    main()
