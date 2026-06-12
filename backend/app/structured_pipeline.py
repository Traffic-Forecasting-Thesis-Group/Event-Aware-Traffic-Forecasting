from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np


def normalize_structured_sources(raw: dict[str, Any]) -> dict[str, Any]:
    road_network = list(raw.get("road_network", []) or [])
    traffic = list(raw.get("traffic", []) or [])
    weather = list(raw.get("weather", []) or [])
    flood = list(raw.get("flood", []) or [])

    def parse_ts(value: Any) -> str:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return str(value)

    normalized_traffic = []
    for item in traffic:
        normalized_traffic.append({
            "segment_id": item.get("segment_id"),
            "timestamp": parse_ts(item.get("timestamp")),
            "speed_kph": float(item.get("speed_kph", 0.0)),
            "flow": float(item.get("flow", 0.0)),
            "density": float(item.get("density", 0.0)),
        })

    return {
        "road_segments": road_network,
        "traffic_observations": normalized_traffic,
        "weather_observations": weather,
        "flood_hazards": flood,
    }


def _encode_time_features(timestamp_iso: str) -> tuple[float, float]:
    try:
        dt = datetime.fromisoformat(timestamp_iso)
        seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
        time_of_day = seconds / 86400.0
        day_of_week = dt.weekday() / 7.0
        return float(time_of_day), float(day_of_week)
    except Exception:
        return 0.0, 0.0


def build_baseline_d2stgnn_dataset(
    raw: dict[str, Any],
    input_len: int = 12,
    output_len: int = 12,
) -> dict[str, Any]:
    dataset = normalize_structured_sources(raw)
    segments = dataset["road_segments"]
    traffic = dataset["traffic_observations"]

    node_ids = [str(item.get("segment_id")) for item in segments]
    num_nodes = max(len(node_ids), 1)

    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    for i, source in enumerate(segments):
        for j, target in enumerate(segments):
            if source.get("to_node") == target.get("from_node"):
                adjacency[i, j] = 1.0

    history = np.zeros((input_len, num_nodes, 6), dtype=np.float32)
    for t in range(min(input_len, len(traffic))):
        item = traffic[t]
        seg_id = str(item.get("segment_id"))
        idx = node_ids.index(seg_id) if seg_id in node_ids else 0
        tod, dow = _encode_time_features(item.get("timestamp", ""))
        history[t, idx, 0] = float(item.get("speed_kph", 0.0))
        history[t, idx, 1] = float(item.get("flow", 0.0))
        history[t, idx, 2] = float(item.get("density", 0.0))
        history[t, idx, 3] = 1.0
        history[t, idx, 4] = tod
        history[t, idx, 5] = dow

    node_features = np.zeros((num_nodes, 2), dtype=np.float32)
    for i, item in enumerate(segments):
        node_features[i, 0] = float(item.get("length_m", 0.0))
        node_features[i, 1] = float(item.get("speed_limit", 0.0))

    return {
        "dataset": dataset,
        "history_tensor": history,
        "target_tensor": history[:output_len] if output_len <= input_len else history,
        "adjacency_matrix": adjacency,
        "node_features": node_features,
        "node_ids": node_ids,
        "input_len": input_len,
        "output_len": output_len,
        "num_feat": 4,
    }
