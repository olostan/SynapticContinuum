"""
EXP-0005 WP-00: Adversarial Falsification Unit Tests.

Explicitly tests that the independent mathematical oracle and fixture loaders
reject or falsify:
  1. Zero or negative synaptic delay (`delay_ms <= 0` -> `CausalityViolationError`).
  2. Negative event timestamp (`t_ms < 0` -> `CausalityViolationError`).
  3. Out-of-order / backward input timestamps (`t_{k+1} < t_k` -> `CausalityViolationError`).
  4. Corrupted fixture SHA-256 digest (`ChecksumMismatchError`).
  5. Altered synaptic weight on Golden B (`w = 0.35 mV` instead of `0.40 mV` -> falsifies spike at 4 ms).
  6. Mixed / wrong physical units (`s` instead of `ms`, or `V` instead of `mV` -> `UnitMismatchError`).
  7. Rounded / quantized arrival timestamps perturbing subthreshold trajectory beyond 1e-10 tolerance.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from helper_imports import EXP0005_ROOT, load_oracle_module


class TestFalsificationAdversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle_mod = load_oracle_module()
        cls.fixtures_dir = EXP0005_ROOT / "fixtures"

    def test_reject_non_positive_synaptic_delay(self) -> None:
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=2)
        with self.assertRaises(self.oracle_mod.CausalityViolationError):
            self.oracle_mod.AnalyticLIFOracle(
                params=params,
                edges=[self.oracle_mod.DirectedEdge(src_id=0, dst_id=1, delay_ms=0.0, weight_mv=0.5)],
            )
        with self.assertRaises(self.oracle_mod.CausalityViolationError):
            self.oracle_mod.AnalyticLIFOracle(
                params=params,
                edges=[self.oracle_mod.DirectedEdge(src_id=0, dst_id=1, delay_ms=-1.0, weight_mv=0.5)],
            )

    def test_reject_negative_or_backward_event_timestamps(self) -> None:
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=1)
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)

        # Negative event time
        with self.assertRaises(self.oracle_mod.CausalityViolationError):
            oracle.run(
                external_events=[
                    self.oracle_mod.ImpulseEvent(t_ms=-0.1, target_id=0, src_id=-1, ordinal=0, weight_mv=0.5)
                ],
                horizon_ms=10.0,
            )

        # Backward timestamp order in external stream
        with self.assertRaises(self.oracle_mod.CausalityViolationError):
            oracle.run(
                external_events=[
                    self.oracle_mod.ImpulseEvent(t_ms=3.0, target_id=0, src_id=-1, ordinal=0, weight_mv=0.4),
                    self.oracle_mod.ImpulseEvent(t_ms=1.0, target_id=0, src_id=-1, ordinal=1, weight_mv=0.4),
                ],
                horizon_ms=10.0,
            )

    def test_reject_corrupted_sha256_checksum(self) -> None:
        fpath = self.fixtures_dir / "golden_a_passive_leak.json"
        corrupted_sha = "0" * 64
        with self.assertRaises(self.oracle_mod.ChecksumMismatchError):
            self.oracle_mod.verify_file_sha256(fpath, corrupted_sha)

    def test_reject_mixed_or_wrong_units(self) -> None:
        with self.assertRaises(self.oracle_mod.UnitMismatchError):
            self.oracle_mod.AnalyticLIFParams(num_nodes=1, time_unit="s", voltage_unit="mV").validate()
        with self.assertRaises(self.oracle_mod.UnitMismatchError):
            self.oracle_mod.AnalyticLIFParams(num_nodes=1, time_unit="ms", voltage_unit="V").validate()

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_csv = Path(tmpdir) / "bad_units_edges.csv"
            bad_csv.write_text("src_id,dst_id,delay_s,weight_V\n0,1,0.002,0.001\n", encoding="utf-8")
            with self.assertRaises(self.oracle_mod.UnitMismatchError):
                self.oracle_mod.load_edges_csv(bad_csv)

    def test_perturbed_weight_falsifies_golden_b_spike(self) -> None:
        # Perturbing weight from 0.40 mV to 0.35 mV prevents threshold crossing at t=4 ms
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=1, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)
        perturbed_events = [
            self.oracle_mod.ImpulseEvent(t_ms=1.0, target_id=0, src_id=-1, ordinal=0, weight_mv=0.35),
            self.oracle_mod.ImpulseEvent(t_ms=3.0, target_id=0, src_id=-1, ordinal=1, weight_mv=0.35),
            self.oracle_mod.ImpulseEvent(t_ms=4.0, target_id=0, src_id=-1, ordinal=2, weight_mv=0.35),
        ]
        res = oracle.run(external_events=perturbed_events, horizon_ms=10.0)
        self.assertEqual(len(res.spikes), 0, "Perturbed weight w=0.35 mV must not cross threshold")
        self.assertLess(res.event_log[-1].v_pre_reset_mv, 1.0)

    def test_perturbed_timestamp_rounding_shifts_potential_beyond_tolerance(self) -> None:
        # If an adapter quantizes t=1.04 ms to t=1.00 ms on a dt=0.1 ms grid, V(3.0-) shifts
        # by more than the 1e-10 analytic oracle tolerance.
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=1, tau_ms=10.0, v_th_mv=1.0)
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)
        exact_res = oracle.run(
            external_events=[
                self.oracle_mod.ImpulseEvent(t_ms=1.04, target_id=0, src_id=-1, ordinal=0, weight_mv=0.4)
            ],
            horizon_ms=5.0,
            sample_times_ms=[3.0],
        )
        rounded_res = oracle.run(
            external_events=[
                self.oracle_mod.ImpulseEvent(t_ms=1.00, target_id=0, src_id=-1, ordinal=0, weight_mv=0.4)
            ],
            horizon_ms=5.0,
            sample_times_ms=[3.0],
        )
        diff = abs(exact_res.sampled_potentials_mv[3.0][0] - rounded_res.sampled_potentials_mv[3.0][0])
        self.assertGreater(diff, 1e-4, "Grid rounding error must be detectable well above 1e-10 analytic tolerance")
        self.assertNotEqual(exact_res.output_trace_sha256, rounded_res.output_trace_sha256)


if __name__ == "__main__":
    unittest.main()
