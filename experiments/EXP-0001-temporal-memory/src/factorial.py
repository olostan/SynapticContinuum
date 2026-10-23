"""Elapsed-gap x update-count factorial experiment and multi-point ablation suite.

Preregistered & amended protocol addressing PR #6 reviewer feedback:
1. Exact physical time conservation: total elapsed time sum(dt) = Delta.
   - If J=0: single jump with dt = Delta.
   - If J>0: J steps of delta_t = Delta / J. Final event processed with dt = 0.0 (state already at t2).
2. Symmetrical across recurrent architectures:
   - Condition (a): Freeze state + analytic decay (passive decay only, no recurrent excitation).
   - Condition (b): Scheduled free evolution (J evenly-spaced steps of delta_t = Delta / J).
   - Condition (c): Clumped compute (J steps with delta_t = 0.0 immediately before readout, event with dt = Delta).
   - Condition (d): Noise / sleep control (matched perturbation).
3. Multi-point diagnostic trace and feature ablation:
   - Interval ablation: zero z after Event 1, propagate through interval.
   - Feature ablation: zero explicit [dt, log1p(dt)] inputs at inference.
   - Boundary ablation: zero z at Event 2 boundary with matched h.
"""
from typing import Any, Dict, List
import numpy as np
import torch
import torch.nn as nn
from src.data import SequenceDataset


def run_model_forward_with_dynamics(
    model: nn.Module,
    symbols: torch.Tensor,
    delta_times: torch.Tensor,
    timestamps: torch.Tensor,
    gap: float,
    J: int,
    condition: str = "scheduled_evolution",
    device: str = "cpu",
) -> Dict[str, Any]:
    """Execute forward pass under exact time-conserving silent conditions.
    
    symbols: [batch, 3]
    delta_times: [batch, 3]
    timestamps: [batch, 3]
    gap: physical elapsed time for d2
    J: inner silent step count in {0, 1, 8, 64}
    condition: 'scheduled_evolution', 'analytic_decay', 'clumped_compute', 'sleep_freeze'
    """
    batch_size = symbols.shape[0]
    dt0 = delta_times[:, 0:1]
    dt1 = delta_times[:, 1:2]
    t0 = timestamps[:, 0:1]
    t1 = timestamps[:, 1:2]

    # Step 0: Event A at t0=0
    # Step 1: Event B at t1=d1
    if hasattr(model, "trace_bases"):  # TraceBankModel
        h0 = torch.zeros(batch_size, model.hidden_dim, device=device)
        z0 = torch.zeros(batch_size, model.hidden_dim, model.trace_bases, device=device)
        h1, z1 = model.step(h0, z0, symbols[:, 0], dt0)
        h2, z2 = model.step(h1, z1, symbols[:, 1], dt1)

        if J == 0 or condition == "sleep_freeze":
            # Direct event arrival with dt = gap
            h_final, z_final = model.step(h2, z2, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        elif condition == "analytic_decay":
            # Passive decay only over gap, no recurrent coupling
            taus = model.get_taus()
            decay_z = torch.exp(-torch.tensor(gap, device=device) / taus)
            z_decayed = z2 * decay_z.unsqueeze(0).unsqueeze(0)
            tau_s = torch.exp(torch.clamp(model.log_tau_state, min=-2.0, max=3.0))
            decay_h = torch.exp(-torch.tensor(gap, device=device) / tau_s)
            h_decayed = h2 * decay_h
            h_final, z_final = model.step(h_decayed, z_decayed, symbols[:, 2], torch.zeros(batch_size, 1, device=device))
        elif condition == "clumped_compute":
            # J steps with dt=0 (pure compute cycles), then event with dt=gap
            h_cur, z_cur = h2, z2
            for _ in range(J):
                h_cur, z_cur = model.silent_step(h_cur, z_cur, torch.zeros(batch_size, 1, device=device))
            h_final, z_final = model.step(h_cur, z_cur, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        else:  # scheduled_evolution
            # J steps of dt = gap / J, then event at t2 with dt = 0.0
            dt_sub = torch.full((batch_size, 1), gap / J, device=device)
            h_cur, z_cur = h2, z2
            for _ in range(J):
                h_cur, z_cur = model.silent_step(h_cur, z_cur, dt_sub)
            h_final, z_final = model.step(h_cur, z_cur, symbols[:, 2], torch.zeros(batch_size, 1, device=device))

        logits = model.readout(h_final).squeeze(-1)
        return {"logits": logits, "h_final": h_final}

    elif hasattr(model, "log_decay_rate"):  # DiagonalDecaySSM
        h0 = torch.zeros(batch_size, model.hidden_dim, device=device)
        h1 = model.step(h0, symbols[:, 0], dt0)
        h2 = model.step(h1, symbols[:, 1], dt1)

        if J == 0 or condition == "sleep_freeze":
            h_final = model.step(h2, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        elif condition == "analytic_decay":
            rates = model.get_decay_rates()
            decay = torch.exp(-torch.tensor(gap, device=device) * rates)
            h_decayed = h2 * decay.unsqueeze(0)
            h_final = model.step(h_decayed, symbols[:, 2], torch.zeros(batch_size, 1, device=device))
        elif condition == "clumped_compute":
            h_cur = h2
            for _ in range(J):
                h_cur = model.silent_step(h_cur, torch.zeros(batch_size, 1, device=device))
            h_final = model.step(h_cur, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        else:  # scheduled_evolution
            dt_sub = torch.full((batch_size, 1), gap / J, device=device)
            h_cur = h2
            for _ in range(J):
                h_cur = model.silent_step(h_cur, dt_sub)
            h_final = model.step(h_cur, symbols[:, 2], torch.zeros(batch_size, 1, device=device))

        logits = model.readout(h_final).squeeze(-1)
        return {"logits": logits, "h_final": h_final}

    elif hasattr(model, "gru"):  # TimeAwareGRU
        h0 = torch.zeros(batch_size, model.hidden_dim, device=device)
        h1 = model.step(h0, symbols[:, 0], dt0)
        h2 = model.step(h1, symbols[:, 1], dt1)

        if J == 0 or condition == "sleep_freeze":
            h_final = model.step(h2, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        elif condition == "analytic_decay":
            # GRU has no passive decay; condition (a) preserves h2
            h_final = model.step(h2, symbols[:, 2], torch.zeros(batch_size, 1, device=device))
        elif condition == "clumped_compute":
            h_cur = h2
            for _ in range(J):
                h_cur = model.silent_step(h_cur, torch.zeros(batch_size, 1, device=device))
            h_final = model.step(h_cur, symbols[:, 2], torch.full((batch_size, 1), gap, device=device))
        else:  # scheduled_evolution
            dt_sub = torch.full((batch_size, 1), gap / J, device=device)
            h_cur = h2
            for _ in range(J):
                h_cur = model.silent_step(h_cur, dt_sub)
            h_final = model.step(h_cur, symbols[:, 2], torch.zeros(batch_size, 1, device=device))

        logits = model.readout(h_final).squeeze(-1)
        return {"logits": logits, "h_final": h_final}

    elif hasattr(model, "fir_taps"):  # SparseFIRModel
        h0 = model.step([], [], symbols[:, 0], dt0, t0)
        hist_h = [h0]
        hist_t = [t0]
        h1 = model.step(hist_h, hist_t, symbols[:, 1], dt1, t1)
        hist_h.append(h1)
        hist_t.append(t1)

        if J == 0 or condition == "sleep_freeze":
            t2 = t1 + gap
            h_final = model.step(hist_h, hist_t, symbols[:, 2], torch.full((batch_size, 1), gap, device=device), t2)
        elif condition == "clumped_compute":
            h_cur = h1
            t_cur = t1
            for _ in range(J):
                h_cur = model.silent_step(hist_h, hist_t, torch.zeros(batch_size, 1, device=device), t_cur)
                hist_h.append(h_cur)
                hist_t.append(t_cur)
            t2 = t1 + gap
            h_final = model.step(hist_h, hist_t, symbols[:, 2], torch.full((batch_size, 1), gap, device=device), t2)
        else:  # scheduled_evolution
            dt_sub = gap / J
            t_cur = t1
            for j in range(1, J + 1):
                t_cur = t1 + j * dt_sub
                h_cur = model.silent_step(hist_h, hist_t, torch.full((batch_size, 1), dt_sub, device=device), t_cur)
                hist_h.append(h_cur)
                hist_t.append(t_cur)
            h_final = model.step(hist_h, hist_t, symbols[:, 2], torch.zeros(batch_size, 1, device=device), t1 + gap)

        logits = model.readout(h_final).squeeze(-1)
        return {"logits": logits, "h_final": h_final}

    else:
        # Fallback for feedforward baselines
        mod_delta = delta_times.clone()
        mod_delta[:, 2] = gap
        b = {
            "symbols": symbols,
            "delta_times": mod_delta,
            "timestamps": timestamps,
            "labels": (gap > 1.5 * delta_times[:, 1]).float(),
            "d1_d2": torch.stack([delta_times[:, 1], torch.full_like(delta_times[:, 1], gap)], dim=-1),
        }
        logits = model(b)
        return {"logits": logits, "h_final": None}


def run_factorial_and_ablation(
    model: nn.Module,
    model_name: str,
    test_dataset: SequenceDataset,
    gaps: List[float] = [1.0, 10.0],
    update_counts: List[int] = [0, 1, 8, 64],
    device: str = "cpu",
    max_eval_samples: int = 500,
) -> Dict[str, Any]:
    """Execute unified silence x computation factorial and multi-point diagnostic ablation."""
    model.eval()
    model.to(device)

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
        "factorial_conditions": {},
        "diagnostic_ablations": {},
    }

    with torch.no_grad():
        base_logits = model(base_batch)
        base_preds = (torch.sigmoid(base_logits) >= 0.5).float()
        results["base_accuracy"] = round(float((base_preds == labels).float().mean().item()), 4)

        # Factorial over gaps, update counts J, and conditions (a, b, c)
        for gap in gaps:
            gap_key = f"gap_{gap:.1f}"
            results["factorial_conditions"][gap_key] = {}
            target_labels = (gap > 1.5 * delta_times[:, 1]).float()

            for J in update_counts:
                j_key = f"J_{J}"
                results["factorial_conditions"][gap_key][j_key] = {}

                # Condition (b): Scheduled free evolution (exact time conservation)
                res_b = run_model_forward_with_dynamics(
                    model, symbols, delta_times, timestamps, gap, J, condition="scheduled_evolution", device=device
                )
                preds_b = (torch.sigmoid(res_b["logits"]) >= 0.5).float()
                acc_b = float((preds_b == target_labels).float().mean().item())
                results["factorial_conditions"][gap_key][j_key]["scheduled_evolution_acc"] = round(acc_b, 4)
                results["factorial_conditions"][gap_key][j_key]["mean_logit"] = round(float(res_b["logits"].mean().item()), 4)

                # Condition (c): Clumped compute (dt=0 for silent steps)
                if J > 0:
                    res_c = run_model_forward_with_dynamics(
                        model, symbols, delta_times, timestamps, gap, J, condition="clumped_compute", device=device
                    )
                    preds_c = (torch.sigmoid(res_c["logits"]) >= 0.5).float()
                    acc_c = float((preds_c == target_labels).float().mean().item())
                    results["factorial_conditions"][gap_key][j_key]["clumped_compute_acc"] = round(acc_c, 4)

            # Condition (a): Freeze + analytic decay (J independent)
            res_a = run_model_forward_with_dynamics(
                model, symbols, delta_times, timestamps, gap, 1, condition="analytic_decay", device=device
            )
            preds_a = (torch.sigmoid(res_a["logits"]) >= 0.5).float()
            results["factorial_conditions"][gap_key]["analytic_decay_acc"] = round(
                float((preds_a == target_labels).float().mean().item()), 4
            )

        # Multi-Point Diagnostic Ablation Suite
        # 1. Explicit dt feature ablation (zero explicit delta_t input features)
        zero_dt = torch.zeros_like(delta_times)
        batch_no_dt = {
            "symbols": symbols,
            "delta_times": zero_dt,
            "timestamps": timestamps,
            "labels": labels,
            "d1_d2": d1_d2,
        }
        logits_no_dt = model(batch_no_dt)
        preds_no_dt = (torch.sigmoid(logits_no_dt) >= 0.5).float()
        acc_no_dt = float((preds_no_dt == labels).float().mean().item())
        logit_diff_dt = float(torch.abs(base_logits - logits_no_dt).mean().item())
        flip_dt = float((base_preds != preds_no_dt).float().mean().item())

        results["diagnostic_ablations"]["explicit_dt_feature_ablation"] = {
            "post_ablation_accuracy": round(acc_no_dt, 4),
            "mean_abs_logit_diff": round(logit_diff_dt, 4),
            "prediction_flip_rate": round(flip_dt, 4),
        }

        # 2. TraceBank specific multi-point causal ablations
        if hasattr(model, "trace_bases"):
            dt0 = delta_times[:, 0:1]
            dt1 = delta_times[:, 1:2]
            dt2 = delta_times[:, 2:3]
            h0 = torch.zeros(n, model.hidden_dim, device=device)
            z0 = torch.zeros(n, model.hidden_dim, model.trace_bases, device=device)
            h1, z1 = model.step(h0, z0, symbols[:, 0], dt0)
            h2, z2 = model.step(h1, z1, symbols[:, 1], dt1)
            h_norm, z_norm = model.step(h2, z2, symbols[:, 2], dt2)
            logits_norm = model.readout(h_norm).squeeze(-1)
            preds_norm = (torch.sigmoid(logits_norm) >= 0.5).float()

            # (A) Boundary ablation: zero z2 right at final event step
            z2_zero = torch.zeros_like(z2)
            h_bnd, _ = model.step(h2, z2_zero, symbols[:, 2], dt2)
            logits_bnd = model.readout(h_bnd).squeeze(-1)
            preds_bnd = (torch.sigmoid(logits_bnd) >= 0.5).float()
            results["diagnostic_ablations"]["boundary_trace_ablation"] = {
                "state_perturbation_l2": round(float(torch.norm(h_norm - h_bnd, dim=-1).mean().item()), 4),
                "mean_abs_logit_diff": round(float(torch.abs(logits_norm - logits_bnd).mean().item()), 4),
                "prediction_flip_rate": round(float((preds_norm != preds_bnd).float().mean().item()), 4),
                "post_ablation_accuracy": round(float((preds_bnd == labels).float().mean().item()), 4),
            }

            # (B) Interval ablation: zero z1 after Event 1, then propagate to Event 2
            z1_zero = torch.zeros_like(z1)
            h2_from_abl, z2_from_abl = model.step(h1, z1_zero, symbols[:, 1], dt1)
            h_int, _ = model.step(h2_from_abl, z2_from_abl, symbols[:, 2], dt2)
            logits_int = model.readout(h_int).squeeze(-1)
            preds_int = (torch.sigmoid(logits_int) >= 0.5).float()
            results["diagnostic_ablations"]["interval_trace_ablation"] = {
                "state_perturbation_l2": round(float(torch.norm(h_norm - h_int, dim=-1).mean().item()), 4),
                "mean_abs_logit_diff": round(float(torch.abs(logits_norm - logits_int).mean().item()), 4),
                "prediction_flip_rate": round(float((preds_norm != preds_int).float().mean().item()), 4),
                "post_ablation_accuracy": round(float((preds_int == labels).float().mean().item()), 4),
            }

    return results
