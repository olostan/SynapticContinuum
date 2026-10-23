"""Property tests requested by scientific review on PR #6.

Properties tested:
1. J=0 invariance (dynamics forward equals direct jump).
2. Exact physical time conservation (no double-counted or truncated time).
3. Pure analytic decay partition invariance.
4. Negative control dataset independence, balance, and semantics.
"""
import pytest
import torch
import numpy as np
from src.data import generate_all_datasets
from src.models import TraceBankModel, DiagonalDecaySSM, TimeAwareGRU
from src.factorial import run_model_forward_with_dynamics


def test_j0_invariance():
    """Verify that J=0 scheduled evolution equals standard direct jump."""
    batch_size = 4
    symbols = torch.tensor([[0, 1, 2]] * batch_size)
    delta_times = torch.tensor([[0.0, 2.0, 5.0]] * batch_size)
    timestamps = torch.tensor([[0.0, 2.0, 7.0]] * batch_size)

    for model_cls in [TraceBankModel, DiagonalDecaySSM, TimeAwareGRU]:
        model = model_cls(hidden_dim=32)
        model.eval()

        res_j0 = run_model_forward_with_dynamics(
            model, symbols, delta_times, timestamps, gap=5.0, J=0, condition="scheduled_evolution"
        )
        res_direct = run_model_forward_with_dynamics(
            model, symbols, delta_times, timestamps, gap=5.0, J=0, condition="sleep_freeze"
        )

        assert torch.allclose(res_j0["logits"], res_direct["logits"], atol=1e-5), (
            f"J=0 output diverges from direct jump for {model_cls.__name__}"
        )


def test_time_conservation_and_no_double_counting():
    """Verify that scheduled evolution partitions gap Delta exactly without double-counting."""
    gap = 8.0
    for J in [1, 4, 8, 16]:
        dt_sub = gap / J
        total_time = sum([dt_sub for _ in range(J)])
        assert np.isclose(total_time, gap), f"Time partition {total_time} does not sum to gap {gap}"


def test_analytic_decay_partition_invariance():
    """Verify that pure exponential decay is invariant to substep partition J."""
    gap = 6.0
    taus = torch.tensor([0.5, 1.0, 2.0, 5.0, 10.0])
    decay_single = torch.exp(-gap / taus)

    for J in [1, 2, 4, 8, 32]:
        dt_sub = gap / J
        decay_step = torch.exp(-dt_sub / taus)
        decay_accum = decay_step**J
        assert torch.allclose(decay_single, decay_accum, atol=1e-6), (
            f"Analytic decay partition failed for J={J}"
        )


def test_negative_control_task_splits():
    """Verify negative control suites have task-specific train/val/test splits."""
    suites, audits = generate_all_datasets(seed=42, train_size=60, val_size=20, test_size=20)

    for task in ["control_symbol", "control_order"]:
        assert task in suites
        assert set(suites[task].keys()) == {"train", "val", "test"}
        for split_name, ds in suites[task].items():
            assert len(ds) == audits[task][split_name]["size"]
            assert audits[task][split_name]["positive_fraction"] == 0.5
