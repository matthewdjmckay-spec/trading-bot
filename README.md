# Trading Signal Bot — v1

A simple, fully transparent signal bot: pulls price data, runs an
EMA-crossover + RSI + ATR strategy, and tells you BUY / SELL / HOLD with a
stop loss and take profit. Built for **logic testing on a demo account**,
not live trading with real money.

## What it does

- Pulls candle data for any symbol yfinance supports (gold, forex pairs, crypto, stocks).
- Computes EMA(9)/EMA(21) crossover, RSI(14), and ATR(14).
- Fires a BUY when the fast EMA crosses above the slow EMA and RSI isn't
  already overbought; SELL on the mirror condition.
- Sets stop loss / take profit as a multiple of ATR, so they scale with
  current volatility instead of being a fixed number of pips.
- Backtests the strategy with a chronological train/test split, so you can
  see whether it holds up on data it wasn't "tuned" on.
- Optionally pings a Discord webhook with the signal.

## Setup

```bash
pip install -r requirements.txt
```

If you want Discord alerts: create a webhook (Discord server → channel
settings → Integrations → Webhooks → New Webhook → Copy URL) and paste it
into `config.py` as `DISCORD_WEBHOOK_URL`.

## Usage

Get the current signal:
```bash
python main.py signal
python main.py signal EURUSD=X      # override symbol for this run
```

Run a backtest:
```bash
python main.py backtest
python main.py backtest GC=F
```

## Switching instruments

Edit `SYMBOL` in `config.py`, or pass a symbol on the command line. Common
yfinance tickers:

| Instrument | Ticker |
|---|---|
| Gold (futures, closest free proxy to XAUUSD) | `GC=F` |
| EUR/USD | `EURUSD=X` |
| GBP/USD | `GBPUSD=X` |
| USD/JPY | `JPY=X` |
| Bitcoin | `BTC-USD` |

**Note:** yfinance doesn't give true broker spot/spread data for XAUUSD.
Prices will be close but not identical to what you'd see on your demo
platform (MT4/MT5, etc). Fine for v1 logic testing — before you act on a
signal on the demo account, glance at your broker's own chart to confirm
you're looking at a similar setup.

## Reading the backtest output

```
Trades: 47
Win rate: 44.7%
Avg win: +0.33%  |  Avg loss: -0.19%
Expectancy per trade: +0.039%
Max drawdown (cumulative %): -1.12%
```

- **Win rate is not the number that matters.** A 45% win rate with wins
  bigger than losses (like above) beats an 80% win rate where the 20% of
  losses are catastrophic. If you ever see backtest win rates around 80%+,
  that's a signal to suspect a bug or overfitting — not a signal to get
  excited.
- **Expectancy per trade** is the real bottom line: average % gain/loss per
  trade, across wins and losses combined. Positive and consistent across
  both the train and test windows is what you're actually looking for.
- **Train vs Test**: if performance looks great on train and falls apart on
  test, the strategy was shaped around noise in that specific period, not a
  real pattern.

## Known limitations of v1 (on purpose, to keep it simple)

- No spread, commission, or slippage modeled in the backtest — real results
  will be a bit worse than shown.
- One position open at a time, no partial fills or scaling in/out.
- The strategy logic (EMA/RSI/ATR crossover) is intentionally simple and
  readable rather than optimized — the point of v1 is to have a working,
  understandable skeleton you can now start experimenting on.
- yfinance limits how much history you can pull at small intervals (e.g.
  1m/5m candles are usually only available for the last several days).

## Sensible next steps once you've played with this

1. Paper trade / demo trade this for a couple weeks and log every signal
   vs what the market actually did — compare live signal quality to what
   the backtest predicted.
2. Add spread/commission modeling to the backtest so numbers are more honest.
3. Try walk-forward testing (re-run train/test on rolling windows) instead
   of a single 70/30 split, before trusting any parameter you tune.
4. Only then consider swapping the strategy layer for something more
   sophisticated (multi-indicator confirmation, ML models, etc.) — once you
   have a backtest harness you trust, experimenting on top of it is a much
   more grounded exercise.
