import numpy as np
import pytest
from backend.app.fusion import encode_events_to_embeddings, fuse_forecast_with_events


# ---------------------------------------------------------------------------
# encode_events_to_embeddings
# ---------------------------------------------------------------------------

def test_encode_empty_events_returns_zero_matrix():
    result = encode_events_to_embeddings([], c_dim=16, max_events=8)
    assert result.shape == (1, 8, 16)
    assert np.allclose(result, 0.0)


def test_encode_single_event_shape():
    events = [{"title": "traffic jam on EDSA", "traffic_related": True, "keywords": ["traffic"]}]
    result = encode_events_to_embeddings(events, c_dim=32, max_events=4)
    assert result.shape == (1, 4, 32)


def test_encode_traffic_related_upweighted():
    events_plain = [{"title": "traffic jam", "traffic_related": False, "keywords": []}]
    events_traffic = [{"title": "traffic jam", "traffic_related": True, "keywords": []}]
    plain = encode_events_to_embeddings(events_plain, c_dim=16, max_events=4)
    traffic = encode_events_to_embeddings(events_traffic, c_dim=16, max_events=4)
    # Traffic-related row should be 1.5x the plain row
    assert np.allclose(traffic[0, 0], plain[0, 0] * 1.5, atol=1e-5)


def test_encode_padding_rows_are_zero():
    events = [{"title": "flood warning", "traffic_related": True, "keywords": ["flood"]}]
    result = encode_events_to_embeddings(events, c_dim=8, max_events=5)
    # Rows 1..4 should be zero-padded
    assert np.allclose(result[0, 1:], 0.0)


def test_encode_truncates_to_max_events():
    events = [{"title": "incident", "traffic_related": False, "keywords": []}] * 10
    result = encode_events_to_embeddings(events, c_dim=8, max_events=4)
    assert result.shape == (1, 4, 8)


# ---------------------------------------------------------------------------
# fuse_forecast_with_events
# ---------------------------------------------------------------------------

def test_fuse_forecast_passthrough_no_events():
    forecast = np.ones((1, 2, 1), dtype=np.float32)
    events = {"count": 0, "events": []}
    fused = fuse_forecast_with_events(forecast, events)
    assert np.allclose(fused, forecast)


def test_fuse_forecast_passthrough_with_traffic_events():
    """CrossModal fusion is done inside D2STGNN; fuse_forecast_with_events
    must not apply any post-hoc scalar bias."""
    forecast = np.ones((1, 2, 1), dtype=np.float32)
    events = {"count": 10, "events": [{"traffic_related": True}] * 10}
    fused = fuse_forecast_with_events(forecast, events)
    assert np.allclose(fused, forecast), (
        "fuse_forecast_with_events should be a passthrough — "
        "event fusion is handled by CrossModal attention inside D2STGNN"
    )


def test_fuse_forecast_output_dtype():
    forecast = np.array([[[2.0]]], dtype=np.float64)
    fused = fuse_forecast_with_events(forecast, {"events": []})
    assert fused.dtype == np.float32
