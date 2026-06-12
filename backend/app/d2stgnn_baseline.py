from __future__ import annotations

import numpy as np


class D2STGNNBaseline:
    """A lightweight D2STGNN-style baseline implementation for structured traffic forecasting.

    This intentionally keeps the model simple and deterministic so the structured
    adapter can be verified and connected to the real baseline architecture later.
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_len: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_len = output_len

    def _spatial_mix(self, history: np.ndarray, adjacency: np.ndarray) -> np.ndarray:
        # Simple graph diffusion over the adjacency matrix, preserving the node/feature dimensions.
        normalized = adjacency / np.maximum(adjacency.sum(axis=1, keepdims=True), 1.0)
        return np.tanh(np.einsum("tnf,nm->tmf", history, normalized))

    def __call__(self, history_tensor: np.ndarray, adjacency_matrix: np.ndarray) -> np.ndarray:
        history = np.asarray(history_tensor, dtype=np.float32)
        adjacency = np.asarray(adjacency_matrix, dtype=np.float32)

        if history.ndim != 3:
            raise ValueError("history_tensor must have shape [T, N, F]")

        spatial = self._spatial_mix(history, adjacency)
        temporal = np.mean(spatial, axis=0)  # [N, F]
        forecast = np.repeat(temporal[:, :1], self.output_len, axis=1)  # [N, output_len]
        return np.expand_dims(forecast, axis=0)  # [1, N, output_len]
