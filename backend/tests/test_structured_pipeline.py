import numpy as np

from backend.app.structured_pipeline import (
    build_baseline_d2stgnn_dataset,
    normalize_structured_sources,
)


def test_normalize_structured_sources_creates_canonical_dataset():
    raw = {
        "road_network": [
            {"segment_id": "seg-1", "source": "osm", "from_node": "n1", "to_node": "n2", "length_m": 400.0},
            {"segment_id": "seg-2", "source": "osm", "from_node": "n2", "to_node": "n3", "length_m": 500.0},
        ],
        "traffic": [
            {"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 28.0, "flow": 700},
            {"segment_id": "seg-2", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 25.0, "flow": 680},
        ],
        "weather": [{"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "temperature_c": 31.0, "rain_mm": 2.0}],
        "flood": [{"segment_id": "seg-1", "hazard_level": 2}],
    }
    dataset = normalize_structured_sources(raw)
    assert dataset["road_segments"][0]["segment_id"] == "seg-1"
    assert dataset["traffic_observations"][0]["speed_kph"] == 28.0


def test_build_baseline_d2stgnn_dataset_returns_graph_ready_shapes():
    raw = {
        "road_network": [
            {"segment_id": "seg-1", "from_node": "n1", "to_node": "n2"},
            {"segment_id": "seg-2", "from_node": "n2", "to_node": "n3"},
        ],
        "traffic": [
            {"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 30.0, "flow": 600},
            {"segment_id": "seg-2", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 26.0, "flow": 580},
        ],
        "weather": [{"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "temperature_c": 32.0, "rain_mm": 1.2}],
        "flood": [{"segment_id": "seg-1", "hazard_level": 2}],
    }
    dataset = build_baseline_d2stgnn_dataset(raw, input_len=1, output_len=1)
    assert dataset["history_tensor"].shape[0] == 1      # T=1
    assert dataset["history_tensor"].shape[2] == 6      # 6 features (4 traffic + 2 time)
    assert dataset["adjacency_matrix"].shape == (2, 2)
    assert dataset["node_features"].shape[1] == 2
    assert dataset["num_feat"] == 4


def test_history_tensor_time_features_in_valid_range():
    raw = {
        "road_network": [{"segment_id": "seg-1", "from_node": "n1", "to_node": "n2"}],
        "traffic": [
            {"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 30.0, "flow": 600},
        ],
        "weather": [],
        "flood": [],
    }
    dataset = build_baseline_d2stgnn_dataset(raw, input_len=1, output_len=1)
    history = dataset["history_tensor"]  # [1, 1, 6]
    time_of_day = history[0, 0, 4]
    day_of_week = history[0, 0, 5]
    assert 0.0 <= time_of_day < 1.0, f"time_of_day out of range: {time_of_day}"
    assert 0.0 <= day_of_week < 1.0, f"day_of_week out of range: {day_of_week}"


def test_adjacency_matrix_encodes_road_topology():
    raw = {
        "road_network": [
            {"segment_id": "seg-1", "from_node": "n1", "to_node": "n2"},
            {"segment_id": "seg-2", "from_node": "n2", "to_node": "n3"},
        ],
        "traffic": [],
        "weather": [],
        "flood": [],
    }
    dataset = build_baseline_d2stgnn_dataset(raw, input_len=1, output_len=1)
    adj = dataset["adjacency_matrix"]
    assert adj[0, 1] == 1.0
    assert adj[1, 0] == 0.0
