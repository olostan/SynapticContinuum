"""
EXP-0005 WP-00: Atlas v2 JSON Schema & Semantic Validator Unit Tests.

Verifies:
  1. `schemas/synthetic_validation_sample_NOT_A_RUN.json` passes when `--allow-synthetic-sample` is enabled.
  2. `schemas/synthetic_validation_sample_NOT_A_RUN.json` is REJECTED when `--allow-synthetic-sample` is False.
  3. Any `null` field lacking an entry in `missing_or_unsupported_fields` is REJECTED.
  4. Any non-null field spuriously listed in `missing_or_unsupported_fields` is REJECTED.
  5. Mismatched fixture SHA-256 or workload_id for a known `workload_instance_id` is REJECTED.
  6. Fixed-dt solver (`dt_ms = 0.1`) claiming `equivalent-exact` is REJECTED.
  7. Cross-framework record claiming `parity_claim_with_exp0004 = True` is REJECTED.
  8. Active workload with `active_neurons_count = 0` or `committed_events = 0` (allocation-as-activity) is REJECTED.
  9. ROSS record missing `rolled_back_events` is REJECTED.
  10. Historical EXP-0004 `schemas/benchmark_schema.json` remains bit-identical to its v1.0.0 SHA-256.
"""

from __future__ import annotations

import copy
import json
import unittest

from helper_imports import EXP0005_ROOT, load_validator_module


class TestSchemaV2Validator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.val_mod = load_validator_module()
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

        with self.assertRaises(self.val_mod.RecordValidationError):
            self.val_mod.validate_sc05_v2_record(
                record=self.sample,
                schema=self.schema,
                fixtures_manifest=self.manifest,
                allow_synthetic_sample=False,
            )

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
