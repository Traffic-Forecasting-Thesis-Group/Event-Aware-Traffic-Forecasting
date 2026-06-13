import numpy as np
import torch


def remove_nan_inf(x):
    """Return a tensor/array with NaNs and infs safely replaced by zeros."""
    if isinstance(x, torch.Tensor):
        x = x.detach().cpu()
    arr = np.asarray(x)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
