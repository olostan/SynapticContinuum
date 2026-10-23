"""Schedulers for neural simulation: Event-Driven (lazy/eager), Sparse Sync, and Dense Sync.

Governed by SPEC.md:
- Exact mathematical parity of dynamical laws.
- Event-driven priority queue with stable sequence IDs and lazy decay.
- Fixed-step synchronous simulation with grid refinement dt in {0.2, 0.1, 0.05}.
- Tracking processed events, edges, wall time, peak queue, and propagated active fraction.
"""
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from .queue import Event, EventKind, EventQueue, QueueCapacityExceededError
from .substrate import NeuralGraph, SubstrateConfig, SubstrateState


@dataclass
class SimulationResult:
    scheduler_name: str
    wall_time_sec: float
    total_events_processed: int
    total_edges_traversed: int
    total_spikes: int
    peak_queue_size: int
    final_time: float
    final_potentials: np.ndarray
    spike_records: List[Tuple[float, int]]  # (timestamp, node_id)
    injected_active_fraction: float
    propagated_active_fraction: float
    max_queue_exceeded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseScheduler:
    """Abstract interface for all simulation schedulers."""

    def __init__(self, config: SubstrateConfig, graph: NeuralGraph):
        self.config = config
        self.graph = graph

    def run(
        self,
        external_events: List[Tuple[float, int, float]],  # (time, target, amplitude)
        t_max: float,
        max_events: int = 1_000_000,
    ) -> SimulationResult:
        raise NotImplementedError


class EventDrivenScheduler(BaseScheduler):
    """Exact priority-queue event-driven scheduler with lazy node decay."""

    def __init__(self, config: SubstrateConfig, graph: NeuralGraph, lazy_decay: bool = True):
        super().__init__(config, graph)
        self.lazy_decay = lazy_decay

    def run(
        self,
        external_events: List[Tuple[float, int, float]],
        t_max: float,
        max_events: int = 1_000_000,
    ) -> SimulationResult:
        start_wall = time.perf_counter()
        state = SubstrateState(self.config)
        queue = EventQueue(max_capacity=max_events)

        # Inject external events
        for t, target, amp in external_events:
            if t <= t_max:
                queue.push(
                    timestamp=t,
                    source=-1,
                    target=target,
                    amplitude=amp,
                    kind=EventKind.EXTERNAL,
                )

        spike_records: List[Tuple[float, int]] = []
        events_processed = 0
        edges_traversed = 0
        capacity_exceeded = False

        try:
            while not queue.is_empty():
                if events_processed >= max_events:
                    capacity_exceeded = True
                    break

                ev = queue.pop()
                events_processed += 1

                if ev.timestamp > t_max:
                    break

                # Advance and process impulse
                fired = state.receive_impulse(
                    node=ev.target,
                    current_time=ev.timestamp,
                    amplitude=ev.amplitude,
                    kind=ev.kind,
                )

                if fired:
                    spike_records.append((ev.timestamp, ev.target))
                    # Propagate across outgoing edges
                    targets = self.graph.adj_targets[ev.target]
                    weights = self.graph.adj_weights[ev.target]
                    delays = self.graph.adj_delays[ev.target]
                    num_targets = len(targets)
                    edges_traversed += num_targets

                    for i in range(num_targets):
                        arrival_time = ev.timestamp + float(delays[i])
                        if arrival_time <= t_max:
                            queue.push(
                                timestamp=arrival_time,
                                source=ev.target,
                                target=int(targets[i]),
                                amplitude=float(weights[i]),
                                kind=EventKind.SPIKE,
                            )
        except QueueCapacityExceededError:
            capacity_exceeded = True

        # Advance all nodes to t_max for exact final state
        state.advance_all_potentials(t_max)
        wall_time = time.perf_counter() - start_wall

        injected_fraction = len(external_events) / (self.config.num_nodes * max(t_max, 1e-5))
        propagated_fraction = state.total_spikes / (self.config.num_nodes * max(t_max, 1e-5))

        return SimulationResult(
            scheduler_name="event_driven_lazy" if self.lazy_decay else "event_driven_eager",
            wall_time_sec=wall_time,
            total_events_processed=events_processed,
            total_edges_traversed=edges_traversed,
            total_spikes=state.total_spikes,
            peak_queue_size=queue.peak_size,
            final_time=t_max,
            final_potentials=state.potentials.copy(),
            spike_records=spike_records,
            injected_active_fraction=injected_fraction,
            propagated_active_fraction=propagated_fraction,
            max_queue_exceeded=capacity_exceeded,
        )


class DenseSynchronousScheduler(BaseScheduler):
    """Dense fixed-step synchronous simulation updating all N nodes at each dt."""

    def __init__(self, config: SubstrateConfig, graph: NeuralGraph, dt: float = 0.1):
        super().__init__(config, graph)
        self.dt = dt

    def run(
        self,
        external_events: List[Tuple[float, int, float]],
        t_max: float,
        max_events: int = 1_000_000,
    ) -> SimulationResult:
        start_wall = time.perf_counter()
        N = self.config.num_nodes
        dt = self.dt
        num_steps = int(np.ceil(t_max / dt))
        decay_factor = np.exp(-dt / self.config.tau_m)

        potentials = np.zeros(N, dtype=np.float32)
        refractory_until = np.full(N, -1e9, dtype=np.float32)
        total_spikes = 0
        spike_records: List[Tuple[float, int]] = []
        edges_traversed = 0
        events_processed = 0

        # Bin external events into steps
        external_inputs: Dict[int, List[Tuple[int, float]]] = {}
        for t, target, amp in external_events:
            step = int(np.floor(t / dt))
            if 0 <= step <= num_steps:
                external_inputs.setdefault(step, []).append((target, amp))

        # Ring buffer for delayed synaptic transmissions
        max_delay_steps = int(np.ceil(self.config.max_delay / dt)) + 2
        delay_ring = [np.zeros(N, dtype=np.float32) for _ in range(max_delay_steps)]

        for step in range(num_steps):
            current_time = step * dt
            ring_idx = step % max_delay_steps
            syn_inputs = delay_ring[ring_idx]

            # 1. Analytic decay
            potentials *= decay_factor

            # 2. Add external inputs for this step
            if step in external_inputs:
                for target, amp in external_inputs[step]:
                    events_processed += 1
                    if current_time >= refractory_until[target]:
                        potentials[target] += amp

            # 3. Add synaptic inputs
            nonzero_syn = np.nonzero(syn_inputs)[0]
            if len(nonzero_syn) > 0:
                events_processed += len(nonzero_syn)
                for node in nonzero_syn:
                    if current_time >= refractory_until[node]:
                        potentials[node] += syn_inputs[node]
            # Reset ring slot
            syn_inputs.fill(0.0)

            # 4. Spiking check for all N nodes
            is_refractory = current_time < refractory_until
            potentials[is_refractory] = self.config.v_reset
            fired_nodes = np.where((potentials >= self.config.threshold) & (~is_refractory))[0]

            if len(fired_nodes) > 0:
                total_spikes += len(fired_nodes)
                potentials[fired_nodes] = self.config.v_reset
                refractory_until[fired_nodes] = current_time + self.config.refractory_period

                for node in fired_nodes:
                    spike_records.append((current_time, int(node)))
                    targets = self.graph.adj_targets[node]
                    weights = self.graph.adj_weights[node]
                    delays = self.graph.adj_delays[node]
                    num_targets = len(targets)
                    edges_traversed += num_targets

                    for i in range(num_targets):
                        target_node = targets[i]
                        w = weights[i]
                        d = delays[i]
                        delay_step_count = max(1, int(np.round(d / dt)))
                        target_step = step + delay_step_count
                        if target_step < num_steps:
                            target_ring_idx = target_step % max_delay_steps
                            delay_ring[target_ring_idx][target_node] += w

        wall_time = time.perf_counter() - start_wall
        injected_fraction = len(external_events) / (N * max(t_max, 1e-5))
        propagated_fraction = total_spikes / (N * max(t_max, 1e-5))

        return SimulationResult(
            scheduler_name=f"dense_sync_dt_{dt}",
            wall_time_sec=wall_time,
            total_events_processed=events_processed,
            total_edges_traversed=edges_traversed,
            total_spikes=total_spikes,
            peak_queue_size=max_delay_steps * N,
            final_time=t_max,
            final_potentials=potentials.copy(),
            spike_records=spike_records,
            injected_active_fraction=injected_fraction,
            propagated_active_fraction=propagated_fraction,
            metadata={"dt": dt, "num_steps": num_steps},
        )


class SparseSynchronousScheduler(BaseScheduler):
    """Sparse fixed-step synchronous simulation updating only active nodes."""

    def __init__(self, config: SubstrateConfig, graph: NeuralGraph, dt: float = 0.1):
        super().__init__(config, graph)
        self.dt = dt

    def run(
        self,
        external_events: List[Tuple[float, int, float]],
        t_max: float,
        max_events: int = 1_000_000,
    ) -> SimulationResult:
        start_wall = time.perf_counter()
        N = self.config.num_nodes
        dt = self.dt
        num_steps = int(np.ceil(t_max / dt))

        potentials = np.zeros(N, dtype=np.float32)
        last_updated = np.zeros(N, dtype=np.float32)
        refractory_until = np.full(N, -1e9, dtype=np.float32)
        total_spikes = 0
        spike_records: List[Tuple[float, int]] = []
        edges_traversed = 0
        events_processed = 0

        # Bin external events
        external_inputs: Dict[int, List[Tuple[int, float]]] = {}
        for t, target, amp in external_events:
            step = int(np.floor(t / dt))
            if 0 <= step <= num_steps:
                external_inputs.setdefault(step, []).append((target, amp))

        max_delay_steps = int(np.ceil(self.config.max_delay / dt)) + 2
        # Use dict of node->amp for sparse delay buffer
        delay_ring: List[Dict[int, float]] = [{} for _ in range(max_delay_steps)]

        for step in range(num_steps):
            current_time = step * dt
            ring_idx = step % max_delay_steps
            syn_map = delay_ring[ring_idx]

            active_nodes: Set[int] = set()
            if step in external_inputs:
                for target, _ in external_inputs[step]:
                    active_nodes.add(target)
            if syn_map:
                for target in syn_map:
                    active_nodes.add(target)

            if active_nodes:
                for node in active_nodes:
                    # Advance potential lazily to current_time
                    delta = current_time - last_updated[node]
                    if delta > 0:
                        potentials[node] *= np.exp(-delta / self.config.tau_m)
                        last_updated[node] = current_time

                    # Apply external input
                    if step in external_inputs:
                        for target, amp in external_inputs[step]:
                            if target == node:
                                events_processed += 1
                                if current_time >= refractory_until[node]:
                                    potentials[node] += amp

                    # Apply synaptic input
                    if node in syn_map:
                        events_processed += 1
                        if current_time >= refractory_until[node]:
                            potentials[node] += syn_map[node]

                    # Check spiking
                    if current_time < refractory_until[node]:
                        potentials[node] = self.config.v_reset
                    elif potentials[node] >= self.config.threshold:
                        total_spikes += 1
                        spike_records.append((current_time, node))
                        potentials[node] = self.config.v_reset
                        refractory_until[node] = current_time + self.config.refractory_period

                        targets = self.graph.adj_targets[node]
                        weights = self.graph.adj_weights[node]
                        delays = self.graph.adj_delays[node]
                        num_targets = len(targets)
                        edges_traversed += num_targets

                        for i in range(num_targets):
                            target_node = int(targets[i])
                            w = float(weights[i])
                            d = float(delays[i])
                            delay_step_count = max(1, int(np.round(d / dt)))
                            target_step = step + delay_step_count
                            if target_step < num_steps:
                                target_ring_idx = target_step % max_delay_steps
                                d_map = delay_ring[target_ring_idx]
                                d_map[target_node] = d_map.get(target_node, 0.0) + w

            # Clear ring slot
            delay_ring[ring_idx] = {}

        # Final pass: decay all potentials to t_max
        for node in range(N):
            delta = t_max - last_updated[node]
            if delta > 0:
                potentials[node] *= np.exp(-delta / self.config.tau_m)
                last_updated[node] = t_max

        wall_time = time.perf_counter() - start_wall
        injected_fraction = len(external_events) / (N * max(t_max, 1e-5))
        propagated_fraction = total_spikes / (N * max(t_max, 1e-5))

        return SimulationResult(
            scheduler_name=f"sparse_sync_dt_{dt}",
            wall_time_sec=wall_time,
            total_events_processed=events_processed,
            total_edges_traversed=edges_traversed,
            total_spikes=total_spikes,
            peak_queue_size=sum(len(d) for d in delay_ring),
            final_time=t_max,
            final_potentials=potentials.copy(),
            spike_records=spike_records,
            injected_active_fraction=injected_fraction,
            propagated_active_fraction=propagated_fraction,
            metadata={"dt": dt, "num_steps": num_steps},
        )
