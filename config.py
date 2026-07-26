"""
Central config. Change SYMBOL to switch instruments without touching other files.

Secrets (API keys, webhooks) are NOT stored in this file, on purpose - this file
is safe to upload to GitHub. Locally, real values come from local_secrets.py
(which is in .gitignore and never gets uploaded). On GitHub Actions, real values
come from GitHub Secrets instead. Either way, this file just reads whichever is
available.
"""
import os

try:
    import local_secrets as _local
except ImportError:
    _local = None


def _secret(env_name: str) -> str:
    """Environment variable (GitHub Actions) takes priority, then local_secrets.py (your Mac), then blank."""
    return os.getenv(env_name) or (getattr(_local, env_name, "") if _local else "") or ""


SYMBOL = "GC=F"
WATCHLIST = ["GC=F", "EURUSD=X", "GBPUSD=X"]
INTERVAL = "15m"
LOOKBACK_PERIOD = "5d"

EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_UPPER = 70
RSI_LOWER = 30
ATR_PERIOD = 14
ATR_SL_MULT = 1.5
ATR_TP_MULT = 2.5

BACKTEST_PERIOD = "60d"
BACKTEST_INTERVAL = "15m"
INITIAL_BALANCE = 10000
RISK_PER_TRADE_PCT = 1.0
MAX_MARGIN_USAGE_PCT = 5.0

DISCORD_WEBHOOKS = {
    "GC=F": _secret("DISCORD_WEBHOOK_GOLD"),
    "EURUSD=X": _secret("DISCORD_WEBHOOK_EURUSD"),
    "GBPUSD=X": _secret("DISCORD_WEBHOOK_GBPUSD"),
}
DEFAULT_DISCORD_WEBHOOK_URL = _secret("DISCORD_WEBHOOK_DEFAULT")
TRADE_RESULTS_WEBHOOK_URL = _secret("DISCORD_WEBHOOK_RESULTS")

OANDA_API_TOKEN = _secret("OANDA_API_TOKEN")
OANDA_ACCOUNT_ID = _secret("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = _secret("OANDA_ENVIRONMENT") or "practice"

CHECK_INTERVAL_SECONDS = 60
