#!/usr/bin/env python3
"""
EXP-0005 WP-00: Deterministic Workload & Fixture Transport Generator.

Generates backend-neutral, deterministic CSV and JSON fixtures for:
  - Golden A: sc05/analytic-leak/v1
  - Golden B: sc05/analytic-threshold/v1
  - Golden C1: sc05/replay/v1 (causal chain A->B->C with d=2 ms)
  - Golden C2: sc05/replay/v1 (simultaneous arrivals & refractory clamp)
  - Pilot Disconnected (sc05/disconnected/v1, N=128, D=4)
  - Pilot Modular SBM (sc05/modular/v1, N=128, D=4)
  - Historical EXP-0004 Config Provenance Map (read-only SHA-256 & unit translation)

All generated CSVs use LF line endings, explicit physical units (ms, mV),
strictly positive axonal delays (delay_ms > 0), and deterministic sorting:
  - Edges sorted by: (src_id, dst_id, delay_ms, weight_mV)
  - External events sorted by: (t_ms, target_id, src_id, ordinal)

Supports `--seed` and `--output` for writing large scale fixtures (e.g. N=10k, 100k)
outside Git (`$SC_ARTIFACT_ROOT/EXP-0005/fixtures/`).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXP0005_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP0005_ROOT.parent.parent
EXP0004_ROOT = REPO_ROOT / "experiments" / "EXP-0004-topology-adaptive-scheduling"


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
    and no self-edges.
    """
    if num_nodes <= 1 or out_degree <= 0:
        return []
    k = min(out_degree, num_nodes - 1)
    rng = SplitMix64(seed)
    edges: List[Tuple[int, int, float, float]] = []

    nodes_per_mod = max(1, num_nodes // num_modules)

    for u in range(num_nodes):
        mod_u = min(num_modules - 1, u // nodes_per_mod)
        mod_start = mod_u * nodes_per_mod
        mod_end = num_nodes if mod_u == num_modules - 1 else (mod_u + 1) * nodes_per_mod
        targets_set = set()

        while len(targets_set) < k:
            if topology == "disconnected":
                cand = mod_start + rng.uniform_uint(max(1, mod_end - mod_start))
            elif topology == "modular_sbm":
                if rng.uniform_float(0.0, 1.0) < cross_module_ratio:
                    cand = rng.uniform_uint(num_nodes)
                else:
                    cand = mod_start + rng.uniform_uint(max(1, mod_end - mod_start))
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


def generate_external_events(
    num_nodes: int,
    num_events: int,
    horizon_ms: float,
    seed: int,
    active_fraction: float = 0.25,
    min_weight_mv: float = 0.55,
    max_weight_mv: float = 1.15,
) -> List[Tuple[float, int, int, int, float]]:
    """
    Generate deterministic external stimulus pulses (t_ms, target_id, src_id=-1, ordinal, weight_mV).
    """
    rng = SplitMix64(seed ^ 0xA5A5A5A55A5A5A5A)
    active_limit = max(1, int(round(num_nodes * active_fraction)))
    raw_events: List[Tuple[float, int, float]] = []
    for _ in range(num_events):
        t_ms = round(rng.uniform_float(0.5, horizon_ms), 6)
        target_id = rng.uniform_uint(active_limit)
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


def build_default_wp00_fixtures(output_dir: Path) -> Dict[str, Any]:
    """
    Build all committed WP-00 Golden and Pilot fixtures in `output_dir` and return
    the complete manifest dictionary.
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
    workloads_manifest["golden_c_causal_chain"] = {
        "workload_id": "sc05/replay/v1",
        "seed": 0,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/replay/v1",
            0,
            {"num_nodes": 3, "tau_ms": 10.0, "v_th_mv": 1.0, "refractory_ms": 2.0},
            {
                "golden_c_causal_chain_edges.csv": gc_edges_sha,
                "golden_c_causal_chain_events.csv": gc_events_sha,
            },
        ),
        "files": ["golden_c_causal_chain_edges.csv", "golden_c_causal_chain_events.csv"],
    }
    workloads_manifest["golden_c_tie_adversarial"] = {
        "workload_id": "sc05/replay/v1",
        "seed": 0,
        "workload_instance_id": compute_workload_instance_id(
            "sc05/replay/v1",
            0,
            {"num_nodes": 1, "tau_ms": 10.0, "v_th_mv": 1.0, "refractory_ms": 2.0, "tie_policy": "(t_ms,target_id,src_id,ordinal)"},
            {"golden_c_tie_adversarial_events.csv": gc_tie_sha},
        ),
        "files": ["golden_c_tie_adversarial_events.csv"],
    }

    # 4. Pilot Disconnected Fixture (sc05/disconnected/v1, N=128, D=4, seed=11)
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
    )
    disc_edges_sha = _write_and_record(
        "pilot_disconnected_n128_d4_s11_edges.csv",
        serialize_edges_csv(disc_edges),
        "Pilot disconnected 4-module graph fixture (N=128, D=4, 512 directed edges, seed=11)",
    )
    disc_events_sha = _write_and_record(
        "pilot_disconnected_n128_d4_s11_events.csv",
        serialize_events_csv(disc_events),
        "Pilot disconnected external stimulus fixture (64 events over 100 ms, seed=11)",
    )
    disc_cfg = {
        "topology": "disconnected",
        "num_nodes": 128,
        "out_degree": 4,
        "num_modules": 4,
        "cross_module_ratio": 0.0,
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

    # 5. Pilot Modular SBM Fixture (sc05/modular/v1, N=128, D=4, seed=11)
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
    )
    mod_edges_sha = _write_and_record(
        "pilot_modular_n128_d4_s11_edges.csv",
        serialize_edges_csv(mod_edges),
        "Pilot modular SBM 4-module graph fixture (N=128, D=4, c=0.05, 512 directed edges, seed=11)",
    )
    mod_events_sha = _write_and_record(
        "pilot_modular_n128_d4_s11_events.csv",
        serialize_events_csv(mod_events),
        "Pilot modular SBM external stimulus fixture (64 events over 100 ms, seed=11)",
    )
    mod_cfg = {
        "topology": "modular_sbm",
        "num_nodes": 128,
        "out_degree": 4,
        "num_modules": 4,
        "cross_module_ratio": 0.05,
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
        "policies": {
            "edge_direction": "directed_src_to_dst",
            "self_edges": "forbidden",
            "duplicate_edges": "forbidden_per_src_dst_pair",
            "delay_constraint": "strictly_positive_delay_ms_gt_0",
            "event_tie_break_order": ["t_ms", "target_id", "src_id", "ordinal"],
            "refractory_interval": "half_open_[t_spike, t_spike + refractory_ms)",
        },
        "files": files_manifest,
        "workloads": workloads_manifest,
        "historical_exp0004_provenance": historical_exp0004_refs,
    }

    manifest_bytes = canonical_json_bytes(manifest_obj)
    (output_dir / "manifest_sha256.json").write_bytes(manifest_bytes)
    return manifest_obj


def generate_custom_fixture_cli(
    output_dir: Path,
    topology: str,
    num_nodes: int,
    out_degree: int,
    num_events: int,
    horizon_ms: float,
    seed: int,
) -> Dict[str, Any]:
    """Generate an on-demand fixture (e.g. outside Git for large scales) with SHA-256 manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{topology}_n{num_nodes}_d{out_degree}_s{seed}"
    edges = generate_Topology_edges(
        topology=topology,
        num_nodes=num_nodes,
        out_degree=out_degree,
        seed=seed,
    )
    events = generate_external_events(
        num_nodes=num_nodes,
        num_events=num_events,
        horizon_ms=horizon_ms,
        seed=seed,
    )
    edges_bytes = serialize_edges_csv(edges)
    events_bytes = serialize_events_csv(events)

    edges_file = f"{prefix}_edges.csv"
    events_file = f"{prefix}_events.csv"
    (output_dir / edges_file).write_bytes(edges_bytes)
    (output_dir / events_file).write_bytes(events_bytes)

    edges_sha = sha256_bytes(edges_bytes)
    events_sha = sha256_bytes(events_bytes)
    workload_id = f"sc05/{topology}/v1"
    cfg = {
        "topology": topology,
        "num_nodes": num_nodes,
        "out_degree": out_degree,
        "num_events": num_events,
        "horizon_ms": horizon_ms,
    }
    w_instance_id = compute_workload_instance_id(
        workload_id,
        seed,
        cfg,
        {edges_file: edges_sha, events_file: events_sha},
    )
    summary = {
        "workload_id": workload_id,
        "workload_instance_id": w_instance_id,
        "seed": seed,
        "config": cfg,
        "files": {
            edges_file: {"byte_count": len(edges_bytes), "sha256": edges_sha},
            events_file: {"byte_count": len(events_bytes), "sha256": events_sha},
        },
    }
    (output_dir / f"{prefix}_manifest.json").write_bytes(canonical_json_bytes(summary))
    return summary


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
        default=str(EXP0005_ROOT / "fixtures"),
        help="Output directory for generated fixtures",
    )
    parser.add_argument("--topology", choices=["disconnected", "modular_sbm", "random"], default="modular_sbm")
    parser.add_argument("--nodes", type=int, default=128)
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--events", type=int, default=64)
    parser.add_argument("--horizon-ms", type=float, default=100.0)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    if args.mode == "wp00-committed":
        manifest = build_default_wp00_fixtures(out_path)
        total_bytes = sum(f["byte_count"] for f in manifest["files"].values())
        print(
            f"[WP-00] Generated {len(manifest['files'])} fixture files in {out_path} "
            f"(total {total_bytes} bytes <= 1 MiB policy)."
        )
    else:
        summary = generate_custom_fixture_cli(
            output_dir=out_path,
            topology=args.topology,
            num_nodes=args.nodes,
            out_degree=args.degree,
            num_events=args.events,
            horizon_ms=args.horizon_ms,
            seed=args.seed,
        )
        print(f"[WP-00] Generated custom fixture {summary['workload_instance_id']} in {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
