import numpy as np
import torch

from backend.app.structured_pipeline import build_baseline_d2stgnn_dataset
from backend.app.d2stgnn_baseline import D2STGNNBaseline
from backend.app.d2stgnn_external import D2STGNN


def test_external_d2stgnn_smoke_path_runs():
    model = D2STGNN(
        num_feat=4,
        num_hidden=512,
        node_hidden=64,
        time_emb_dim=64,
        seq_length=2,
        k_s=1,
        k_t=1,
        num_nodes=2,
        gap=1,
        day_in_week_size=7,
        time_in_day_size=288,
        dropout=0.1,
        adjs=[torch.eye(2, dtype=torch.float32), torch.eye(2, dtype=torch.float32)],
    )

    history = torch.tensor([[[0.1, 0.2, 0.3, 0.4, 0.1, 0.2],
                              [0.2, 0.3, 0.4, 0.5, 0.1, 0.2]],
                             [[0.3, 0.4, 0.5, 0.6, 0.1, 0.2],
                              [0.4, 0.5, 0.6, 0.7, 0.1, 0.2]]], dtype=torch.float32).unsqueeze(0)
    future = torch.tensor([[[0.5, 0.6, 0.7, 0.8, 0.1, 0.2],
                            [0.6, 0.7, 0.8, 0.9, 0.1, 0.2]]], dtype=torch.float32).unsqueeze(0)

    forecast = model(history, future, batch_seen=1, epoch=0, train=False)

    assert forecast.shape[0] == 1
    assert forecast.shape[1] == 4
    assert forecast.shape[2] == 2
    assert forecast.shape[3] == 1


def test_d2stgnn_baseline_returns_forecast_tensor():
    raw = {
        "road_network": [
            {"segment_id": "seg-1", "from_node": "n1", "to_node": "n2", "length_m": 400.0},
            {"segment_id": "seg-2", "from_node": "n2", "to_node": "n3", "length_m": 500.0},
        ],
        "traffic": [
            {"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 30.0, "flow": 600},
            {"segment_id": "seg-2", "timestamp": "2026-06-12T08:00:00+08:00", "speed_kph": 26.0, "flow": 580},
        ],
        "weather": [{"segment_id": "seg-1", "timestamp": "2026-06-12T08:00:00+08:00", "temperature_c": 32.0, "rain_mm": 1.2}],
        "flood": [{"segment_id": "seg-1", "hazard_level": 2}],
    }

    dataset = build_baseline_d2stgnn_dataset(raw, input_len=2, output_len=1)
    model = D2STGNNBaseline(input_dim=4, hidden_dim=8, output_len=1)

    prediction = model(dataset["history_tensor"], dataset["adjacency_matrix"])

    assert prediction.shape[0] == 1
    assert prediction.shape[1] == 2
    assert prediction.shape[2] == 1
