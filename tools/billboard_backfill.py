import json
import os
import time
import requests
from datetime import datetime, timedelta
import billboard
from claude_agent_sdk import tool

# billboard.py doesn't set a browser-like User-Agent by default, which can
# trigger bot detection / empty responses on repeated historical requests.
# Patch requests globally to always send one.
_original_get = requests.get
def _patched_get(*args, **kwargs):
    headers = kwargs.get("headers", {}) or {}
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    kwargs["headers"] = headers
    return _original_get(*args, **kwargs)
requests.get = _patched_get


async def _backfill_since(start_date_str="2026-01-01"):
    os.makedirs("data/raw", exist_ok=True)
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

    current = billboard.ChartData("hot-100")
    current_date = datetime.strptime(current.date, "%Y-%m-%d")

    saved = []
    failed = []
    target_date_dt = current_date

    while target_date_dt >= start_date:
        target_date = target_date_dt.strftime("%Y-%m-%d")

        chart = None
        for attempt in range(3):
            try:
                chart = billboard.ChartData("hot-100", date=target_date)
                if len(chart) == 0:
                    print(f"  Empty response for {target_date}, attempt {attempt+1}/3, retrying...", flush=True)
                    chart = None
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                print(f"  Error for {target_date}, attempt {attempt+1}/3: {e}", flush=True)
                time.sleep(3)

        if chart is None or len(chart) == 0:
            print(f"FAILED after retries: {target_date}", flush=True)
            failed.append(target_date)
            target_date_dt -= timedelta(weeks=1)
            continue

        entries = [
            {"rank": e.rank, "title": e.title, "artist": e.artist,
             "weeks_on_chart": e.weeks, "peak_pos": e.peakPos, "last_pos": e.lastPos}
            for e in chart
        ]
        actual_date = chart.date
        out_path = f"data/raw/billboard_hot100_{actual_date}.json"
        with open(out_path, "w") as f:
            json.dump({"chart_date": actual_date, "entries": entries}, f, indent=2)

        saved.append(actual_date)
        print(f"[{len(saved)}] Saved {actual_date}", flush=True)
        time.sleep(2)  # slightly longer delay, more polite
        target_date_dt -= timedelta(weeks=1)

    result = f"Backfilled {len(saved)} weeks: {saved[-1] if saved else 'none'} to {saved[0] if saved else 'none'}"
    if failed:
        result += f". FAILED after retries: {', '.join(failed)}"
    return result


@tool(
    "backfill_billboard_history",
    "Fetch Billboard Hot 100 history since a given date and save each week as raw JSON",
    {"weeks": int}
)
async def backfill_billboard_history(args):
    weeks = args.get("weeks", 12)
    # kept for compatibility, not used by _backfill_since
    return {"content": [{"type": "text", "text": "Use _backfill_since directly for date-range backfills."}]}