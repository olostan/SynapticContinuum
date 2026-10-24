"""
EXP-0005 WP-00: Atlas v2 JSON Schema & Semantic Validator Unit Tests.

Verifies:
  1. `schemas/synthetic_validation_sample_NOT_A_RUN.json` passes when `--allow-synthetic-sample` is enabled,
     including independent on-disk config/fixture SHA-256 verification and `workload_instance_id` recipe recomputation.
  2. `schemas/synthetic_validation_sample_NOT_A_RUN.json` is REJECTED when `--allow-synthetic-sample` is False.
  3. Fail-closed manifest check: passing `fixtures_manifest=None` or an invalid manifest structure is REJECTED.
  4. On-demand custom fixture export (`generate_custom_fixture_cli`, including default `modular_sbm` -> `sc05/modular/v1`)
     round-trips end-to-end through `validate_sc05_v2_record`, and tampering with on-disk fixture bytes,
     `config_path` bytes, or `workload_instance_id` is REJECTED.
  5. Fixed-step native model (`dt_ms = 0.1`) with documented tolerated discrepancy passes under
     `semantic_classification = "aligned-with-tolerance"` (with full 40-char commit SHA and explicit null reasons),
     while claiming `"equivalent-exact"` with `dt_ms = 0.1` is REJECTED.
  6. Any `null` field lacking an entry in `missing_or_unsupported_fields` is REJECTED.
  7. Cross-framework record claiming `parity_claim_with_exp0004 = True` is REJECTED.
  8. Active workload with `active_neurons_count = 0` or `committed_events = 0` (allocation-as-activity) is REJECTED.
  9. ROSS record missing `rolled_back_events` is REJECTED.
  10. Historical EXP-0004 `schemas/benchmark_schema.json` remains bit-identical to its v1.0.0 SHA-256.
"""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from helper_imports import (
    EXP0005_ROOT,
    load_fixture_generator_module,
    load_validator_module,
)


class TestSchemaV2Validator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.val_mod = load_validator_module()
        cls.gen_mod = load_fixture_generator_module()
        cls.schema = json.loads((EXP0005_ROOT / "schemas" / "sc05_benchmark_v2.json").read_text(encoding="utf-8"))
        cls.sample = json.loads(
            (EXP0005_ROOT / "schemas" / "synthetic_validation_sample_NOT_A_RUN.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads((EXP0005_ROOT / "fixtures" / "manifest_sha256.json").read_text(encoding="utf-8"))

    def test_exp0004_v1_schema_untouched(self) -> None:
        sha = self.val_mod.verify_exp0004_v1_schema_untouched()
        self.assertEqual(sha, "902952859c911a20d7c455a30be60a9bd96c9476222021541f165cec657bf968")

    def test_synthetic_sample_accepted_only_with_explicit_flag(self) -> None:
        summary = self.val_mod.validate_sc05_v2_record(
            record=self.sample,
            schema=self.schema,
            fixtures_manifest=self.manifest,
            allow_synthetic_sample=True,
        )
        self.assertTrue(summary["valid"])
        self.assertTrue(summary["synthetic_validation_sample"])
        self.assertEqual(summary["workload_instance_id"], summary["recomputed_workload_instance_id"])

        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=self.sample,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=False,
            )

    def test_fail_closed_when_manifest_missing(self) -> None:
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=self.sample,
                schema=self.schema,
                fixtures_manifest=None,
                allow_synthetic_sample=True,
            )

    def test_custom_fixture_roundtrip_and_tamper_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # 1. Generate custom on-demand fixture (default modular_sbm -> sc05/modular/v1)
            w_entry = self.gen_mod.generate_custom_fixture_cli(
                output_dir=tmp_path,
                topology="modular_sbm",
                num_nodes=64,
                out_degree=4,
                num_events=32,
                horizon_ms=50.0,
                seed=23,
                num_modules=4,
                stimulus_distribution="stratified_modules",
            )
            self.assertEqual(w_entry["workload_id"], "sc05/modular/v1")

            custom_manifest_path = tmp_path / "manifest_sha256.json"
            custom_manifest = json.loads(custom_manifest_path.read_text(encoding="utf-8"))
            custom_manifest_sha = hashlib.sha256(custom_manifest_path.read_bytes()).hexdigest()

            edges_fname, events_fname = w_entry["files"]
            edges_sha = custom_manifest["files"][edges_fname]["sha256"]
            events_sha = custom_manifest["files"][events_fname]["sha256"]

            # 2. Build a record referencing the custom fixture and validate end-to-end
            rec = copy.deepcopy(self.sample)
            rec["workload_identity"] = {
                "workload_id": w_entry["workload_id"],
                "workload_instance_id": w_entry["workload_instance_id"],
                "seed": 23,
                "rng_stream_id": "SplitMix64-deterministic-v1:seed=23",
                "config_path": str(custom_manifest_path),
                "config_sha256": custom_manifest_sha,
                "edges_fixture_sha256": edges_sha,
                "events_fixture_sha256": events_sha,
                "adapted_input_sha256": events_sha,
                "historical_exp0004_triple": None,
            }
            summary = self.val_mod.validate_sc05_v2_record(
                record=rec,
                schema=self.schema,
                fixtures_manifest=custom_manifest,
                fixtures_base_dir=tmp_path,
                allow_synthetic_sample=True,
            )
            self.assertTrue(summary["valid"])
            self.assertEqual(summary["workload_id"], "sc05/modular/v1")

            # 3. Tamper with raw bytes of the on-disk edges CSV file -> MUST FAIL
            edges_disk_path = tmp_path / edges_fname
            orig_edges_bytes = edges_disk_path.read_bytes()
            edges_disk_path.write_bytes(orig_edges_bytes + b"\n0,1,1.00000000,0.10000000\n")
            with self.assertRaises(self.val_mod.RecordValidationError):
                self.val_mod.validate_sc05_v2_record(
                    record=rec,
                    schema=self.schema,
                    fixtures_manifest=custom_manifest,
                    fixtures_base_dir=tmp_path,
                    allow_synthetic_sample=True,
                )
            edges_disk_path.write_bytes(orig_edges_bytes)

            # 4. Tamper with config_sha256 vs on-disk config file -> MUST FAIL
            bad_cfg_rec = copy.deepcopy(rec)
            bad_cfg_rec["workload_identity"]["config_sha256"] = "b" * 64
            with self.assertRaises(self.val_mod.RecordValidationError):
                self.val_mod.validate_sc05_v2_record(
                    record=bad_cfg_rec,
                    schema=self.schema,
                    fixtures_manifest=custom_manifest,
                    fixtures_base_dir=tmp_path,
                    allow_synthetic_sample=True,
                )

            # 5. Tamper with manifest recipe config without updating workload_instance_id -> MUST FAIL
            tampered_manifest = copy.deepcopy(custom_manifest)
            for k in tampered_manifest["workloads"]:
                tampered_manifest["workloads"][k]["config"]["tau_ms"] = 99.0
            with self.assertRaises(self.val_mod.RecordValidationError):
                self.val_mod.validate_sc05_v2_record(
                    record=rec,
                    schema=self.schema,
                    fixtures_manifest=tampered_manifest,
                    fixtures_base_dir=tmp_path,
                    allow_synthetic_sample=True,
                )

            # 6. Delete fixture file on disk -> MUST FAIL in default mode
            edges_disk_path.unlink()
            with self.assertRaises(self.val_mod.RecordValidationError):
                self.val_mod.validate_sc05_v2_record(
                    record=rec,
                    schema=self.schema,
                    fixtures_manifest=custom_manifest,
                    fixtures_base_dir=tmp_path,
                    allow_synthetic_sample=True,
                )

    def test_fixed_dt_native_model_passes_aligned_with_tolerance(self) -> None:
        """
        Verify that a legitimate fixed-dt native simulator record (e.g. NEST / Brian2 grid LIF
        with dt_ms=0.1, adapted_input_sha256, full 40-char commit SHA, and documented error
        metrics) passes under `Tier-B-observationally-aligned` / `aligned-with-tolerance`.
        """
        aligned = copy.deepcopy(self.sample)
        aligned["synthetic_validation_sample"] = False
        aligned["synthetic_notice"] = None
        aligned["git_provenance"]["commit_sha"] = "b91c9faa81287e570e66c45a117e34623b13c110"
        aligned["backend_provenance"]["backend_name"] = "NEST"
        aligned["backend_provenance"]["backend_variant"] = "iaf_psc_delta_grid"
        aligned["backend_provenance"]["version_tag"] = "3.10"
        aligned["backend_provenance"]["license"] = "GPL-2.0-or-later"
        aligned["workload_identity"]["adapted_input_sha256"] = "1" * 64
        aligned["model_semantics"]["comparison_tier"] = "Tier-B-observationally-aligned"
        aligned["model_semantics"]["semantic_classification"] = "aligned-with-tolerance"
        aligned["model_semantics"]["solver_kind"] = "fixed_step_exact_propagator_grid"
        aligned["model_semantics"]["dt_ms"] = 0.1
        aligned["model_semantics"]["delay_rounding_policy"] = "grid_nearest_multiple_of_dt_0.1ms"
        aligned["scale_and_activity_metrics"]["neuron_integration_steps"] = 128000
        aligned["validation_and_fidelity"]["spike_precision"] = 0.98
        aligned["validation_and_fidelity"]["spike_recall"] = 0.98
        aligned["validation_and_fidelity"]["spike_time_mae_ms"] = 0.042
        aligned["validation_and_fidelity"]["spike_time_p95_ms"] = 0.095
        aligned["validation_and_fidelity"]["membrane_rmse_mv"] = 0.0031

        # Update missing_or_unsupported_fields since dt_ms and neuron_integration_steps are now populated
        del aligned["missing_or_unsupported_fields"]["model_semantics.dt_ms"]
        del aligned["missing_or_unsupported_fields"]["scale_and_activity_metrics.neuron_integration_steps"]

        summary = self.val_mod.validate_sc05_v2_record(
            record=aligned,
            schema=self.schema,
            fixtures_manifest=self.manifest,
            allow_synthetic_sample=False,
        )
        self.assertTrue(summary["valid"])
        self.assertFalse(summary["synthetic_validation_sample"])
        self.assertEqual(summary["semantic_classification"], "aligned-with-tolerance")

    def test_reject_undocumented_null_field(self) -> None:
        bad = copy.deepcopy(self.sample)
        del bad["missing_or_unsupported_fields"]["model_semantics.dt_ms"]
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )

    def test_reject_mismatched_fixture_hash_for_known_workload_instance(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["workload_identity"]["edges_fixture_sha256"] = "a" * 64
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )

    def test_reject_fixed_dt_claiming_equivalent_exact(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["model_semantics"]["dt_ms"] = 0.1
        del bad["missing_or_unsupported_fields"]["model_semantics.dt_ms"]
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )

    def test_reject_false_exp0004_parity_claim(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["validation_and_fidelity"]["parity_claim_with_exp0004"] = True
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )

    def test_reject_allocation_only_claimed_as_active_workload(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["scale_and_activity_metrics"]["active_neurons_count"] = 0
        bad["scale_and_activity_metrics"]["committed_events"] = 0
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )

    def test_reject_ross_without_rollback_metrics(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["backend_provenance"]["backend_name"] = "ROSS"
        bad["model_semantics"]["semantic_classification"] = "native-only"
        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=bad,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=True,
            )


if __name__ == "__main__":
    unittest.main()
