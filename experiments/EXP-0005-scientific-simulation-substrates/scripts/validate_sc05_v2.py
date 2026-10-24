#!/usr/bin/env python3
"""
EXP-0005 WP-00: Standalone Atlas v2 Record Validator (`sc05_benchmark_v2.json`).

Enforces both JSON Schema Draft 2020-12 structure and domain-specific scientific
integrity contracts:
  1. External `jsonschema` package check: if unavailable, reports schema validation
     unavailable rather than silently substituting a weak check.
  2. Synthetic Sample Gate: rejects records with `synthetic_validation_sample=true`
     unless `--allow-synthetic-sample` is explicitly passed.
  3. Zero-for-Unmeasured / Missingness Gate: every `null` value inside
     `backend_provenance`, `workload_identity`, `model_semantics`,
     `scale_and_activity_metrics`, `lifecycle_timing`, `resource_and_safety`, or
     `validation_and_fidelity` MUST have a corresponding entry in
     `missing_or_unsupported_fields` with a non-empty explanation.
  4. Fixture & Workload Identity Gate: when `--fixtures-manifest` is supplied (default
     `fixtures/manifest_sha256.json`), verifies that `workload_instance_id`,
     `edges_fixture_sha256`, and `events_fixture_sha256` match the canonical manifest.
  5. False Exactness & Parity Gate:
     - Rejects `parity_claim_with_exp0004 == true` unless `backend_name == "exp0004_historical_external"`
       and `historical_exp0004_triple` is populated.
     - Rejects `semantic_classification == "equivalent-exact"` if `dt_ms` is not null
       (grid-discretized solver), or if `adapted_input_sha256 != events_fixture_sha256`,
       or if `backward_time_committed_events > 0`, or if `oracle_passed` is not `true`.
  6. Allocation-as-Activity Gate:
     - Outside `sc05/long-silence/v1` and `sc05/analytic-leak/v1`, rejects any record
       claiming successful simulation completion (`exit_status == 0`) with
       `committed_events == 0` or `active_neurons_count == 0`.
  7. Optimistic PDES (ROSS) Causality Gate:
     - When `backend_name == "ROSS"`, requires `rolled_back_events`, `reexecuted_events`,
       and `committed_events` to be non-null and `scheduler_processed_events >= committed_events`.
  8. Historical EXP-0004 v1 Preservation Gate:
     - Verifies that `../EXP-0004-topology-adaptive-scheduling/schemas/benchmark_schema.json`
       retains its exact historical SHA-256 (`902952859c911a20d7c455a30be60a9bd96c9476222021541f165cec657bf968`).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
    try:
        JSONSCHEMA_VERSION = importlib.metadata.version("jsonschema")
    except Exception:
        JSONSCHEMA_VERSION = "unknown"
except ImportError:
    jsonschema = None  # type: ignore[assignment]
    JSONSCHEMA_AVAILABLE = False
    JSONSCHEMA_VERSION = None


EXP0005_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = EXP0005_ROOT / "schemas" / "sc05_benchmark_v2.json"
DEFAULT_MANIFEST_PATH = EXP0005_ROOT / "fixtures" / "manifest_sha256.json"
EXP0004_SCHEMA_PATH = (
    EXP0005_ROOT.parent / "EXP-0004-topology-adaptive-scheduling" / "schemas" / "benchmark_schema.json"
)
EXP0004_SCHEMA_EXPECTED_SHA256 = "902952859c911a20d7c455a30be60a9bd96c9476222021541f165cec657bf968"


class SchemaValidationUnavailableError(RuntimeError):
    """Raised when `jsonschema` is not installed in the Python environment."""


class RecordValidationError(ValueError):
    """Raised when a record fails schema v2 or semantic/provenance validation."""


TRACKED_NULL_SECTIONS = (
    "backend_provenance",
    "workload_identity",
    "model_semantics",
    "scale_and_activity_metrics",
    "lifecycle_timing",
    "resource_and_safety",
    "validation_and_fidelity",
)


def verify_exp0004_v1_schema_untouched() -> str:
    if not EXP0004_SCHEMA_PATH.exists():
        raise RecordValidationError(f"Missing historical EXP-0004 schema at {EXP0004_SCHEMA_PATH}")
    actual_sha = hashlib.sha256(EXP0004_SCHEMA_PATH.read_bytes()).hexdigest()
    if actual_sha != EXP0004_SCHEMA_EXPECTED_SHA256:
        raise RecordValidationError(
            f"Historical EXP-0004 v1 schema modified! Expected {EXP0004_SCHEMA_EXPECTED_SHA256}, got {actual_sha}"
        )
    return actual_sha


def collect_null_field_paths(record: Dict[str, Any]) -> List[str]:
    null_paths: List[str] = []
    for section in TRACKED_NULL_SECTIONS:
        sec_obj = record.get(section)
        if isinstance(sec_obj, dict):
            for key, val in sec_obj.items():
                if val is None:
                    null_paths.append(f"{section}.{key}")
    return sorted(null_paths)


def validate_sc05_v2_record(
    record: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    fixtures_manifest: Optional[Dict[str, Any]] = None,
    allow_synthetic_sample: bool = False,
) -> Dict[str, Any]:
    """
    Validate a single EXP-0005 v2 record against JSON Schema Draft 2020-12 and
    all scientific semantic gates. Returns a structured validation summary or
    raises RecordValidationError / SchemaValidationUnavailableError.
    """
    if not JSONSCHEMA_AVAILABLE or jsonschema is None:
        raise SchemaValidationUnavailableError(
            "External package 'jsonschema' is unavailable; refusing to substitute ad-hoc schema check."
        )

    if schema is None:
        schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))

    try:
        jsonschema.validate(instance=record, schema=schema)
    except jsonschema.ValidationError as exc:
        raise RecordValidationError(f"JSON Schema v2 validation failed: {exc.message}") from exc

    # 1. Synthetic sample gate
    is_synthetic = bool(record.get("synthetic_validation_sample", False))
    if is_synthetic and not allow_synthetic_sample:
        raise RecordValidationError(
            f"Record '{record.get('run_id')}' is marked synthetic_validation_sample=True (NOT A RUN) "
            "and cannot be accepted as a measured benchmark run."
        )

    # 2. Missing/null field explanation gate
    null_paths = collect_null_field_paths(record)
    missing_map = record.get("missing_or_unsupported_fields", {})
    for np in null_paths:
        reason = missing_map.get(np)
        if not reason or not isinstance(reason, str) or len(reason.strip()) < 3:
            raise RecordValidationError(
                f"Null field '{np}' lacks an explicit reason in 'missing_or_unsupported_fields'."
            )
    for declared_path in missing_map:
        if declared_path not in null_paths:
            raise RecordValidationError(
                f"Field '{declared_path}' is listed in 'missing_or_unsupported_fields' but is not null in the record."
            )

    # 3. Workload & fixture SHA-256 identity gate
    wi = record["workload_identity"]
    if fixtures_manifest is not None:
        known_instances = {
            w["workload_instance_id"]: w for w in fixtures_manifest.get("workloads", {}).values()
        }
        w_inst_id = wi["workload_instance_id"]
        if w_inst_id not in known_instances:
            raise RecordValidationError(
                f"Unknown workload_instance_id '{w_inst_id}' not found in fixtures manifest."
            )
        expected_w = known_instances[w_inst_id]
        if wi["workload_id"] != expected_w["workload_id"]:
            raise RecordValidationError(
                f"Workload ID mismatch for instance {w_inst_id}: got {wi['workload_id']}, "
                f"expected {expected_w['workload_id']}"
            )
        if int(wi["seed"]) != int(expected_w["seed"]):
            raise RecordValidationError(
                f"Seed mismatch for workload instance {w_inst_id}: got {wi['seed']}, expected {expected_w['seed']}"
            )
        files_meta = fixtures_manifest.get("files", {})
        for fname in expected_w.get("files", []):
            f_sha = files_meta.get(fname, {}).get("sha256")
            if fname.endswith("_edges.csv") and wi.get("edges_fixture_sha256") != f_sha:
                raise RecordValidationError(
                    f"edges_fixture_sha256 mismatch for {fname}: got {wi.get('edges_fixture_sha256')}, expected {f_sha}"
                )
            if fname.endswith("_events.csv") and wi.get("events_fixture_sha256") != f_sha:
                raise RecordValidationError(
                    f"events_fixture_sha256 mismatch for {fname}: got {wi.get('events_fixture_sha256')}, expected {f_sha}"
                )

    # 4. False exactness & parity gates
    ms = record["model_semantics"]
    vf = record["validation_and_fidelity"]
    bp = record["backend_provenance"]

    if vf.get("parity_claim_with_exp0004") is True:
        if bp.get("backend_name") != "exp0004_historical_external" or wi.get("historical_exp0004_triple") is None:
            raise RecordValidationError(
                "Cross-framework record cannot claim exact parity_claim_with_exp0004=True; "
                "historical EXP-0004 digests apply only to EXP-0004 engines."
            )

    if ms.get("semantic_classification") == "equivalent-exact":
        if ms.get("dt_ms") is not None:
            raise RecordValidationError(
                f"Fixed-step solver (dt_ms={ms.get('dt_ms')}) cannot claim semantic_classification='equivalent-exact' "
                "against continuous-time analytic delta-LIF."
            )
        if wi.get("events_fixture_sha256") is not None and wi.get("adapted_input_sha256") != wi.get("events_fixture_sha256"):
            raise RecordValidationError(
                "Record with quantized/adapted input events (adapted_input_sha256 != events_fixture_sha256) "
                "cannot claim semantic_classification='equivalent-exact'."
            )
        if int(vf.get("backward_time_committed_events", 0)) > 0 or not vf.get("timestamp_monotonicity_passed"):
            raise RecordValidationError(
                "Record with backward-time events or failed monotonicity cannot claim 'equivalent-exact'."
            )
        if vf.get("oracle_passed") is not True:
            raise RecordValidationError(
                "Record claiming 'equivalent-exact' must have validation_and_fidelity.oracle_passed=True."
            )

    # 5. Allocation-as-activity gate
    sam = record["scale_and_activity_metrics"]
    rs = record["resource_and_safety"]
    if rs.get("exit_status") == 0 and wi["workload_id"] not in ("sc05/long-silence/v1", "sc05/analytic-leak/v1"):
        if sam.get("active_neurons_count") in (0, None) or sam.get("committed_events") in (0, None):
            raise RecordValidationError(
                f"Allocation-only or zero-activity run on active workload '{wi['workload_id']}' "
                f"(active_neurons_count={sam.get('active_neurons_count')}, committed_events={sam.get('committed_events')})."
            )

    # 6. Optimistic PDES (ROSS) causality gate
    if bp.get("backend_name") == "ROSS":
        if sam.get("rolled_back_events") is None or sam.get("reexecuted_events") is None or sam.get("committed_events") is None:
            raise RecordValidationError(
                "ROSS backend records must report rolled_back_events, reexecuted_events, and committed_events explicitly."
            )
        if int(sam["scheduler_processed_events"]) < int(sam["committed_events"]):
            raise RecordValidationError(
                "ROSS scheduler_processed_events cannot be less than committed_events."
            )

    # 7. Timing & repetition consistency gate
    lt = record["lifecycle_timing"]
    reps = lt["rep_steady_simulation_wall_s"]
    if len(reps) != int(lt["measured_repetitions"]):
        raise RecordValidationError(
            f"Length of rep_steady_simulation_wall_s ({len(reps)}) != measured_repetitions ({lt['measured_repetitions']})."
        )
    if float(lt["total_end_to_end_wall_s"]) + 1e-12 < float(lt["steady_simulation_wall_s"]):
        raise RecordValidationError(
            f"total_end_to_end_wall_s ({lt['total_end_to_end_wall_s']}) < steady_simulation_wall_s ({lt['steady_simulation_wall_s']})."
        )

    return {
        "valid": True,
        "run_id": record["run_id"],
        "schema_version": record["schema_version"],
        "synthetic_validation_sample": is_synthetic,
        "workload_id": wi["workload_id"],
        "workload_instance_id": wi["workload_instance_id"],
        "semantic_classification": ms["semantic_classification"],
        "null_fields_documented_count": len(null_paths),
        "jsonschema_version": JSONSCHEMA_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EXP-0005 Atlas v2 benchmark records")
    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to sc05_benchmark_v2.json",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(EXP0005_ROOT / "schemas" / "synthetic_validation_sample_NOT_A_RUN.json"),
        help="Path to JSON record file to validate",
    )
    parser.add_argument(
        "--fixtures-manifest",
        type=str,
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to fixtures/manifest_sha256.json",
    )
    parser.add_argument(
        "--allow-synthetic-sample",
        action="store_true",
        help="Allow validation of synthetic_validation_sample=true records",
    )
    parser.add_argument(
        "--report-out",
        type=str,
        default=None,
        help="Optional path to write JSON validation report",
    )
    args = parser.parse_args()

    v1_sha = verify_exp0004_v1_schema_untouched()
    schema_path = Path(args.schema).resolve()
    input_path = Path(args.input).resolve()
    manifest_path = Path(args.fixtures_manifest).resolve()

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    record = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None

    summary = validate_sc05_v2_record(
        record=record,
        schema=schema,
        fixtures_manifest=manifest,
        allow_synthetic_sample=args.allow_synthetic_sample,
    )
    summary["exp0004_v1_schema_sha256_verified"] = v1_sha
    summary["input_file"] = str(input_path.relative_to(EXP0005_ROOT.parent.parent))
    summary["input_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()

    if args.report_out:
        out_p = Path(args.report_out).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
