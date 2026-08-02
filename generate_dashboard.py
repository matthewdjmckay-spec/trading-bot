"""
Generates a self-contained dashboard.html from the bot's trade data, with an
interactive date range filter (all stats/chart/table recompute live in the
browser - no need to regenerate the file to look at a different date range).

Usage:
    python3 generate_dashboard.py
"""
import json
import os
from datetime import datetime

HISTORY_FILE = "trade_history.json"
OUTPUT_FILE = "dashboard.html"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def build_dashboard():
    history = load_json(HISTORY_FILE, default=[])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

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
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 20px; }}
  .filter-bar {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }}
  .filter-bar label {{ font-size: 13px; color: var(--muted); }}
  .filter-bar input[type="date"] {{
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 13px;
  }}
  .filter-bar button {{
    background: var(--accent);
    color: #0f1419;
    border: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }}
  .filter-bar button.secondary {{
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--border);
  }}
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
  .empty {{ color: var(--muted); }}
</style>
</head>
<body>
  <h1>📊 Trading Bot Dashboard</h1>
  <div class="subtitle" id="subtitle">Generated {generated_at}</div>

  <div class="filter-bar">
    <label for="startDate">From</label>
    <input type="date" id="startDate">
    <label for="endDate">To</label>
    <input type="date" id="endDate">
    <button onclick="applyFilter()">Apply</button>
    <button class="secondary" onclick="clearFilter()">Show all time</button>
  </div>

  <div class="stats-grid" id="statsGrid"></div>

  <div class="card">
    <h2>Cumulative P/L Over Time</h2>
    <canvas id="pnlChart"></canvas>
  </div>

  <div class="card">
    <h2>Performance by Symbol</h2>
    <table id="symbolTable"><tbody></tbody></table>
  </div>

  <div class="card">
    <h2>All Trades (most recent first)</h2>
    <table id="tradeTable"><tbody></tbody></table>
  </div>

<script>
const ALL_TRADES = {json.dumps(history)};
let chart = null;

function render(trades) {{
  const total = trades.length;
  const wins = trades.filter(t => t.pnl > 0).length;
  const losses = trades.filter(t => t.pnl < 0).length;
  const totalPnl = trades.reduce((sum, t) => sum + t.pnl, 0);
  const winRate = total ? (wins / total * 100) : 0;

  document.getElementById('subtitle').textContent =
    `Generated {generated_at} · ${{total}} trade${{total !== 1 ? 's' : ''}} in selected range`;

  document.getElementById('statsGrid').innerHTML = `
    <div class="stat-card"><div class="stat-label">Total Trades</div><div class="stat-value">${{total}}</div></div>
    <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value">${{winRate.toFixed(1)}}%</div></div>
    <div class="stat-card"><div class="stat-label">Wins / Losses</div><div class="stat-value">${{wins}} / ${{losses}}</div></div>
    <div class="stat-card"><div class="stat-label">Total P/L</div><div class="stat-value ${{totalPnl >= 0 ? 'pos' : 'neg'}}">${{totalPnl >= 0 ? '+' : ''}}${{totalPnl.toFixed(2)}}</div></div>
  `;

  const bySymbol = {{}};
  trades.forEach(t => {{
    if (!bySymbol[t.symbol]) bySymbol[t.symbol] = {{ trades: 0, wins: 0, pnl: 0 }};
    bySymbol[t.symbol].trades++;
    if (t.pnl > 0) bySymbol[t.symbol].wins++;
    bySymbol[t.symbol].pnl += t.pnl;
  }});
  const symbolRows = Object.entries(bySymbol).map(([sym, d]) => `
    <tr>
      <td>${{sym}}</td>
      <td>${{d.trades}}</td>
      <td>${{(d.wins / d.trades * 100).toFixed(1)}}%</td>
      <td class="${{d.pnl >= 0 ? 'pos' : 'neg'}}">${{d.pnl >= 0 ? '+' : ''}}${{d.pnl.toFixed(2)}}</td>
    </tr>
  `).join('');
  document.querySelector('#symbolTable tbody').innerHTML =
    `<tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>Total P/L</th></tr>` +
    (symbolRows || '<tr><td colspan="4" class="empty">No trades in this range</td></tr>');

  const tradeRows = [...trades].reverse().map(t => `
    <tr>
      <td>${{t.closed_at.slice(0, 16).replace('T', ' ')}}</td>
      <td>${{t.symbol}}</td>
      <td><span class="badge ${{t.outcome === 'TAKE_PROFIT' ? 'badge-win' : t.outcome === 'STOP_LOSS' ? 'badge-loss' : 'badge-neutral'}}">${{t.outcome.replace('_', ' ')}}</span></td>
      <td class="${{t.pnl >= 0 ? 'pos' : 'neg'}}">${{t.pnl >= 0 ? '+' : ''}}${{t.pnl.toFixed(2)}}</td>
    </tr>
  `).join('');
  document.querySelector('#tradeTable tbody').innerHTML =
    `<tr><th>Closed</th><th>Symbol</th><th>Outcome</th><th>P/L</th></tr>` +
    (tradeRows || '<tr><td colspan="4" class="empty">No trades in this range</td></tr>');

  const byDate = {{}};
  trades.forEach(t => {{
    const day = t.closed_at.slice(0, 10);
    if (!byDate[day]) byDate[day] = [];
    byDate[day].push(t);
  }});
  const sortedDays = Object.keys(byDate).sort();

  let running = 0;
  const cumulative = [];
  sortedDays.forEach(day => {{
    byDate[day].forEach(t => {{ running += t.pnl; }});
    cumulative.push(Math.round(running * 100) / 100);
  }});

  const dateLabels = sortedDays.map(d => {{
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-GB', {{ day: 'numeric', month: 'short' }});
  }});

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('pnlChart'), {{
    type: 'line',
    data: {{
      labels: dateLabels,
      datasets: [{{
        label: 'Cumulative P/L',
        data: cumulative,
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88,166,255,0.1)',
        fill: true,
        tension: 0.2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            title: (items) => {{
              const day = sortedDays[items[0].dataIndex];
              return new Date(day + 'T00:00:00').toLocaleDateString('en-GB', {{ day: 'numeric', month: 'long', year: 'numeric' }});
            }},
            label: (item) => {{
              const day = sortedDays[item.dataIndex];
              return byDate[day].map(t => {{
                const sign = t.pnl >= 0 ? '+' : '';
                const outcomeLabel = t.outcome === 'TAKE_PROFIT' ? 'TP' : t.outcome === 'STOP_LOSS' ? 'SL' : t.outcome;
                return `${{t.symbol}}: ${{sign}}${{t.pnl.toFixed(2)}} (${{outcomeLabel}})`;
              }});
            }},
            afterLabel: () => ''
          }}
        }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b949e', maxTicksLimit: 12 }}, grid: {{ color: '#2a3441' }} }},
        y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#2a3441' }} }}
      }}
    }}
  }});
}}

function applyFilter() {{
  const start = document.getElementById('startDate').value;
  const end = document.getElementById('endDate').value;
  let filtered = ALL_TRADES;
  if (start) filtered = filtered.filter(t => t.closed_at.slice(0, 10) >= start);
  if (end) filtered = filtered.filter(t => t.closed_at.slice(0, 10) <= end);
  render(filtered);
}}

function clearFilter() {{
  document.getElementById('startDate').value = '';
  document.getElementById('endDate').value = '';
  render(ALL_TRADES);
}}

render(ALL_TRADES);
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {OUTPUT_FILE}")
    print(f"Open it in your browser to view (double-click the file, or drag it into a browser window).")


if __name__ == "__main__":
    build_dashboard()
