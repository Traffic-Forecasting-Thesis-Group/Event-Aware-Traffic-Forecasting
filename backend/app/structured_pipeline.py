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


def _extract_weather_for_segment(
    segment_id: str,
    weather: list[dict],
) -> tuple[float, float]:
    """Return (rain_mm, temperature_c) for the closest weather observation to segment."""
    for w in weather:
        if str(w.get("segment_id", "")) == segment_id:
            return float(w.get("rain_mm", 0.0)), float(w.get("temperature_c", 30.0))
    # fallback: use first available observation if no segment match
    if weather:
        return float(weather[0].get("rain_mm", 0.0)), float(weather[0].get("temperature_c", 30.0))
    return 0.0, 30.0


def _extract_flood_for_segment(
    segment_id: str,
    flood: list[dict],
) -> float:
    """Return flood hazard level [0.0-1.0] for segment. 0=none, 1=extreme."""
    _LEVEL_MAP = {"none": 0.0, "low": 0.25, "moderate": 0.5, "high": 0.75, "extreme": 1.0}
    for f in flood:
        if str(f.get("segment_id", "")) == segment_id:
            level = str(f.get("hazard_level", "none")).lower()
            return _LEVEL_MAP.get(level, float(f.get("hazard_level", 0.0)))
    return 0.0


def build_baseline_d2stgnn_dataset(
    raw: dict[str, Any],
    input_len: int = 12,
    output_len: int = 12,
) -> dict[str, Any]:
    """Build the full D2STGNN-ready dataset from OSMnx, TomTom,
    OpenWeatherMap, and Project NOAH data sources.

    History tensor columns [T, N, 9]:
        0: speed_kph       (TomTom)
        1: flow            (TomTom)
        2: density         (TomTom)
        3: valid_flag      (1.0 if observation present)
        4: time_of_day     (fraction of day [0,1))
        5: day_of_week     (fraction of week [0,~0.857])
        6: rain_mm         (OpenWeatherMap)
        7: temperature_c   (OpenWeatherMap, normalized /50)
        8: flood_hazard    (Project NOAH, [0,1])
    """
    dataset = normalize_structured_sources(raw)
    segments = dataset["road_segments"]
    traffic = dataset["traffic_observations"]
    weather = dataset["weather_observations"]
    flood = dataset["flood_hazards"]

    node_ids = [str(item.get("segment_id")) for item in segments]
    num_nodes = max(len(node_ids), 1)

    # Adjacency matrix from OSMnx road network topology
    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    for i, source in enumerate(segments):
        for j, target in enumerate(segments):
            if source.get("to_node") == target.get("from_node"):
                adjacency[i, j] = 1.0

    # History tensor: 9 features per node per timestep
    num_feat = 4  # traffic features fed to D2STGNN embedding layer
    num_total = 9  # full feature set including weather/flood/time
    history = np.zeros((input_len, num_nodes, num_total), dtype=np.float32)

    for t in range(min(input_len, len(traffic))):
        item = traffic[t]
        seg_id = str(item.get("segment_id"))
        idx = node_ids.index(seg_id) if seg_id in node_ids else 0
        tod, dow = _encode_time_features(item.get("timestamp", ""))
        rain, temp = _extract_weather_for_segment(seg_id, weather)
        flood_h = _extract_flood_for_segment(seg_id, flood)

        history[t, idx, 0] = float(item.get("speed_kph", 0.0))
        history[t, idx, 1] = float(item.get("flow", 0.0))
        history[t, idx, 2] = float(item.get("density", 0.0))
        history[t, idx, 3] = 1.0           # valid flag
        history[t, idx, 4] = tod
        history[t, idx, 5] = dow
        history[t, idx, 6] = rain / 100.0  # normalize: 100mm = 1.0
        history[t, idx, 7] = temp / 50.0   # normalize: 50C = 1.0
        history[t, idx, 8] = flood_h

    # Node-level static features from OSMnx
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
        "num_feat": num_feat,
    }
