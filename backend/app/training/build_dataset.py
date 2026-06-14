"""
Build D2STGNN-ready train/val/test tensors from the raw TomTom CSV
produced by collect_tomtom.py.

Output tensors have shape [T, N, 6]:
    channel 0: speed_kph        (TomTom currentSpeed)
    channel 1: flow_proxy       (currentSpeed / freeFlowSpeed, derived)
    channel 2: density          (placeholder, 0.0 — TomTom free tier has no density)
    channel 3: valid_flag       (1.0 if a real observation exists for this
                                  (timestep, node), 0.0 if interpolated/missing)
    channel 4: time_of_day      (fraction of day in [0, 1))
    channel 5: day_of_week      (fraction of week in [0, 6/7])

NOTE on num_feat vs total channels:
    D2STGNN's _D2STGNN_DEFAULTS sets num_feat=4. Its _prepare_inputs()
    slices `X[:, :, :, :num_feat]` as the traffic features fed to the
    embedding layer, and reads columns [num_feat] and [num_feat+1] as
    time_of_day and day_of_week. So the tensor's LAST TWO columns must
    always be (time_of_day, day_of_week), regardless of num_feat.
    With num_feat=4, total channels = 6, matching the layout above.

Train/val/test split: 70/15/15, TEMPORAL (not random) — earlier
timestamps go to train, later timestamps go to test. This respects
the time-series nature of the data and avoids leakage.

Usage:
    python build_dataset.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from segments import NODE_IDS, NUM_NODES

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
DEFAULT_INPUT_CSV = RAW_DIR / "tomtom_traffic.csv"

# Resampling interval. Must match the collector's polling interval
# (5 minutes) and D2STGNN's time_in_day_size=288 (24h * 60 / 5 = 288).
RESAMPLE_FREQ = "5min"
TIME_IN_DAY_SIZE = 288  # 24h / 5min

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# TEST_FRAC is the remainder (0.15)

NUM_FEAT_TOTAL = 6  # speed, flow, density, valid_flag, time_of_day, day_of_week


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp", "Node"])
    df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")
    df["Flow"] = pd.to_numeric(df["Flow"], errors="coerce")
    return df


def build_time_grid(df: pd.DataFrame) -> pd.DatetimeIndex:
    start = df["Timestamp"].min().floor(RESAMPLE_FREQ)
    end = df["Timestamp"].max().ceil(RESAMPLE_FREQ)
    return pd.date_range(start=start, end=end, freq=RESAMPLE_FREQ, tz="UTC")


def pivot_node(df: pd.DataFrame, node_id: str, time_grid: pd.DatetimeIndex) -> pd.DataFrame:
    """Resample one node's observations onto the fixed time grid.

    Returns a DataFrame indexed by time_grid with columns:
    speed, flow, valid_flag (before interpolation).
    """
    sub = df[df["Node"] == node_id].copy()
    sub = sub.set_index("Timestamp").sort_index()

    # Bin into the time grid (nearest preceding slot)
    sub = sub[["Speed", "Flow"]].resample(RESAMPLE_FREQ).mean()

    out = sub.reindex(time_grid)
    out["valid_flag"] = (~out["Speed"].isna()).astype(np.float32)
    return out


def build_tensor(df: pd.DataFrame) -> tuple[np.ndarray, pd.DatetimeIndex]:
    time_grid = build_time_grid(df)
    T = len(time_grid)
    N = NUM_NODES

    tensor = np.zeros((T, N, NUM_FEAT_TOTAL), dtype=np.float32)

    for i, node_id in enumerate(NODE_IDS):
        node_df = pivot_node(df, node_id, time_grid)

        speed = node_df["Speed"]
        flow = node_df["Flow"]
        valid = node_df["valid_flag"].to_numpy()

        # Interpolate missing speed/flow values, then forward/back-fill
        # any remaining edge NaNs (e.g. if a node has no data at the
        # very start/end of the collection window).
        speed_filled = speed.interpolate(limit_direction="both")
        flow_filled = flow.interpolate(limit_direction="both")

        # If a node has ZERO observations at all, interpolate() leaves
        # NaNs. Fall back to 0.0 so training doesn't crash, but this
        # node's data will be uninformative -- check collection coverage.
        speed_filled = speed_filled.fillna(0.0).to_numpy()
        flow_filled = flow_filled.fillna(0.0).to_numpy()

        tensor[:, i, 0] = speed_filled            # speed_kph
        tensor[:, i, 1] = flow_filled             # flow_proxy
        tensor[:, i, 2] = 0.0                     # density (placeholder)
        tensor[:, i, 3] = valid                   # valid_flag

    # Time-of-day / day-of-week, same for all nodes at a given timestep
    seconds = (
        time_grid.hour * 3600 + time_grid.minute * 60 + time_grid.second
    ).to_numpy()
    tod = seconds / 86400.0
    dow = time_grid.dayofweek.to_numpy() / 7.0

    for i in range(N):
        tensor[:, i, 4] = tod
        tensor[:, i, 5] = dow

    return tensor, time_grid


def normalize_speed_flow(tensor: np.ndarray, train_end: int) -> tuple[np.ndarray, dict]:
    """Z-score normalize channels 0 (speed) and 1 (flow) using TRAIN stats only.

    valid_flag, time_of_day, day_of_week are left unnormalized (they are
    already in meaningful bounded ranges: {0,1}, [0,1), [0,1)).
    """
    stats = {}
    out = tensor.copy()
    for ch, name in [(0, "speed"), (1, "flow")]:
        train_vals = tensor[:train_end, :, ch]
        mean = float(train_vals.mean())
        std = float(train_vals.std())
        std = std if std > 1e-6 else 1.0
        out[:, :, ch] = (tensor[:, :, ch] - mean) / std
        stats[name] = {"mean": mean, "std": std}
    return out, stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT_CSV),
        help="Path to the raw traffic CSV (real or synthetic)",
    )
    args = parser.parse_args()
    input_csv = Path(args.input)

    if not input_csv.exists():
        raise SystemExit(
            f"Input file not found: {input_csv}\n"
            "Run collect_tomtom.py on a schedule first to gather real data, "
            "or generate_synthetic_history.py for a synthetic dataset."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = load_raw(input_csv)
    tensor, time_grid = build_tensor(df)
    T = tensor.shape[0]

    print(f"[build_dataset] total timesteps: {T} "
          f"({time_grid[0]} to {time_grid[-1]})")

    if T < 50:
        print("[build_dataset] WARNING: very few timesteps collected. "
              "Model will not learn meaningful patterns yet. "
              "Keep collecting data and re-run this script later.")

    # Temporal split
    train_end = int(T * TRAIN_FRAC)
    val_end = int(T * (TRAIN_FRAC + VAL_FRAC))

    # Normalize speed/flow using train-set statistics only
    tensor_norm, norm_stats = normalize_speed_flow(tensor, train_end)

    train = tensor_norm[:train_end]
    val = tensor_norm[train_end:val_end]
    test = tensor_norm[val_end:]

    print(f"[build_dataset] split sizes -> train: {train.shape[0]}, "
          f"val: {val.shape[0]}, test: {test.shape[0]}")

    np.savez(PROCESSED_DIR / "train.npz", data=train)
    np.savez(PROCESSED_DIR / "val.npz", data=val)
    np.savez(PROCESSED_DIR / "test.npz", data=test)

    import json
    with open(PROCESSED_DIR / "norm_stats.json", "w") as f:
        json.dump(norm_stats, f, indent=2)

    print(f"[build_dataset] saved train/val/test npz + norm_stats.json to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()