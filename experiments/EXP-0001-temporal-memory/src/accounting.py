"""Resource, parameter, and MAC accounting for EXP-0001 models."""
import os
import resource
from typing import Any, Dict
import torch
import torch.nn as nn


def count_parameters(model: nn.Module) -> Dict[str, Any]:
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    fixed_params = total_params - trainable_params
    
    # 4 bytes per float32 param
    weight_bytes = total_params * 4
    weight_mib = weight_bytes / (1024 * 1024)
    # Adam state: 2 moments + grad + param = 16 bytes/trainable param
    adam_mib = (trainable_params * 16 + fixed_params * 4) / (1024 * 1024)

    return {
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "fixed_parameters": fixed_params,
        "weight_mib": round(weight_mib, 4),
        "adam_mib": round(adam_mib, 4),
    }


def estimate_macs_per_step(model_name: str, hidden_dim: int = 128, **kwargs) -> int:
    """Analytical MAC estimation per sequence step."""
    name = model_name.lower()
    embed_dim = kwargs.get("embed_dim", 16)
    in_dim = embed_dim + 2

    if "majority" in name:
        return 0
    elif "arithmetic" in name:
        return 1  # 1 multiplication / comparison
    elif "mlp" in name:
        # 4 -> H -> H -> 1
        return (4 * hidden_dim) + (hidden_dim * hidden_dim) + (hidden_dim * 1)
    elif "reservoir" in name:
        # in_proj: in_dim * H, rec: H * H, readout: H * 1 (at final step)
        return (in_dim * hidden_dim) + (hidden_dim * hidden_dim)
    elif "gru" in name:
        # Standard GRU: 3 gates, each (in_dim + hidden_dim) * hidden_dim
        return 3 * (in_dim + hidden_dim) * hidden_dim
    elif "ssm" in name:
        # in_proj: in_dim * H, rec_proj: H * H, diagonal decay: H
        return (in_dim * hidden_dim) + (hidden_dim * hidden_dim) + hidden_dim
    elif "trace" in name:
        # in_proj: in_dim * H
        # trace update: B * H (decay)
        # sparse coupling: E * B (where E = max_degree * H)
        # state update: H
        B = kwargs.get("trace_bases", 8)
        deg = kwargs.get("max_degree", 8)
        E = deg * hidden_dim
        return (in_dim * hidden_dim) + (B * hidden_dim) + (E * B) + hidden_dim
    elif "fir" in name:
        # in_proj: in_dim * H
        # interpolation: ~4 ops * K * H
        # sparse taps: E * K (where E = max_degree * H)
        K = kwargs.get("fir_taps", 8)
        deg = kwargs.get("max_degree", 8)
        E = deg * hidden_dim
        return (in_dim * hidden_dim) + (4 * K * hidden_dim) + (E * K)
    else:
        return hidden_dim * hidden_dim


def get_peak_rss_mb() -> float:
    """Return peak resident set size in megabytes."""
    # On Linux, ru_maxrss is in KiB; on macOS, in bytes
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    import platform
    if platform.system() == "Darwin":
        return round(rss / (1024 * 1024), 2)
    return round(rss / 1024, 2)
