"""Tests for factorial gap x update-count and trace ablation."""
import torch
from src.data import generate_all_datasets
from src.models import TraceBankModel, TimeAwareGRU
from src.factorial import run_factorial_and_ablation


def test_factorial_and_ablation():
    suites, _ = generate_all_datasets(seed=42, train_size=50, val_size=20, test_size=20)
    test_ds = suites["temporal"]["test_id"]

    # Test with TraceBankModel
    trace_model = TraceBankModel(hidden_dim=32, trace_bases=4, max_degree=4)
    res_trace = run_factorial_and_ablation(
        trace_model,
        "trace_bank",
        test_ds,
        gaps=[1.0, 5.0],
        update_counts=[0, 2],
        max_eval_samples=20,
    )
    assert "factorial_conditions" in res_trace
    assert "gap_1.0" in res_trace["factorial_conditions"]
    assert "J_0" in res_trace["factorial_conditions"]["gap_1.0"]
    assert "diagnostic_ablations" in res_trace
    assert "boundary_trace_ablation" in res_trace["diagnostic_ablations"]
    assert "interval_trace_ablation" in res_trace["diagnostic_ablations"]
    assert "explicit_dt_feature_ablation" in res_trace["diagnostic_ablations"]

    # Test with GRU
    gru_model = TimeAwareGRU(hidden_dim=32)
    res_gru = run_factorial_and_ablation(
        gru_model,
        "gru",
        test_ds,
        gaps=[1.0, 5.0],
        update_counts=[0, 2],
        max_eval_samples=20,
    )
    assert "factorial_conditions" in res_gru
