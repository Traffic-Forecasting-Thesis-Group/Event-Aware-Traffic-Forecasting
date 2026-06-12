from __future__ import annotations

from typing import Any

from .structured_pipeline import build_baseline_d2stgnn_dataset


def prepare_baseline_input(raw_structured_data: dict[str, Any]) -> dict[str, Any]:
    """Prepare the structured data for a baseline D2STGNN-style training/evaluation pipeline."""
    return build_baseline_d2stgnn_dataset(raw_structured_data)
