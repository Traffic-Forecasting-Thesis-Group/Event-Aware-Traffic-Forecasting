"""
Train D2STGNN on the TomTom-derived dataset built by build_dataset.py.

Loads train/val/test npz tensors of shape [T, N, 6], slices them into
sliding windows of (history=seq_length, future=seq_length), and trains
the model defined in app/d2stgnn_external/d2stgnn_arch.py using the
same hyperparameters as main.py's _D2STGNN_DEFAULTS.

Loss: MAE (L1) on the speed channel only (channel 0), since that is
the primary forecasting target. Masking via valid_flag (channel 3)
excludes originally-missing observations from the loss.

Usage:
    python train.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

# --- Make `app` importable -------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.d2stgnn_external import D2STGNN  # noqa: E402
from segments import NUM_NODES            # noqa: E402

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
ARTIFACT_DIR  = Path(__file__).resolve().parents[3] / "artifacts" / "model_registry"

# ---- Model config (must match main.py's _D2STGNN_DEFAULTS) ----------------
D2STGNN_DEFAULTS = dict(
    num_feat=4,
    num_hidden=512,
    node_hidden=64,
    time_emb_dim=64,
    seq_length=12,
    k_s=2,
    k_t=3,
    gap=1,
    day_in_week_size=7,
    time_in_day_size=288,
    dropout=0.1,
)

SEQ_LENGTH     = D2STGNN_DEFAULTS["seq_length"]
NUM_FEAT_TOTAL = 6  # speed, flow, density, valid_flag, time_of_day, day_of_week

# ---- Training hyperparameters ----------------------------------------------
DEFAULT_BATCH_SIZE    = 32
DEFAULT_LEARNING_RATE = 1e-4
DEFAULT_NUM_EPOCHS    = 2
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class WindowDataset(Dataset):
    """Slices a [T, N, C] array into overlapping (history, future) windows."""

    def __init__(self, data: np.ndarray, seq_length: int):
        self.data       = data
        self.seq_length = seq_length
        T = data.shape[0]
        self.num_windows = max(0, T - 2 * seq_length + 1)

    def __len__(self) -> int:
        return self.num_windows

    def __getitem__(self, idx: int):
        L       = self.seq_length
        history = self.data[idx: idx + L]
        future  = self.data[idx + L: idx + 2 * L]
        return (
            torch.tensor(history, dtype=torch.float32),
            torch.tensor(future,  dtype=torch.float32),
        )


def load_split(name: str) -> np.ndarray:
    path = PROCESSED_DIR / f"{name}.npz"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run build_dataset.py first.")
    return np.load(path)["data"]


def load_adjacency() -> torch.Tensor:
    path = PROCESSED_DIR / "adj_mx.npy"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run build_adjacency.py first.")
    return torch.tensor(np.load(path), dtype=torch.float32)


def masked_mae(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """MAE on the speed channel, masked by valid_flag.

    pred:   [B, seq_length, N, 1]
    target: [B, seq_length, N, 1]
    mask:   [B, seq_length, N, 1]
    """
    diff  = torch.abs(pred - target) * mask
    denom = mask.sum().clamp(min=1.0)
    return diff.sum() / denom


def run_epoch(model, loader, adjs, optimizer, train: bool, epoch: int) -> float:
    model.train(mode=train)
    total_loss    = 0.0
    total_batches = 0

    pbar = tqdm(enumerate(loader), total=len(loader),
                desc=f"Epoch {epoch} [train={train}]", leave=False)

    for batch_idx, (history, future) in pbar:
        history = history.to(DEVICE)
        future  = future.to(DEVICE)

        target_speed = future[:, :, :, 0:1]
        target_mask  = future[:, :, :, 3:4]

        if train:
            optimizer.zero_grad()

        forecast = model(
            history_data=history,
            future_data=future,
            batch_seen=batch_idx,
            epoch=epoch,
            train=train,
            event_embeddings=None,
        )

        forecast = _align_forecast_to_target(forecast, target_speed)
        loss     = masked_mae(forecast, target_speed, target_mask)

        if torch.isnan(loss):
            pbar.set_postfix(loss="NaN-skip")
            continue

        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

        total_loss    += loss.item()
        total_batches += 1
        pbar.set_postfix(loss=f"{loss.item():.4f}")

    return total_loss / max(total_batches, 1)


def _align_forecast_to_target(forecast: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Verify forecast shape matches target; raises a clear error if the
    out_fc_2 fix in d2stgnn_arch.py has not been applied."""
    B, F, N, C  = forecast.shape
    target_len  = target.shape[1]
    if F != target_len:
        raise RuntimeError(
            f"Forecast time dimension ({F}) != target time dimension ({target_len}). "
            "Apply the out_fc_2 fix in d2stgnn_arch.py: "
            "self.out_fc_2 = nn.Linear(self._output_hidden, "
            "model_args['gap'] * model_args['seq_length'])"
        )
    return forecast


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=DEFAULT_NUM_EPOCHS)
    parser.add_argument("--batch-size", type=int,   default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lr",         type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--subset",     type=int,   default=800,
                        help="Max training windows per epoch (default 800 for speed)")
    args = parser.parse_args()

    train_data = load_split("train")
    val_data   = load_split("val")
    test_data  = load_split("test")

    train_ds = WindowDataset(train_data, SEQ_LENGTH)
    val_ds   = WindowDataset(val_data,   SEQ_LENGTH)
    test_ds  = WindowDataset(test_data,  SEQ_LENGTH)

    if len(train_ds) == 0:
        raise SystemExit(
            f"Not enough data for even one training window. "
            f"Need at least {2 * SEQ_LENGTH} timesteps, "
            f"have {train_data.shape[0]}. Keep collecting data."
        )

    print(f"[train] windows -> train: {len(train_ds)}, val: {len(val_ds)}, test: {len(test_ds)}")

    subset_indices = list(range(min(args.subset, len(train_ds))))
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=torch.utils.data.SubsetRandomSampler(subset_indices),
    )
    val_loader  = DataLoader(val_ds,  batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    adj  = load_adjacency().to(DEVICE)
    adjs = [adj for _ in range(D2STGNN_DEFAULTS["k_s"])]

    model = D2STGNN(
        num_nodes=NUM_NODES,
        adjs=adjs,
        **D2STGNN_DEFAULTS,
    ).to(DEVICE)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    best_val_loss = float("inf")
    best_path     = ARTIFACT_DIR / "d2stgnn_tomtom_best.pt"

    for epoch in range(1, args.epochs + 1):
        train_loss = run_epoch(model, train_loader, adjs, optimizer, train=True,  epoch=epoch)

        with torch.no_grad():
            val_loss = run_epoch(model, val_loader, adjs, optimizer, train=False, epoch=epoch)

        print(f"[train] epoch {epoch:03d} | train_mae={train_loss:.4f} | val_mae={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "model_state_dict": model.state_dict(),
                "model_args":       D2STGNN_DEFAULTS,
                "num_nodes":        NUM_NODES,
                "epoch":            epoch,
                "val_mae":          val_loss,
            }, best_path)
            print(f"[train]   -> new best model saved to {best_path}")

    checkpoint = torch.load(best_path, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    with torch.no_grad():
        test_loss = run_epoch(model, test_loader, adjs, optimizer, train=False, epoch=0)
    print(f"[train] final test_mae (best checkpoint, epoch {checkpoint['epoch']}): {test_loss:.4f}")


if __name__ == "__main__":
    main()
