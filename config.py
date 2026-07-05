"""
Central config. Change SYMBOL to switch instruments without touching other files.

yfinance ticker formats:
  Gold (spot proxy):   "GC=F"      (COMEX gold futures, closest free proxy to XAUUSD)
  EUR/USD:             "EURUSD=X"
  GBP/USD:             "GBPUSD=X"
  USD/JPY:             "JPY=X"
  Bitcoin:              "BTC-USD"

Note: yfinance does not offer true broker XAUUSD spot/spread data. This is fine for
v1 testing logic, but before demo-account trading, cross-check signals against your
broker's own chart (e.g. MT5) since prices/spreads will differ slightly.
"""

SYMBOL = "GC=F"          # <-- default single symbol (used by main.py)
WATCHLIST = ["GC=F", "EURUSD=X", "GBPUSD=X"]   # <-- symbols auto_runner.py watches when run with no argument
INTERVAL = "15m"          # candle timeframe: 1m,5m,15m,30m,60m,1d etc (yfinance limits history for small intervals)
LOOKBACK_PERIOD = "5d"    # how much history to pull for live signal calc

# Strategy parameters (EMA crossover + RSI filter + ATR-based TP/SL)
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_UPPER = 70            # avoid buying when RSI already overbought
RSI_LOWER = 30            # avoid selling when RSI already oversold
ATR_PERIOD = 14
ATR_SL_MULT = 1.5         # stop loss = ATR * this, away from entry
ATR_TP_MULT = 2.5         # take profit = ATR * this, away from entry (risk:reward ~1:1.67)

# Backtest settings
BACKTEST_PERIOD = "60d"
BACKTEST_INTERVAL = "15m"
INITIAL_BALANCE = 10000
RISK_PER_TRADE_PCT = 1.0   # % of balance risked per trade (for position sizing in backtest)

# Discord notification (optional). Leave blank to skip notifications.
# Paste a different webhook URL per symbol so each instrument posts to its own channel.
# Any symbol not listed here falls back to DEFAULT_DISCORD_WEBHOOK_URL.
DISCORD_WEBHOOKS = {
    "GC=F": "https://discord.com/api/webhooks/1522979502181974059/Hpfm3XjaLN4lSoXLxjwUxSOxHiV_6gpag2CMTF4yrrjZrvNFjStyzaq_DasnF0wB9pRl",       # paste gold channel's webhook URL here
    "EURUSD=X": "https://discord.com/api/webhooks/1522989653916123218/5SejOXFB3qQqynQjlS7XONH7-A8u6M6f0xrj_YQd-T80DhBbJoqgi7WqDmDr6152BIJt",   # paste EUR/USD channel's webhook URL here
    "GBPUSD=X": "https://discord.com/api/webhooks/1522989771301847141/DOtmGltIK6aIqW4qnDaN7rzuwkviV_dQKwAxbblniv8Kr63dS8AIm5Tadr6dSIo0tCId",   # paste GBP/USD channel's webhook URL here
}
DEFAULT_DISCORD_WEBHOOK_URL = ""   # used if a symbol isn't in DISCORD_WEBHOOKS above
TRADE_RESULTS_WEBHOOK_URL = "https://discord.com/api/webhooks/1523434789728686311/UOrSLMic6oq-J8z_CqPK7QRGL8Ah1fhGTha2OQUAvokFtTgC4mV877x6kI4pQpFDGGCf"     # paste a separate channel's webhook here for a running P/L summary of every closed trade

# OANDA demo account credentials - paste your own values here, never share them elsewhere.
# Get these from OANDA Hub -> My Account -> My Services -> Manage API Access (token)
# and from your trading dashboard top-left (account ID, format 100-001-1234567-001).
OANDA_API_TOKEN = "973bfb43f020439fb5c1888a2cb343c7-c895ff574f50c37599c2818514c6c049"     # paste your personal access token here
OANDA_ACCOUNT_ID = "101-004-39722902-001"    # paste your account ID here
OANDA_ENVIRONMENT = "practice"   # "practice" = demo account, "live" = real money (do not use live yet)

# Auto-runner settings (for auto_runner.py - continuous background checking)
CHECK_INTERVAL_SECONDS = 60   # how often to check for a new signal, in seconds

