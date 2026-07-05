"""
CLI entry point.

Usage:
    python main.py signal              -> get current buy/sell/hold for config.SYMBOL
    python main.py signal EURUSD=X     -> override the symbol for this run
    python main.py backtest            -> run train/test split backtest on config.SYMBOL
    python main.py backtest GC=F       -> backtest a different symbol
"""
import sys

import config
from data_fetcher import fetch_candles
from strategy import latest_signal
from backtester import train_test_split_backtest
from notifier import send_discord_signal


def cmd_signal(symbol: str):
    print(f"Fetching {symbol} @ {config.INTERVAL} candles ({config.LOOKBACK_PERIOD} lookback)...")
    df = fetch_candles(symbol, config.LOOKBACK_PERIOD, config.INTERVAL)
    sig = latest_signal(df, config, symbol)

    print("\n--- SIGNAL ---")
    print(f"Symbol:     {symbol}")
    print(f"Time:       {sig.timestamp}")
    print(f"Action:     {sig.action}")
    print(f"Price:      {sig.price:.4f}")
    if sig.stop_loss is not None:
        print(f"Stop Loss:  {sig.stop_loss:.4f}")
        print(f"Take Profit:{sig.take_profit:.4f}")
    print(f"Reason:     {sig.reason}")

    if sig.action != "HOLD":
        webhook = config.DISCORD_WEBHOOKS.get(symbol) or config.DEFAULT_DISCORD_WEBHOOK_URL
        send_discord_signal(webhook, symbol, sig)


def cmd_backtest(symbol: str):
    print(f"Backtesting {symbol} @ {config.BACKTEST_INTERVAL} over {config.BACKTEST_PERIOD}...")
    df = fetch_candles(symbol, config.BACKTEST_PERIOD, config.BACKTEST_INTERVAL)
    train_result, test_result = train_test_split_backtest(df, config)

    print("\n=== TRAIN (first 70% of data) ===")
    print(train_result.summary())
    print("\n=== TEST (last 30% of data, unseen by 'training') ===")
    print(test_result.summary())

    print(
        "\nNote: this strategy has no parameters being fitted/optimized in v1, "
        "so 'train' vs 'test' here just checks consistency across two different "
        "market periods - not overfitting in the formal sense yet. Once you start "
        "tuning EMA/RSI/ATR values in config.py to chase better backtest numbers, "
        "this split becomes essential: only trust settings that hold up on the "
        "TEST half, not ones that only look good on TRAIN."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("signal", "backtest"):
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else config.SYMBOL

    if mode == "signal":
        cmd_signal(symbol)
    else:
        cmd_backtest(symbol)
