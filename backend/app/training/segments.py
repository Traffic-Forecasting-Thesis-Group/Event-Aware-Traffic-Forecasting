"""
Fixed list of road segments (graph nodes) used for the TomTom-based
D2STGNN pilot dataset.

Each segment has a stable `id` (used as the node_id everywhere), a
human-readable `name`, and a `lat`/`lon` midpoint used to query the
TomTom Flow Segment Data API.

IMPORTANT: The order of this list defines the node ordering (axis N)
in every tensor (history, adjacency, etc.). Do not reorder once you
start collecting data, or your time series will become misaligned.

Corridor: EDSA (3 points, north to south) + Roxas Boulevard (2 points),
which connect near the EDSA Extension / Macapagal Blvd area.
"""

SEGMENTS = [
   {"id": "seg_01", "name": "EDSA - North Ave / Munoz",   "lat": 14.6560, "lon": 121.0010},
    {"id": "seg_02", "name": "EDSA - Ortigas Ave Jct",     "lat": 14.5870, "lon": 121.0570},
    {"id": "seg_03", "name": "EDSA - Taft Ave / Pasay",    "lat": 14.5380, "lon": 121.0000},
    {"id": "seg_04", "name": "Roxas Blvd - Manila Bay (near US Embassy)", "lat": 14.5730, "lon": 120.9800},
    {"id": "seg_05", "name": "Roxas Blvd - Macapagal Jct / Pasay",        "lat": 14.5340, "lon": 120.9900},
]

NODE_IDS = [s["id"] for s in SEGMENTS]
NUM_NODES = len(SEGMENTS)
