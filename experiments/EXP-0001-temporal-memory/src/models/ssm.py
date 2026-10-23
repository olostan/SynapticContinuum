"""Diagonal-decay continuous-time State-Space Model for EXP-0001."""
from typing import Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class DiagonalDecaySSM(nn.Module):
    """Event-driven diagonal-decay SSM with continuous elapsed-time decay.
    
    dh/dt = -diag(lambda) * h + input_drive
    Between events separated by dt, state decays by exp(-dt * lambda).
    """
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

        self.in_proj = nn.Linear(input_dim, hidden_dim)
        self.recurrent_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)

        # Log-timescales: initialized uniformly in [log(0.1), log(10.0)]
        init_log_rates = torch.linspace(-1.0, 2.0, hidden_dim)
        self.log_decay_rate = nn.Parameter(init_log_rates)

        self.readout = nn.Linear(hidden_dim, 1)

    def get_decay_rates(self) -> torch.Tensor:
        # Clamp to avoid numerical overflow / instability
        return torch.exp(torch.clamp(self.log_decay_rate, min=-5.0, max=5.0))

    def step(
        self,
        h_prev: torch.Tensor,
        sym: torch.Tensor,
        dt: torch.Tensor,
    ) -> torch.Tensor:
        """Single event step update."""
        rates = self.get_decay_rates()  # [hidden_dim]
        # dt: [batch, 1]
        decay = torch.exp(-dt * rates.unsqueeze(0))  # [batch, hidden_dim]

        dt_feat = torch.cat([dt, torch.log1p(dt)], dim=-1)
        x_emb = self.embed(sym)
        x_in = torch.cat([x_emb, dt_feat], dim=-1)
        in_drive = self.in_proj(x_in)
        rec_drive = self.recurrent_proj(h_prev)
        target = torch.tanh(rec_drive + in_drive)

        h_new = decay * h_prev + (1.0 - decay) * target
        return h_new

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
            h = self.step(h, sym, dt)
            all_h.append(h)

        logits = self.readout(h).squeeze(-1)
        if return_hidden:
            return logits, torch.stack(all_h, dim=1)
        return logits
