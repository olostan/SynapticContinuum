"""Deterministic tests for data generator, split auditor, and negative controls."""
import numpy as np
import pytest
from src.data import generate_all_datasets, audit_splits


def test_data_generation_balance_and_shapes():
    suites, audits = generate_all_datasets(
        seed=11,
        train_size=200,
        val_size=50,
        test_size=50,
    )
    datasets = suites["temporal"]
    audit = audits["temporal"]

    for name in ["train", "val", "test_id", "test_interpolation", "test_extrapolation"]:
        ds = datasets[name]
        assert len(ds) == audit[name]["size"]
        assert audit[name]["positive_fraction"] == 0.5
        assert audit[name]["positive_count"] == len(ds) // 2

        # Check tensor shapes
        item = ds[0]
        assert item["symbols"].shape == (3,)
        assert item["delta_times"].shape == (3,)
        assert item["timestamps"].shape == (3,)
        assert item["d1_d2"].shape == (2,)


def test_data_regimes_and_disjointness():
    suites, audits = generate_all_datasets(
        seed=11,
        train_size=300,
        val_size=100,
        test_size=100,
    )
    datasets = suites["temporal"]
    audit = audits["temporal"]

    # Train excludes [4, 5] for d1
    train_ds = datasets["train"]
    for s in train_ds.samples:
        assert not (4.0 <= s.d1 <= 5.0)

    # Interpolation strictly in [4, 5] for d1
    interp_ds = datasets["test_interpolation"]
    for s in interp_ds.samples:
        assert 4.0 <= s.d1 <= 5.0

    # Extrapolation strictly in [12, 16] for d1 and [10, 30] for d2
    extrap_ds = datasets["test_extrapolation"]
    for s in extrap_ds.samples:
        assert 12.0 <= s.d1 <= 16.0
        assert 10.0 <= s.d2 <= 30.0

    # Overlaps must be zero
    overlaps = audit["overlaps"]
    for pair, count in overlaps.items():
        assert count == 0, f"Leakage detected between splits: {pair} has {count} shared tuples"


def test_negative_controls():
    suites, audits = generate_all_datasets(
        seed=11,
        train_size=100,
        val_size=40,
        test_size=40,
    )

    ctrl_sym = suites["control_symbol"]["test"]
    assert len(ctrl_sym) == 40
    # Final symbol must be token 2 or 3
    for s in ctrl_sym.samples:
        assert s.symbols[2] in (2, 3)
        assert s.label == (1 if s.symbols[2] == 3 else 0)

    ctrl_ord = suites["control_order"]["test"]
    assert len(ctrl_ord) == 40
    for s in ctrl_ord.samples:
        assert s.symbols[:2] in ([0, 1], [1, 0])
        assert s.label == (1 if s.symbols[0] == 0 else 0)
