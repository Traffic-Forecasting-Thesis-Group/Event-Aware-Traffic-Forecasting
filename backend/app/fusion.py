from __future__ import annotations

import numpy as np

_TRAFFIC_VOCAB = [
    'traffic', 'congestion', 'road', 'jam', 'flood', 'accident',
    'delay', 'closure', 'incident', 'construction', 'rally', 'protest',
    'event', 'rain', 'typhoon', 'storm', 'signal', 'detour', 'edsa',
    'roxas', 'mmda', 'ambulance', 'fire', 'emergency', 'slow', 'heavy',
]
_VOCAB_INDEX = {w: i for i, w in enumerate(_TRAFFIC_VOCAB)}
_VOCAB_SIZE = len(_TRAFFIC_VOCAB)


def _keyword_vector(text, keywords):
    vec = np.zeros(_VOCAB_SIZE, dtype=np.float32)
    combined = (text + ' ' + ' '.join(keywords or [])).lower()
    for word, idx in _VOCAB_INDEX.items():
        if word in combined:
            vec[idx] = 1.0
    return vec


def encode_events_to_embeddings(events, c_dim, max_events=384):
    """Encode a list of events into a [1, max_events, c_dim] embedding matrix.

    Uses keyword-projection embedding: keyword indicator vector @ random
    projection matrix. Traffic-related events are upweighted by 1.5x.
    This tensor is passed to D2STGNN as event_embeddings for CrossModal
    attention fusion inside the model.
    """
    rng = np.random.default_rng(seed=42)
    projection = rng.standard_normal((_VOCAB_SIZE, c_dim)).astype(np.float32)
    projection /= np.linalg.norm(projection, axis=0, keepdims=True).clip(min=1e-8)
    rows = []
    for ev in (events or []):
        text = str(ev.get('embedding_text') or ev.get('title') or '')
        keywords = list(ev.get('keywords') or [])
        kv = _keyword_vector(text, keywords)
        emb = kv @ projection
        if ev.get('traffic_related'):
            emb *= 1.5
        rows.append(emb)
    if len(rows) == 0:
        matrix = np.zeros((max_events, c_dim), dtype=np.float32)
    elif len(rows) >= max_events:
        matrix = np.stack(rows[:max_events], axis=0)
    else:
        pad = np.zeros((max_events - len(rows), c_dim), dtype=np.float32)
        matrix = np.vstack([np.stack(rows, axis=0), pad])
    return matrix[np.newaxis, :, :]


def fuse_forecast_with_events(forecast, events):
    """Return forecast unchanged.

    CrossModal attention fusion of event embeddings and spatiotemporal
    features is performed inside D2STGNN (d2stgnn_arch.py) via the
    CrossModal module. No post-hoc adjustment is needed or correct here.
    """
    return np.asarray(forecast, dtype=np.float32)
