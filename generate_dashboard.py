"""
Generates a self-contained dashboard.html from the bot's trade data.

Usage:
    python3 generate_dashboard.py

Run this any time (after a `git pull` to get the latest data) and open the
resulting dashboard.html in your browser to see:
- Overall stats: total trades, win rate, total P/L, per-symbol breakdown
- A cumulative P/L chart over time
- A full table of every individual closed trade

This reads trade_stats.json and trade_history.json from the current folder -
both are written automatically by the bot every time a trade closes.
"""
import json
import os
from datetime import datetime

STATS_FILE = "trade_stats.json"
HISTORY_FILE = "trade_history.json"
OUTPUT_FILE = "dashboard.html"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def build_dashboard():
    stats = load_json(STATS_FILE, default={"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0})
    history = load_json(HISTORY_FILE, default=[])

    by_symbol = {}
    for trade in history:
        sym = trade["symbol"]
        by_symbol.setdefault(sym, {"trades": 0, "wins": 0, "pnl": 0.0})
        by_symbol[sym]["trades"] += 1
        if trade["pnl"] > 0:
            by_symbol[sym]["wins"] += 1
        by_symbol[sym]["pnl"] += trade["pnl"]

    win_rate = (stats["wins"] / stats["total_trades"] * 100) if stats["total_trades"] else 0.0

    cumulative = []
    running_total = 0.0
    for trade in history:
        running_total += trade["pnl"]
        cumulative.append(round(running_total, 2))

    labels = [f"Trade {i+1}" for i in range(len(history))]

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    symbol_rows = "".join(
        f"""<tr>
            <td>{sym}</td>
            <td>{data['trades']}</td>
            <td>{(data['wins']/data['trades']*100):.1f}%</td>
            <td class="{'pos' if data['pnl'] >= 0 else 'neg'}">{data['pnl']:+.2f}</td>
        </tr>"""
        for sym, data in by_symbol.items()
    )

    trade_rows = "".join(
        f"""<tr>
            <td>{trade['closed_at'][:16].replace('T', ' ')}</td>
            <td>{trade['symbol']}</td>
            <td><span class="badge {'badge-win' if trade['outcome']=='TAKE_PROFIT' else 'badge-loss' if trade['outcome']=='STOP_LOSS' else 'badge-neutral'}">{trade['outcome'].replace('_',' ').title()}</span></td>
            <td class="{'pos' if trade['pnl'] >= 0 else 'neg'}">{trade['pnl']:+.2f}</td>
        </tr>"""
        for trade in reversed(history)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Trading Bot Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1419;
    --card: #1a2129;
    --border: #2a3441;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #3fb950;
    --red: #f85149;
    --accent: #58a6ff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0;
    padding: 32px;
  }}
  h1 {{ font-size: 22px; margin: 0 0 4px 0; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 28px; }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
  }}
  .stat-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-value {{ font-size: 26px; font-weight: 600; margin-top: 6px; }}
  .pos {{ color: var(--green); }}
  .neg {{ color: var(--red); }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .card h2 {{ font-size: 15px; margin: 0 0 16px 0; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; color: var(--muted); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 12px; text-transform: uppercase; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
  .badge-win {{ background: rgba(63,185,80,0.15); color: var(--green); }}
  .badge-loss {{ background: rgba(248,81,73,0.15); color: var(--red); }}
  .badge-neutral {{ background: rgba(139,148,158,0.15); color: var(--muted); }}
  canvas {{ max-height: 280px; }}
</style>
</head>
<body>
  <h1>📊 Trading Bot Dashboard</h1>
  <div class="subtitle">Generated {generated_at} · {stats['total_trades']} total closed trades</div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Total Trades</div>
      <div class="stat-value">{stats['total_trades']}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Win Rate</div>
      <div class="stat-value">{win_rate:.1f}%</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Wins / Losses</div>
      <div class="stat-value">{stats['wins']} / {stats['losses']}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total P/L</div>
      <div class="stat-value {'pos' if stats['total_pnl'] >= 0 else 'neg'}">{stats['total_pnl']:+.2f}</div>
    </div>
  </div>

  <div class="card">
    <h2>Cumulative P/L Over Time</h2>
    <canvas id="pnlChart"></canvas>
  </div>

  <div class="card">
    <h2>Performance by Symbol</h2>
    <table>
      <tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>Total P/L</th></tr>
      {symbol_rows if symbol_rows else '<tr><td colspan="4" style="color:var(--muted)">No closed trades yet</td></tr>'}
    </table>
  </div>

  <div class="card">
    <h2>All Trades (most recent first)</h2>
    <table>
      <tr><th>Closed</th><th>Symbol</th><th>Outcome</th><th>P/L</th></tr>
      {trade_rows if trade_rows else '<tr><td colspan="4" style="color:var(--muted)">No closed trades yet</td></tr>'}
    </table>
  </div>

<script>
const ctx = document.getElementById('pnlChart');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(labels)},
    datasets: [{{
      label: 'Cumulative P/L',
      data: {json.dumps(cumulative)},
      borderColor: '#58a6ff',
      backgroundColor: 'rgba(88,166,255,0.1)',
      fill: true,
      tension: 0.2,
      pointRadius: 2,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#8b949e', maxTicksLimit: 10 }}, grid: {{ color: '#2a3441' }} }},
      y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#2a3441' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {OUTPUT_FILE}")
    print(f"Open it in your browser to view (double-click the file, or drag it into a browser window).")


if __name__ == "__main__":
    build_dashboard()
