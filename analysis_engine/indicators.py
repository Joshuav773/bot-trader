from typing import Optional
import pandas as pd

try:
    import pandas_ta as ta
except Exception:  # pragma: no cover
    ta = None


def compute_sma(series: pd.Series, length: int = 20) -> pd.Series:
    """Compute Simple Moving Average using pandas-ta if available, else pandas.

    Args:
        series: Price series.
        length: Window length.

    Returns:
        SMA series aligned to input index.
    """
    if ta is not None and hasattr(ta, "sma"):
        return ta.sma(series, length=length)
    return series.rolling(window=length, min_periods=length).mean()


def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Compute RSI using pandas-ta if available; fallback implementation otherwise."""
    if ta is not None and hasattr(ta, "rsi"):
        return ta.rsi(series, length=length)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=length).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
