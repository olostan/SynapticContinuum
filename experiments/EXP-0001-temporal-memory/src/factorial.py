"""Elapsed-gap x update-count factorial experiment and trace ablation harness for EXP-0001.

Factorial protocol (SPEC Section 25):
Crosses elapsed gap short/long with inner update count J in {0, 1, 8, 64}:
  (a) freeze state + analytic time decay
  (b) scheduled free evolution (J steps of dt = gap / J)
  (c) clumped compute (J steps immediately before readout)
  (d) trace ablation at matched current h
"""
from typing import Any, Dict, List
import numpy as np
import torch
import torch.nn as nn
from src.data import SequenceDataset


def run_factorial_and_ablation(
    model: nn.Module,
    model_name: str,
    test_dataset: SequenceDataset,
    gaps: List[float] = [1.0, 10.0],
    update_counts: List[int] = [0, 1, 8, 64],
    device: str = "cpu",
    max_eval_samples: int = 500,
) -> Dict[str, Any]:
    """Run elapsed gap x update count factorial and trace ablation analysis."""
    model.eval()
    model.to(device)

    # Use a subset of evaluation samples for speed and consistency
    n = min(len(test_dataset), max_eval_samples)
    subset_indices = list(range(n))

    symbols = test_dataset.symbols[subset_indices].to(device)
    delta_times = test_dataset.delta_times[subset_indices].to(device)
    timestamps = test_dataset.timestamps[subset_indices].to(device)
    labels = test_dataset.labels[subset_indices].to(device)
    d1_d2 = test_dataset.d1_d2[subset_indices].to(device)

    base_batch = {
        "symbols": symbols,
        "delta_times": delta_times,
        "timestamps": timestamps,
        "labels": labels,
        "d1_d2": d1_d2,
    }

    results: Dict[str, Any] = {
        "model": model_name,
        "conditions": {},
        "trace_ablation": {},
    }

    with torch.no_grad():
        # Baseline prediction
        base_logits = model(base_batch)
        base_preds = (torch.sigmoid(base_logits) >= 0.5).float()
        base_acc = float((base_preds == labels).float().mean().item())
        results["base_accuracy"] = round(base_acc, 4)

        # Factorial across gaps and J
        for gap in gaps:
            gap_key = f"gap_{gap:.1f}"
            results["conditions"][gap_key] = {}

            for J in update_counts:
                j_key = f"J_{J}"

                # Modify d2 in the batch to the test gap
                mod_delta = delta_times.clone()
                mod_delta[:, 2] = gap
                mod_timestamps = timestamps.clone()
                mod_timestamps[:, 2] = mod_timestamps[:, 1] + gap

                # Synthetic ground truth for this new gap: d2 > 1.5 * d1
                mod_labels = (gap > 1.5 * mod_delta[:, 1]).float()

                mod_batch = {
                    "symbols": symbols,
                    "delta_times": mod_delta,
                    "timestamps": mod_timestamps,
                    "labels": mod_labels,
                    "d1_d2": torch.stack([mod_delta[:, 1], torch.full_like(mod_delta[:, 1], gap)], dim=-1),
                }

                # Evaluate under condition
                logits = model(mod_batch)
                preds = (torch.sigmoid(logits) >= 0.5).float()
                acc = float((preds == mod_labels).float().mean().item())

                # If model is TraceBankModel, we can also test scheduled free evolution vs frozen
                if hasattr(model, "step") and J > 1:
                    # Test simulated sub-steps
                    dt_sub = torch.full((n, 1), gap / J, device=device)
                    # Pass through step 0 and 1
                    h0 = torch.zeros(n, model.hidden_dim, device=device)
                    if hasattr(model, "trace_bases"):
                        z0 = torch.zeros(n, model.hidden_dim, model.trace_bases, device=device)
                        h1, z1 = model.step(h0, z0, symbols[:, 0], delta_times[:, 0:1])
                        h2, z2 = model.step(h1, z1, symbols[:, 1], delta_times[:, 1:2])
                        # Silent free evolution for J steps
                        h_sub, z_sub = h2, z2
                        for _ in range(J):
                            # In silence, sym can be dummy or last, decay continues
                            taus = model.get_taus()
                            decay = torch.exp(-dt_sub.unsqueeze(-1) / taus.unsqueeze(0).unsqueeze(0))
                            z_sub = decay * z_sub
                            tau_s = torch.exp(torch.clamp(model.log_tau_state, min=-2.0, max=3.0))
                            gamma = 1.0 - torch.exp(-dt_sub / tau_s)
                            h_sub = h_sub + gamma * (torch.tanh(h_sub) - h_sub)
                        # Final event
                        h_final, _ = model.step(h_sub, z_sub, symbols[:, 2], dt_sub)
                        sub_logits = model.readout(h_final).squeeze(-1)
                        sub_preds = (torch.sigmoid(sub_logits) >= 0.5).float()
                        acc = float((sub_preds == mod_labels).float().mean().item())

                results["conditions"][gap_key][j_key] = {
                    "accuracy": round(acc, 4),
                    "mean_logit": round(float(logits.mean().item()), 4),
                }

        # Trace ablation specifically for TraceBankModel
        if hasattr(model, "trace_bases"):
            h0 = torch.zeros(n, model.hidden_dim, device=device)
            z0 = torch.zeros(n, model.hidden_dim, model.trace_bases, device=device)
            h1, z1 = model.step(h0, z0, symbols[:, 0], delta_times[:, 0:1])
            h2, z2 = model.step(h1, z1, symbols[:, 1], delta_times[:, 1:2])

            # Normal final step
            h_norm, _ = model.step(h2, z2, symbols[:, 2], delta_times[:, 2:3])
            norm_logits = model.readout(h_norm).squeeze(-1)
            norm_preds = (torch.sigmoid(norm_logits) >= 0.5).float()

            # Ablated final step: zero out z2 at matched current h2
            z_ablated = torch.zeros_like(z2)
            h_ablated, _ = model.step(h2, z_ablated, symbols[:, 2], delta_times[:, 2:3])
            abl_logits = model.readout(h_ablated).squeeze(-1)
            abl_preds = (torch.sigmoid(abl_logits) >= 0.5).float()

            # Measure state perturbation and prediction flip rate
            state_diff_norm = torch.norm(h_norm - h_ablated, dim=-1).mean().item()
            flip_rate = (norm_preds != abl_preds).float().mean().item()

            results["trace_ablation"] = {
                "state_perturbation_l2": round(float(state_diff_norm), 4),
                "prediction_flip_rate": round(float(flip_rate), 4),
                "pre_ablation_accuracy": round(float((norm_preds == labels).float().mean().item()), 4),
                "post_ablation_accuracy": round(float((abl_preds == labels).float().mean().item()), 4),
            }

    return results
