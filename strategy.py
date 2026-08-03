"""
V1 strategy: EMA crossover for direction, RSI as a filter to avoid chasing
an already-overbought/oversold move, ATR to size stop loss / take profit
relative to current volatility.
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from indicators import add_indicators


@dataclass
class Signal:
    timestamp: pd.Timestamp
    action: str
    price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reason: str


def generate_signals(df: pd.DataFrame, cfg) -> pd.DataFrame:
    ema_trend_period = getattr(cfg, "EMA_TREND", None)
    data = add_indicators(df, cfg.EMA_FAST, cfg.EMA_SLOW, cfg.RSI_PERIOD, cfg.ATR_PERIOD, ema_trend_period)

    fast_above_slow = data["ema_fast"] > data["ema_slow"]
    prev_above = fast_above_slow.shift(1, fill_value=False)
    crossed_up = fast_above_slow & (~prev_above)
    crossed_down = (~fast_above_slow) & prev_above

    buy_cond = crossed_up & (data["rsi"] < cfg.RSI_UPPER)
    sell_cond = crossed_down & (data["rsi"] > cfg.RSI_LOWER)

    if ema_trend_period:
        in_uptrend = data["Close"] > data["ema_trend"]
        in_downtrend = data["Close"] < data["ema_trend"]
        buy_cond = buy_cond & in_uptrend
        sell_cond = sell_cond & in_downtrend

    # Diagnostic breakdown - lets us explain exactly WHY a bar was a HOLD,
    # permanently, in every log line going forward.
    data["diag_crossed_up"] = crossed_up
    data["diag_crossed_down"] = crossed_down
    data["diag_rsi_blocked_buy"] = crossed_up & ~(data["rsi"] < cfg.RSI_UPPER)
    data["diag_rsi_blocked_sell"] = crossed_down & ~(data["rsi"] > cfg.RSI_LOWER)
    if ema_trend_period:
        data["diag_trend_blocked_buy"] = crossed_up & (data["rsi"] < cfg.RSI_UPPER) & ~in_uptrend
        data["diag_trend_blocked_sell"] = crossed_down & (data["rsi"] > cfg.RSI_LOWER) & ~in_downtrend

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
    data = generate_signals(df, cfg)
    last = data.iloc[-1]

    action = last["action"]
    reason_parts = [
        f"EMA{cfg.EMA_FAST}={last['ema_fast']:.4f}",
        f"EMA{cfg.EMA_SLOW}={last['ema_slow']:.4f}",
        f"RSI({cfg.RSI_PERIOD})={last['rsi']:.1f}",
        f"ATR({cfg.ATR_PERIOD})={last['atr']:.4f}",
    ]
    if "ema_trend" in data.columns:
        reason_parts.append(f"EMA{cfg.EMA_TREND}(trend)={last['ema_trend']:.4f}")
    if action == "HOLD":
        if bool(last["diag_trend_blocked_buy"]) if "diag_trend_blocked_buy" in data.columns else False:
            reason_parts.insert(0, f"EMA crossed UP but blocked by trend filter (price below EMA{cfg.EMA_TREND})")
        elif bool(last["diag_trend_blocked_sell"]) if "diag_trend_blocked_sell" in data.columns else False:
            reason_parts.insert(0, f"EMA crossed DOWN but blocked by trend filter (price above EMA{cfg.EMA_TREND})")
        elif bool(last["diag_rsi_blocked_buy"]):
            reason_parts.insert(0, f"EMA crossed UP but blocked by RSI (RSI {last['rsi']:.1f} >= {cfg.RSI_UPPER}, overbought)")
        elif bool(last["diag_rsi_blocked_sell"]):
            reason_parts.insert(0, f"EMA crossed DOWN but blocked by RSI (RSI {last['rsi']:.1f} <= {cfg.RSI_LOWER}, oversold)")
        else:
            reason_parts.insert(0, "No fresh EMA crossover on this candle")
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
