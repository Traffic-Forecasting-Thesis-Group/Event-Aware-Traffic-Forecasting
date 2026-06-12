from __future__ import annotations

try:
    from .d2stgnn_arch import D2STGNN
except Exception:  # pragma: no cover - fallback for lightweight environments
    D2STGNN = None

from ..d2stgnn_baseline import D2STGNNBaseline

__all__ = ["D2STGNN", "D2STGNNBaseline"]
