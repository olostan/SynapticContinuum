"""Training loop, validation selection, and early stopping for EXP-0001."""
import copy
import time
from typing import Any, Dict, Tuple
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from src.eval import evaluate_model


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    lr: float = 0.001,
    max_epochs: int = 25,
    patience: int = 5,
    device: str = "cpu",
) -> Tuple[nn.Module, Dict[str, Any]]:
    """Train model with validation early stopping and best-checkpoint selection."""
    model.to(device)

    # Check if model has trainable parameters
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    if not trainable_params:
        # Non-trainable model (Majority, Arithmetic Oracle)
        initial_val = evaluate_model(model, val_loader, device=device)
        return model, {
            "epochs_trained": 0,
            "train_time_sec": 0.0,
            "best_epoch": 0,
            "best_val_loss": initial_val["loss"],
            "best_val_balanced_acc": initial_val["balanced_accuracy"],
            "converged": True,
        }

    optimizer = torch.optim.Adam(trainable_params, lr=lr)
    criterion = nn.BCEWithLogitsLoss()

    best_val_loss = float("inf")
    best_val_acc = 0.0
    best_weights = copy.deepcopy(model.state_dict())
    best_epoch = 0
    patience_counter = 0

    start_time = time.time()

    for epoch in range(1, max_epochs + 1):
        model.train()
        total_train_loss = 0.0
        train_samples = 0

        for batch in train_loader:
            labels = batch["labels"].to(device)
            batch_dev = {k: v.to(device) for k, v in batch.items()}

            optimizer.zero_grad()
            logits = model(batch_dev)
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=2.0)
            optimizer.step()

            total_train_loss += loss.item() * labels.shape[0]
            train_samples += labels.shape[0]

        # Evaluate on validation split
        val_metrics = evaluate_model(model, val_loader, device=device)
        val_loss = val_metrics["loss"]

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            best_val_acc = val_metrics["balanced_accuracy"]
            best_epoch = epoch
            best_weights = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    train_time = round(time.time() - start_time, 2)
    # Restore best validation weights
    model.load_state_dict(best_weights)

    return model, {
        "epochs_trained": epoch,
        "train_time_sec": train_time,
        "best_epoch": best_epoch,
        "best_val_loss": round(best_val_loss, 4),
        "best_val_balanced_acc": round(best_val_acc, 4),
        "early_stopped": patience_counter >= patience,
    }
