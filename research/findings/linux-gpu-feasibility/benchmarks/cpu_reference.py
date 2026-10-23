"""CPU reference implementations using NumPy and PyTorch (AVX2-optimized)."""

import numpy as np
import torch


class CPUReferenceEngine:
    def __init__(self):
        self.num_threads = torch.get_num_threads()

    def run_gemm_numpy(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        return np.matmul(A, B)

    def run_gemm_torch(self, A_t: torch.Tensor, B_t: torch.Tensor) -> torch.Tensor:
        return torch.matmul(A_t, B_t)

    def run_trace_decay_numpy(self, Z: np.ndarray, H: np.ndarray, alpha: np.ndarray) -> np.ndarray:
        # Z: (N, K), H: (N,), alpha: (K,)
        # H[:, None] broadcasts across K
        return alpha * Z + (1.0 - alpha) * H[:, None]

    def run_trace_decay_torch(self, Z_t: torch.Tensor, H_t: torch.Tensor, alpha_t: torch.Tensor) -> torch.Tensor:
        return alpha_t * Z_t + (1.0 - alpha_t) * H_t.unsqueeze(-1)

    def run_recurrent_step_numpy(self, W: np.ndarray, h: np.ndarray, b: np.ndarray, x: np.ndarray) -> np.ndarray:
        return np.tanh(np.dot(W, h) + b + x)

    def run_recurrent_step_torch(self, W_t: torch.Tensor, h_t: torch.Tensor, b_t: torch.Tensor, x_t: torch.Tensor) -> torch.Tensor:
        return torch.tanh(torch.matmul(W_t, h_t) + b_t + x_t)

    def run_sparse_scatter_numpy(self, src: np.ndarray, dst: np.ndarray, weights: np.ndarray, h_in: np.ndarray, num_dst: int) -> np.ndarray:
        out = np.zeros(num_dst, dtype=np.float32)
        np.add.at(out, dst, weights * h_in[src])
        return out

    def run_sparse_scatter_torch(self, src_t: torch.Tensor, dst_t: torch.Tensor, weights_t: torch.Tensor, h_in_t: torch.Tensor, num_dst: int) -> torch.Tensor:
        out = torch.zeros(num_dst, dtype=torch.float32)
        vals = weights_t * h_in_t[src_t]
        out.scatter_add_(0, dst_t, vals)
        return out

    def run_event_driven_sparse_cpu(self, active_src_nodes: list[int], adj_list: list[list[tuple[int, float]]], h_in: np.ndarray, num_dst: int) -> np.ndarray:
        """Pure event-driven simulation: only traverse edges from actively firing nodes."""
        out = np.zeros(num_dst, dtype=np.float32)
        for src in active_src_nodes:
            val = h_in[src]
            if val != 0.0:
                for dst, w in adj_list[src]:
                    out[dst] += w * val
        return out

    def run_recurrent_step_autograd_torch(self, W_t: torch.Tensor, h_t: torch.Tensor, x_t: torch.Tensor) -> float:
        """Forward + backward pass on recurrent step."""
        W_param = W_t.clone().detach().requires_grad_(True)
        h_next = torch.tanh(torch.matmul(W_param, h_t) + x_t)
        loss = h_next.sum()
        loss.backward()
        return float(loss.item())
