"""Neural graph substrate, membrane potential laws, and dynamical state representation.

Governed by SPEC.md:
- Directed weighted graph G=(V,E), weights w, transmission delays d >= 0
- Analytic passive leak: h_i(t) = h_i(t0) * exp(-(t - t0) / tau_m)
- Exact threshold emission, refractory period, and reset.
- Strict mathematical parity across event-driven and synchronous schedulers.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from .memory import BoundedEventHistory, ExponentialTraceBank


@dataclass
class SubstrateConfig:
    num_nodes: int = 128
    mean_out_degree: int = 16
    tau_m: float = 5.0
    threshold: float = 1.0
    v_reset: float = 0.0
    refractory_period: float = 1.0
    min_delay: float = 0.2
    max_delay: float = 2.0
    history_capacity_L: int = 0
    trace_bases_B: int = 0
    homeostasis: bool = False
    homeostasis_rate: float = 0.05
    homeostasis_tau: float = 20.0


class NeuralGraph:
    """Directed weighted graph with transmission delays and adjacency lookup."""

    def __init__(
        self,
        num_nodes: int,
        adj_targets: List[np.ndarray],
        adj_weights: List[np.ndarray],
        adj_delays: List[np.ndarray],
    ):
        self.num_nodes = num_nodes
        self.adj_targets = adj_targets
        self.adj_weights = adj_weights
        self.adj_delays = adj_delays
        self.total_edges = sum(len(targets) for targets in adj_targets)

    @classmethod
    def create_random(
        cls,
        num_nodes: int,
        mean_out_degree: int,
        seed: int,
        weight_scale: float = 0.25,
        min_delay: float = 0.2,
        max_delay: float = 2.0,
        allow_self_loops: bool = False,
    ) -> "NeuralGraph":
        """Generate deterministic directed random graph with given out-degree."""
        rng = np.random.default_rng(seed)
        adj_targets: List[np.ndarray] = []
        adj_weights: List[np.ndarray] = []
        adj_delays: List[np.ndarray] = []

        # Bound degree by num_nodes - 1 if no self-loops
        k = min(mean_out_degree, num_nodes - 1 if not allow_self_loops else num_nodes)
        if k < 0:
            k = 0

        for u in range(num_nodes):
            if k == 0 or num_nodes <= 1:
                targets = np.empty((0,), dtype=np.int32)
            else:
                possible = np.arange(num_nodes)
                if not allow_self_loops:
                    possible = possible[possible != u]
                targets = rng.choice(possible, size=k, replace=False).astype(np.int32)

            # Dale's law or mixed excitatory/inhibitory weights (80% E, 20% I)
            is_inhibitory = rng.random() < 0.20
            w_raw = rng.uniform(0.5, 1.5, size=len(targets)).astype(np.float32) * weight_scale
            if is_inhibitory:
                weights = -w_raw
            else:
                weights = w_raw

            delays = rng.uniform(min_delay, max_delay, size=len(targets)).astype(np.float32)

            adj_targets.append(targets)
            adj_weights.append(weights)
            adj_delays.append(delays)

        return cls(num_nodes, adj_targets, adj_weights, adj_delays)


class SubstrateState:
    """Mutable dynamic state of all nodes in the substrate."""

    def __init__(self, config: SubstrateConfig):
        self.config = config
        self.num_nodes = config.num_nodes
        self.potentials = np.zeros(self.num_nodes, dtype=np.float32)
        self.last_update_times = np.zeros(self.num_nodes, dtype=np.float32)
        self.refractory_until = np.full(self.num_nodes, -1e9, dtype=np.float32)
        self.thresholds = np.full(self.num_nodes, config.threshold, dtype=np.float32)
        self.spike_counts = np.zeros(self.num_nodes, dtype=np.int32)
        self.total_spikes: int = 0

        self.trace_bank = ExponentialTraceBank(
            num_nodes=self.num_nodes,
            num_bases=config.trace_bases_B,
        )
        self.history = BoundedEventHistory(
            num_nodes=self.num_nodes,
            capacity_L=config.history_capacity_L,
        )

    def advance_node_potential(self, node: int, current_time: float) -> float:
        """Analytically decay node's potential from its last update time to current_time."""
        dt = current_time - self.last_update_times[node]
        if dt < 0:
            raise ValueError(f"Non-causal time travel: dt={dt} < 0 for node {node}")
        if dt > 0:
            self.potentials[node] *= np.exp(-dt / self.config.tau_m)
            self.last_update_times[node] = current_time
        return float(self.potentials[node])

    def advance_all_potentials(self, current_time: float) -> np.ndarray:
        """Advance all nodes' potentials analytically to current_time."""
        dt = current_time - self.last_update_times
        valid = dt > 0
        if np.any(valid):
            self.potentials[valid] *= np.exp(-dt[valid] / self.config.tau_m)
            self.last_update_times[valid] = current_time
        return self.potentials

    def receive_impulse(
        self,
        node: int,
        current_time: float,
        amplitude: float,
        kind: int = 1,
    ) -> bool:
        """
        Process impulse arrival:
        1. Advance state analytically to current_time.
        2. If node is refractory, input can still be received/integrated or shunted based on spec.
           Per standard LIF: inputs during absolute refractory are shunted or integrated.
           Standard LIF specification: node state is clamped at v_reset during refractory period.
        3. Check threshold. If potential >= threshold and t >= refractory_until:
           return True (spike emitted). Node state reset, refractory_until updated.
        """
        self.advance_node_potential(node, current_time)

        # Update traces and history on impulse
        self.trace_bank.advance_and_add(node, current_time, amplitude)
        self.history.record_event(node, current_time, amplitude, kind)

        # If currently in refractory period, potential remains clamped at reset
        if current_time < self.refractory_until[node]:
            self.potentials[node] = self.config.v_reset
            return False

        self.potentials[node] += amplitude

        # Check spiking threshold
        current_thresh = self.thresholds[node]
        if self.potentials[node] >= current_thresh:
            self.potentials[node] = self.config.v_reset
            self.refractory_until[node] = current_time + self.config.refractory_period
            self.spike_counts[node] += 1
            self.total_spikes += 1

            # Homeostatic threshold adaptation if enabled
            if self.config.homeostasis:
                self.thresholds[node] += self.config.homeostasis_rate

            return True

        return False

    def reset(self) -> None:
        self.potentials.fill(0.0)
        self.last_update_times.fill(0.0)
        self.refractory_until.fill(-1e9)
        self.thresholds.fill(self.config.threshold)
        self.spike_counts.fill(0)
        self.total_spikes = 0
        self.trace_bank.reset()
        self.history.reset()
