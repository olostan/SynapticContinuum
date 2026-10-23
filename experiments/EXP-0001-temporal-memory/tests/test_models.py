"""Deterministic unit and smoke tests for all EXP-0001 models."""
import pytest
import torch
from src.models import (
    MajorityModel,
    ArithmeticOracle,
    MLPOracle,
    ReservoirModel,
    TimeAwareGRU,
    DiagonalDecaySSM,
    TraceBankModel,
    SparseFIRModel,
)
from src.accounting import count_parameters, estimate_macs_per_step


@pytest.fixture
def dummy_batch():
    batch_size = 8
    seq_len = 3
    return {
        "symbols": torch.randint(0, 3, (batch_size, seq_len)),
        "delta_times": torch.tensor([[0.0, 2.0, 4.0]] * batch_size),
        "timestamps": torch.tensor([[0.0, 2.0, 6.0]] * batch_size),
        "labels": torch.tensor([1.0, 0.0] * (batch_size // 2)),
        "d1_d2": torch.tensor([[2.0, 4.0]] * batch_size),
    }


def test_majority_model(dummy_batch):
    model = MajorityModel(prior=0.5)
    logits = model(dummy_batch)
    assert logits.shape == (8,)
    params = count_parameters(model)
    assert params["trainable_parameters"] == 0


def test_arithmetic_oracle(dummy_batch):
    model = ArithmeticOracle()
    logits = model(dummy_batch)
    assert logits.shape == (8,)
    # d2=4.0 > 1.5 * d1=3.0 -> true (positive)
    assert torch.all(logits > 0)


def test_mlp_oracle(dummy_batch):
    model = MLPOracle(hidden_dim=32)
    logits = model(dummy_batch)
    assert logits.shape == (8,)
    loss = logits.sum()
    loss.backward()
    params = count_parameters(model)
    assert params["trainable_parameters"] > 0


def test_reservoir_model(dummy_batch):
    model = ReservoirModel(hidden_dim=32, vocab_size=4, seed=42)
    logits = model(dummy_batch)
    assert logits.shape == (8,)
    loss = logits.sum()
    loss.backward()
    params = count_parameters(model)
    assert params["trainable_parameters"] == 33  # readout weight (32) + bias (1)
    assert params["fixed_parameters"] > 0


def test_gru_model(dummy_batch):
    model = TimeAwareGRU(hidden_dim=32, vocab_size=4)
    logits, h_seq = model(dummy_batch, return_hidden=True)
    assert logits.shape == (8,)
    assert h_seq.shape == (8, 3, 32)
    loss = logits.sum()
    loss.backward()


def test_ssm_model(dummy_batch):
    model = DiagonalDecaySSM(hidden_dim=32, vocab_size=4)
    logits, h_seq = model(dummy_batch, return_hidden=True)
    assert logits.shape == (8,)
    assert h_seq.shape == (8, 3, 32)
    loss = logits.sum()
    loss.backward()


def test_trace_bank_model(dummy_batch):
    model = TraceBankModel(
        hidden_dim=32,
        trace_bases=4,
        max_degree=4,
        vocab_size=4,
        seed=42,
    )
    logits, h_seq, z_seq = model(dummy_batch, return_hidden=True)
    assert logits.shape == (8,)
    assert h_seq.shape == (8, 3, 32)
    assert z_seq.shape == (8, 3, 32, 4)
    loss = logits.sum()
    loss.backward()


def test_fir_model(dummy_batch):
    model = SparseFIRModel(
        hidden_dim=32,
        fir_taps=4,
        max_degree=4,
        vocab_size=4,
        seed=42,
    )
    logits, h_seq = model(dummy_batch, return_hidden=True)
    assert logits.shape == (8,)
    assert h_seq.shape == (8, 3, 32)
    loss = logits.sum()
    loss.backward()


def test_mac_estimation():
    for name in ["majority", "arithmetic", "mlp", "reservoir", "gru", "ssm", "trace", "fir"]:
        macs = estimate_macs_per_step(name, hidden_dim=128)
        assert isinstance(macs, int)
        assert macs >= 0
