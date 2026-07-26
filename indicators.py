"""
Indicator calculations, implemented directly in pandas so there's no dependency
on TA-Lib (which needs a compiled C library and is annoying to install).
"""
import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def add_indicators(df: pd.DataFrame, ema_fast: int, ema_slow: int, rsi_period: int, atr_period: int, ema_trend: int = None) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = ema(out["Close"], ema_fast)
    out["ema_slow"] = ema(out["Close"], ema_slow)
    out["rsi"] = rsi(out["Close"], rsi_period)
    out["atr"] = atr(out, atr_period)
    if ema_trend:
        out["ema_trend"] = ema(out["Close"], ema_trend)
    return out
