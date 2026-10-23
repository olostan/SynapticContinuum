"""Time-Aware GRU baseline for EXP-0001."""
from typing import Dict, Tuple
import torch
import torch.nn as nn


class TimeAwareGRU(nn.Module):
    """GRU baseline that explicitly observes inter-event intervals dt."""
    def __init__(
        self,
        hidden_dim: int = 128,
        vocab_size: int = 4,
        embed_dim: int = 16,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.embed = nn.Embedding(vocab_size, embed_dim)
        input_dim = embed_dim + 2  # embed + dt + log1p(dt)

        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            batch_first=True,
        )
        self.readout = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        batch: Dict[str, torch.Tensor],
        return_hidden: bool = False,
    ) -> torch.Tensor | Tuple[torch.Tensor, torch.Tensor]:
        symbols = batch["symbols"]  # [batch, seq_len]
        delta_times = batch["delta_times"]  # [batch, seq_len]

        emb = self.embed(symbols)  # [batch, seq_len, embed_dim]
        dt = delta_times.unsqueeze(-1)  # [batch, seq_len, 1]
        log_dt = torch.log1p(dt)  # [batch, seq_len, 1]

        x_seq = torch.cat([emb, dt, log_dt], dim=-1)  # [batch, seq_len, input_dim]

        out_seq, h_n = self.gru(x_seq)  # out_seq: [batch, seq_len, hidden_dim]
        last_h = out_seq[:, -1, :]  # [batch, hidden_dim]
        logits = self.readout(last_h).squeeze(-1)

        if return_hidden:
            return logits, out_seq
        return logits
