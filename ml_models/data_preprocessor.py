from typing import Tuple
import numpy as np
import pandas as pd


def make_supervised(
    series: pd.Series,
    window: int = 50,
    horizon: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert a univariate series into supervised learning samples (X, y).

    X shape: (n_samples, window, 1)
    y shape: (n_samples,)
    """
    values = series.astype("float32").values
    X, y = [], []
    for i in range(window, len(values) - horizon + 1):
        X.append(values[i - window : i])
        y.append(values[i + horizon - 1])
    X = np.array(X, dtype="float32").reshape(-1, window, 1)
    y = np.array(y, dtype="float32")
    return X, y
