import torch
from backend.app.d2stgnn_external import D2STGNN


def test_external_d2stgnn_smoke_path_runs():
    """Full D2STGNN forward pass with 9-feature history tensor
    (4 traffic + 2 time + 3 env: rain, temp, flood)."""
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
    history = torch.tensor([
        [[0.1, 0.2, 0.3, 1.0, 0.1, 0.2, 0.01, 0.64, 0.0],
         [0.2, 0.3, 0.4, 1.0, 0.1, 0.2, 0.01, 0.64, 0.0]],
        [[0.3, 0.4, 0.5, 1.0, 0.1, 0.2, 0.02, 0.64, 0.0],
         [0.4, 0.5, 0.6, 1.0, 0.1, 0.2, 0.02, 0.64, 0.0]],
    ], dtype=torch.float32).unsqueeze(0)
    future = torch.zeros(1, 2, 2, 9, dtype=torch.float32)
    forecast = model(history, future, batch_seen=1, epoch=0, train=False)
    assert forecast.shape == (1, 4, 2, 1), f"Unexpected shape: {forecast.shape}"


def test_external_d2stgnn_with_event_embeddings():
    """D2STGNN CrossModal fusion with injected NLP event embeddings."""
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
    history = torch.zeros(1, 2, 2, 9, dtype=torch.float32)
    future = torch.zeros(1, 2, 2, 9, dtype=torch.float32)
    event_emb = torch.randn(1, 384, 512, dtype=torch.float32)
    forecast = model(
        history, future, batch_seen=0, epoch=0, train=False,
        event_embeddings=event_emb,
    )
    assert forecast.shape == (1, 4, 2, 1), f"Unexpected shape: {forecast.shape}"
