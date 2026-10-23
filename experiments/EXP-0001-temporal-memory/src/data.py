"""Data generation, regimes, rejection sampling, and split auditing for EXP-0001.

Synthetic sequences of three symbols A, B, C with timestamps t=(0, d1, d1+d2).
Main classification label: y = 1[d2 > 1.5 * d1].
"""
import hashlib
from typing import Any, Dict, List, NamedTuple, Set, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class SequenceSample(NamedTuple):
    symbols: List[int]
    delta_times: List[float]
    timestamps: List[float]
    label: int
    d1: float
    d2: float


class SequenceDataset(Dataset):
    def __init__(self, samples: List[SequenceSample]):
        self.samples = samples
        self.symbols = torch.tensor([s.symbols for s in samples], dtype=torch.long)
        self.delta_times = torch.tensor([s.delta_times for s in samples], dtype=torch.float32)
        self.timestamps = torch.tensor([s.timestamps for s in samples], dtype=torch.float32)
        self.labels = torch.tensor([s.label for s in samples], dtype=torch.float32)
        self.d1_d2 = torch.tensor([[s.d1, s.d2] for s in samples], dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "symbols": self.symbols[idx],
            "delta_times": self.delta_times[idx],
            "timestamps": self.timestamps[idx],
            "labels": self.labels[idx],
            "d1_d2": self.d1_d2[idx],
        }


def sample_single_pair(
    rng: np.random.Generator,
    d1_range: Tuple[float, float],
    d2_range: Tuple[float, float],
    d1_excluded: Tuple[float, float] = None,
    target_label: int = None,
    epsilon: float = 0.05,
    max_attempts: int = 10000,
) -> Tuple[float, float, int]:
    """Sample a valid (d1, d2) pair respecting bounds, exclusions, and target label."""
    for _ in range(max_attempts):
        d1 = rng.uniform(d1_range[0], d1_range[1])
        if d1_excluded is not None and (d1_excluded[0] <= d1 <= d1_excluded[1]):
            continue
        d2 = rng.uniform(d2_range[0], d2_range[1])

        diff = d2 - 1.5 * d1
        if abs(diff) < epsilon:
            continue

        label = 1 if diff > 0 else 0
        if target_label is not None and label != target_label:
            continue

        return float(d1), float(d2), label

    raise RuntimeError(
        f"Failed to sample (d1, d2) within {max_attempts} attempts for ranges "
        f"d1={d1_range}, d2={d2_range}, excluded={d1_excluded}, target_label={target_label}"
    )


def generate_balanced_split(
    rng: np.random.Generator,
    size: int,
    d1_range: Tuple[float, float],
    d2_range: Tuple[float, float],
    d1_excluded: Tuple[float, float] = None,
    epsilon: float = 0.05,
) -> List[SequenceSample]:
    """Generate a balanced split with size // 2 positive and size // 2 negative samples."""
    samples: List[SequenceSample] = []
    n_pos = size // 2
    n_neg = size - n_pos

    # Generate positive samples
    for _ in range(n_pos):
        d1, d2, label = sample_single_pair(
            rng, d1_range, d2_range, d1_excluded, target_label=1, epsilon=epsilon
        )
        samples.append(
            SequenceSample(
                symbols=[0, 1, 2],  # A=0, B=1, C=2
                delta_times=[0.0, d1, d2],
                timestamps=[0.0, d1, d1 + d2],
                label=label,
                d1=d1,
                d2=d2,
            )
        )

    # Generate negative samples
    for _ in range(n_neg):
        d1, d2, label = sample_single_pair(
            rng, d1_range, d2_range, d1_excluded, target_label=0, epsilon=epsilon
        )
        samples.append(
            SequenceSample(
                symbols=[0, 1, 2],  # A=0, B=1, C=2
                delta_times=[0.0, d1, d2],
                timestamps=[0.0, d1, d1 + d2],
                label=label,
                d1=d1,
                d2=d2,
            )
        )

    # Deterministically shuffle the generated samples
    indices = rng.permutation(len(samples))
    return [samples[i] for i in indices]


def generate_negative_control_symbol(
    rng: np.random.Generator,
    size: int,
    d1_range: Tuple[float, float] = (1.0, 10.0),
    d2_range: Tuple[float, float] = (1.0, 15.0),
    d1_excluded: Tuple[float, float] = (4.0, 5.0),
    epsilon: float = 0.05,
) -> List[SequenceSample]:
    """Control 1: Final symbol is randomly C (token 2) or D (token 3).
    Label is 1[symbol == D], completely independent of (d1, d2).
    """
    samples: List[SequenceSample] = []
    n_pos = size // 2
    n_neg = size - n_pos

    for is_d in [1] * n_pos + [0] * n_neg:
        d1, d2, _ = sample_single_pair(
            rng, d1_range, d2_range, d1_excluded, target_label=None, epsilon=epsilon
        )
        final_symbol = 3 if is_d else 2  # D=3, C=2
        samples.append(
            SequenceSample(
                symbols=[0, 1, final_symbol],
                delta_times=[0.0, d1, d2],
                timestamps=[0.0, d1, d1 + d2],
                label=is_d,
                d1=d1,
                d2=d2,
            )
        )

    indices = rng.permutation(len(samples))
    return [samples[i] for i in indices]


def generate_negative_control_order(
    rng: np.random.Generator,
    size: int,
    d1_range: Tuple[float, float] = (1.0, 10.0),
    d2_range: Tuple[float, float] = (1.0, 15.0),
    d1_excluded: Tuple[float, float] = (4.0, 5.0),
    epsilon: float = 0.05,
) -> List[SequenceSample]:
    """Control 2: First two symbols are shuffled to (A, B) or (B, A).
    Label is 1[first symbol == A], completely independent of (d1, d2).
    """
    samples: List[SequenceSample] = []
    n_pos = size // 2
    n_neg = size - n_pos

    for first_is_a in [1] * n_pos + [0] * n_neg:
        d1, d2, _ = sample_single_pair(
            rng, d1_range, d2_range, d1_excluded, target_label=None, epsilon=epsilon
        )
        symbols = [0, 1, 2] if first_is_a else [1, 0, 2]
        samples.append(
            SequenceSample(
                symbols=symbols,
                delta_times=[0.0, d1, d2],
                timestamps=[0.0, d1, d1 + d2],
                label=first_is_a,
                d1=d1,
                d2=d2,
            )
        )

    indices = rng.permutation(len(samples))
    return [samples[i] for i in indices]


def audit_splits(
    splits: Dict[str, List[SequenceSample]],
) -> Dict[str, Any]:
    """Audit split sizes, balance, ranges, and verify disjoint tuple hashes."""
    stats = {}
    tuple_hashes: Dict[str, Set[str]] = {}

    for name, sample_list in splits.items():
        labels = [s.label for s in sample_list]
        d1s = [s.d1 for s in sample_list]
        d2s = [s.d2 for s in sample_list]

        hashes = {
            hashlib.sha256(f"{s.d1:.6f}_{s.d2:.6f}_{s.symbols}".encode()).hexdigest()
            for s in sample_list
        }
        tuple_hashes[name] = hashes

        stats[name] = {
            "size": len(sample_list),
            "positive_count": int(sum(labels)),
            "positive_fraction": float(np.mean(labels)),
            "d1_min": float(np.min(d1s)),
            "d1_max": float(np.max(d1s)),
            "d2_min": float(np.min(d2s)),
            "d2_max": float(np.max(d2s)),
            "unique_tuples": len(hashes),
        }

    # Cross-split overlap check
    overlaps = {}
    names = list(splits.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            overlap = len(tuple_hashes[n1].intersection(tuple_hashes[n2]))
            overlaps[f"{n1}_vs_{n2}"] = overlap

    stats["overlaps"] = overlaps
    return stats


def generate_all_datasets(
    seed: int,
    train_size: int = 10000,
    val_size: int = 2000,
    test_size: int = 4000,
    epsilon: float = 0.05,
) -> Tuple[Dict[str, Dict[str, SequenceDataset]], Dict[str, Any]]:
    """Generate all datasets for a given seed with deterministic substreams.
    
    Generates three independent task suites:
      1. 'temporal': main ratio comparison task (train, val, test_id, test_interpolation, test_extrapolation)
      2. 'control_symbol': negative control trained specifically on symbol identity (train, val, test)
      3. 'control_order': negative control trained specifically on sequence order (train, val, test)
    """
    ss = np.random.SeedSequence(seed)
    # Spawn 11 distinct RNGs for full suite isolation
    rngs = [np.random.default_rng(s) for s in ss.spawn(11)]
    (
        rng_ratio_tr,
        rng_ratio_va,
        rng_ratio_id,
        rng_ratio_in,
        rng_ratio_ex,
        rng_sym_tr,
        rng_sym_va,
        rng_sym_te,
        rng_ord_tr,
        rng_ord_va,
        rng_ord_te,
    ) = rngs

    # 1. Main Temporal Ratio Task
    temporal_splits = {
        "train": generate_balanced_split(
            rng_ratio_tr, train_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "val": generate_balanced_split(
            rng_ratio_va, val_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "test_id": generate_balanced_split(
            rng_ratio_id, test_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "test_interpolation": generate_balanced_split(
            rng_ratio_in, test_size, d1_range=(4.0, 5.0), d2_range=(1.0, 15.0), d1_excluded=None, epsilon=epsilon
        ),
        "test_extrapolation": generate_balanced_split(
            rng_ratio_ex, test_size, d1_range=(12.0, 16.0), d2_range=(10.0, 30.0), d1_excluded=None, epsilon=epsilon
        ),
    }

    # 2. Control Symbol Task (Trained on final symbol C vs D)
    sym_splits = {
        "train": generate_negative_control_symbol(
            rng_sym_tr, train_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "val": generate_negative_control_symbol(
            rng_sym_va, val_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "test": generate_negative_control_symbol(
            rng_sym_te, test_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
    }

    # 3. Control Order Task (Trained on initial order AB vs BA)
    ord_splits = {
        "train": generate_negative_control_order(
            rng_ord_tr, train_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "val": generate_negative_control_order(
            rng_ord_va, val_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
        "test": generate_negative_control_order(
            rng_ord_te, test_size, d1_range=(1.0, 10.0), d2_range=(1.0, 15.0), d1_excluded=(4.0, 5.0), epsilon=epsilon
        ),
    }

    suites = {
        "temporal": {k: SequenceDataset(v) for k, v in temporal_splits.items()},
        "control_symbol": {k: SequenceDataset(v) for k, v in sym_splits.items()},
        "control_order": {k: SequenceDataset(v) for k, v in ord_splits.items()},
    }

    audits = {
        "temporal": audit_splits(temporal_splits),
        "control_symbol": audit_splits(sym_splits),
        "control_order": audit_splits(ord_splits),
    }

    return suites, audits
