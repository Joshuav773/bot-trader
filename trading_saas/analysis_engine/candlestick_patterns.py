import pandas as pd


def detect_hammer(df: pd.DataFrame) -> pd.Series:
    """
    Detect Hammer candlestick pattern.

    A Hammer is identified by a small body near the top of the range and a
    long lower shadow (>= 2x body) with a relatively small upper shadow.

    Args:
        df: DataFrame with columns 'Open', 'High', 'Low', 'Close'.

    Returns:
        Boolean Series where True indicates a hammer.
    """
    if df.empty:
        return pd.Series([], dtype=bool)

    body_size = (df["Close"] - df["Open"]).abs()
    lower_wick = df[["Open", "Close"]].min(axis=1) - df["Low"]
    upper_wick = df["High"] - df[["Open", "Close"]].max(axis=1)

    is_hammer = (lower_wick >= 2 * body_size) & (upper_wick < body_size)
    return is_hammer.fillna(False)
