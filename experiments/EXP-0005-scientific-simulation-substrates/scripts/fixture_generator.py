#!/usr/bin/env python3
"""
EXP-0005 WP-00: Deterministic Workload & Fixture Transport Generator.

Generates backend-neutral, deterministic CSV and JSON fixtures for:
  - Golden A: sc05/analytic-leak/v1
  - Golden B: sc05/analytic-threshold/v1
  - Golden C1: sc05/replay/v1 (causal chain A->B->C with d=2 ms)
  - Golden C2: sc05/replay/v1 (simultaneous arrivals & refractory clamp)
  - Pilot Disconnected (sc05/disconnected/v1, N=128, D=4, stratified_modules)
  - Pilot Disconnected Localized Control (sc05/disconnected/v1, N=128, D=4, localized_first_module)
  - Pilot Modular SBM (sc05/modular/v1, N=128, D=4, stratified_modules)
  - Historical EXP-0004 Config Provenance Map (read-only SHA-256 & unit translation)

All generated CSVs use LF line endings, explicit physical units (ms, mV),
strictly positive axonal delays (delay_ms > 0), and deterministic sorting:
  - Edges sorted by: (src_id, dst_id, delay_ms, weight_mV)
  - External events sorted by: (t_ms, target_id, src_id, ordinal)

Custom on-demand exports (`--mode custom`) default outside Git
(`$SC_ARTIFACT_ROOT/EXP-0005/fixtures/` or `/tmp/sc-artifacts/EXP-0005/fixtures/`),
refuse to write into the committed `EXP-0005/fixtures` directory, isolate each
workload inside `<output_dir>/<workload_instance_id>/`, and forbid destructive
collisions unless `--allow-overwrite` is explicitly passed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


EXP0005_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP0005_ROOT.parent.parent
EXP0004_ROOT = REPO_ROOT / "experiments" / "EXP-0004-topology-adaptive-scheduling"
COMMITTED_FIXTURES_DIR = (EXP0005_ROOT / "fixtures").resolve()

TOPOLOGY_TO_WORKLOAD_ID: Dict[str, str] = {
    "disconnected": "sc05/disconnected/v1",
    "modular_sbm": "sc05/modular/v1",
    "modular": "sc05/modular/v1",
    "random": "sc05/random/v1",
    "smallworld": "sc05/smallworld/v1",
    "hierarchical": "sc05/hierarchical/v1",
}


class SplitMix64:
    """
    Self-contained, deterministic 64-bit SplitMix64 pseudo-random generator.
    Identical mathematical constants across Python/C++ for cross-platform reproducibility,
    with zero dependency on EXP-0004 binaries.
    """

    def __init__(self, seed: int = 42) -> None:
        self.state: int = (seed & 0xFFFFFFFFFFFFFFFF) if seed != 0 else 0x123456789ABCDEF0

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF

    def uniform_uint(self, n: int) -> int:
        if n <= 1:
            return 0
        x = self.next_u64() & 0xFFFFFFFF
        return ((x * n) >> 32) & 0xFFFFFFFF

    def uniform_float(self, min_val: float, max_val: float) -> float:
        r = self.next_u64()
        u = float(r >> 11) * (1.0 / 9007199254740992.0)
        return min_val + u * (max_val - min_val)


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize dictionary/list into canonical UTF-8 JSON bytes with LF newline."""
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_float_canonical(val: float) -> str:
    """Deterministic decimal string formatting to 8 decimal places."""
    return f"{float(val):.8f}"


def serialize_edges_csv(edges: List[Tuple[int, int, float, float]]) -> bytes:
    """
    Sort and serialize directed edges (src_id, dst_id, delay_ms, weight_mV) to UTF-8 CSV bytes.
    Enforces:
      - No self-loops unless explicitly permitted (none in canonical fixtures)
      - Strictly positive delay_ms > 0
      - Deterministic sort order: (src_id, dst_id, round(delay_ms, 8), round(weight_mV, 8))
    """
    sorted_edges = sorted(
        edges,
        key=lambda e: (int(e[0]), int(e[1]), round(float(e[2]), 8), round(float(e[3]), 8)),
    )
    buf = io.StringIO(newline="\n")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["src_id", "dst_id", "delay_ms", "weight_mV"])
    for src_id, dst_id, delay_ms, weight_mv in sorted_edges:
        if delay_ms <= 0.0:
            raise ValueError(f"Invalid non-positive synaptic delay_ms={delay_ms} on edge {src_id}->{dst_id}")
        writer.writerow([int(src_id), int(dst_id), format_float_canonical(delay_ms), format_float_canonical(weight_mv)])
    return buf.getvalue().encode("utf-8")


def serialize_events_csv(events: List[Tuple[float, int, int, int, float]]) -> bytes:
    """
    Sort and serialize external stimulus events (t_ms, target_id, src_id, ordinal, weight_mV).
    Enforces:
      - t_ms >= 0.0
      - Deterministic tie-break key: (t_ms, target_id, src_id, ordinal)
    """
    sorted_events = sorted(
        events,
        key=lambda ev: (round(float(ev[0]), 8), int(ev[1]), int(ev[2]), int(ev[3])),
    )
    buf = io.StringIO(newline="\n")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["t_ms", "target_id", "src_id", "ordinal", "weight_mV"])
    for t_ms, target_id, src_id, ordinal, weight_mv in sorted_events:
        if t_ms < 0.0:
            raise ValueError(f"Invalid negative event timestamp t_ms={t_ms}")
        writer.writerow([
            format_float_canonical(t_ms),
            int(target_id),
            int(src_id),
            int(ordinal),
            format_float_canonical(weight_mv),
        ])
    return buf.getvalue().encode("utf-8")


def validate_topology_parameters(
    topology: str,
    num_nodes: int,
    out_degree: int,
    num_modules: int,
    cross_module_ratio: float = 0.05,
) -> None:
    """
    Validate graph generation parameters upfront and fail fast on impossible degree/module
    combinations instead of entering infinite rejection-sampling loops.
    """
    if num_nodes < 2:
        raise ValueError(f"num_nodes must be >= 2 for directed edge generation, got {num_nodes}")
    if out_degree < 0:
        raise ValueError(f"out_degree must be >= 0, got {out_degree}")
    if out_degree >= num_nodes:
        raise ValueError(
            f"out_degree ({out_degree}) must be strictly less than num_nodes ({num_nodes}) without self-edges/duplicates."
        )
    if num_modules < 1 or num_modules > num_nodes:
        raise ValueError(f"num_modules ({num_modules}) must satisfy 1 <= num_modules <= num_nodes ({num_nodes}).")
    if not (0.0 <= cross_module_ratio <= 1.0):
        raise ValueError(f"cross_module_ratio ({cross_module_ratio}) must be in [0.0, 1.0].")

    if topology in ("disconnected", "modular_sbm", "modular"):
        nodes_per_mod = num_nodes // num_modules
        min_mod_size = nodes_per_mod
        if topology == "disconnected" and out_degree >= min_mod_size:
            raise ValueError(
                f"Impossible disconnected graph parameters: out_degree={out_degree} >= module_size={min_mod_size} "
                f"(num_nodes={num_nodes}, num_modules={num_modules}) without self-edges or duplicate edges."
            )
        if topology in ("modular_sbm", "modular") and cross_module_ratio == 0.0 and out_degree >= min_mod_size:
            raise ValueError(
                f"Impossible modular_sbm parameters with cross_module_ratio=0.0: out_degree={out_degree} "
                f">= module_size={min_mod_size}."
            )


def generate_Topology_edges(
    topology: str,
    num_nodes: int,
    out_degree: int,
    seed: int,
    num_modules: int = 4,
    cross_module_ratio: float = 0.05,
    min_delay_ms: float = 1.0,
    max_delay_ms: float = 5.0,
    weight_scale_mv: float = 0.45,
) -> List[Tuple[int, int, float, float]]:
    """
    Generate a deterministic directed graph with unique (src_id, dst_id) pairs per node
    and no self-edges. Fails fast if parameters are invalid or if rejection sampling
    exceeds a bounded attempt limit.
    """
    if out_degree == 0:
        return []
    validate_topology_parameters(
        topology=topology,
        num_nodes=num_nodes,
        out_degree=out_degree,
        num_modules=num_modules,
        cross_module_ratio=cross_module_ratio,
    )
    k = out_degree
    rng = SplitMix64(seed)
    edges: List[Tuple[int, int, float, float]] = []

    nodes_per_mod = num_nodes // num_modules
    max_attempts_per_node = max(1000, k * 250)

    for u in range(num_nodes):
        mod_u = min(num_modules - 1, u // nodes_per_mod)
        mod_start = mod_u * nodes_per_mod
        mod_end = num_nodes if mod_u == num_modules - 1 else (mod_u + 1) * nodes_per_mod
        mod_size = mod_end - mod_start
        targets_set = set()
        attempts = 0

        while len(targets_set) < k:
            attempts += 1
            if attempts > max_attempts_per_node:
                raise RuntimeError(
                    f"Exceeded max target sampling attempts ({max_attempts_per_node}) on node {u} "
                    f"for topology={topology}, N={num_nodes}, D={out_degree}, M={num_modules}."
                )
            if topology == "disconnected":
                cand = mod_start + rng.uniform_uint(mod_size)
            elif topology in ("modular_sbm", "modular"):
                # If all (mod_size - 1) intra-module neighbors are already exhausted, allow cross-module fallback
                # when cross_module_ratio > 0; otherwise sample according to cross_module_ratio.
                intra_exhausted = len([t for t in targets_set if mod_start <= t < mod_end]) >= (mod_size - 1)
                if (intra_exhausted and cross_module_ratio > 0.0) or (
                    rng.uniform_float(0.0, 1.0) < cross_module_ratio
                ):
                    cand = rng.uniform_uint(num_nodes)
                else:
                    cand = mod_start + rng.uniform_uint(mod_size)
            elif topology == "random":
                cand = rng.uniform_uint(num_nodes)
            else:
                raise ValueError(f"Unsupported topology '{topology}'")

            if cand != u and 0 <= cand < num_nodes:
                targets_set.add(cand)

        is_inhibitory = rng.uniform_float(0.0, 1.0) < 0.20
        for v in sorted(targets_set):
            w_mag = rng.uniform_float(0.5, 1.5) * weight_scale_mv
            w_mv = -w_mag if is_inhibitory else w_mag
            d_ms = rng.uniform_float(min_delay_ms, max_delay_ms)
            edges.append((u, v, round(d_ms, 6), round(w_mv, 6)))

    return edges


def compute_stimulus_target_budget(
    num_nodes: int,
    num_modules: int,
    active_fraction: float,
    stimulus_distribution: str,
) -> Dict[str, Any]:
    """
    Compute and validate the realized target-neuron pool budget for external stimulus:
      - `active_fraction` (in `(0.0, 1.0]`) is defined as the **within-module active fraction**
        for each stimulated module.
      - Under `stratified_modules`, all `num_modules` modules are stimulated; each module `m`
        exposes `active_per_module = max(1, min(mod_size, round(mod_size * active_fraction)))`
        candidate target neurons `[mod_start, mod_start + active_per_module)`.
      - Under `localized_first_module`, **only Module 0** (`[0, mod0_size)`) is ever stimulated,
        and `active_fraction` applies to Module 0's size (`mod0_size`):
        `active_in_mod0 = max(1, min(mod0_size, round(mod0_size * active_fraction)))`
        candidate target neurons `[0, active_in_mod0) subset [0, mod0_size)`.
        Even at `active_fraction = 0.50` or `1.00`, target IDs in `localized_first_module`
        are strictly constrained to Module 0 (`[0, mod0_size)`).
    """
    if num_nodes < 1:
        raise ValueError(f"num_nodes must be >= 1, got {num_nodes}")
    if num_modules < 1 or num_modules > num_nodes:
        raise ValueError(f"num_modules ({num_modules}) must be in [1, {num_nodes}]")
    if not (0.0 < active_fraction <= 1.0):
        raise ValueError(f"active_fraction must be in (0.0, 1.0], got {active_fraction}")

    nodes_per_mod = max(1, num_nodes // num_modules)
    if stimulus_distribution == "stratified_modules":
        per_mod_pools: List[int] = []
        for m in range(num_modules):
            mod_start = m * nodes_per_mod
            mod_end = num_nodes if m == num_modules - 1 else (m + 1) * nodes_per_mod
            mod_size = max(1, mod_end - mod_start)
            active_in_mod = max(1, min(mod_size, int(round(mod_size * active_fraction))))
            per_mod_pools.append(active_in_mod)
        return {
            "active_fraction_scope": "per_stimulated_module",
            "stimulated_modules": list(range(num_modules)),
            "target_pool_per_module": per_mod_pools,
            "total_target_pool_neurons": sum(per_mod_pools),
        }
    elif stimulus_distribution == "localized_first_module":
        mod0_size = num_nodes if num_modules == 1 else nodes_per_mod
        active_in_mod0 = max(1, min(mod0_size, int(round(mod0_size * active_fraction))))
        per_mod_pools = [active_in_mod0] + [0 for _ in range(num_modules - 1)]
        return {
            "active_fraction_scope": "within_module_0_only",
            "stimulated_modules": [0],
            "target_pool_per_module": per_mod_pools,
            "total_target_pool_neurons": active_in_mod0,
        }
    else:
        raise ValueError(f"Unsupported stimulus_distribution='{stimulus_distribution}'")


def generate_external_events(
    num_nodes: int,
    num_events: int,
    horizon_ms: float,
    seed: int,
    active_fraction: float = 0.25,
    num_modules: int = 4,
    stimulus_distribution: str = "stratified_modules",
    min_weight_mv: float = 0.55,
    max_weight_mv: float = 1.15,
) -> List[Tuple[float, int, int, int, float]]:
    """
    Generate deterministic external stimulus pulses (t_ms, target_id, src_id=-1, ordinal, weight_mV).

    Supported `stimulus_distribution` modes:
      - `"stratified_modules"`: distributes external events evenly across all `num_modules`
        contiguous modules (`i % num_modules`), sampling targets within `[mod_start, mod_start + active_in_mod)`
        where `active_in_mod = max(1, min(mod_size, round(mod_size * active_fraction)))`.
      - `"localized_first_module"`: strictly constrains all external events to Module 0
        (`[0, mod0_size)`), sampling targets within `[0, active_in_mod0)` where
        `active_in_mod0 = max(1, min(mod0_size, round(mod0_size * active_fraction)))`.
        Even for `active_fraction = 0.50` or `1.00`, no target ever spills into Module 1..M-1.
    """
    if num_events < 0:
        raise ValueError(f"num_events must be >= 0, got {num_events}")
    if horizon_ms <= 0.0:
        raise ValueError(f"horizon_ms must be > 0, got {horizon_ms}")
    budget = compute_stimulus_target_budget(
        num_nodes=num_nodes,
        num_modules=num_modules,
        active_fraction=active_fraction,
        stimulus_distribution=stimulus_distribution,
    )

    rng = SplitMix64(seed ^ 0xA5A5A5A55A5A5A5A)
    nodes_per_mod = max(1, num_nodes // num_modules)
    raw_events: List[Tuple[float, int, float]] = []

    for i in range(num_events):
        t_ms = round(rng.uniform_float(0.5, horizon_ms), 6)
        if stimulus_distribution == "stratified_modules":
            mod_idx = i % num_modules
            mod_start = mod_idx * nodes_per_mod
            active_in_mod = budget["target_pool_per_module"][mod_idx]
            target_id = mod_start + rng.uniform_uint(active_in_mod)
        elif stimulus_distribution == "localized_first_module":
            active_in_mod0 = budget["target_pool_per_module"][0]
            target_id = rng.uniform_uint(active_in_mod0)
        else:
            raise ValueError(f"Unsupported stimulus_distribution='{stimulus_distribution}'")

        w_mv = round(rng.uniform_float(min_weight_mv, max_weight_mv), 6)
        raw_events.append((t_ms, target_id, w_mv))

    raw_events.sort(key=lambda x: (x[0], x[1]))
    events: List[Tuple[float, int, int, int, float]] = []
    for ordinal, (t_ms, target_id, w_mv) in enumerate(raw_events):
        events.append((t_ms, target_id, -1, ordinal, w_mv))
    return events


def compute_workload_instance_id(
    workload_id: str,
    seed: int,
    config_obj: Dict[str, Any],
    file_hashes: Dict[str, str],
) -> str:
    """
    Compute canonical SHA-256 workload_instance_id from UTF-8 serialized recipe,
    config parameters, seed, and underlying fixture file SHA-256 digests.
    """
    payload = {
        "canonicalization": "utf8-json-sorted-keys-v1",
        "workload_id": workload_id,
        "seed": seed,
        "config": config_obj,
        "fixture_file_sha256": file_hashes,
    }
    return sha256_bytes(canonical_json_bytes(payload))


def _default_manifest_policies() -> Dict[str, Any]:
    return {
        "edge_direction": "directed_src_to_dst",
        "self_edges": "forbidden",
        "duplicate_edges": "forbidden_per_src_dst_pair",
        "delay_constraint": "strictly_positive_delay_ms_gt_0",
        "event_tie_break_order": ["t_ms", "target_id", "src_id", "ordinal"],
        "refractory_interval": "half_open_[t_spike, t_spike + refractory_ms)",
        "active_fraction_definition": (
            "fraction of neurons within each stimulated module eligible to receive external events; "
            "localized_first_module is strictly bounded to Module 0 [0, N//num_modules) for all active_fraction in (0, 1]"
        ),
    }


def build_default_wp00_fixtures(output_dir: Path) -> Dict[str, Any]:
    """
    Build all committed WP-00 Golden and Pilot fixtures in `output_dir` and return
    the complete manifest dictionary (`sc05-fixture-manifest-v1`).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    files_manifest: Dict[str, Dict[str, Any]] = {}
    workloads_manifest: Dict[str, Dict[str, Any]] = {}

    def _write_and_record(rel_name: str, data: bytes, description: str) -> str:
        fpath = output_dir / rel_name
        fpath.write_bytes(data)
        digest = sha256_bytes(data)
        files_manifest[rel_name] = {
            "path": f"fixtures/{rel_name}",
            "byte_count": len(data),
            "sha256": digest,
            "description": description,
        }
        return digest

    # 1. Golden A: Passive analytic leak (sc05/analytic-leak/v1)
    golden_a_cfg = {
        "workload_id": "sc05/analytic-leak/v1",
        "description": "Single-neuron passive exponential membrane decay without stimulus",
        "units": {"time": "ms", "voltage": "mV"},
        "neuron_parameters": {
            "num_nodes": 1,
            "tau_ms": 10.0,
            "e_l_mv": 0.0,
            "v_reset_mv": 0.0,
            "v_th_mv": 1.0,
            "refractory_ms": 2.0,
            "v_init_mv": [0.8],
        },
        "sample_times_ms": [0.0, 10.0, 20.0],
        "expected_hand_oracle": {
            "potentials_mv_at_samples": [
                0.8,
                0.8 * math.exp(-1.0),
                0.8 * math.exp(-2.0),
            ],
            "tolerance_mv": 1e-12,
            "expected_spikes": [],
        },
    }
    ga_sha = _write_and_record(
        "golden_a_passive_leak.json",
        canonical_json_bytes(golden_a_cfg),
        "Golden A passive analytic leak fixture (V(0)=0.8 mV, tau=10 ms, samples at 0, 10, 20 ms)",
    )
    workloads_manifest["golden_a_passive_leak"] = {
        "workload_id": "sc05/analytic-leak/v1",
        "seed": 0,
        "config": golden_a_cfg["neuron_parameters"],
        "workload_instance_id": compute_workload_instance_id(
            "sc05/analytic-leak/v1", 0, golden_a_cfg["neuron_parameters"], {"golden_a_passive_leak.json": ga_sha}
        ),
        "files": ["golden_a_passive_leak.json"],
    }

    # 2. Golden B: Threshold, reset, and refractory clamp (sc05/analytic-threshold/v1)
    v3_minus = 0.4 * math.exp(-2.0 / 10.0)
    v3_plus = v3_minus + 0.4
    v4_minus = v3_plus * math.exp(-1.0 / 10.0)
    v4_pre_reset = v4_minus + 0.4

    golden_b_cfg = {
        "workload_id": "sc05/analytic-threshold/v1",
        "description": "Single-neuron analytic delta-LIF with 3 external arrivals at 1, 3, 4 ms (w=0.4 mV)",
        "units": {"time": "ms", "voltage": "mV"},
        "neuron_parameters": {
            "num_nodes": 1,
            "tau_ms": 10.0,
            "e_l_mv": 0.0,
            "v_reset_mv": 0.0,
            "v_th_mv": 1.0,
            "refractory_ms": 2.0,
            "v_init_mv": [0.0],
            "threshold_tolerance_mv": 1e-10,
            "refractory_boundary_policy": "half_open_strict_less_than",
        },
        "external_events": [
            {"t_ms": 1.0, "target_id": 0, "src_id": -1, "ordinal": 0, "weight_mV": 0.4},
            {"t_ms": 3.0, "target_id": 0, "src_id": -1, "ordinal": 1, "weight_mV": 0.4},
            {"t_ms": 4.0, "target_id": 0, "src_id": -1, "ordinal": 2, "weight_mV": 0.4},
        ],
        "expected_hand_oracle": {
            "v_at_1_plus_mv": 0.4,
            "v_at_3_minus_mv": v3_minus,
            "v_at_3_plus_mv": v3_plus,
            "v_at_4_minus_mv": v4_minus,
            "v_at_4_pre_reset_mv": v4_pre_reset,
            "v_at_4_post_reset_mv": 0.0,
            "refractory_until_ms": 6.0,
            "expected_spikes": [{"t_ms": 4.0, "node_id": 0}],
            "tolerance_mv": 1e-10,
        },
    }
    gb_sha = _write_and_record(
        "golden_b_threshold_reset.json",
        canonical_json_bytes(golden_b_cfg),
        "Golden B analytic threshold/reset fixture (arrivals at 1, 3, 4 ms; spike at 4 ms)",
    )
    workloads_manifest["golden_b_threshold_reset"] = {
        "workload_id": "sc05/analytic-threshold/v1",
        "seed": 0,
        "config": golden_b_cfg["neuron_parameters"],
        "workload_instance_id": compute_workload_instance_id(
            "sc05/analytic-threshold/v1", 0, golden_b_cfg["neuron_parameters"], {"golden_b_threshold_reset.json": gb_sha}
        ),
        "files": ["golden_b_threshold_reset.json"],
    }

    # 3. Golden C1 & C2: Directed causal chain A->B->C (delay 2 ms) & simultaneous arrival tie-breaks
    gc_edges = [
        (0, 1, 2.0, 1.2),
        (1, 2, 2.0, 1.2),
    ]
    gc_events = [
        (1.0, 0, -1, 0, 1.2),
    ]
    gc_tie_events = [
        (2.0, 0, 1, 0, 0.6),
        (2.0, 0, 2, 1, 0.5),
        (2.0, 0, 3, 2, 1.5),
        (3.5, 0, -1, 3, 0.9),  # Inside refractory [2.0, 4.0) -> clamped
        (4.0, 0, -1, 4, 0.5),  # Exactly on boundary t == refractory_until (4.0) -> active under half-open [t_s, t_s+tau_ref)
    ]
    gc_edges_sha = _write_and_record(
        "golden_c_causal_chain_edges.csv",
        serialize_edges_csv(gc_edges),
        "Golden C directed causal chain edges 0->1->2 with delay_ms=2.0, weight_mV=1.2",
    )
    gc_events_sha = _write_and_record(
        "golden_c_causal_chain_events.csv",
        serialize_events_csv(gc_events),
        "Golden C external stimulus at t=1.0 ms to node 0 (earliest deliveries at 3.0 ms and 5.0 ms)",
    )
    gc_tie_sha = _write_and_record(
        "golden_c_tie_adversarial_events.csv",
        serialize_events_csv(gc_tie_events),
        "Golden C2 simultaneous arrival tie-break and refractory clamp boundary test events",
    )
    gc1_cfg = {"num_nodes": 3, "tau_ms": 10.0, "v_th_mv": 1.0, "refractory_ms": 2.0}
    workloads_manifest["golden_c_causal_chain"] = {
        "workload_id": "sc05/replay/v1",
        "seed": 0,
        "config": gc1_cfg,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/replay/v1",
            0,
            gc1_cfg,
            {
                "golden_c_causal_chain_edges.csv": gc_edges_sha,
                "golden_c_causal_chain_events.csv": gc_events_sha,
            },
        ),
        "files": ["golden_c_causal_chain_edges.csv", "golden_c_causal_chain_events.csv"],
    }
    gc2_cfg = {
        "num_nodes": 1,
        "tau_ms": 10.0,
        "v_th_mv": 1.0,
        "refractory_ms": 2.0,
        "tie_policy": "(t_ms,target_id,src_id,ordinal)",
    }
    workloads_manifest["golden_c_tie_adversarial"] = {
        "workload_id": "sc05/replay/v1",
        "seed": 0,
        "config": gc2_cfg,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/replay/v1",
            0,
            gc2_cfg,
            {"golden_c_tie_adversarial_events.csv": gc_tie_sha},
        ),
        "files": ["golden_c_tie_adversarial_events.csv"],
    }

    # 4. Pilot Disconnected Fixture — Stratified Across All 4 Modules (sc05/disconnected/v1, N=128, D=4, seed=11)
    disc_edges = generate_Topology_edges(
        topology="disconnected",
        num_nodes=128,
        out_degree=4,
        seed=11,
        num_modules=4,
        cross_module_ratio=0.0,
    )
    disc_events = generate_external_events(
        num_nodes=128,
        num_events=64,
        horizon_ms=100.0,
        seed=11,
        active_fraction=0.25,
        num_modules=4,
        stimulus_distribution="stratified_modules",
    )
    disc_edges_sha = _write_and_record(
        "pilot_disconnected_n128_d4_s11_edges.csv",
        serialize_edges_csv(disc_edges),
        "Pilot disconnected 4-module graph fixture (N=128, D=4, 512 directed edges, seed=11)",
    )
    disc_events_sha = _write_and_record(
        "pilot_disconnected_n128_d4_s11_events.csv",
        serialize_events_csv(disc_events),
        "Pilot disconnected stratified external stimulus (64 events, 16 per module across 4 modules, seed=11)",
    )
    disc_budget = compute_stimulus_target_budget(128, 4, 0.25, "stratified_modules")
    disc_cfg = {
        "topology": "disconnected",
        "num_nodes": 128,
        "out_degree": 4,
        "num_modules": 4,
        "cross_module_ratio": 0.0,
        "active_fraction": 0.25,
        "stimulus_distribution": "stratified_modules",
        "target_pool_per_module": disc_budget["target_pool_per_module"],
        "total_target_pool_neurons": disc_budget["total_target_pool_neurons"],
        "horizon_ms": 100.0,
        "tau_ms": 10.0,
        "v_th_mv": 1.0,
        "v_reset_mv": 0.0,
        "refractory_ms": 2.0,
    }
    workloads_manifest["pilot_disconnected_n128_d4_s11"] = {
        "workload_id": "sc05/disconnected/v1",
        "seed": 11,
        "config": disc_cfg,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/disconnected/v1",
            11,
            disc_cfg,
            {
                "pilot_disconnected_n128_d4_s11_edges.csv": disc_edges_sha,
                "pilot_disconnected_n128_d4_s11_events.csv": disc_events_sha,
            },
        ),
        "files": [
            "pilot_disconnected_n128_d4_s11_edges.csv",
            "pilot_disconnected_n128_d4_s11_events.csv",
        ],
    }

    # 4b. Pilot Disconnected Localized-Activity Control (Module 0 only, N=128, D=4, seed=11)
    # Note: active_fraction=0.25 within Module 0 (32 nodes) exposes 8 target neurons [0..7] in Module 0,
    # matching the per-module active target pool (8 neurons/module) of the stratified workload!
    disc_loc_events = generate_external_events(
        num_nodes=128,
        num_events=64,
        horizon_ms=100.0,
        seed=11,
        active_fraction=0.25,
        num_modules=4,
        stimulus_distribution="localized_first_module",
    )
    disc_loc_events_sha = _write_and_record(
        "pilot_disconnected_localized_n128_d4_s11_events.csv",
        serialize_events_csv(disc_loc_events),
        "Pilot disconnected localized-activity control external stimulus (all 64 events in Module 0 [0..7], seed=11)",
    )
    disc_loc_budget = compute_stimulus_target_budget(128, 4, 0.25, "localized_first_module")
    disc_loc_cfg = {
        "topology": "disconnected",
        "num_nodes": 128,
        "out_degree": 4,
        "num_modules": 4,
        "cross_module_ratio": 0.0,
        "active_fraction": 0.25,
        "stimulus_distribution": "localized_first_module",
        "target_pool_per_module": disc_loc_budget["target_pool_per_module"],
        "total_target_pool_neurons": disc_loc_budget["total_target_pool_neurons"],
        "horizon_ms": 100.0,
        "tau_ms": 10.0,
        "v_th_mv": 1.0,
        "v_reset_mv": 0.0,
        "refractory_ms": 2.0,
    }
    workloads_manifest["pilot_disconnected_localized_n128_d4_s11"] = {
        "workload_id": "sc05/disconnected/v1",
        "seed": 11,
        "config": disc_loc_cfg,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/disconnected/v1",
            11,
            disc_loc_cfg,
            {
                "pilot_disconnected_n128_d4_s11_edges.csv": disc_edges_sha,
                "pilot_disconnected_localized_n128_d4_s11_events.csv": disc_loc_events_sha,
            },
        ),
        "files": [
            "pilot_disconnected_n128_d4_s11_edges.csv",
            "pilot_disconnected_localized_n128_d4_s11_events.csv",
        ],
    }

    # 5. Pilot Modular SBM Fixture — Stratified Across All 4 Modules (sc05/modular/v1, N=128, D=4, seed=11)
    mod_edges = generate_Topology_edges(
        topology="modular_sbm",
        num_nodes=128,
        out_degree=4,
        seed=11,
        num_modules=4,
        cross_module_ratio=0.05,
    )
    mod_events = generate_external_events(
        num_nodes=128,
        num_events=64,
        horizon_ms=100.0,
        seed=11,
        active_fraction=0.25,
        num_modules=4,
        stimulus_distribution="stratified_modules",
    )
    mod_edges_sha = _write_and_record(
        "pilot_modular_n128_d4_s11_edges.csv",
        serialize_edges_csv(mod_edges),
        "Pilot modular SBM 4-module graph fixture (N=128, D=4, c=0.05, 512 directed edges, seed=11)",
    )
    mod_events_sha = _write_and_record(
        "pilot_modular_n128_d4_s11_events.csv",
        serialize_events_csv(mod_events),
        "Pilot modular SBM stratified external stimulus (64 events, 16 per module across 4 modules, seed=11)",
    )
    mod_budget = compute_stimulus_target_budget(128, 4, 0.25, "stratified_modules")
    mod_cfg = {
        "topology": "modular_sbm",
        "num_nodes": 128,
        "out_degree": 4,
        "num_modules": 4,
        "cross_module_ratio": 0.05,
        "active_fraction": 0.25,
        "stimulus_distribution": "stratified_modules",
        "target_pool_per_module": mod_budget["target_pool_per_module"],
        "total_target_pool_neurons": mod_budget["total_target_pool_neurons"],
        "horizon_ms": 100.0,
        "tau_ms": 10.0,
        "v_th_mv": 1.0,
        "v_reset_mv": 0.0,
        "refractory_ms": 2.0,
    }
    workloads_manifest["pilot_modular_n128_d4_s11"] = {
        "workload_id": "sc05/modular/v1",
        "seed": 11,
        "config": mod_cfg,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/modular/v1",
            11,
            mod_cfg,
            {
                "pilot_modular_n128_d4_s11_edges.csv": mod_edges_sha,
                "pilot_modular_n128_d4_s11_events.csv": mod_events_sha,
            },
        ),
        "files": [
            "pilot_modular_n128_d4_s11_edges.csv",
            "pilot_modular_n128_d4_s11_events.csv",
        ],
    }

    # 6. Read-only provenance reference to EXP-0004 canonical configs
    exp4_mod_path = EXP0004_ROOT / "configs" / "canonical_modular_sbm_n100k.json"
    exp4_disc_path = EXP0004_ROOT / "configs" / "canonical_disconnected_control_n100k.json"
    exp4_schema_path = EXP0004_ROOT / "schemas" / "benchmark_schema.json"

    historical_exp0004_refs = {
        "read_only_verified": True,
        "cross_language_hash_equality_claimed": False,
        "note": (
            "EXP-0004 configs are parameter definitions (tau_m=5.0, min_delay=0.2, max_delay=1.0). "
            "EXP-0005 uses explicit physical units (ms, mV, tau_ms=10.0, refractory_ms=2.0) and "
            "SHA-256 fixture byte identity. Historical 64-bit FNV-1a checksums apply only to EXP-0004."
        ),
        "files": {
            "canonical_modular_sbm_n100k.json": {
                "relative_path": "../EXP-0004-topology-adaptive-scheduling/configs/canonical_modular_sbm_n100k.json",
                "sha256": sha256_file(exp4_mod_path) if exp4_mod_path.exists() else None,
            },
            "canonical_disconnected_control_n100k.json": {
                "relative_path": "../EXP-0004-topology-adaptive-scheduling/configs/canonical_disconnected_control_n100k.json",
                "sha256": sha256_file(exp4_disc_path) if exp4_disc_path.exists() else None,
            },
            "benchmark_schema_v1.json": {
                "relative_path": "../EXP-0004-topology-adaptive-scheduling/schemas/benchmark_schema.json",
                "sha256": sha256_file(exp4_schema_path) if exp4_schema_path.exists() else None,
            },
        },
    }

    manifest_obj = {
        "schema_version": "sc05-fixture-manifest-v1",
        "generator": "experiments/EXP-0005-scientific-simulation-substrates/scripts/fixture_generator.py",
        "rng_algorithm": "SplitMix64-deterministic-v1",
        "units": {
            "time": "ms",
            "voltage": "mV",
            "weight": "mV",
            "delay": "ms",
        },
        "policies": _default_manifest_policies(),
        "files": files_manifest,
        "workloads": workloads_manifest,
        "historical_exp0004_provenance": historical_exp0004_refs,
    }

    manifest_bytes = canonical_json_bytes(manifest_obj)
    (output_dir / "manifest_sha256.json").write_bytes(manifest_bytes)
    return manifest_obj


def default_external_custom_dir() -> Path:
    """Return default external artifact directory outside Git for custom fixtures."""
    env_root = os.environ.get("SC_ARTIFACT_ROOT")
    if env_root:
        return Path(env_root).resolve() / "EXP-0005" / "fixtures"
    return Path("/tmp/sc-artifacts/EXP-0005/fixtures").resolve()


def generate_custom_fixture_cli(
    output_dir: Optional[Path],
    topology: str,
    num_nodes: int,
    out_degree: int,
    num_events: int,
    horizon_ms: float,
    seed: int,
    num_modules: int = 4,
    cross_module_ratio: float = 0.05,
    active_fraction: float = 0.25,
    stimulus_distribution: str = "stratified_modules",
    allow_overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Generate an on-demand fixture outside Git using content-addressed naming
    and per-instance directory isolation (`<output_dir>/<workload_instance_id>/`).

    Safety & Non-Collision Guarantees:
      1. Refuses to write into the committed `EXP-0005/fixtures` directory so canonical
         committed fixtures can never be accidentally overwritten by `--mode custom`.
      2. Names fixture files and manifest keys by a 16-hex-char config digest + seed
         (`custom_<topo>_n<N>_d<D>_s<seed>_<cfg_hash12>`) and stores each workload instance
         inside `<output_dir>/<workload_instance_id>/` while also indexing it in the
         shared root `<output_dir>/manifest_sha256.json` under its unique `workload_instance_id`.
      3. Two workloads at the same `(topology, num_nodes, out_degree, seed)` that differ in
         `num_events`, `horizon_ms`, `num_modules`, `cross_module_ratio`, `active_fraction`,
         or `stimulus_distribution` receive distinct file names, distinct directories, and
         distinct entries in `manifest_sha256.json` with zero collision.
      4. If the exact same `workload_instance_id` already exists in `output_dir` and
         `allow_overwrite=False`, raises `FileExistsError` rather than silently overwriting.
    """
    if topology not in TOPOLOGY_TO_WORKLOAD_ID:
        raise ValueError(f"Unsupported topology '{topology}'; must be one of {sorted(TOPOLOGY_TO_WORKLOAD_ID)}")

    target_root = (output_dir if output_dir is not None else default_external_custom_dir()).resolve()
    if target_root == COMMITTED_FIXTURES_DIR or COMMITTED_FIXTURES_DIR in target_root.parents:
        raise PermissionError(
            f"Refusing to write custom on-demand fixture into committed directory '{target_root}'. "
            "Use an external path (e.g. $SC_ARTIFACT_ROOT/EXP-0005/fixtures)."
        )

    workload_id = TOPOLOGY_TO_WORKLOAD_ID[topology]
    canonical_topo = "modular_sbm" if topology == "modular" else topology
    effective_cross = 0.0 if canonical_topo == "disconnected" else cross_module_ratio

    budget = compute_stimulus_target_budget(
        num_nodes=num_nodes,
        num_modules=num_modules,
        active_fraction=active_fraction,
        stimulus_distribution=stimulus_distribution,
    )
    cfg = {
        "topology": canonical_topo,
        "num_nodes": num_nodes,
        "out_degree": out_degree,
        "num_modules": num_modules,
        "cross_module_ratio": effective_cross,
        "active_fraction": active_fraction,
        "stimulus_distribution": stimulus_distribution,
        "target_pool_per_module": budget["target_pool_per_module"],
        "total_target_pool_neurons": budget["total_target_pool_neurons"],
        "num_events": num_events,
        "horizon_ms": horizon_ms,
        "tau_ms": 10.0,
        "v_th_mv": 1.0,
        "v_reset_mv": 0.0,
        "refractory_ms": 2.0,
    }
    cfg_digest12 = sha256_bytes(canonical_json_bytes({"seed": seed, "config": cfg}))[:12]
    stem = f"custom_{canonical_topo}_n{num_nodes}_d{out_degree}_s{seed}_{cfg_digest12}"

    edges = generate_Topology_edges(
        topology=canonical_topo,
        num_nodes=num_nodes,
        out_degree=out_degree,
        seed=seed,
        num_modules=num_modules,
        cross_module_ratio=effective_cross,
    )
    events = generate_external_events(
        num_nodes=num_nodes,
        num_events=num_events,
        horizon_ms=horizon_ms,
        seed=seed,
        active_fraction=active_fraction,
        num_modules=num_modules,
        stimulus_distribution=stimulus_distribution,
    )
    edges_bytes = serialize_edges_csv(edges)
    events_bytes = serialize_events_csv(events)

    edges_file = f"{stem}_edges.csv"
    events_file = f"{stem}_events.csv"
    edges_sha = sha256_bytes(edges_bytes)
    events_sha = sha256_bytes(events_bytes)

    w_instance_id = compute_workload_instance_id(
        workload_id,
        seed,
        cfg,
        {edges_file: edges_sha, events_file: events_sha},
    )

    instance_dir = target_root / w_instance_id
    root_manifest_path = target_root / "manifest_sha256.json"
    if instance_dir.exists() and not allow_overwrite:
        raise FileExistsError(
            f"Workload instance '{w_instance_id}' already exists at {instance_dir}. "
            "Pass allow_overwrite=True (--allow-overwrite) to overwrite."
        )

    instance_dir.mkdir(parents=True, exist_ok=True)
    rel_edges_path = f"{w_instance_id}/{edges_file}"
    rel_events_path = f"{w_instance_id}/{events_file}"
    (instance_dir / edges_file).write_bytes(edges_bytes)
    (instance_dir / events_file).write_bytes(events_bytes)

    # Also write canonical workload_config.json inside the instance directory so records
    # referencing `workload_config.json` can be checked for exact semantic config equality
    instance_cfg_path = instance_dir / "workload_config.json"
    instance_cfg_bytes = canonical_json_bytes(cfg)
    instance_cfg_path.write_bytes(instance_cfg_bytes)
    instance_cfg_sha = sha256_bytes(instance_cfg_bytes)

    file_entries = {
        edges_file: {
            "path": rel_edges_path,
            "byte_count": len(edges_bytes),
            "sha256": edges_sha,
            "description": f"Custom {canonical_topo} graph edges (N={num_nodes}, D={out_degree}, seed={seed}, cfg={cfg_digest12})",
        },
        events_file: {
            "path": rel_events_path,
            "byte_count": len(events_bytes),
            "sha256": events_sha,
            "description": f"Custom {canonical_topo} stimulus events ({num_events} events, {stimulus_distribution}, f={active_fraction}, seed={seed})",
        },
    }
    workload_entry = {
        "workload_id": workload_id,
        "seed": seed,
        "config": cfg,
        "config_sha256": instance_cfg_sha,
        "workload_instance_id": w_instance_id,
        "files": [edges_file, events_file],
    }

    # Write self-contained per-instance manifest
    instance_manifest_obj = {
        "schema_version": "sc05-fixture-manifest-v1",
        "generator": "experiments/EXP-0005-scientific-simulation-substrates/scripts/fixture_generator.py",
        "rng_algorithm": "SplitMix64-deterministic-v1",
        "units": {"time": "ms", "voltage": "mV", "weight": "mV", "delay": "ms"},
        "policies": _default_manifest_policies(),
        "files": {
            edges_file: {**file_entries[edges_file], "path": edges_file},
            events_file: {**file_entries[events_file], "path": events_file},
        },
        "workloads": {w_instance_id: workload_entry},
    }
    instance_manifest_path = instance_dir / "manifest_sha256.json"
    instance_manifest_path.write_bytes(canonical_json_bytes(instance_manifest_obj))

    # Update shared root manifest without colliding across parameter combinations
    if root_manifest_path.exists():
        root_manifest_obj = json.loads(root_manifest_path.read_text(encoding="utf-8"))
    else:
        root_manifest_obj = {
            "schema_version": "sc05-fixture-manifest-v1",
            "generator": "experiments/EXP-0005-scientific-simulation-substrates/scripts/fixture_generator.py",
            "rng_algorithm": "SplitMix64-deterministic-v1",
            "units": {"time": "ms", "voltage": "mV", "weight": "mV", "delay": "ms"},
            "policies": _default_manifest_policies(),
            "files": {},
            "workloads": {},
        }

    if not allow_overwrite and w_instance_id in root_manifest_obj.get("workloads", {}):
        raise FileExistsError(f"Workload instance '{w_instance_id}' already registered in {root_manifest_path}")

    root_manifest_obj["files"].update(file_entries)
    root_manifest_obj["workloads"][w_instance_id] = workload_entry
    root_manifest_path.write_bytes(canonical_json_bytes(root_manifest_obj))

    return {
        **workload_entry,
        "instance_dir": str(instance_dir),
        "instance_manifest_path": str(instance_manifest_path),
        "root_manifest_path": str(root_manifest_path),
        "workload_config_path": str(instance_cfg_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="EXP-0005 WP-00 Deterministic Fixture & Workload Transport Generator"
    )
    parser.add_argument(
        "--mode",
        choices=["wp00-committed", "custom"],
        default="wp00-committed",
        help="Generate committed WP-00 fixtures or a custom fixture outside Git",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (defaults to EXP-0005/fixtures for wp00-committed, or $SC_ARTIFACT_ROOT/EXP-0005/fixtures for custom)",
    )
    parser.add_argument(
        "--topology",
        choices=["disconnected", "modular_sbm", "modular", "random"],
        default="modular_sbm",
    )
    parser.add_argument("--nodes", type=int, default=128)
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--modules", type=int, default=4)
    parser.add_argument("--cross-module-ratio", type=float, default=0.05)
    parser.add_argument("--active-fraction", type=float, default=0.25)
    parser.add_argument("--events", type=int, default=64)
    parser.add_argument("--horizon-ms", type=float, default=100.0)
    parser.add_argument(
        "--stimulus-distribution",
        choices=["stratified_modules", "localized_first_module"],
        default="stratified_modules",
    )
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwriting an existing custom workload_instance_id directory",
    )
    args = parser.parse_args()

    if args.mode == "wp00-committed":
        out_path = Path(args.output).resolve() if args.output else COMMITTED_FIXTURES_DIR
        manifest = build_default_wp00_fixtures(out_path)
        total_bytes = sum(f["byte_count"] for f in manifest["files"].values())
        print(
            f"[WP-00] Generated {len(manifest['files'])} fixture files in {out_path} "
            f"(total {total_bytes} bytes <= 1 MiB policy)."
        )
    else:
        out_path = Path(args.output).resolve() if args.output else default_external_custom_dir()
        summary = generate_custom_fixture_cli(
            output_dir=out_path,
            topology=args.topology,
            num_nodes=args.nodes,
            out_degree=args.degree,
            num_events=args.events,
            horizon_ms=args.horizon_ms,
            seed=args.seed,
            num_modules=args.modules,
            cross_module_ratio=args.cross_module_ratio,
            active_fraction=args.active_fraction,
            stimulus_distribution=args.stimulus_distribution,
            allow_overwrite=args.allow_overwrite,
        )
        print(
            f"[WP-00] Generated custom fixture {summary['workload_id']} "
            f"(instance={summary['workload_instance_id']}) at {summary['instance_manifest_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
