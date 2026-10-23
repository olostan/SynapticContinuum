"""Deterministic priority event queue with stable sequence IDs and capacity enforcement.

Governed by SPEC.md:
Event queue holds (timestamp, stable_sequence_id, source, target, amplitude, kind).
Order is timestamp then stable sequence ID.
"""
from dataclasses import dataclass
import heapq
from typing import Any, List, Optional, Tuple


class EventKind:
    EXTERNAL = 0
    SPIKE = 1
    FEEDBACK = 2
    PACEMAKER = 3
    PROBE = 4
    SHAM = 5


@dataclass(frozen=True, slots=True, order=False)
class Event:
    timestamp: float
    seq_id: int
    source: int
    target: int
    amplitude: float
    kind: int = EventKind.SPIKE

    def __lt__(self, other: "Event") -> bool:
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.seq_id < other.seq_id


class QueueCapacityExceededError(RuntimeError):
    """Raised when event queue exceeds preregistered max capacity."""
    pass


class EventQueue:
    """Deterministic min-heap priority queue for neural event scheduling."""

    def __init__(self, max_capacity: int = 1_000_000):
        self.max_capacity = max_capacity
        self._heap: List[Tuple[float, int, Event]] = []
        self._seq_counter: int = 0
        self.peak_size: int = 0
        self.total_pushed: int = 0
        self.total_popped: int = 0

    def push(
        self,
        timestamp: float,
        source: int,
        target: int,
        amplitude: float,
        kind: int = EventKind.SPIKE,
    ) -> Event:
        if len(self._heap) >= self.max_capacity:
            raise QueueCapacityExceededError(
                f"Queue exceeded maximum capacity limit of {self.max_capacity} events."
            )
        event = Event(
            timestamp=float(timestamp),
            seq_id=self._seq_counter,
            source=int(source),
            target=int(target),
            amplitude=float(amplitude),
            kind=int(kind),
        )
        self._seq_counter += 1
        heapq.heappush(self._heap, (event.timestamp, event.seq_id, event))
        self.total_pushed += 1
        if len(self._heap) > self.peak_size:
            self.peak_size = len(self._heap)
        return event

    def pop(self) -> Event:
        if not self._heap:
            raise IndexError("pop from empty EventQueue")
        _, _, event = heapq.heappop(self._heap)
        self.total_popped += 1
        return event

    def peek(self) -> Optional[Event]:
        if not self._heap:
            return None
        return self._heap[0][2]

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def clear(self) -> None:
        self._heap.clear()

    def get_all_events(self) -> List[Event]:
        """Returns sorted copy of all queued events without modifying queue."""
        sorted_heap = sorted(self._heap)
        return [item[2] for item in sorted_heap]
