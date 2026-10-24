#!/usr/bin/env python3
"""
EXP-0005 WP-00: Independent Analytic Delta-LIF Mathematical Oracle.

Pure Python 64-bit IEEE-754 standard-library implementation of the canonical
continuous-time leaky integrate-and-fire (delta-LIF) equation with instantaneous
weighted arrivals, refractory clamping, threshold crossing, reset, and strictly
positive axonal delays.

ZERO imports or code reuse from NEST, Brian 2, Arbor, ROSS, or EXP-0001..0004 engines.

Canonical Equations & Semantics (SPEC.md & WORKLOADS.md):
  - Units: time in `ms`, voltage/weight in `mV`
  - Subthreshold evolution outside refractory:
      dV/dt = -(V - E_L) / tau_ms
      V(t^-) = E_L + (V(t_last^+) - E_L) * exp(-(t - t_last) / tau_ms)
  - Event tie-breaking priority key (exact unrounded IEEE-754 float64 timestamp):
      (float(t_ms), target_id, src_id, ordinal)
    Because heap ordering uses the exact unrounded `float(t_ms)`, heap priority
    order and causality monotonicity checks (`dt >= 0`, `t_committed >= last_committed_t`)
    are 100% consistent even for near-simultaneous events separated by `< 1e-12 ms`.
  - Refractory interval policy (half-open):
      [t_spike, t_spike + refractory_ms)
      An arrival at `t < refractory_until_ms` is clamped to `v_reset_mv` and cannot fire.
      An arrival at `t >= refractory_until_ms` is integrated normally.
  - Threshold crossing with explicit analytic tolerance `threshold_tol_mv = 1e-10`:
      If `V(t^-) + weight_mV >= v_th_mv - threshold_tol_mv`, neuron emits a spike at `t`,
      resets `V(t^+) = v_reset_mv`, sets `refractory_until_ms = t + refractory_ms`,
      and schedules outgoing deliveries at `t + delay_ms` (`delay_ms > 0`).
"""

from __future__ import annotations

import csv
import hashlib
import heapq
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class OracleContractError(ValueError):
    """Base error for mathematical contract or fixture integrity violations."""


class CausalityViolationError(OracleContractError):
    """Raised on negative time steps, backward timestamps, or non-positive synaptic delays."""


class UnitMismatchError(OracleContractError):
    """Raised when units are missing, mixed (e.g. seconds instead of ms), or invalid."""


class ChecksumMismatchError(OracleContractError):
    """Raised when fixture bytes do not match their expected SHA-256 digest."""


@dataclass(frozen=True)
class DirectedEdge:
    src_id: int
    dst_id: int
    delay_ms: float
    weight_mv: float


@dataclass(frozen=True)
class ImpulseEvent:
    t_ms: float
    target_id: int
    src_id: int
    ordinal: int
    weight_mv: float

    def sort_key(self) -> Tuple[float, int, int, int]:
        """Exact unrounded IEEE-754 float64 timestamp + deterministic tie-break tuple."""
        return (float(self.t_ms), int(self.target_id), int(self.src_id), int(self.ordinal))


@dataclass
class EventStepRecord:
    t_ms: float
    target_id: int
    src_id: int
    ordinal: int
    weight_mv: float
    v_minus_mv: float
    v_pre_reset_mv: float
    v_plus_mv: float
    was_refractory: bool
    spiked: bool


@dataclass
class OracleSimulationResult:
    num_nodes: int
    horizon_ms: float
    spikes: List[Tuple[float, int]]
    event_log: List[EventStepRecord]
    final_potentials_mv: List[float]
    sampled_potentials_mv: Dict[float, List[float]]
    active_neurons_count: int
    external_events_injected: int
    synapse_deliveries: int
    committed_events: int
    output_trace_sha256: str


@dataclass
class AnalyticLIFParams:
    num_nodes: int = 1
    tau_ms: float = 10.0
    e_l_mv: float = 0.0
    v_reset_mv: float = 0.0
    v_th_mv: float = 1.0
    refractory_ms: float = 2.0
    threshold_tol_mv: float = 1e-10
    v_init_mv: Optional[List[float]] = None
    time_unit: str = "ms"
    voltage_unit: str = "mV"

    def validate(self) -> None:
        if self.time_unit != "ms":
            raise UnitMismatchError(f"Expected time_unit='ms', got '{self.time_unit}'")
        if self.voltage_unit != "mV":
            raise UnitMismatchError(f"Expected voltage_unit='mV', got '{self.voltage_unit}'")
        if self.num_nodes < 1:
            raise OracleContractError(f"num_nodes must be >= 1, got {self.num_nodes}")
        if self.tau_ms <= 0.0 or not math.isfinite(self.tau_ms):
            raise OracleContractError(f"tau_ms must be finite and > 0, got {self.tau_ms}")
        if self.refractory_ms < 0.0 or not math.isfinite(self.refractory_ms):
            raise OracleContractError(f"refractory_ms must be finite and >= 0, got {self.refractory_ms}")
        if self.v_th_mv <= self.v_reset_mv:
            raise OracleContractError(
                f"v_th_mv ({self.v_th_mv}) must be strictly greater than v_reset_mv ({self.v_reset_mv})"
            )
        if self.v_init_mv is not None and len(self.v_init_mv) != self.num_nodes:
            raise OracleContractError(
                f"v_init_mv length ({len(self.v_init_mv)}) != num_nodes ({self.num_nodes})"
            )


def verify_file_sha256(path: Path, expected_sha256: str) -> bytes:
    """Read file bytes and verify exact SHA-256 digest before parsing."""
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise ChecksumMismatchError(
            f"SHA-256 mismatch for {path.name}: expected {expected_sha256}, got {actual}"
        )
    return raw


def load_edges_csv(path: Path, expected_sha256: Optional[str] = None) -> List[DirectedEdge]:
    raw = verify_file_sha256(path, expected_sha256) if expected_sha256 else path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    reader = csv.DictReader(lines)
    required = ["src_id", "dst_id", "delay_ms", "weight_mV"]
    if reader.fieldnames != required:
        if reader.fieldnames and any("_s" in col or "_V" in col for col in reader.fieldnames):
            raise UnitMismatchError(
                f"Mixed or non-canonical column units in {path.name}: {reader.fieldnames} (expected {required})"
            )
        raise OracleContractError(f"Invalid edge CSV header in {path.name}: {reader.fieldnames}")

    edges: List[DirectedEdge] = []
    for row in reader:
        src = int(row["src_id"])
        dst = int(row["dst_id"])
        delay = float(row["delay_ms"])
        weight = float(row["weight_mV"])
        if delay <= 0.0 or not math.isfinite(delay):
            raise CausalityViolationError(
                f"Non-positive or non-finite synaptic delay_ms={delay} on edge {src}->{dst}"
            )
        edges.append(DirectedEdge(src_id=src, dst_id=dst, delay_ms=delay, weight_mv=weight))
    return edges


def load_events_csv(path: Path, expected_sha256: Optional[str] = None) -> List[ImpulseEvent]:
    raw = verify_file_sha256(path, expected_sha256) if expected_sha256 else path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    reader = csv.DictReader(lines)
    required = ["t_ms", "target_id", "src_id", "ordinal", "weight_mV"]
    if reader.fieldnames != required:
        if reader.fieldnames and any("_s" in col or "_V" in col for col in reader.fieldnames):
            raise UnitMismatchError(
                f"Mixed or non-canonical column units in {path.name}: {reader.fieldnames} (expected {required})"
            )
        raise OracleContractError(f"Invalid event CSV header in {path.name}: {reader.fieldnames}")

    events: List[ImpulseEvent] = []
    prev_time = -1.0
    for row in reader:
        t_ms = float(row["t_ms"])
        target_id = int(row["target_id"])
        src_id = int(row["src_id"])
        ordinal = int(row["ordinal"])
        weight = float(row["weight_mV"])
        if t_ms < 0.0 or not math.isfinite(t_ms):
            raise CausalityViolationError(f"Negative or non-finite event timestamp t_ms={t_ms}")
        if t_ms < prev_time:
            raise CausalityViolationError(
                f"Backward event timestamp order in input stream: {t_ms} < {prev_time}"
            )
        prev_time = t_ms
        events.append(
            ImpulseEvent(
                t_ms=t_ms,
                target_id=target_id,
                src_id=src_id,
                ordinal=ordinal,
                weight_mv=weight,
            )
        )
    return events


def compute_trace_sha256(
    spikes: List[Tuple[float, int]],
    final_potentials_mv: List[float],
) -> str:
    """Compute canonical UTF-8 JSON SHA-256 digest of committed spikes and final potentials."""
    payload = {
        "spikes": [[round(t, 12), int(node)] for t, node in spikes],
        "final_potentials_mv": [round(v, 12) for v in final_potentials_mv],
    }
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AnalyticLIFOracle:
    """
    Reference scalar and network continuous-time delta-LIF mathematical oracle.
    """

    def __init__(
        self,
        params: AnalyticLIFParams,
        edges: Optional[List[DirectedEdge]] = None,
    ) -> None:
        params.validate()
        self.params = params
        self.edges: List[DirectedEdge] = list(edges) if edges else []
        self.adj: Dict[int, List[DirectedEdge]] = {i: [] for i in range(params.num_nodes)}

        for e in self.edges:
            if not (0 <= e.src_id < params.num_nodes and 0 <= e.dst_id < params.num_nodes):
                raise OracleContractError(
                    f"Edge ({e.src_id}->{e.dst_id}) out of node range [0, {params.num_nodes})"
                )
            if e.src_id == e.dst_id:
                raise OracleContractError(f"Self-edge ({e.src_id}->{e.dst_id}) forbidden in canonical oracle")
            if e.delay_ms <= 0.0 or not math.isfinite(e.delay_ms):
                raise CausalityViolationError(
                    f"Strictly positive delay_ms required on edge {e.src_id}->{e.dst_id}, got {e.delay_ms}"
                )
            self.adj[e.src_id].append(e)

        for u in self.adj:
            self.adj[u].sort(key=lambda e: (e.dst_id, float(e.delay_ms), float(e.weight_mv)))

    def closed_form_decay(self, v_start_mv: float, dt_ms: float) -> float:
        """
        Analytic passive leak:
          V(t + dt) = E_L + (V(t) - E_L) * exp(-dt / tau_ms)
        """
        if dt_ms < 0.0:
            raise CausalityViolationError(f"Cannot extrapolate backward in time: dt_ms={dt_ms}")
        if dt_ms == 0.0:
            return float(v_start_mv)
        e_l = self.params.e_l_mv
        return float(e_l + (v_start_mv - e_l) * math.exp(-dt_ms / self.params.tau_ms))

    def run(
        self,
        external_events: List[ImpulseEvent],
        horizon_ms: float,
        sample_times_ms: Optional[List[float]] = None,
    ) -> OracleSimulationResult:
        if horizon_ms < 0.0 or not math.isfinite(horizon_ms):
            raise CausalityViolationError(f"Invalid simulation horizon_ms={horizon_ms}")

        n = self.params.num_nodes
        v_mv: List[float] = (
            [float(x) for x in self.params.v_init_mv]
            if self.params.v_init_mv is not None
            else [self.params.e_l_mv for _ in range(n)]
        )
        last_t_ms: List[float] = [0.0 for _ in range(n)]
        refractory_until_ms: List[float] = [-math.inf for _ in range(n)]

        # Validate input event ordering and non-negative timestamps before scheduling
        prev_in_t = -1.0
        for ev in external_events:
            if ev.t_ms < 0.0 or not math.isfinite(ev.t_ms):
                raise CausalityViolationError(f"Invalid negative/non-finite event timestamp t_ms={ev.t_ms}")
            if ev.t_ms < prev_in_t:
                raise CausalityViolationError(
                    f"Input event stream violates timestamp monotonicity: {ev.t_ms} < {prev_in_t}"
                )
            if not (0 <= ev.target_id < n):
                raise OracleContractError(f"Event target_id={ev.target_id} out of range [0, {n})")
            prev_in_t = ev.t_ms

        heap: List[Tuple[Tuple[float, int, int, int], ImpulseEvent]] = []
        next_ordinal = 0
        external_injected = 0
        for ev in external_events:
            if ev.t_ms <= horizon_ms:
                heapq.heappush(heap, (ev.sort_key(), ev))
                external_injected += 1
            next_ordinal = max(next_ordinal, ev.ordinal + 1)

        sorted_samples: List[float] = sorted(sample_times_ms) if sample_times_ms else []
        for st in sorted_samples:
            if st < 0.0 or st > horizon_ms:
                raise CausalityViolationError(f"Sample time {st} ms outside [0, {horizon_ms}]")
        sample_idx = 0
        sampled_potentials: Dict[float, List[float]] = {}

        def _advance_all_to(t_target: float) -> None:
            for i in range(n):
                dt = t_target - last_t_ms[i]
                if dt < 0.0:
                    raise CausalityViolationError(
                        f"Backward state advance on node {i}: {t_target} < {last_t_ms[i]}"
                    )
                if dt > 0.0:
                    if t_target < refractory_until_ms[i]:
                        v_mv[i] = self.params.v_reset_mv
                    elif last_t_ms[i] < refractory_until_ms[i] <= t_target:
                        dt_active = t_target - refractory_until_ms[i]
                        v_mv[i] = self.closed_form_decay(self.params.v_reset_mv, dt_active)
                    else:
                        v_mv[i] = self.closed_form_decay(v_mv[i], dt)
                    last_t_ms[i] = t_target

        spikes: List[Tuple[float, int]] = []
        event_log: List[EventStepRecord] = []
        active_nodes: set[int] = set()
        synapse_deliveries = 0
        committed_events = 0
        last_committed_t = 0.0

        while heap:
            _, ev = heapq.heappop(heap)
            if ev.t_ms > horizon_ms:
                continue

            # Capture any requested sample times strictly before this event timestamp
            while sample_idx < len(sorted_samples) and sorted_samples[sample_idx] < ev.t_ms:
                st = sorted_samples[sample_idx]
                _advance_all_to(st)
                sampled_potentials[st] = list(v_mv)
                sample_idx += 1

            if ev.t_ms < last_committed_t:
                raise CausalityViolationError(
                    f"Committed event out of causal order: {ev.t_ms} < {last_committed_t}"
                )
            last_committed_t = ev.t_ms
            committed_events += 1
            if ev.src_id >= 0:
                synapse_deliveries += 1

            u = ev.target_id
            dt = ev.t_ms - last_t_ms[u]
            if dt < 0.0:
                raise CausalityViolationError(f"Negative dt={dt} on neuron {u}")

            # Advance target neuron u to ev.t_ms
            if ev.t_ms < refractory_until_ms[u]:
                v_minus = self.params.v_reset_mv
                was_ref = True
            else:
                was_ref = False
                if last_t_ms[u] < refractory_until_ms[u] <= ev.t_ms:
                    v_minus = self.closed_form_decay(
                        self.params.v_reset_mv, ev.t_ms - refractory_until_ms[u]
                    )
                else:
                    v_minus = self.closed_form_decay(v_mv[u], dt)

            last_t_ms[u] = ev.t_ms
            active_nodes.add(u)

            if was_ref:
                v_pre_reset = self.params.v_reset_mv
                v_plus = self.params.v_reset_mv
                spiked = False
            else:
                v_pre_reset = v_minus + ev.weight_mv
                if v_pre_reset >= self.params.v_th_mv - self.params.threshold_tol_mv:
                    spiked = True
                    v_plus = self.params.v_reset_mv
                    refractory_until_ms[u] = ev.t_ms + self.params.refractory_ms
                    spikes.append((ev.t_ms, u))
                    for edge in self.adj[u]:
                        arr_t = ev.t_ms + edge.delay_ms
                        if arr_t <= horizon_ms:
                            child = ImpulseEvent(
                                t_ms=arr_t,
                                target_id=edge.dst_id,
                                src_id=u,
                                ordinal=next_ordinal,
                                weight_mv=edge.weight_mv,
                            )
                            next_ordinal += 1
                            heapq.heappush(heap, (child.sort_key(), child))
                else:
                    spiked = False
                    v_plus = v_pre_reset

            v_mv[u] = v_plus
            event_log.append(
                EventStepRecord(
                    t_ms=ev.t_ms,
                    target_id=u,
                    src_id=ev.src_id,
                    ordinal=ev.ordinal,
                    weight_mv=ev.weight_mv,
                    v_minus_mv=v_minus,
                    v_pre_reset_mv=v_pre_reset,
                    v_plus_mv=v_plus,
                    was_refractory=was_ref,
                    spiked=spiked,
                )
            )

        # Capture remaining sample times up to horizon_ms
        while sample_idx < len(sorted_samples):
            st = sorted_samples[sample_idx]
            _advance_all_to(st)
            sampled_potentials[st] = list(v_mv)
            sample_idx += 1

        _advance_all_to(horizon_ms)
        trace_sha = compute_trace_sha256(spikes, v_mv)

        return OracleSimulationResult(
            num_nodes=n,
            horizon_ms=horizon_ms,
            spikes=spikes,
            event_log=event_log,
            final_potentials_mv=list(v_mv),
            sampled_potentials_mv=sampled_potentials,
            active_neurons_count=len(active_nodes),
            external_events_injected=external_injected,
            synapse_deliveries=synapse_deliveries,
            committed_events=committed_events,
            output_trace_sha256=trace_sha,
        )
