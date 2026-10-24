#!/usr/bin/env python3
"""
EXP-0005 WP-00: Standalone Atlas v2 Record Validator (`sc05_benchmark_v2.json`).

Enforces both JSON Schema Draft 2020-12 structure and domain-specific scientific
integrity contracts:
  1. External `jsonschema` package check: if unavailable, reports schema validation
     unavailable rather than silently substituting a weak check.
  2. Synthetic Sample Gate:
     - Rejects records with `synthetic_validation_sample=true` unless `--allow-synthetic-sample`
       is explicitly passed.
     - For real benchmark records (`synthetic_validation_sample=false`), requires a full
       40-character hexadecimal `git_provenance.commit_sha`.
  3. Zero-for-Unmeasured / Missingness Gate: every `null` value inside
     `backend_provenance`, `workload_identity`, `model_semantics`,
     `scale_and_activity_metrics`, `lifecycle_timing`, `resource_and_safety`, or
     `validation_and_fidelity` MUST have a corresponding entry in
     `missing_or_unsupported_fields` with a non-empty explanation.
  4. Fail-Closed Manifest, File Byte Hash & Recipe Identity Gate:
     - Refuses to validate when `fixtures_manifest` is absent (`None`) or missing on disk,
       unless `--allow-external-archived-manifest` is explicitly passed with a valid
       manifest dictionary.
     - Independently computes SHA-256 of the on-disk file at `workload_identity.config_path`
       and verifies equality with `workload_identity.config_sha256`.
     - Independently computes SHA-256 of every referenced fixture file on disk (unless
       explicitly in external-archived mode) and verifies equality with the manifest and
       with `edges_fixture_sha256` / `events_fixture_sha256`.
     - Independently recomputes `workload_instance_id` from `(workload_id, seed, config, file_hashes)`
       using the canonical UTF-8 JSON recipe and rejects any mismatch.
  5. False Exactness & Parity Gate:
     - Rejects `parity_claim_with_exp0004 == true` unless `backend_name == "exp0004_historical_external"`
       and `historical_exp0004_triple` is populated.
     - Rejects `semantic_classification == "equivalent-exact"` if `dt_ms` is not null
       (grid-discretized solver), or if `adapted_input_sha256 != events_fixture_sha256`,
       or if `backward_time_committed_events > 0`, or if `oracle_passed` is not `true`.
     - Allows fixed-step (`dt_ms != null`) native models under `aligned-with-tolerance`
       when tolerance/error metrics and `adapted_input_sha256` are documented.
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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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
REPO_ROOT = EXP0005_ROOT.parent.parent
DEFAULT_SCHEMA_PATH = EXP0005_ROOT / "schemas" / "sc05_benchmark_v2.json"
DEFAULT_MANIFEST_PATH = EXP0005_ROOT / "fixtures" / "manifest_sha256.json"
EXP0004_SCHEMA_PATH = (
    EXP0005_ROOT.parent / "EXP-0004-topology-adaptive-scheduling" / "schemas" / "benchmark_schema.json"
)
EXP0004_SCHEMA_EXPECTED_SHA256 = "902952859c911a20d7c455a30be60a9bd96c9476222021541f165cec657bf968"
FULL_SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")


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


def canonical_json_bytes(obj: Any) -> bytes:
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def recompute_workload_instance_id(
    workload_id: str,
    seed: int,
    config_obj: Dict[str, Any],
    file_hashes: Dict[str, str],
) -> str:
    payload = {
        "canonicalization": "utf8-json-sorted-keys-v1",
        "workload_id": workload_id,
        "seed": int(seed),
        "config": config_obj,
        "fixture_file_sha256": file_hashes,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


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


def _resolve_candidate_path(path_str: str, base_dirs: List[Path]) -> Optional[Path]:
    p = Path(path_str)
    if p.is_absolute() and p.exists() and p.is_file():
        return p
    for bdir in base_dirs:
        cand = (bdir / p).resolve()
        if cand.exists() and cand.is_file():
            return cand
        cand_name = (bdir / p.name).resolve()
        if cand_name.exists() and cand_name.is_file():
            return cand_name
    return None


def validate_sc05_v2_record(
    record: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    fixtures_manifest: Optional[Dict[str, Any]] = None,
    fixtures_base_dir: Optional[Path] = None,
    allow_synthetic_sample: bool = False,
    allow_external_archived_manifest: bool = False,
) -> Dict[str, Any]:
    """
    Validate a single EXP-0005 v2 record against JSON Schema Draft 2020-12 and
    all scientific semantic and byte-hash gates.
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

    # 1. Synthetic sample gate & full commit SHA requirement for real runs
    is_synthetic = bool(record.get("synthetic_validation_sample", False))
    if is_synthetic and not allow_synthetic_sample:
        raise RecordValidationError(
            f"Record '{record.get('run_id')}' is marked synthetic_validation_sample=True (NOT A RUN) "
            "and cannot be accepted as a measured benchmark run."
        )
    commit_sha = record["git_provenance"]["commit_sha"]
    if not is_synthetic and not FULL_SHA40_RE.match(commit_sha):
        raise RecordValidationError(
            f"Measured benchmark records (synthetic_validation_sample=False) require a full 40-char git commit_sha, got '{commit_sha}'."
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

    # 3. Fail-closed manifest, config_path, fixture raw byte hash, and recipe recomputation gate
    if fixtures_manifest is None:
        raise RecordValidationError(
            "fixtures_manifest is required (fail-closed): cannot validate workload identity without a manifest."
        )
    if (
        not isinstance(fixtures_manifest, dict)
        or fixtures_manifest.get("schema_version") != "sc05-fixture-manifest-v1"
        or "workloads" not in fixtures_manifest
        or "files" not in fixtures_manifest
    ):
        raise RecordValidationError(
            "Invalid fixtures_manifest structure: expected schema_version='sc05-fixture-manifest-v1' with 'workloads' and 'files'."
        )

    search_dirs: List[Path] = []
    if fixtures_base_dir is not None:
        search_dirs.append(fixtures_base_dir.resolve())
    search_dirs.extend([EXP0005_ROOT / "fixtures", EXP0005_ROOT, REPO_ROOT])

    wi = record["workload_identity"]
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

    # Verify config_path on disk, its SHA-256, and semantic equality with expected_w["config"]
    cfg_file = _resolve_candidate_path(wi["config_path"], search_dirs)
    config_file_verified_on_disk = False
    if cfg_file is None:
        if not allow_external_archived_manifest:
            raise RecordValidationError(
                f"Referenced workload config_path '{wi['config_path']}' does not exist on disk."
            )
    else:
        raw_cfg_bytes = cfg_file.read_bytes()
        actual_cfg_sha = hashlib.sha256(raw_cfg_bytes).hexdigest()
        if actual_cfg_sha.lower() != wi["config_sha256"].lower():
            raise RecordValidationError(
                f"On-disk config_sha256 mismatch for '{wi['config_path']}': "
                f"record claims {wi['config_sha256']}, actual file bytes hashed to {actual_cfg_sha}."
            )
        config_file_verified_on_disk = True
        if cfg_file.suffix.lower() == ".json":
            try:
                parsed_cfg = json.loads(raw_cfg_bytes.decode("utf-8"))
            except Exception as exc:
                raise RecordValidationError(
                    f"Failed to parse JSON at config_path '{wi['config_path']}': {exc}"
                ) from exc
            if isinstance(parsed_cfg, dict):
                if parsed_cfg.get("schema_version") == "sc05-fixture-manifest-v1":
                    cfg_workloads = parsed_cfg.get("workloads", {})
                    matched_manifest_w = None
                    for mw in cfg_workloads.values():
                        if isinstance(mw, dict) and mw.get("workload_instance_id") == w_inst_id:
                            matched_manifest_w = mw
                            break
                    if matched_manifest_w is None or matched_manifest_w.get("config") != expected_w.get("config"):
                        raise RecordValidationError(
                            f"Semantic config mismatch between config_path manifest '{wi['config_path']}' "
                            f"and expected workload recipe for instance {w_inst_id}."
                        )
                elif "config" in parsed_cfg and isinstance(parsed_cfg["config"], dict):
                    if parsed_cfg["config"] != expected_w.get("config"):
                        raise RecordValidationError(
                            f"Semantic config mismatch in '{wi['config_path']}': "
                            f"file config {parsed_cfg['config']} != manifest recipe config {expected_w.get('config')}."
                        )
                    if "workload_instance_id" in parsed_cfg and parsed_cfg["workload_instance_id"] != w_inst_id:
                        raise RecordValidationError(
                            f"workload_instance_id in config_path '{wi['config_path']}' "
                            f"({parsed_cfg['workload_instance_id']}) != record workload_instance_id ({w_inst_id})."
                        )
                else:
                    if parsed_cfg != expected_w.get("config"):
                        raise RecordValidationError(
                            f"Semantic config mismatch in standalone config file '{wi['config_path']}': "
                            f"file content does not match manifest recipe config for {w_inst_id}."
                        )

    files_meta = fixtures_manifest.get("files", {})
    verified_file_hashes: Dict[str, str] = {}
    physically_verified_fixture_files_count = 0
    for fname in expected_w.get("files", []):
        if fname not in files_meta:
            raise RecordValidationError(f"Fixture file '{fname}' missing from manifest['files'].")
        manifest_f_sha = files_meta[fname]["sha256"]
        manifest_f_bytes = int(files_meta[fname]["byte_count"])

        # Independently hash on-disk fixture file bytes
        rel_path_in_manifest = files_meta[fname].get("path", fname)
        f_disk = _resolve_candidate_path(rel_path_in_manifest, search_dirs) or _resolve_candidate_path(fname, search_dirs)
        if f_disk is None:
            if not allow_external_archived_manifest:
                raise RecordValidationError(
                    f"Referenced fixture file '{fname}' does not exist on disk (fail-closed)."
                )
            actual_f_sha = manifest_f_sha
        else:
            raw_bytes = f_disk.read_bytes()
            actual_f_sha = hashlib.sha256(raw_bytes).hexdigest()
            if actual_f_sha.lower() != manifest_f_sha.lower():
                raise RecordValidationError(
                    f"Tampered fixture file '{fname}' on disk: manifest expects {manifest_f_sha}, "
                    f"actual bytes hashed to {actual_f_sha}."
                )
            if len(raw_bytes) != manifest_f_bytes:
                raise RecordValidationError(
                    f"Byte count mismatch for fixture file '{fname}': manifest expects {manifest_f_bytes}, "
                    f"actual bytes={len(raw_bytes)}."
                )
            physically_verified_fixture_files_count += 1

        verified_file_hashes[fname] = actual_f_sha
        if fname.endswith("_edges.csv") and wi.get("edges_fixture_sha256") != actual_f_sha:
            raise RecordValidationError(
                f"edges_fixture_sha256 mismatch for {fname}: got {wi.get('edges_fixture_sha256')}, expected {actual_f_sha}"
            )
        if fname.endswith("_events.csv") and wi.get("events_fixture_sha256") != actual_f_sha:
            raise RecordValidationError(
                f"events_fixture_sha256 mismatch for {fname}: got {wi.get('events_fixture_sha256')}, expected {actual_f_sha}"
            )

    expected_fixture_files_count = len(expected_w.get("files", []))
    all_bytes_verified = (
        config_file_verified_on_disk
        and physically_verified_fixture_files_count == expected_fixture_files_count
    )
    verification_level = (
        "full_on_disk_bytes_verified" if all_bytes_verified else "manifest_only_unverified_bytes"
    )

    # Independently recompute workload_instance_id from canonical recipe + verified file hashes
    if "config" not in expected_w or not isinstance(expected_w["config"], dict):
        raise RecordValidationError(
            f"Workload entry for '{w_inst_id}' in manifest lacks canonical 'config' object for recipe verification."
        )
    recomputed_instance_id = recompute_workload_instance_id(
        workload_id=expected_w["workload_id"],
        seed=int(expected_w["seed"]),
        config_obj=expected_w["config"],
        file_hashes=verified_file_hashes,
    )
    if recomputed_instance_id.lower() != w_inst_id.lower():
        raise RecordValidationError(
            f"Canonical recipe workload_instance_id mismatch: record/manifest claims {w_inst_id}, "
            f"recomputed from recipe+file hashes is {recomputed_instance_id}."
        )

    # 4. False exactness, aligned-with-tolerance, and parity gates
    ms = record["model_semantics"]
    vf = record["validation_and_fidelity"]
    bp = record["backend_provenance"]

    if vf.get("parity_claim_with_exp0004") is True:
        if bp.get("backend_name") != "exp0004_historical_external" or wi.get("historical_exp0004_triple") is None:
            raise RecordValidationError(
                "Cross-framework record cannot claim exact parity_claim_with_exp0004=True; "
                "historical EXP-0004 digests apply only to EXP-0004 engines."
            )

    sem_cls = ms.get("semantic_classification")
    if sem_cls == "equivalent-exact":
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
    elif sem_cls == "aligned-with-tolerance":
        if int(vf.get("backward_time_committed_events", 0)) > 0 or not vf.get("timestamp_monotonicity_passed"):
            raise RecordValidationError(
                "Record claiming 'aligned-with-tolerance' must pass timestamp monotonicity with 0 backward-time events."
            )
        if vf.get("oracle_passed") is not True:
            raise RecordValidationError(
                "Record claiming 'aligned-with-tolerance' must have validation_and_fidelity.oracle_passed=True within documented tolerance."
            )
        if (
            vf.get("spike_time_mae_ms") is None
            and vf.get("membrane_rmse_mv") is None
            and vf.get("spike_precision") is None
        ):
            raise RecordValidationError(
                "Record claiming 'aligned-with-tolerance' must report at least one quantitative fidelity metric "
                "(spike_time_mae_ms, membrane_rmse_mv, or spike_precision)."
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
        "recomputed_workload_instance_id": recomputed_instance_id,
        "verified_fixture_files_count": physically_verified_fixture_files_count,
        "expected_fixture_files_count": expected_fixture_files_count,
        "verification_level": verification_level,
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
        help="Path to fixtures/manifest_sha256.json (required; fails closed if missing)",
    )
    parser.add_argument(
        "--allow-synthetic-sample",
        action="store_true",
        help="Allow validation of synthetic_validation_sample=true records",
    )
    parser.add_argument(
        "--allow-external-archived-manifest",
        action="store_true",
        help="Allow validating against a manifest whose bulky fixture files reside in external archive storage",
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

    if not schema_path.exists():
        raise RecordValidationError(f"Schema file not found: {schema_path}")
    if not input_path.exists():
        raise RecordValidationError(f"Input record file not found: {input_path}")
    if not manifest_path.exists():
        raise RecordValidationError(
            f"Fixtures manifest not found at {manifest_path} (fail-closed: refusing to validate without manifest)."
        )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    record = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    summary = validate_sc05_v2_record(
        record=record,
        schema=schema,
        fixtures_manifest=manifest,
        fixtures_base_dir=manifest_path.parent,
        allow_synthetic_sample=args.allow_synthetic_sample,
        allow_external_archived_manifest=args.allow_external_archived_manifest,
    )
    summary["exp0004_v1_schema_sha256_verified"] = v1_sha
    try:
        summary["input_file"] = str(input_path.relative_to(REPO_ROOT))
    except ValueError:
        summary["input_file"] = str(input_path)
    summary["input_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()

    if args.report_out:
        out_p = Path(args.report_out).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
