"""
V1 strategy: EMA crossover for direction, RSI as a filter to avoid chasing
an already-overbought/oversold move, ATR to size stop loss / take profit
relative to current volatility (so TP/SL adapt to the instrument and
timeframe instead of using a fixed pip count).

This is intentionally simple and fully transparent - every decision can be
read straight from the code. That's the point for v1: you should be able to
explain *why* it fired a signal, not just trust a black box.
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from indicators import add_indicators


@dataclass
class Signal:
    timestamp: pd.Timestamp
    action: str          # "BUY", "SELL", or "HOLD"
    price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reason: str


def generate_signals(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """
    Adds an 'action' column to the dataframe for every row (used by the backtester
    to simulate trade-by-trade). BUY/SELL fire only on the bar where the EMA
    crossover happens, filtered by RSI; every other bar is HOLD.
    """
    data = add_indicators(df, cfg.EMA_FAST, cfg.EMA_SLOW, cfg.RSI_PERIOD, cfg.ATR_PERIOD)

    fast_above_slow = data["ema_fast"] > data["ema_slow"]
    crossed_up = fast_above_slow & (~fast_above_slow.shift(1).fillna(False))
    crossed_down = (~fast_above_slow) & (fast_above_slow.shift(1).fillna(False))

    buy_cond = crossed_up & (data["rsi"] < cfg.RSI_UPPER)
    sell_cond = crossed_down & (data["rsi"] > cfg.RSI_LOWER)

    data["action"] = "HOLD"
    data.loc[buy_cond, "action"] = "BUY"
    data.loc[sell_cond, "action"] = "SELL"

    data["stop_loss"] = None
    data["take_profit"] = None

    buy_atr = data.loc[buy_cond, "atr"]
    data.loc[buy_cond, "stop_loss"] = data.loc[buy_cond, "Close"] - buy_atr * cfg.ATR_SL_MULT
    data.loc[buy_cond, "take_profit"] = data.loc[buy_cond, "Close"] + buy_atr * cfg.ATR_TP_MULT

    sell_atr = data.loc[sell_cond, "atr"]
    data.loc[sell_cond, "stop_loss"] = data.loc[sell_cond, "Close"] + sell_atr * cfg.ATR_SL_MULT
    data.loc[sell_cond, "take_profit"] = data.loc[sell_cond, "Close"] - sell_atr * cfg.ATR_TP_MULT

    return data


def latest_signal(df: pd.DataFrame, cfg, symbol: str) -> Signal:
    """
    Returns the signal for the most recent completed candle - this is what
    you'd act on "right now" for a given symbol.
    """
    data = generate_signals(df, cfg)
    last = data.iloc[-1]

    action = last["action"]
    reason_parts = [
        f"EMA{cfg.EMA_FAST}={last['ema_fast']:.4f}",
        f"EMA{cfg.EMA_SLOW}={last['ema_slow']:.4f}",
        f"RSI({cfg.RSI_PERIOD})={last['rsi']:.1f}",
        f"ATR({cfg.ATR_PERIOD})={last['atr']:.4f}",
    ]
    if action == "HOLD":
        reason_parts.insert(0, "No fresh EMA crossover on this candle, or RSI filter blocked it")
    else:
        reason_parts.insert(0, f"EMA crossover triggered {action}")

    return Signal(
        timestamp=last.name,
        action=action,
        price=float(last["Close"]),
        stop_loss=float(last["stop_loss"]) if pd.notna(last["stop_loss"]) else None,
        take_profit=float(last["take_profit"]) if pd.notna(last["take_profit"]) else None,
        reason=" | ".join(reason_parts),
    )
