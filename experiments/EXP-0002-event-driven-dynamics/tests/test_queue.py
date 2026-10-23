"""Unit and property tests for deterministic EventQueue."""
import pytest
from src.queue import (
    Event,
    EventKind,
    EventQueue,
    QueueCapacityExceededError,
)


def test_event_queue_timestamp_order():
    q = EventQueue()
    q.push(3.0, source=0, target=1, amplitude=0.5)
    q.push(1.0, source=0, target=2, amplitude=1.0)
    q.push(2.5, source=1, target=2, amplitude=0.8)

    assert len(q) == 3
    e1 = q.pop()
    assert e1.timestamp == 1.0 and e1.target == 2
    e2 = q.pop()
    assert e2.timestamp == 2.5 and e2.target == 2
    e3 = q.pop()
    assert e3.timestamp == 3.0 and e3.target == 1
    assert q.is_empty()


def test_event_queue_stable_tie_breaking():
    """Simultaneous events must be popped strictly in insertion seq_id order."""
    q = EventQueue()
    for i in range(10):
        q.push(5.0, source=0, target=i, amplitude=float(i))

    for i in range(10):
        ev = q.pop()
        assert ev.timestamp == 5.0
        assert ev.target == i
        assert ev.seq_id == i


def test_event_queue_capacity_limit():
    q = EventQueue(max_capacity=5)
    for i in range(5):
        q.push(float(i), source=0, target=1, amplitude=1.0)
    with pytest.raises(QueueCapacityExceededError):
        q.push(6.0, source=0, target=1, amplitude=1.0)


def test_event_queue_empty_pop():
    q = EventQueue()
    with pytest.raises(IndexError):
        q.pop()
