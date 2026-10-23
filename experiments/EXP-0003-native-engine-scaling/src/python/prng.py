"""Deterministic SplitMix64 pseudo-random generator and graph/event generation in Python.

Matches src/cpp/core/prng.hpp bit-for-bit to ensure cross-language parity.
"""
from dataclasses import dataclass
import math
import struct
from typing import List, Tuple
import numpy as np


class DeterministicRNG:
    def __init__(self, seed: int = 42):
        self.state = seed if seed != 0 else 0x123456789ABCDEF0

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        z = (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF
        return z

    def uniform_uint(self, n: int) -> int:
        if n <= 1:
            return 0
        x = self.next_u64() & 0xFFFFFFFF
        return (x * n) >> 32

    def uniform_float(self, min_val: float, max_val: float) -> float:
        r = self.next_u64()
        u = (r >> 40) * (1.0 / 16777216.0)
        return min_val + u * (max_val - min_val)

    def uniform_double(self, min_val: float, max_val: float) -> float:
        r = self.next_u64()
        u = (r >> 11) * (1.0 / 9007199254740992.0)
        return min_val + u * (max_val - min_val)

    def exponential(self, rate: float) -> float:
        if rate <= 0.0:
            return 1e9
        u = self.uniform_double(1e-12, 1.0)
        return -math.log(u) / rate

    def sample_unique(self, count: int, num_nodes: int, exclude_node: int) -> List[int]:
        max_avail = (num_nodes - 1) if exclude_node < num_nodes else num_nodes
        k = min(count, max_avail)
        if k == 0:
            return []
        if k >= max_avail:
            return [i for i in range(num_nodes) if i != exclude_node]

        res = []
        while len(res) < k:
            cand = self.uniform_uint(num_nodes)
            if cand == exclude_node:
                continue
            if cand not in res:
                res.append(cand)
        res.sort()
        return res


def generate_deterministic_graph(
    num_nodes: int,
    mean_out_degree: int,
    seed: int,
    weight_scale: float = 0.25,
    min_delay: float = 0.2,
    max_delay: float = 2.0,
) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray]]:
    """Generates graph matching C++ GraphFactory::create_random."""
    rng = DeterministicRNG(seed)
    adj_targets: List[np.ndarray] = []
    adj_weights: List[np.ndarray] = []
    adj_delays: List[np.ndarray] = []

    k = min(mean_out_degree, num_nodes - 1 if num_nodes > 1 else 0)

    for u in range(num_nodes):
        targets = rng.sample_unique(k, num_nodes, u)
        is_inhibitory = rng.uniform_float(0.0, 1.0) < 0.20

        weights = np.empty(len(targets), dtype=np.float32)
        delays = np.empty(len(targets), dtype=np.float32)

        for i in range(len(targets)):
            w_raw = rng.uniform_float(0.5, 1.5) * weight_scale
            weights[i] = -w_raw if is_inhibitory else w_raw
            delays[i] = rng.uniform_float(min_delay, max_delay)

        adj_targets.append(np.array(targets, dtype=np.int32))
        adj_weights.append(weights)
        adj_delays.append(delays)

    return adj_targets, adj_weights, adj_delays


def generate_deterministic_events(
    num_nodes: int,
    active_fraction: float,
    rate_hz: float,
    t_max: float,
    seed: int,
    timing_type: str = "poisson",
) -> List[Tuple[float, int, float]]:
    """Generates external events matching C++ EventGenerator::generate."""
    rng = DeterministicRNG(seed)
    m = max(1, int(round(num_nodes * active_fraction)))
    m = min(m, num_nodes)

    active_nodes = rng.sample_unique(m, num_nodes, 0xFFFFFFFF)
    events: List[Tuple[float, int, float]] = []

    for node in active_nodes:
        if timing_type == "regular":
            interval = 1.0 / rate_hz
            curr_t = rng.uniform_double(0.0, interval)
            while curr_t <= t_max:
                events.append((curr_t, node, 1.2))
                curr_t += interval
        elif timing_type == "bursty":
            curr_t = rng.exponential(rate_hz * 0.2)
            while curr_t <= t_max:
                burst_size = 1 + rng.uniform_uint(5)
                for b in range(burst_size):
                    if curr_t + b * 0.05 <= t_max:
                        events.append((curr_t + b * 0.05, node, 1.2))
                curr_t += rng.exponential(rate_hz * 0.2)
        else:
            curr_t = rng.exponential(rate_hz)
            while curr_t <= t_max:
                events.append((curr_t, node, 1.2))
                curr_t += rng.exponential(rate_hz)

    # Sort by timestamp, then target
    events.sort(key=lambda ev: (ev[0], ev[1]))
    return events
