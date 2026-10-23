"""Sparse Finite Impulse Response (FIR) model with causal delay taps for EXP-0001."""
from typing import Dict, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class SparseFIRModel(nn.Module):
    """Sparse FIR with fixed random degree <= 8 per node, K=8 taps, learned coefficients.
    
    Causal continuous-time delay interpolation:
      u_i(t) = sum_(j in In(i)) sum_(k=1..K) W_ijk * h_j(t - tau_k)
    Missing past history before t=0 is zero-padded.
    """
    def __init__(
        self,
        hidden_dim: int = 128,
        fir_taps: int = 8,
        max_degree: int = 8,
        vocab_size: int = 4,
        embed_dim: int = 16,
        seed: int = 42,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.fir_taps = fir_taps
        self.max_degree = max_degree

        self.embed = nn.Embedding(vocab_size, embed_dim)
        input_dim = embed_dim + 2  # embed + dt + log1p(dt)
        self.in_proj = nn.Linear(input_dim, hidden_dim)

        # Build fixed random sparse graph
        rng = torch.Generator().manual_seed(seed)
        sources = []
        targets = []
        for i in range(hidden_dim):
            perm = torch.randperm(hidden_dim, generator=rng)
            nbrs = perm[:max_degree]
            for src in nbrs:
                sources.append(src.item())
                targets.append(i)

        self.num_edges = len(sources)
        self.register_buffer("sources", torch.tensor(sources, dtype=torch.long))
        self.register_buffer("targets", torch.tensor(targets, dtype=torch.long))

        # Learnable FIR tap coefficients: [num_edges, fir_taps]
        self.tap_weights = nn.Parameter(
            torch.randn(self.num_edges, fir_taps) / (max_degree * fir_taps) ** 0.5
        )

        # Tap delays tau_k: initialized evenly across [0.5, 15.0]
        init_delays = torch.linspace(0.5, 15.0, fir_taps)
        self.log_delays = nn.Parameter(torch.log(init_delays))

        self.readout = nn.Linear(hidden_dim, 1)

    def get_delays(self) -> torch.Tensor:
        return torch.exp(torch.clamp(self.log_delays, min=-2.0, max=4.0))

    def interpolate_history(
        self,
        history_h: List[torch.Tensor],
        history_t: List[torch.Tensor],
        t_curr: torch.Tensor,
        delays: torch.Tensor,
    ) -> torch.Tensor:
        """Causally interpolate past hidden state h at t_curr - delay.
        
        history_h: list of m tensors each [batch, hidden_dim]
        history_t: list of m tensors each [batch, 1]
        t_curr: [batch, 1]
        delays: [K]
        Returns: [batch, hidden_dim, K]
        """
        batch_size = t_curr.shape[0]
        K = delays.shape[0]
        # query_times: [batch, K]
        query_times = t_curr - delays.unsqueeze(0)

        # If no prior history, return zeros
        if not history_h:
            return torch.zeros(batch_size, self.hidden_dim, K, device=t_curr.device)

        m = len(history_h)
        # Stack history: [batch, m, hidden_dim]
        H = torch.stack(history_h, dim=1)
        # Stack times: [batch, m]
        T = torch.cat(history_t, dim=1)

        # For each tap k, interpolate causally
        interp_taps = []
        for k in range(K):
            q_t = query_times[:, k : k + 1]  # [batch, 1]

            # Find interval in history where T[:, a] <= q_t < T[:, a+1]
            # If q_t < T[:, 0], result is zero (before start of history)
            # If q_t >= T[:, -1], extrapolate with constant last state
            h_interp = torch.zeros(batch_size, self.hidden_dim, device=t_curr.device)

            if m == 1:
                # Only 1 past point: active if q_t >= T[:, 0]
                mask = (q_t >= T[:, 0:1]).float()  # [batch, 1]
                h_interp = H[:, 0, :] * mask
            else:
                # Multi-point piecewise linear causal interpolation
                # Weight from preceding point and next point
                for a in range(m - 1):
                    t_a = T[:, a : a + 1]
                    t_b = T[:, a + 1 : a + 2]
                    interval_mask = ((q_t >= t_a) & (q_t < t_b)).float()
                    denom = torch.clamp(t_b - t_a, min=1e-5)
                    alpha = (q_t - t_a) / denom
                    interp_val = (1.0 - alpha) * H[:, a, :] + alpha * H[:, a + 1, :]
                    h_interp = h_interp + interval_mask * interp_val

                # For q_t >= T[:, -1]
                end_mask = (q_t >= T[:, -1:]).float()
                h_interp = h_interp + end_mask * H[:, -1, :]

            interp_taps.append(h_interp)

        return torch.stack(interp_taps, dim=-1)  # [batch, hidden_dim, K]

    def forward(
        self,
        batch: Dict[str, torch.Tensor],
        return_hidden: bool = False,
    ) -> torch.Tensor | Tuple[torch.Tensor, torch.Tensor]:
        symbols = batch["symbols"]  # [batch, seq_len]
        delta_times = batch["delta_times"]  # [batch, seq_len]
        timestamps = batch["timestamps"]  # [batch, seq_len]
        batch_size, seq_len = symbols.shape

        delays = self.get_delays()  # [K]
        h = torch.zeros(batch_size, self.hidden_dim, device=symbols.device)
        history_h: List[torch.Tensor] = []
        history_t: List[torch.Tensor] = []
        all_h = []

        for step_idx in range(seq_len):
            sym = symbols[:, step_idx]
            dt = delta_times[:, step_idx : step_idx + 1]
            t_curr = timestamps[:, step_idx : step_idx + 1]

            # Interpolate past history at tap delays
            # h_taps: [batch, hidden_dim, K]
            h_taps = self.interpolate_history(history_h, history_t, t_curr, delays)

            # Gather for sparse edges: sources
            # h_edges: [batch, num_edges, K]
            h_edges = h_taps[:, self.sources, :]
            # Multiply by tap weights: [num_edges, K]
            edge_current = (h_edges * self.tap_weights.unsqueeze(0)).sum(dim=-1)

            # Scatter add into targets
            u = torch.zeros(batch_size, self.hidden_dim, device=symbols.device)
            u.scatter_add_(
                1,
                self.targets.unsqueeze(0).expand(batch_size, -1),
                edge_current,
            )

            dt_feat = torch.cat([dt, torch.log1p(dt)], dim=-1)
            x_emb = self.embed(sym)
            x_in = torch.cat([x_emb, dt_feat], dim=-1)
            in_drive = self.in_proj(x_in)

            # Update hidden state
            h = torch.tanh(u + in_drive)
            all_h.append(h)

            # Store in causal history
            history_h.append(h)
            history_t.append(t_curr)

        logits = self.readout(h).squeeze(-1)
        if return_hidden:
            return logits, torch.stack(all_h, dim=1)
        return logits
