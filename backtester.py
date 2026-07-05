"""
Simple, transparent bar-by-bar backtest (no vectorbt dependency, so it's
easy to install and easy to read). One position open at a time.

IMPORTANT LIMITATIONS (read this before trusting any output number):
- No spread/commission modeled by default - real fills will be worse than this.
- Assumes you get filled exactly at the close of the signal candle - in reality
  there's slippage, especially on fast timeframes.
- This is v1 for *logic testing*, not a source of truth for expected returns.
  Always sanity-check results against out-of-sample data (see run_backtest's
  train/test split) before trusting a strategy at all, let alone with money.
"""
from dataclasses import dataclass, field
from typing import List
import pandas as pd

from strategy import generate_signals


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    outcome: str   # "TP", "SL", or "EOD" (still open at end of data)
    pnl_pct: float


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)

    @property
    def total_trades(self):
        return len(self.trades)

    @property
    def win_rate(self):
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl_pct > 0)
        return 100 * wins / len(self.trades)

    @property
    def avg_win_pct(self):
        wins = [t.pnl_pct for t in self.trades if t.pnl_pct > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def avg_loss_pct(self):
        losses = [t.pnl_pct for t in self.trades if t.pnl_pct <= 0]
        return sum(losses) / len(losses) if losses else 0.0

    @property
    def expectancy_pct(self):
        """Average pnl% per trade - the number that actually matters, not win rate alone."""
        if not self.trades:
            return 0.0
        return sum(t.pnl_pct for t in self.trades) / len(self.trades)

    @property
    def max_drawdown_pct(self):
        if not self.trades:
            return 0.0
        equity = [0.0]
        for t in self.trades:
            equity.append(equity[-1] + t.pnl_pct)
        peak = equity[0]
        max_dd = 0.0
        for val in equity:
            peak = max(peak, val)
            max_dd = min(max_dd, val - peak)
        return max_dd

    def summary(self) -> str:
        return (
            f"Trades: {self.total_trades}\n"
            f"Win rate: {self.win_rate:.1f}%\n"
            f"Avg win: {self.avg_win_pct:+.2f}%  |  Avg loss: {self.avg_loss_pct:+.2f}%\n"
            f"Expectancy per trade: {self.expectancy_pct:+.3f}%\n"
            f"Max drawdown (cumulative %): {self.max_drawdown_pct:.2f}%"
        )


def run_backtest(df: pd.DataFrame, cfg) -> BacktestResult:
    data = generate_signals(df, cfg)
    result = BacktestResult()

    open_trade = None

    for i in range(len(data)):
        row = data.iloc[i]

        if open_trade is not None:
            direction = open_trade["direction"]
            hit_tp = (row["High"] >= open_trade["take_profit"]) if direction == "BUY" else (row["Low"] <= open_trade["take_profit"])
            hit_sl = (row["Low"] <= open_trade["stop_loss"]) if direction == "BUY" else (row["High"] >= open_trade["stop_loss"])

            # Conservative assumption: if both TP and SL could have been hit in the
            # same candle, assume the worse outcome (SL) happened first.
            if hit_sl:
                exit_price = open_trade["stop_loss"]
                outcome = "SL"
            elif hit_tp:
                exit_price = open_trade["take_profit"]
                outcome = "TP"
            else:
                continue  # trade still open, move to next bar

            pnl_pct = (
                (exit_price - open_trade["entry_price"]) / open_trade["entry_price"] * 100
                if direction == "BUY"
                else (open_trade["entry_price"] - exit_price) / open_trade["entry_price"] * 100
            )

            result.trades.append(Trade(
                entry_time=open_trade["entry_time"],
                exit_time=row.name,
                direction=direction,
                entry_price=open_trade["entry_price"],
                exit_price=exit_price,
                stop_loss=open_trade["stop_loss"],
                take_profit=open_trade["take_profit"],
                outcome=outcome,
                pnl_pct=pnl_pct,
            ))
            open_trade = None
            continue  # don't open a new trade on the same bar we just closed one

        if row["action"] in ("BUY", "SELL") and pd.notna(row["stop_loss"]):
            open_trade = {
                "direction": row["action"],
                "entry_time": row.name,
                "entry_price": row["Close"],
                "stop_loss": row["stop_loss"],
                "take_profit": row["take_profit"],
            }

    return result


def train_test_split_backtest(df: pd.DataFrame, cfg, split_ratio: float = 0.7):
    """
    Splits data chronologically and runs the backtest separately on each half.
    A strategy that looks great on the train half and falls apart on the test
    half is a strategy that was overfit, not one that has a real edge.
    """
    split_idx = int(len(df) * split_ratio)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    train_result = run_backtest(train_df, cfg)
    test_result = run_backtest(test_df, cfg)

    return train_result, test_result
