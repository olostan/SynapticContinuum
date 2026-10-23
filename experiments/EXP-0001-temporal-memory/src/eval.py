"""Evaluation metrics and evaluation harness for EXP-0001."""
from typing import Any, Dict
import torch
import torch.nn as nn
from torch.utils.data import DataLoader


def evaluate_model(
    model: nn.Module,
    data_loader: DataLoader,
    device: str = "cpu",
) -> Dict[str, Any]:
    """Evaluate model on a dataset and return loss, balanced accuracy, TPR, TNR."""
    model.eval()
    criterion = nn.BCEWithLogitsLoss()

    total_loss = 0.0
    total_samples = 0
    tp = 0
    tn = 0
    fp = 0
    fn = 0

    with torch.no_grad():
        for batch in data_loader:
            labels = batch["labels"].to(device)
            # Send batch tensors to device
            batch_dev = {k: v.to(device) for k, v in batch.items()}
            logits = model(batch_dev)

            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.shape[0]
            total_samples += labels.shape[0]

            preds = (torch.sigmoid(logits) >= 0.5).float()
            pos = labels == 1.0
            neg = labels == 0.0

            tp += int(((preds == 1.0) & pos).sum().item())
            tn += int(((preds == 0.0) & neg).sum().item())
            fp += int(((preds == 1.0) & neg).sum().item())
            fn += int(((preds == 0.0) & pos).sum().item())

    avg_loss = total_loss / max(total_samples, 1)
    acc = (tp + tn) / max(total_samples, 1)
    tpr = tp / max(tp + fn, 1)
    tnr = tn / max(tn + fp, 1)
    balanced_acc = 0.5 * (tpr + tnr)

    return {
        "loss": round(float(avg_loss), 4),
        "balanced_accuracy": round(float(balanced_acc), 4),
        "accuracy": round(float(acc), 4),
        "tpr": round(float(tpr), 4),
        "tnr": round(float(tnr), 4),
        "samples": total_samples,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }
