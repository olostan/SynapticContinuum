"""Baseline models for EXP-0001: Majority, Arithmetic Oracle, MLP Oracle, Reservoir."""
from typing import Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class MajorityModel(nn.Module):
    """Majority class baseline (predicts constant probability ~0.5)."""
    def __init__(self, prior: float = 0.5):
        super().__init__()
        logit = float(torch.logit(torch.tensor(min(max(prior, 1e-4), 1.0 - 1e-4))))
        self.bias = nn.Parameter(torch.tensor([logit]), requires_grad=False)

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        batch_size = batch["labels"].shape[0]
        return self.bias.expand(batch_size)


class ArithmeticOracle(nn.Module):
    """Exact arithmetic ratio predictor: 1[d2 > 1.5 * d1]. Non-streaming sanity ceiling."""
    def __init__(self, high_confidence: float = 20.0):
        super().__init__()
        self.high_confidence = high_confidence
        # Dummy parameter so optimizers don't complain
        self.dummy = nn.Parameter(torch.zeros(1), requires_grad=False)

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        d1_d2 = batch["d1_d2"]  # [batch, 2]
        d1 = d1_d2[:, 0]
        d2 = d1_d2[:, 1]
        is_pos = (d2 > 1.5 * d1).float()
        # Return very large positive or negative logits
        return (is_pos * 2.0 - 1.0) * self.high_confidence


class MLPOracle(nn.Module):
    """Feedforward MLP taking tabular (d1, d2, log1p(d1), log1p(d2)). Non-causal sanity ceiling."""
    def __init__(self, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        d1_d2 = batch["d1_d2"]  # [batch, 2]
        d1 = d1_d2[:, 0:1]
        d2 = d1_d2[:, 1:2]
        features = torch.cat([d1, d2, torch.log1p(d1), torch.log1p(d2)], dim=-1)
        return self.net(features).squeeze(-1)


class ReservoirModel(nn.Module):
    """Fixed random recurrent reservoir with trained linear readout.
    
    Reservoir weights are frozen with spectral radius scaled to 0.95.
    Input features include symbol embedding, dt, and log1p(dt).
    """
    def __init__(
        self,
        hidden_dim: int = 128,
        vocab_size: int = 4,
        embed_dim: int = 16,
        seed: int = 42,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.embed = nn.Embedding(vocab_size, embed_dim)
        input_dim = embed_dim + 2  # embed + dt + log1p(dt)
        self.in_proj = nn.Linear(input_dim, hidden_dim)

        # Freeze embedding and input projection for reservoir
        self.embed.weight.requires_grad = False
        self.in_proj.weight.requires_grad = False
        self.in_proj.bias.requires_grad = False

        # Frozen reservoir recurrent weight
        rng = torch.Generator().manual_seed(seed)
        W = torch.randn(hidden_dim, hidden_dim, generator=rng)
        # Scale spectral radius to 0.95
        eigenvalues = torch.linalg.eigvals(W)
        max_eig = torch.max(torch.abs(eigenvalues))
        if max_eig > 0:
            W = W * (0.95 / max_eig)
        self.W_res = nn.Parameter(W, requires_grad=False)
        self.b_res = nn.Parameter(torch.zeros(hidden_dim), requires_grad=False)

        # Trainable readout head
        self.readout = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        batch: Dict[str, torch.Tensor],
        return_hidden: bool = False,
    ) -> torch.Tensor | Tuple[torch.Tensor, torch.Tensor]:
        symbols = batch["symbols"]  # [batch, seq_len]
        delta_times = batch["delta_times"]  # [batch, seq_len]
        batch_size, seq_len = symbols.shape

        h = torch.zeros(batch_size, self.hidden_dim, device=symbols.device)
        all_h = []

        for t in range(seq_len):
            sym = symbols[:, t]
            dt = delta_times[:, t : t + 1]
            dt_feat = torch.cat([dt, torch.log1p(dt)], dim=-1)
            x_emb = self.embed(sym)
            x_in = torch.cat([x_emb, dt_feat], dim=-1)

            proj = self.in_proj(x_in)
            rec = F.linear(h, self.W_res, self.b_res)
            h = torch.tanh(rec + proj)
            all_h.append(h)

        logits = self.readout(h).squeeze(-1)
        if return_hidden:
            return logits, torch.stack(all_h, dim=1)
        return logits
