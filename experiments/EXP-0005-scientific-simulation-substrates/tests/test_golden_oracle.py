"""
EXP-0005 WP-00: Golden A, B, C1, C2 Hand-Verified Mathematical Oracle Unit Tests.

Verifies:
  1. Golden A (`sc05/analytic-leak/v1`): V(t) = 0.8 * exp(-t/10) at t=0, 10, 20 ms to <= 1e-12 mV.
  2. Golden B (`sc05/analytic-threshold/v1`): 3 arrivals at 1, 3, 4 ms (w=0.4 mV);
     V(3+) ≈ 0.727492301231 mV (no spike); V_pre(4+) ≈ 1.058262171219 mV -> exactly 1 spike at 4.0 ms,
     reset to 0.0 mV, refractory until 6.0 ms; verified to <= 1e-10 mV.
  3. Golden C1 (`sc05/replay/v1`): causal chain A->B->C (0->1->2) with delay 2.0 ms per link;
     external input at 1.0 ms produces earliest deliveries at B (3.0 ms) and C (5.0 ms).
  4. Golden C2 (`sc05/replay/v1`): simultaneous arrivals at t=2.0 ms sorted by
     (t_ms, target_id, src_id, ordinal), refractory clamping inside [2.0, 4.0) ms,
     and exact boundary release at t = 4.0 ms.
  5. Pilot disconnected and modular N=128, D=4 fixtures execute deterministically on the oracle.
"""

from __future__ import annotations

import json
import math
import unittest

from helper_imports import EXP0005_ROOT, load_oracle_module


class TestGoldenOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle_mod = load_oracle_module()
        cls.fixtures_dir = EXP0005_ROOT / "fixtures"
        cls.manifest = json.loads((cls.fixtures_dir / "manifest_sha256.json").read_text(encoding="utf-8"))

    def test_golden_a_passive_leak_1e12(self) -> None:
        fpath = self.fixtures_dir / "golden_a_passive_leak.json"
        expected_sha = self.manifest["files"]["golden_a_passive_leak.json"]["sha256"]
        raw = self.oracle_mod.verify_file_sha256(fpath, expected_sha)
        data = json.loads(raw.decode("utf-8"))

        np_cfg = data["neuron_parameters"]
        params = self.oracle_mod.AnalyticLIFParams(
            num_nodes=np_cfg["num_nodes"],
            tau_ms=np_cfg["tau_ms"],
            e_l_mv=np_cfg["e_l_mv"],
            v_reset_mv=np_cfg["v_reset_mv"],
            v_th_mv=np_cfg["v_th_mv"],
            refractory_ms=np_cfg["refractory_ms"],
            v_init_mv=np_cfg["v_init_mv"],
        )
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)
        res = oracle.run(external_events=[], horizon_ms=20.0, sample_times_ms=[0.0, 10.0, 20.0])

        # Hand-derived closed-form values
        hand_v0 = 0.8
        hand_v10 = 0.29430355293715387
        hand_v20 = 0.10826822658929016

        self.assertEqual(len(res.spikes), 0)
        self.assertAlmostEqual(res.sampled_potentials_mv[0.0][0], hand_v0, delta=1e-12)
        self.assertAlmostEqual(res.sampled_potentials_mv[10.0][0], hand_v10, delta=1e-12)
        self.assertAlmostEqual(res.sampled_potentials_mv[20.0][0], hand_v20, delta=1e-12)
        self.assertAlmostEqual(res.final_potentials_mv[0], hand_v20, delta=1e-12)

    def test_golden_b_threshold_reset_1e10(self) -> None:
        fpath = self.fixtures_dir / "golden_b_threshold_reset.json"
        expected_sha = self.manifest["files"]["golden_b_threshold_reset.json"]["sha256"]
        raw = self.oracle_mod.verify_file_sha256(fpath, expected_sha)
        data = json.loads(raw.decode("utf-8"))

        np_cfg = data["neuron_parameters"]
        params = self.oracle_mod.AnalyticLIFParams(
            num_nodes=np_cfg["num_nodes"],
            tau_ms=np_cfg["tau_ms"],
            e_l_mv=np_cfg["e_l_mv"],
            v_reset_mv=np_cfg["v_reset_mv"],
            v_th_mv=np_cfg["v_th_mv"],
            refractory_ms=np_cfg["refractory_ms"],
            threshold_tol_mv=np_cfg["threshold_tolerance_mv"],
            v_init_mv=np_cfg["v_init_mv"],
        )
        events = [
            self.oracle_mod.ImpulseEvent(
                t_ms=ev["t_ms"],
                target_id=ev["target_id"],
                src_id=ev["src_id"],
                ordinal=ev["ordinal"],
                weight_mv=ev["weight_mV"],
            )
            for ev in data["external_events"]
        ]
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)
        res = oracle.run(external_events=events, horizon_ms=10.0)

        # Verify exactly one spike at t = 4.0 ms
        self.assertEqual(res.spikes, [(4.0, 0)])
        self.assertEqual(len(res.event_log), 3)

        # Hand-calculated intermediate values (IEEE-754 64-bit):
        # V(1+) = 0.4
        # V(3-) = 0.4 * exp(-0.2) = 0.32749230123119274
        # V(3+) = 0.7274923012311927
        # V(4-) = V(3+) * exp(-0.1) = 0.6582622554870710
        # V_pre(4+) = V(4-) + 0.4 = 1.0582622554870710
        hand_v1_plus = 0.4
        hand_v3_minus = 0.32749230123119274
        hand_v3_plus = 0.7274923012311927
        hand_v4_minus = 0.6582622554870710
        hand_v4_pre_reset = 1.0582622554870710

        step1, step2, step3 = res.event_log
        self.assertAlmostEqual(step1.v_plus_mv, hand_v1_plus, delta=1e-10)
        self.assertFalse(step1.spiked)

        self.assertAlmostEqual(step2.v_minus_mv, hand_v3_minus, delta=1e-10)
        self.assertAlmostEqual(step2.v_plus_mv, hand_v3_plus, delta=1e-10)
        self.assertFalse(step2.spiked)

        self.assertAlmostEqual(step3.v_minus_mv, hand_v4_minus, delta=1e-10)
        self.assertAlmostEqual(step3.v_pre_reset_mv, hand_v4_pre_reset, delta=1e-10)
        self.assertAlmostEqual(step3.v_plus_mv, 0.0, delta=1e-12)
        self.assertTrue(step3.spiked)

    def test_golden_c1_causal_chain_delays(self) -> None:
        edges_path = self.fixtures_dir / "golden_c_causal_chain_edges.csv"
        events_path = self.fixtures_dir / "golden_c_causal_chain_events.csv"
        edges = self.oracle_mod.load_edges_csv(
            edges_path, self.manifest["files"]["golden_c_causal_chain_edges.csv"]["sha256"]
        )
        events = self.oracle_mod.load_events_csv(
            events_path, self.manifest["files"]["golden_c_causal_chain_events.csv"]["sha256"]
        )

        params = self.oracle_mod.AnalyticLIFParams(num_nodes=3, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges)
        res = oracle.run(external_events=events, horizon_ms=10.0)

        # A (0) spikes at 1.0 ms -> B (1) receives & spikes at 3.0 ms -> C (2) receives & spikes at 5.0 ms
        self.assertEqual(res.spikes, [(1.0, 0), (3.0, 1), (5.0, 2)])
        self.assertEqual(res.external_events_injected, 1)
        self.assertEqual(res.synapse_deliveries, 2)
        self.assertEqual(res.committed_events, 3)

    def test_golden_c2_simultaneous_arrivals_tie_break_and_refractory_clamp(self) -> None:
        events_path = self.fixtures_dir / "golden_c_tie_adversarial_events.csv"
        events = self.oracle_mod.load_events_csv(
            events_path, self.manifest["files"]["golden_c_tie_adversarial_events.csv"]["sha256"]
        )
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=1, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params)
        res = oracle.run(external_events=events, horizon_ms=6.0)

        # Event 0: (t=2.0, src=1, ord=0, w=0.6) -> V(2.0+) = 0.6 mV, no spike
        # Event 1: (t=2.0, src=2, ord=1, w=0.5) -> V_pre = 1.1 mV -> SPIKE at 2.0 ms, V(2.0+) = 0.0, ref until 4.0 ms
        # Event 2: (t=2.0, src=3, ord=2, w=1.5) -> arrives during refractory [2.0, 4.0) -> clamped to 0.0 mV, no second spike
        # Event 3: (t=3.5, src=-1, ord=3, w=0.9) -> arrives during refractory (3.5 < 4.0) -> clamped to 0.0 mV
        # Event 4: (t=4.0, src=-1, ord=4, w=0.5) -> arrives on boundary t == 4.0 ms -> active! V(4.0+) = 0.5 mV
        self.assertEqual(res.spikes, [(2.0, 0)])
        self.assertEqual([e.src_id for e in res.event_log[:3]], [1, 2, 3])
        self.assertFalse(res.event_log[0].was_refractory)
        self.assertTrue(res.event_log[1].spiked)
        self.assertTrue(res.event_log[2].was_refractory)
        self.assertFalse(res.event_log[2].spiked)
        self.assertEqual(res.event_log[2].v_plus_mv, 0.0)
        self.assertTrue(res.event_log[3].was_refractory)
        self.assertFalse(res.event_log[4].was_refractory)
        self.assertAlmostEqual(res.event_log[4].v_plus_mv, 0.5, delta=1e-12)

    def test_pilot_fixtures_deterministic_oracle_execution(self) -> None:
        for prefix in ("pilot_disconnected_n128_d4_s11", "pilot_modular_n128_d4_s11"):
            edges_f = f"{prefix}_edges.csv"
            events_f = f"{prefix}_events.csv"
            edges = self.oracle_mod.load_edges_csv(
                self.fixtures_dir / edges_f, self.manifest["files"][edges_f]["sha256"]
            )
            events = self.oracle_mod.load_events_csv(
                self.fixtures_dir / events_f, self.manifest["files"][events_f]["sha256"]
            )
            params = self.oracle_mod.AnalyticLIFParams(num_nodes=128, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
            oracle1 = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges)
            res1 = oracle1.run(external_events=events, horizon_ms=100.0)

            oracle2 = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges)
            res2 = oracle2.run(external_events=events, horizon_ms=100.0)

            self.assertEqual(res1.output_trace_sha256, res2.output_trace_sha256)
            self.assertGreater(res1.committed_events, 0)
            self.assertGreater(res1.active_neurons_count, 0)


if __name__ == "__main__":
    unittest.main()
