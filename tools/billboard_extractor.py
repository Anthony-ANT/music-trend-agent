import json
import os
from datetime import datetime
import billboard
from claude_agent_sdk import tool

@tool(
    "get_billboard_hot100",
    "Fetch the current Billboard Hot 100 chart and save it as raw JSON",
    {}
)
async def get_billboard_hot100(args):
    chart = billboard.ChartData("hot-100")

    entries = [
        {
            "rank": entry.rank,
            "title": entry.title,
            "artist": entry.artist,
            "weeks_on_chart": entry.weeks,
            "peak_pos": entry.peakPos,
            "last_pos": entry.lastPos,
        }
        for entry in chart
    ]

    date_str = chart.date or datetime.now().strftime("%Y-%m-%d")
    os.makedirs("data/raw", exist_ok=True)
    out_path = f"data/raw/billboard_hot100_{date_str}.json"

    with open(out_path, "w") as f:
        json.dump({"chart_date": date_str, "entries": entries}, f, indent=2)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Saved {len(entries)} chart entries to {out_path} (chart date: {date_str})"
            }
        ]
    }