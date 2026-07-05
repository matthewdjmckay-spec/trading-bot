"""
One-shot version of auto_runner.py, built for GitHub Actions.

Instead of looping forever (which needs a computer that never turns off),
this runs ONE check across the whole watchlist, then exits. GitHub Actions
calls this on a schedule (e.g. every 15 minutes) - see
.github/workflows/trading_bot.yml

This reuses the exact same logic as auto_runner.py (check_once,
check_open_trades) so behavior is identical - just single-shot instead of
an infinite loop.
"""
import config
from auto_runner import check_once, check_open_trades

if __name__ == "__main__":
    if config.OANDA_ENVIRONMENT != "practice":
        print("SAFETY STOP: OANDA_ENVIRONMENT is not 'practice'. Exiting without doing anything.")
        raise SystemExit(1)

    for symbol in config.WATCHLIST:
        try:
            check_once(symbol)
        except Exception as e:
            print(f"{symbol}: Error during check: {e}")

    try:
        check_open_trades()
    except Exception as e:
        print(f"Error checking open trades: {e}")
