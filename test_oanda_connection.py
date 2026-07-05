"""
Run this FIRST, before anything else, to confirm your OANDA token and
account ID are correct. It doesn't place any trades - it just checks that
OANDA recognizes your credentials and prints your account info back.

Usage:
    python3 test_oanda_connection.py
"""
import config
from oanda_client import test_connection

if not config.OANDA_API_TOKEN or not config.OANDA_ACCOUNT_ID:
    print("OANDA_API_TOKEN or OANDA_ACCOUNT_ID is empty in config.py - fill both in first.")
else:
    try:
        account = test_connection()
        print("Connected successfully!")
        print(f"Account ID:       {account['id']}")
        print(f"Balance:          {account['balance']} {account['currency']}")
        print(f"Open trades:      {account['openTradeCount']}")
        print(f"Unrealized P/L:   {account['unrealizedPL']}")
        print(f"Environment:      {config.OANDA_ENVIRONMENT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        print(
            "\nCommon causes: wrong account ID format, token was regenerated/revoked, "
            "or OANDA_ENVIRONMENT in config.py doesn't match your account type "
            "(should be 'practice' for a demo account)."
        )
