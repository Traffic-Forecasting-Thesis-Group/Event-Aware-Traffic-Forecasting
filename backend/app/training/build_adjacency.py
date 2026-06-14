"""
Build the adjacency matrix for the 5 TomTom segments.

Computes pairwise haversine distances between segment midpoints, then
applies a thresholded Gaussian kernel (same style as METR-LA's
adj_mx.pkl construction):

    W_ij = exp(-(d_ij^2) / sigma^2)   if d_ij <= threshold
much    W_ij = 0                          otherwise

Output: data/processed/adj_mx.npy, shape (N, N), float32.

This matrix is later loaded by train.py and passed to D2STGNN as the
`adjs` argument (a list of k_s identical matrices, matching how
main.py currently does it: `adjs = [adj_tensor for _ in range(k_s)]`).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from segments import SEGMENTS, NUM_NODES

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "adj_mx.npy"

# Distance threshold in km: pairs farther than this get weight 0.
DISTANCE_THRESHOLD_KM = 8.0
# Gaussian kernel width (km). Smaller = sharper falloff with distance.
SIGMA_KM = 4.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_adjacency() -> np.ndarray:
    adj = np.zeros((NUM_NODES, NUM_NODES), dtype=np.float32)
    for i, a in enumerate(SEGMENTS):
        for j, b in enumerate(SEGMENTS):
            if i == j:
                adj[i, j] = 1.0
                continue
            d = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            if d <= DISTANCE_THRESHOLD_KM:
                adj[i, j] = math.exp(-(d ** 2) / (SIGMA_KM ** 2))
            else:
                adj[i, j] = 0.0
    return adj


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    adj = build_adjacency()
    np.save(OUTPUT_FILE, adj)
    print(f"[build_adjacency] saved {adj.shape} adjacency matrix to {OUTPUT_FILE}")
    print(adj)


if __name__ == "__main__":
    main()
