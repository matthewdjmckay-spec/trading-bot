"""
Thin wrapper around OANDA's v20 REST API. Handles:
- authentication
- mapping our internal symbol names (from yfinance, e.g. "GC=F") to OANDA's
  instrument names (e.g. "XAU_USD")
- position sizing based on account risk %
- placing a market order with attached stop loss / take profit

OANDA API docs: https://developer.oanda.com/rest-live-v20/introduction/
"""
import requests
import config

BASE_URLS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

# Maps our yfinance-style symbols to OANDA's instrument naming convention.
# Extend this if you add more symbols to config.WATCHLIST.
SYMBOL_MAP = {
    "GC=F": "XAU_USD",
    "EURUSD=X": "EUR_USD",
    "GBPUSD=X": "GBP_USD",
    "JPY=X": "USD_JPY",
    "BTC-USD": "BTC_USD",
}


def _base_url():
    return BASE_URLS[config.OANDA_ENVIRONMENT]


def _headers():
    return {
        "Authorization": f"Bearer {config.OANDA_API_TOKEN}",
        "Content-Type": "application/json",
    }


def to_oanda_instrument(symbol: str) -> str:
    if symbol not in SYMBOL_MAP:
        raise ValueError(
            f"No OANDA instrument mapping for '{symbol}'. Add it to SYMBOL_MAP in oanda_client.py."
        )
    return SYMBOL_MAP[symbol]


def test_connection() -> dict:
    """
    Confirms the token + account ID work. Returns account summary info,
    or raises an exception with OANDA's error message if something's wrong.
    """
    url = f"{_base_url()}/v3/accounts/{config.OANDA_ACCOUNT_ID}/summary"
    resp = requests.get(url, headers=_headers(), timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"OANDA connection failed ({resp.status_code}): {resp.text}")
    return resp.json()["account"]


def get_account_balance() -> float:
    account = test_connection()
    return float(account["balance"])


def calculate_units(direction: str, entry_price: float, stop_loss: float) -> int:
    """
    Position size based on config.RISK_PER_TRADE_PCT of account balance.

    NOTE - simplification for v1: this treats 1 unit of price movement as
    1 unit of account currency risk, which is only exactly true for pairs
    quoted directly in your account currency (e.g. EUR_USD when your account
    is in USD). For XAU_USD or JPY pairs the true risk-per-unit differs -
    good enough for demo-account testing, but not precise enough to rely on
    with real money without refining the pip-value calculation per instrument.
    """
    balance = get_account_balance()
    risk_amount = balance * (config.RISK_PER_TRADE_PCT / 100)
    price_risk = abs(entry_price - stop_loss)

    if price_risk == 0:
        raise ValueError("Stop loss distance is zero - can't size a position.")

    units = int(risk_amount / price_risk)
    if direction == "SELL":
        units = -units
    return units


def get_trade(trade_id: str) -> dict:
    """
    Fetches current status of a single trade by ID. Use this to check whether
    an open trade has since closed (hit its TP or SL).
    """
    url = f"{_base_url()}/v3/accounts/{config.OANDA_ACCOUNT_ID}/trades/{trade_id}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"OANDA get_trade failed ({resp.status_code}): {resp.text}")
    return resp.json()["trade"]


def place_market_order(symbol: str, direction: str, entry_price: float, stop_loss: float, take_profit: float) -> dict:
    """
    Places a market order on OANDA with attached stop loss and take profit.
    direction must be "BUY" or "SELL".
    Returns OANDA's response JSON, or raises an exception on failure.
    """
    instrument = to_oanda_instrument(symbol)
    units = calculate_units(direction, entry_price, stop_loss)

    order_payload = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": f"{stop_loss:.5f}"},
            "takeProfitOnFill": {"price": f"{take_profit:.5f}"},
        }
    }

    url = f"{_base_url()}/v3/accounts/{config.OANDA_ACCOUNT_ID}/orders"
    resp = requests.post(url, headers=_headers(), json=order_payload, timeout=10)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"OANDA order failed ({resp.status_code}): {resp.text}")

    return resp.json()
