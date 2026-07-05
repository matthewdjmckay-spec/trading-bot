"""
Sends fake example messages to Discord so you can confirm every channel and
message type is wired up correctly, without waiting for a real signal or trade.

Usage:
    python3 test_notifier.py
"""
import pandas as pd

import config
from strategy import Signal
from notifier import send_discord_signal, send_trade_placed, send_trade_closed, send_trade_result_summary

symbol = "GC=F"

print("Testing signal message (gold channel)...")
fake_signal = Signal(
    timestamp=pd.Timestamp.now(),
    action="BUY",
    price=4188.50,
    stop_loss=4175.16,
    take_profit=4210.73,
    reason="TEST MESSAGE - not a real signal | EMA9=4189.58 | EMA21=4176.38 | RSI(14)=66.4",
)
webhook = config.DISCORD_WEBHOOKS.get(symbol) or config.DEFAULT_DISCORD_WEBHOOK_URL
print("  ->", "OK" if send_discord_signal(webhook, symbol, fake_signal) else "FAILED (check webhook in config.py)")

print("Testing 'trade placed' message (gold channel)...")
print("  ->", "OK" if send_trade_placed(webhook, symbol, "BUY", 238, 4188.50) else "FAILED")

print("Testing 'trade closed' message (gold channel)...")
print("  ->", "OK" if send_trade_closed(webhook, symbol, "TAKE_PROFIT", 42.50) else "FAILED")

print("Testing trade-results summary channel...")
fake_stats = {"total_trades": 3, "wins": 2, "losses": 1, "total_pnl": 18.30}
print("  ->", "OK" if send_trade_result_summary(config.TRADE_RESULTS_WEBHOOK_URL, symbol, "TAKE_PROFIT", 42.50, fake_stats) else "FAILED (check TRADE_RESULTS_WEBHOOK_URL in config.py)")

print("Testing EUR/USD channel...")
eurusd_webhook = config.DISCORD_WEBHOOKS.get("EURUSD=X")
print("  ->", "OK" if send_discord_signal(eurusd_webhook, "EURUSD=X", fake_signal) else "FAILED (check DISCORD_WEBHOOK_EURUSD in local_secrets.py)")

print("Testing GBP/USD channel...")
gbpusd_webhook = config.DISCORD_WEBHOOKS.get("GBPUSD=X")
print("  ->", "OK" if send_discord_signal(gbpusd_webhook, "GBPUSD=X", fake_signal) else "FAILED (check DISCORD_WEBHOOK_GBPUSD in local_secrets.py)")

print("\nDone. Check all your Discord channels now - each should have one new test message.")
