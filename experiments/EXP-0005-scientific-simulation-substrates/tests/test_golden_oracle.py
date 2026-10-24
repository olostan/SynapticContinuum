"""
EXP-0005 WP-00: Golden A, B, C1, C2 Hand-Verified Mathematical Oracle Unit Tests.

Verifies:
  1. Golden A (`sc05/analytic-leak/v1`): V(t) = 0.8 * exp(-t/10) at t=0, 10, 20 ms to <= 1e-12 mV.
  2. Golden B (`sc05/analytic-threshold/v1`): 3 arrivals at 1, 3, 4 ms (w=0.4 mV);
     V(3+) ≈ 0.727492301231 mV (no spike); V_pre(4+) ≈ 1.058262255487 mV -> exactly 1 spike at 4.0 ms,
     reset to 0.0 mV, refractory until 6.0 ms; verified to <= 1e-10 mV.
  3. Golden C1 (`sc05/replay/v1`): causal chain A->B->C (0->1->2) with delay 2.0 ms per link;
     external input at 1.0 ms produces earliest deliveries at B (3.0 ms) and C (5.0 ms).
  4. Golden C2 (`sc05/replay/v1`): simultaneous arrivals at t=2.0 ms sorted by
     (t_ms, target_id, src_id, ordinal), refractory clamping inside [2.0, 4.0) ms,
     and exact boundary release at t = 4.0 ms.
  5. Near-simultaneous timestamps (`dt < 1e-12 ms`) and same-time independent input/source tie-breaking
     order on unrounded IEEE-754 float64 timestamps without causality violation.
  6. Stratified pilot disconnected fixture (`pilot_disconnected_n128_d4_s11`) produces observed active
     neurons and committed events in ALL 4 disconnected modules, whereas the localized control
     (`pilot_disconnected_localized_n128_d4_s11`) produces activity only in Module 0.
"""

from __future__ import annotations

import json
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

        self.assertEqual(res.spikes, [(4.0, 0)])
        self.assertEqual(len(res.event_log), 3)

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

    def test_near_simultaneous_sub_1e12_timestamps_and_same_time_source_tie_order(self) -> None:
        """
        Verify that two events separated by < 1e-12 ms (e.g. 2.0 ms and 2.0 + 3e-13 ms)
        are ordered by their exact unrounded IEEE-754 float64 timestamps even when the
        earlier event has a larger target_id/src_id, preventing any spurious backward-time
        causality error that `round(t_ms, 12)` would have induced.
        Also verify that exact same-time arrivals from external (`src_id=-1`) and internal
        (`src_id >= 0`) sources execute in strict `(t_ms, target_id, src_id, ordinal)` order.
        """
        params = self.oracle_mod.AnalyticLIFParams(num_nodes=3, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
        # Edge 0 -> 1 with delay 1.0 + 3e-13 ms: when node 0 spikes at 1.0 ms, child arrives at 2.0 + 3e-13 ms
        edges = [
            self.oracle_mod.DirectedEdge(src_id=0, dst_id=1, delay_ms=1.0 + 3e-13, weight_mv=0.3),
        ]
        oracle = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges)
        external_events = [
            # Triggers spike on node 0 at t=1.0 ms -> schedules synaptic arrival at node 1 at t = 2.0 + 3e-13 ms
            self.oracle_mod.ImpulseEvent(t_ms=1.0, target_id=0, src_id=-1, ordinal=0, weight_mv=1.2),
            # Exact same time t=2.0 ms on node 1 from two sources (src=-1 vs src=2)
            self.oracle_mod.ImpulseEvent(t_ms=2.0, target_id=1, src_id=2, ordinal=2, weight_mv=0.25),
            self.oracle_mod.ImpulseEvent(t_ms=2.0, target_id=1, src_id=-1, ordinal=1, weight_mv=0.20),
            # External arrival on node 2 at t=2.0 ms (higher target_id=2, but strictly earlier than 2.0 + 3e-13 ms!)
            self.oracle_mod.ImpulseEvent(t_ms=2.0, target_id=2, src_id=-1, ordinal=3, weight_mv=0.40),
        ]
        # Sort external events by canonical sort_key before passing
        external_events.sort(key=lambda e: e.sort_key())
        res = oracle.run(external_events=external_events, horizon_ms=5.0)

        committed_keys = [(step.t_ms, step.target_id, step.src_id, step.ordinal) for step in res.event_log]
        # 1. t=1.0 on node 0
        # 2. t=2.0 on node 1, src=-1 (external comes before src=2 at exact same timestamp & target)
        # 3. t=2.0 on node 1, src=2
        # 4. t=2.0 on node 2, src=-1 (processed BEFORE t=2.0 + 3e-13 on node 1 because unrounded 2.0 < 2.0 + 3e-13)
        # 5. t=2.0 + 3e-13 on node 1, src=0
        self.assertEqual(len(committed_keys), 5)
        self.assertEqual(committed_keys[1][:3], (2.0, 1, -1))
        self.assertEqual(committed_keys[2][:3], (2.0, 1, 2))
        self.assertEqual(committed_keys[3][:3], (2.0, 2, -1))
        self.assertEqual(committed_keys[4][1:3], (1, 0))
        self.assertGreater(committed_keys[4][0], 2.0)

    def test_pilot_stratified_vs_localized_per_module_activity(self) -> None:
        """
        Verify that on the 4-module disconnected graph (N=128, 32 nodes/module):
          - `pilot_disconnected_n128_d4_s11` (stratified_modules) produces active neurons and
            committed events in ALL 4 modules.
          - `pilot_disconnected_localized_n128_d4_s11` (localized_first_module) produces active
            neurons and committed events ONLY in Module 0 (`[0, 32)`), with 0 events in Modules 1..3.
        """
        edges = self.oracle_mod.load_edges_csv(
            self.fixtures_dir / "pilot_disconnected_n128_d4_s11_edges.csv",
            self.manifest["files"]["pilot_disconnected_n128_d4_s11_edges.csv"]["sha256"],
        )
        strat_events = self.oracle_mod.load_events_csv(
            self.fixtures_dir / "pilot_disconnected_n128_d4_s11_events.csv",
            self.manifest["files"]["pilot_disconnected_n128_d4_s11_events.csv"]["sha256"],
        )
        loc_events = self.oracle_mod.load_events_csv(
            self.fixtures_dir / "pilot_disconnected_localized_n128_d4_s11_events.csv",
            self.manifest["files"]["pilot_disconnected_localized_n128_d4_s11_events.csv"]["sha256"],
        )

        params = self.oracle_mod.AnalyticLIFParams(num_nodes=128, tau_ms=10.0, v_th_mv=1.0, refractory_ms=2.0)
        strat_res = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges).run(
            external_events=strat_events, horizon_ms=100.0
        )
        loc_res = self.oracle_mod.AnalyticLIFOracle(params=params, edges=edges).run(
            external_events=loc_events, horizon_ms=100.0
        )

        strat_mod_events = {0: 0, 1: 0, 2: 0, 3: 0}
        strat_mod_active_nodes: Dict[int, set[int]] = {0: set(), 1: set(), 2: set(), 3: set()}
        for step in strat_res.event_log:
            m = step.target_id // 32
            strat_mod_events[m] += 1
            strat_mod_active_nodes[m].add(step.target_id)

        for m in range(4):
            self.assertGreaterEqual(
                strat_mod_events[m], 16, f"Module {m} must have >=16 committed events in stratified fixture"
            )
            self.assertGreater(
                len(strat_mod_active_nodes[m]), 0, f"Module {m} must have active neurons in stratified fixture"
            )

        loc_mod_events = {0: 0, 1: 0, 2: 0, 3: 0}
        for step in loc_res.event_log:
            loc_mod_events[step.target_id // 32] += 1
        self.assertGreater(loc_mod_events[0], 64)
        self.assertEqual(loc_mod_events[1], 0)
        self.assertEqual(loc_mod_events[2], 0)
        self.assertEqual(loc_mod_events[3], 0)


if __name__ == "__main__":
    unittest.main()
