import pandas as pd
from typing import Tuple


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


def detect_engulfing(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Detect Bullish and Bearish Engulfing patterns.
    
    Returns:
        (bullish_engulfing, bearish_engulfing) boolean Series
    """
    if len(df) < 2:
        return pd.Series([False] * len(df), dtype=bool), pd.Series([False] * len(df), dtype=bool)
    
    bullish = pd.Series([False] * len(df), dtype=bool)
    bearish = pd.Series([False] * len(df), dtype=bool)
    
    for i in range(1, len(df)):
        prev_open = df["Open"].iloc[i-1]
        prev_close = df["Close"].iloc[i-1]
        curr_open = df["Open"].iloc[i]
        curr_close = df["Close"].iloc[i]
        
        # Bullish engulfing: previous bearish, current bullish, current engulfs previous
        if prev_close < prev_open and curr_close > curr_open:
            if curr_open < prev_close and curr_close > prev_open:
                bullish.iloc[i] = True
        
        # Bearish engulfing: previous bullish, current bearish, current engulfs previous
        if prev_close > prev_open and curr_close < curr_open:
            if curr_open > prev_close and curr_close < prev_open:
                bearish.iloc[i] = True
    
    return bullish, bearish


def detect_doji(df: pd.DataFrame, threshold: float = 0.1) -> pd.Series:
    """
    Detect Doji pattern (small body, indicating indecision).
    
    Args:
        threshold: Body size as fraction of total range (default 10%)
    
    Returns:
        Boolean Series where True indicates a doji.
    """
    if df.empty:
        return pd.Series([], dtype=bool)
    
    body_size = (df["Close"] - df["Open"]).abs()
    total_range = df["High"] - df["Low"]
    
    # Doji: body is small relative to range
    is_doji = (body_size / total_range) < threshold
    return is_doji.fillna(False)


def detect_shooting_star(df: pd.DataFrame) -> pd.Series:
    """
    Detect Shooting Star pattern (bearish reversal).
    
    Returns:
        Boolean Series where True indicates a shooting star.
    """
    if df.empty:
        return pd.Series([], dtype=bool)
    
    body_size = (df["Close"] - df["Open"]).abs()
    upper_wick = df["High"] - df[["Open", "Close"]].max(axis=1)
    lower_wick = df[["Open", "Close"]].min(axis=1) - df["Low"]
    
    # Shooting star: long upper wick, small body, small lower wick
    is_shooting_star = (upper_wick >= 2 * body_size) & (lower_wick < body_size) & (df["Close"] < df["Open"])
    return is_shooting_star.fillna(False)


def detect_bullish_patterns(df: pd.DataFrame) -> pd.Series:
    """Detect any bullish candlestick pattern (hammer, bullish engulfing)."""
    hammer = detect_hammer(df)
    bullish_engulfing, _ = detect_engulfing(df)
    return hammer | bullish_engulfing
