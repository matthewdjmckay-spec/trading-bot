"""
Runs continuously in the background: checks every symbol in config.WATCHLIST
every CHECK_INTERVAL_SECONDS, and only sends a Discord message when it's a NEW
BUY/SELL signal for that symbol - not a repeat of one already sent, and not
on every HOLD.
"""
import sys
import time
import json
import os
import traceback
from datetime import datetime

import config
from data_fetcher import fetch_candles
from strategy import latest_signal
from notifier import send_discord_signal, send_trade_closed, send_trade_placed, send_trade_result_summary
import oanda_client

STATE_FILE = "alerted_state.json"
OPEN_TRADES_FILE = "open_trades.json"
STATS_FILE = "trade_stats.json"
HISTORY_FILE = "trade_history.json"


def append_trade_history(symbol: str, outcome: str, realized_pl: float, strategy: str = "ema_crossover"):
    history = _load_json(HISTORY_FILE, default=[])
    history.append({
        "symbol": symbol,
        "outcome": outcome,
        "pnl": realized_pl,
        "strategy": strategy,
        "closed_at": datetime.now().isoformat(),
    })
    _save_json(HISTORY_FILE, history)


def update_and_get_stats(realized_pl: float) -> dict:
    stats = _load_json(STATS_FILE, default={"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0})
    stats["total_trades"] += 1
    if realized_pl > 0:
        stats["wins"] += 1
    elif realized_pl < 0:
        stats["losses"] += 1
    stats["total_pnl"] += realized_pl
    _save_json(STATS_FILE, stats)
    return stats


def track_open_trade(trade_id: str, symbol: str):
    trades = _load_json(OPEN_TRADES_FILE, default={})
    trades[trade_id] = symbol
    _save_json(OPEN_TRADES_FILE, trades)


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def _save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f)


def check_open_trades():
    trades = _load_json(OPEN_TRADES_FILE, default={})
    if not trades:
        return

    still_open = {}
    for trade_id, symbol in trades.items():
        try:
            trade = oanda_client.get_trade(trade_id)
        except Exception as e:
            print(f"Error checking trade {trade_id} ({symbol}): {e}")
            still_open[trade_id] = symbol
            continue

        if trade["state"] == "OPEN":
            still_open[trade_id] = symbol
            continue

        realized_pl = float(trade.get("realizedPL", 0))
        outcome = "TAKE_PROFIT" if realized_pl > 0 else "STOP_LOSS" if realized_pl < 0 else "CLOSED"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {symbol}: trade {trade_id} CLOSED - {outcome} - P/L: {realized_pl:+.2f}")
        send_trade_closed(get_webhook_for(symbol), symbol, outcome, realized_pl)

        stats = update_and_get_stats(realized_pl)
        append_trade_history(symbol, outcome, realized_pl)
        send_trade_result_summary(config.TRADE_RESULTS_WEBHOOK_URL, symbol, outcome, realized_pl, stats)

    _save_json(OPEN_TRADES_FILE, still_open)


def load_last_alerted(symbol: str):
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        return state.get(symbol)
    except (json.JSONDecodeError, IOError):
        return None


def save_last_alerted(symbol: str, timestamp_str: str):
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            state = {}
    state[symbol] = timestamp_str
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_webhook_for(symbol: str) -> str:
    return config.DISCORD_WEBHOOKS.get(symbol) or config.DEFAULT_DISCORD_WEBHOOK_URL


def has_open_trade_for_symbol(symbol: str) -> bool:
    trades = _load_json(OPEN_TRADES_FILE, default={})
    return symbol in trades.values()


def check_once(symbol: str):
    df = fetch_candles(symbol, config.LOOKBACK_PERIOD, config.INTERVAL)
    sig = latest_signal(df, config, symbol)
    ts_str = str(sig.timestamp)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if sig.action == "HOLD":
        print(f"[{now}] {symbol}: HOLD - {sig.reason}")
        return

    last_alerted = load_last_alerted(symbol)
    if last_alerted == ts_str:
        print(f"[{now}] {symbol}: {sig.action} signal on candle {ts_str} already alerted - skipping duplicate")
        return

    print(f"[{now}] {symbol}: NEW {sig.action} signal @ {sig.price:.4f} - sending Discord alert")
    send_discord_signal(get_webhook_for(symbol), symbol, sig)
    save_last_alerted(symbol, ts_str)

    if has_open_trade_for_symbol(symbol):
        print(f"[{now}] {symbol}: already has an open trade - skipping new entry (matches backtest's one-at-a-time rule)")
        return

    try:
        result = oanda_client.place_market_order(symbol, sig.action, sig.price, sig.stop_loss, sig.take_profit)
        fill = result.get("orderFillTransaction")
        if fill:
            print(f"[{now}] {symbol}: OANDA order FILLED - {fill['units']} units @ {fill['price']}")
            send_trade_placed(get_webhook_for(symbol), symbol, sig.action, int(float(fill["units"])), float(fill["price"]))

            trade_opened = fill.get("tradeOpened")
            if trade_opened:
                track_open_trade(trade_opened["tradeID"], symbol)
        else:
            cancel = result.get("orderCancelTransaction")
            reason = cancel.get("reason") if cancel else "unknown"
            print(f"[{now}] {symbol}: OANDA order NOT filled - reason: {reason}")
    except Exception as e:
        print(f"[{now}] {symbol}: OANDA order FAILED: {e}")


def main():
    symbols = [sys.argv[1]] if len(sys.argv) > 1 else config.WATCHLIST

    if config.OANDA_ENVIRONMENT != "practice":
        print("SAFETY STOP: config.OANDA_ENVIRONMENT is not set to 'practice'.")
        return

    if not any(config.DISCORD_WEBHOOKS.values()) and not config.DEFAULT_DISCORD_WEBHOOK_URL:
        print("WARNING: no webhook URLs configured.")

    print(f"Watching {symbols} - checking every {config.CHECK_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.\n")

    while True:
        for symbol in symbols:
            try:
                check_once(symbol)
            except Exception as e:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{now}] {symbol}: Error during check (will retry next interval): {e}")
                traceback.print_exc()

        try:
            check_open_trades()
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Error checking open trades: {e}")

        time.sleep(config.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
