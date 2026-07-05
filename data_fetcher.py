"""
Pulls OHLCV candle data. Swappable backend - v1 uses yfinance (free, no API key).
"""
import pandas as pd


def fetch_candles(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    indexed by datetime.
    """
    import yfinance as yf

    df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(
            f"No data returned for symbol='{symbol}' period='{period}' interval='{interval}'. "
            "Check the ticker format and that the interval/period combo is allowed by yfinance "
            "(short intervals like 1m/5m only support short lookback periods)."
        )

    # yfinance sometimes returns MultiIndex columns for single tickers - flatten if so
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()
    return df
