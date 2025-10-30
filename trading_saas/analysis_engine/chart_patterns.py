from typing import Optional
import pandas as pd


def detect_head_and_shoulders(df: pd.DataFrame, lookback: int = 100) -> pd.Series:
    """
    Stub detector for Head & Shoulders pattern.
    Returns a boolean Series (all False) as a placeholder for future implementation.
    """
    return pd.Series([False] * len(df), index=df.index)
