from typing import Literal, Optional
import pandas as pd


class DataManager:
    """Utilities for resampling, aligning, and cleaning OHLCV datasets."""

    @staticmethod
    def resample_ohlcv(df: pd.DataFrame, timeframe: Literal["1D", "1H", "15T", "5T", "1T"] = "1D") -> pd.DataFrame:
        """
        Resample OHLCV data to a new timeframe.
        Expects columns: Open, High, Low, Close, Volume
        """
        if df.empty:
            return df.copy()
        o = df["Open"].resample(timeframe).first()
        h = df["High"].resample(timeframe).max()
        l = df["Low"].resample(timeframe).min()
        c = df["Close"].resample(timeframe).last()
        v = df["Volume"].resample(timeframe).sum()
        out = pd.concat([o, h, l, c, v], axis=1)
        out.columns = ["Open", "High", "Low", "Close", "Volume"]
        return out.dropna()

    @staticmethod
    def fill_missing(df: pd.DataFrame, method: Literal["ffill", "bfill", "none"] = "ffill") -> pd.DataFrame:
        if method == "ffill":
            return df.ffill()
        if method == "bfill":
            return df.bfill()
        return df

    @staticmethod
    def align(left: pd.DataFrame, right: pd.DataFrame, how: str = "inner") -> tuple[pd.DataFrame, pd.DataFrame]:
        idx = left.index.union(right.index)
        l2 = left.reindex(idx).ffill()
        r2 = right.reindex(idx).ffill()
        if how == "inner":
            common = left.index.intersection(right.index)
            return l2.loc[common], r2.loc[common]
        return l2, r2
