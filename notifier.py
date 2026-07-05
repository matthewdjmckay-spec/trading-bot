"""
Sends the current signal to Discord via a webhook. Telegram is not included
in v1 to keep things simple - Discord webhooks need zero bot-setup ceremony
(no bot token, no slash commands), just a URL you paste into config.py.

To get a webhook URL: Discord server -> channel settings -> Integrations ->
Webhooks -> New Webhook -> Copy Webhook URL.
"""
import requests


def send_discord_signal(webhook_url: str, symbol: str, signal) -> bool:
    if not webhook_url:
        print("[notifier] No Discord webhook configured in config.py - skipping send.")
        return False

    color = {"BUY": 3066993, "SELL": 15158332, "HOLD": 9807270}.get(signal.action, 9807270)

    direction_word = "rising" if signal.action == "BUY" else "falling"
    plain_english = (
        f"The strategy thinks price is about to start {direction_word}, based on a "
        f"short-term average crossing a longer-term average."
    )

    fields = [
        {"name": "Entry price", "value": f"{signal.price:.4f}", "inline": True},
    ]

    if signal.stop_loss is not None and signal.take_profit is not None:
        risk = abs(signal.price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.price)
        rr_ratio = reward / risk if risk > 0 else 0

        fields.append({
            "name": "🛑 Stop Loss (exit if wrong)",
            "value": f"{signal.stop_loss:.4f}  (risking {risk:.4f})",
            "inline": True,
        })
        fields.append({
            "name": "🎯 Take Profit (exit if right)",
            "value": f"{signal.take_profit:.4f}  (targeting {reward:.4f})",
            "inline": True,
        })
        fields.append({
            "name": "Risk : Reward",
            "value": f"1 : {rr_ratio:.2f}  (for every $1 risked, this targets ${rr_ratio:.2f})",
            "inline": False,
        })

    fields.append({"name": "Why it fired", "value": signal.reason, "inline": False})

    embed = {
        "title": f"{symbol} — {signal.action}" + (" 📈" if signal.action == "BUY" else " 📉"),
        "description": plain_english,
        "color": color,
        "fields": fields,
        "footer": {"text": "Automated v1 strategy signal — for demo account testing only, not financial advice."},
        "timestamp": signal.timestamp.isoformat() if hasattr(signal.timestamp, "isoformat") else None,
    }

    payload = {"embeds": [embed]}

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    return True


def send_trade_placed(webhook_url: str, symbol: str, direction: str, units: int, fill_price: float) -> bool:
    if not webhook_url:
        return False

    embed = {
        "title": f"✅ Trade placed — {symbol}",
        "description": f"{direction} order filled on your OANDA demo account.",
        "color": 3447003,
        "fields": [
            {"name": "Units", "value": str(abs(units)), "inline": True},
            {"name": "Fill price", "value": f"{fill_price:.5f}", "inline": True},
        ],
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    resp.raise_for_status()
    return True


def send_trade_closed(webhook_url: str, symbol: str, outcome: str, realized_pl: float) -> bool:
    if not webhook_url:
        return False

    if outcome == "TAKE_PROFIT":
        title = f"🎯 Take Profit hit — {symbol}"
        color = 3066993
    elif outcome == "STOP_LOSS":
        title = f"🛑 Stop Loss hit — {symbol}"
        color = 15158332
    else:
        title = f"🔔 Trade closed — {symbol}"
        color = 9807270

    embed = {
        "title": title,
        "description": f"Realized P/L: {realized_pl:+.2f}",
        "color": color,
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    resp.raise_for_status()
    return True


def send_trade_result_summary(webhook_url: str, symbol: str, outcome: str, realized_pl: float, stats: dict) -> bool:
    """
    Posts to the dedicated running-P/L channel: this trade's result plus
    the cumulative scoreboard (total trades, win rate, total P/L) so far.
    """
    if not webhook_url:
        return False

    color = 3066993 if realized_pl > 0 else 15158332 if realized_pl < 0 else 9807270
    outcome_label = {"TAKE_PROFIT": "Win (TP)", "STOP_LOSS": "Loss (SL)"}.get(outcome, "Closed")

    win_rate = (stats["wins"] / stats["total_trades"] * 100) if stats["total_trades"] else 0.0

    embed = {
        "title": f"{symbol} — {outcome_label}",
        "color": color,
        "fields": [
            {"name": "This trade", "value": f"{realized_pl:+.2f}", "inline": True},
            {"name": "Total trades", "value": str(stats["total_trades"]), "inline": True},
            {"name": "Win rate", "value": f"{win_rate:.1f}%", "inline": True},
            {"name": "Total P/L (running)", "value": f"{stats['total_pnl']:+.2f}", "inline": False},
        ],
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    resp.raise_for_status()
    return True
