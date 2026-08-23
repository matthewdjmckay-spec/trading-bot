"""
Called only when a git conflict happens on the state files (two runs tried to
save at once). Instead of blindly keeping one run's version and silently
losing the other's trade entries, this properly merges:

- trade_history.json: union of both runs' trade entries (no data loss)
- open_trades.json / alerted_state.json: merged dicts (safe, no real overlap risk)
- trade_stats.json: ALWAYS recomputed fresh from the merged trade_history.json,
  rather than merged as separate counters - this also permanently fixes the
  class of bug where trade_stats.json could drift out of sync with the real
  trade log.

Usage (called from the workflow, not run manually):
    python3 merge_state.py
"""
import json
import subprocess
import sys

FILES = ["alerted_state.json", "open_trades.json", "trade_history.json", "trade_stats.json"]


def load_local(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_from_origin(path, default):
    try:
        result = subprocess.run(
            ["git", "show", f"origin/main:{path}"],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return default


def merge_trade_history(ours, theirs):
    combined = ours + theirs
    seen = set()
    merged = []
    for entry in combined:
        key = (entry.get("symbol"), entry.get("outcome"), entry.get("pnl"), entry.get("closed_at"))
        if key not in seen:
            seen.add(key)
            merged.append(entry)
    merged.sort(key=lambda e: e.get("closed_at") or "")
    return merged


def merge_dict(ours, theirs):
    merged = dict(theirs)
    merged.update(ours)
    return merged


def recompute_stats(history):
    wins = sum(1 for t in history if t["pnl"] > 0)
    losses = sum(1 for t in history if t["pnl"] < 0)
    total_pnl = sum(t["pnl"] for t in history)
    return {"total_trades": len(history), "wins": wins, "losses": losses, "total_pnl": total_pnl}


def main():
    ours_history = load_local("trade_history.json", [])
    theirs_history = load_from_origin("trade_history.json", [])
    merged_history = merge_trade_history(ours_history, theirs_history)

    ours_open = load_local("open_trades.json", {})
    theirs_open = load_from_origin("open_trades.json", {})
    merged_open = merge_dict(ours_open, theirs_open)

    ours_alerted = load_local("alerted_state.json", {})
    theirs_alerted = load_from_origin("alerted_state.json", {})
    merged_alerted = merge_dict(ours_alerted, theirs_alerted)

    merged_stats = recompute_stats(merged_history)

    with open("trade_history.json", "w") as f:
        json.dump(merged_history, f)
    with open("open_trades.json", "w") as f:
        json.dump(merged_open, f)
    with open("alerted_state.json", "w") as f:
        json.dump(merged_alerted, f)
    with open("trade_stats.json", "w") as f:
        json.dump(merged_stats, f)

    print(f"Merged state: {len(merged_history)} total trade history entries "
          f"({len(ours_history)} local + {len(theirs_history)} remote, "
          f"{len(ours_history) + len(theirs_history) - len(merged_history)} exact duplicates removed).")


if __name__ == "__main__":
    main()
