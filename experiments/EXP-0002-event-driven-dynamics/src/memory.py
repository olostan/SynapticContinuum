"""Temporal representations: Exponential Trace Banks and Bounded Event History buffers.

Governed by SPEC.md Stage 2 & Definitions:
- Exponential trace z(t) = z(t0) * exp(-(t - t0) / tau) + q
- Bounded explicit event history L in {0, 1, 4, 16, 64, 256} events per node
- Exact memory accounting in bytes, capacity-matched comparisons, and lazy evaluation.
"""
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np


class ExponentialTraceBank:
    """Exact analytic exponential trace bank with lazy evaluation."""

    def __init__(
        self,
        num_nodes: int,
        num_bases: int = 4,
        tau_min: float = 1.0,
        tau_max: float = 50.0,
        tau_list: Optional[List[float]] = None,
    ):
        self.num_nodes = num_nodes
        self.num_bases = num_bases
        if num_bases == 0:
            self.taus = np.empty((0,), dtype=np.float32)
            self.values = np.empty((num_nodes, 0), dtype=np.float32)
            self.last_times = np.zeros(num_nodes, dtype=np.float32)
        else:
            if tau_list is not None:
                assert len(tau_list) == num_bases
                self.taus = np.array(tau_list, dtype=np.float32)
            else:
                if num_bases == 1:
                    self.taus = np.array([tau_min], dtype=np.float32)
                else:
                    self.taus = np.geomspace(tau_min, tau_max, num_bases, dtype=np.float32)
            self.values = np.zeros((num_nodes, num_bases), dtype=np.float32)
            self.last_times = np.zeros(num_nodes, dtype=np.float32)

    def advance_and_add(self, node: int, current_time: float, amplitude: float = 1.0) -> None:
        """Lazily advance node's traces to current_time and add amplitude."""
        if self.num_bases == 0:
            return
        dt = current_time - self.last_times[node]
        if dt < 0:
            raise ValueError(f"Non-causal time travel: dt={dt} < 0")
        if dt > 0:
            decay = np.exp(-dt / self.taus)
            self.values[node] *= decay
        self.values[node] += amplitude
        self.last_times[node] = current_time

    def get_values(self, node: int, current_time: float) -> np.ndarray:
        """Read node's traces lazily evaluated at current_time without mutating state."""
        if self.num_bases == 0:
            return np.empty((0,), dtype=np.float32)
        dt = current_time - self.last_times[node]
        if dt < 0:
            raise ValueError(f"Non-causal time travel: dt={dt} < 0")
        decay = np.exp(-dt / self.taus) if dt > 0 else 1.0
        return self.values[node] * decay

    def get_all_values(self, current_time: float) -> np.ndarray:
        """Read all nodes' traces lazily evaluated at current_time."""
        if self.num_bases == 0:
            return np.empty((self.num_nodes, 0), dtype=np.float32)
        dt = current_time - self.last_times  # shape (N,)
        decay = np.exp(-dt[:, None] / self.taus[None, :])
        return self.values * decay

    def reset(self) -> None:
        if self.num_bases > 0:
            self.values.fill(0.0)
            self.last_times.fill(0.0)

    @property
    def storage_bytes(self) -> int:
        """Exact memory footprint in bytes."""
        if self.num_bases == 0:
            return 0
        # float32 values (4 bytes) + float32 last_times (4 bytes) + float32 taus (4 bytes)
        return int(
            self.values.nbytes
            + self.last_times.nbytes
            + self.taus.nbytes
        )


class BoundedEventHistory:
    """Fixed-capacity ring buffer storing up to L recent events per node."""

    def __init__(self, num_nodes: int, capacity_L: int):
        self.num_nodes = num_nodes
        self.capacity_L = capacity_L
        if capacity_L > 0:
            self.timestamps = np.zeros((num_nodes, capacity_L), dtype=np.float32)
            self.amplitudes = np.zeros((num_nodes, capacity_L), dtype=np.float32)
            self.kinds = np.zeros((num_nodes, capacity_L), dtype=np.int8)
            self.heads = np.zeros(num_nodes, dtype=np.int32)
            self.counts = np.zeros(num_nodes, dtype=np.int32)
        else:
            self.timestamps = np.empty((num_nodes, 0), dtype=np.float32)
            self.amplitudes = np.empty((num_nodes, 0), dtype=np.float32)
            self.kinds = np.empty((num_nodes, 0), dtype=np.int8)
            self.heads = np.zeros(num_nodes, dtype=np.int32)
            self.counts = np.zeros(num_nodes, dtype=np.int32)

    def record_event(
        self, node: int, timestamp: float, amplitude: float = 1.0, kind: int = 1
    ) -> None:
        """Append an event to node's circular history buffer."""
        if self.capacity_L == 0:
            return
        idx = self.heads[node]
        self.timestamps[node, idx] = timestamp
        self.amplitudes[node, idx] = amplitude
        self.kinds[node, idx] = kind
        self.heads[node] = (idx + 1) % self.capacity_L
        if self.counts[node] < self.capacity_L:
            self.counts[node] += 1

    def get_events(self, node: int) -> List[Tuple[float, float, int]]:
        """Return list of (timestamp, amplitude, kind) in chronological order."""
        if self.capacity_L == 0 or self.counts[node] == 0:
            return []
        count = self.counts[node]
        head = self.heads[node]
        # Start index is head - count modulo capacity
        start_idx = (head - count) % self.capacity_L
        events = []
        for i in range(count):
            curr_idx = (start_idx + i) % self.capacity_L
            events.append(
                (
                    float(self.timestamps[node, curr_idx]),
                    float(self.amplitudes[node, curr_idx]),
                    int(self.kinds[node, curr_idx]),
                )
            )
        return events

    def query_kernel(
        self,
        node: int,
        query_time: float,
        kernel_fn: Callable[[np.ndarray], np.ndarray],
    ) -> float:
        """Compute causal kernel convolution sum over node's history."""
        if self.capacity_L == 0 or self.counts[node] == 0:
            return 0.0
        count = self.counts[node]
        head = self.heads[node]
        indices = (np.arange(head - count, head) % self.capacity_L).astype(np.int32)
        t_arr = self.timestamps[node, indices]
        a_arr = self.amplitudes[node, indices]
        dt = query_time - t_arr
        # Causal filter: only events where dt >= 0
        valid = dt >= 0.0
        if not np.any(valid):
            return 0.0
        weights = kernel_fn(dt[valid])
        return float(np.sum(a_arr[valid] * weights))

    def reset(self) -> None:
        if self.capacity_L > 0:
            self.timestamps.fill(0.0)
            self.amplitudes.fill(0.0)
            self.kinds.fill(0)
            self.heads.fill(0)
            self.counts.fill(0)

    @property
    def storage_bytes(self) -> int:
        """Exact memory footprint in bytes."""
        if self.capacity_L == 0:
            return 0
        # float32 timestamps (4 bytes) + float32 amplitudes (4 bytes) + int8 kinds (1 byte)
        # + int32 heads (4 bytes) + int32 counts (4 bytes)
        return int(
            self.timestamps.nbytes
            + self.amplitudes.nbytes
            + self.kinds.nbytes
            + self.heads.nbytes
            + self.counts.nbytes
        )
