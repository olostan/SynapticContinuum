"""Source-shared exponential trace bank model for EXP-0001."""
from typing import Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class TraceBankModel(nn.Module):
    """Source-shared B=8 exponential leaky traces with learned sparse recurrent coupling.
    
    Maintains B timescales tau_b per unit:
      dz_jb/dt = (h_j - z_jb) / tau_b
    Incoming current:
      u_i = sum_(j in In(i)) sum_b C_ijb z_jb
    """
    def __init__(
        self,
        hidden_dim: int = 128,
        trace_bases: int = 8,
        max_degree: int = 8,
        vocab_size: int = 4,
        embed_dim: int = 16,
        seed: int = 42,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.trace_bases = trace_bases
        self.max_degree = max_degree

        self.embed = nn.Embedding(vocab_size, embed_dim)
        input_dim = embed_dim + 2  # embed + dt + log1p(dt)
        self.in_proj = nn.Linear(input_dim, hidden_dim)

        # Build fixed random sparse graph (each node receives from max_degree neighbors)
        rng = torch.Generator().manual_seed(seed)
        sources = []
        targets = []
        for i in range(hidden_dim):
            # choose max_degree distinct neighbors
            perm = torch.randperm(hidden_dim, generator=rng)
            nbrs = perm[:max_degree]
            for src in nbrs:
                sources.append(src.item())
                targets.append(i)

        self.num_edges = len(sources)
        self.register_buffer("sources", torch.tensor(sources, dtype=torch.long))
        self.register_buffer("targets", torch.tensor(targets, dtype=torch.long))

        # Learnable synaptic coupling weights: [num_edges, trace_bases]
        self.coupling = nn.Parameter(
            torch.randn(self.num_edges, trace_bases) / (max_degree * trace_bases) ** 0.5
        )

        # Log timescales: initialized spanning [0.5, 20.0]
        init_taus = torch.linspace(0.5, 20.0, trace_bases)
        self.log_tau = nn.Parameter(torch.log(init_taus))

        # State adaptation rate
        self.log_tau_state = nn.Parameter(torch.tensor(0.0))

        self.readout = nn.Linear(hidden_dim, 1)

    def get_taus(self) -> torch.Tensor:
        return torch.exp(torch.clamp(self.log_tau, min=-2.0, max=5.0))

    def step(
        self,
        h_prev: torch.Tensor,
        z_prev: torch.Tensor,
        sym: torch.Tensor,
        dt: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Update trace bank and state over elapsed dt with input event (sym).
        
        h_prev: [batch, hidden_dim]
        z_prev: [batch, hidden_dim, trace_bases]
        sym: [batch]
        dt: [batch, 1]
        """
        batch_size = h_prev.shape[0]
        taus = self.get_taus()  # [B]
        # decay: [batch, 1, B]
        decay = torch.exp(-dt.unsqueeze(-1) / taus.unsqueeze(0).unsqueeze(0))
        # Update trace filter
        z_new = decay * z_prev + (1.0 - decay) * h_prev.unsqueeze(-1)

        # Compute synaptic current via sparse coupling
        # z_edges: [batch, num_edges, B]
        z_edges = z_new[:, self.sources, :]
        # edge_current: [batch, num_edges]
        edge_current = (z_edges * self.coupling.unsqueeze(0)).sum(dim=-1)

        # Scatter add into targets
        u = torch.zeros(batch_size, self.hidden_dim, device=h_prev.device)
        u.scatter_add_(
            1,
            self.targets.unsqueeze(0).expand(batch_size, -1),
            edge_current,
        )

        dt_feat = torch.cat([dt, torch.log1p(dt)], dim=-1)
        x_emb = self.embed(sym)
        x_in = torch.cat([x_emb, dt_feat], dim=-1)
        in_drive = self.in_proj(x_in)

        # State transition
        tau_s = torch.exp(torch.clamp(self.log_tau_state, min=-2.0, max=3.0))
        gamma = 1.0 - torch.exp(-dt / tau_s)
        target = torch.tanh(u + in_drive)
        h_new = h_prev + gamma * (target - h_prev)

        return h_new, z_new

    def forward(
        self,
        batch: Dict[str, torch.Tensor],
        return_hidden: bool = False,
    ) -> torch.Tensor | Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        symbols = batch["symbols"]  # [batch, seq_len]
        delta_times = batch["delta_times"]  # [batch, seq_len]
        batch_size, seq_len = symbols.shape

        h = torch.zeros(batch_size, self.hidden_dim, device=symbols.device)
        z = torch.zeros(batch_size, self.hidden_dim, self.trace_bases, device=symbols.device)

        all_h = []
        all_z = []

        for t in range(seq_len):
            sym = symbols[:, t]
            dt = delta_times[:, t : t + 1]
            h, z = self.step(h, z, sym, dt)
            all_h.append(h)
            all_z.append(z)

        logits = self.readout(h).squeeze(-1)
        if return_hidden:
            return logits, torch.stack(all_h, dim=1), torch.stack(all_z, dim=1)
        return logits
