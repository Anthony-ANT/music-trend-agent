import asyncio
from dotenv import load_dotenv
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
)
from tools.billboard_backfill import backfill_billboard_history
from tools.musicbrainz_extractor import get_artist_genres_bulk
from tools.cleaning_stager import clean_and_stage_all_weeks
from tools.bigquery_loader import load_staged_data_to_bigquery, load_all_staged_data_to_bigquery
from tools.query_reporter import run_bigquery_query

load_dotenv()

SCHEMA_DESCRIPTION = """
Table: chart_history (dataset: music_trends)
Columns:
- chart_date (DATE) — 37 distinct weeks, 2026-01-03 to 2026-09-12
- rank (INTEGER), title (STRING), artist (STRING) — original Billboard credit string
- primary_artist_used (STRING, nullable) — the artist name actually looked up in MusicBrainz;
  NULL for the earliest-loaded week (2026-09-12), populated for all other weeks
- weeks_on_chart (INTEGER), peak_pos (INTEGER)
- last_pos (INTEGER, nullable) — prior week's position; NULL for debuts and re-entry anomalies
- is_debut (BOOLEAN), is_reentry_anomaly (BOOLEAN)
- is_release_week_bulk_entry (BOOLEAN) — flags artists dropping 5+ simultaneous debuts in one week
  (excludes organic movement, e.g. Rod Wave, J. Cole had large flood weeks)
- mbid (STRING, nullable), genre_tags (REPEATED STRING) — filtered to a curated genre allowlist

Known data-quality notes:
- Roughly 9 artists (J. Cole, George Birge, Junior H, and others) had confirmed MusicBrainz
  name-collision errors and were manually corrected to have zero genre_tags rather than
  trust a wrong match. An estimated ~10-12% of the ~230 unique artists may have uncaught
  similar issues.
- Exclude is_release_week_bulk_entry = true rows from genre-level analysis.
- A song can have multiple genre_tags; use UNNEST for genre-level analysis.
- You now have 37 weeks of real history — use it. Track a song or genre's rank trajectory
  across multiple weeks, not just single-week deltas, since that's what "climb speed"
  actually means with this much data available.
"""

async def main():
    server = create_sdk_mcp_server(
        name="music-tools",
        version="1.0.0",
        tools=[
            backfill_billboard_history,
            get_artist_genres_bulk,
            clean_and_stage_all_weeks,
            load_staged_data_to_bigquery,
            load_all_staged_data_to_bigquery,
            run_bigquery_query,
        ],
    )

    options = ClaudeAgentOptions(
        mcp_servers={"tools": server},
        allowed_tools=["mcp__tools__run_bigquery_query"],
        disallowed_tools=[
            "Read", "Write", "Edit", "MultiEdit",
            "Bash", "PowerShell",
            "Glob", "Grep",
            "WebSearch", "WebFetch",
            "Task", "TodoRead", "TodoWrite",
        ],
        max_turns=15,
        max_budget_usd=1.50,
        cwd=".",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            f"{SCHEMA_DESCRIPTION}\n\n"
            "Using this full 37-week table, analyze which genres show the fastest "
            "chart climb on the Billboard Hot 100 this year. Write and run the SQL "
            "yourself. Use the full time series properly — e.g. rank trajectory per "
            "song/genre over multiple weeks — rather than a single-week delta. "
            "Include sample size per genre alongside any climb-speed statistic, and "
            "check whether findings survive removing outlier songs before reporting "
            "them as real. Give a final written summary with your conclusion and caveats."
        )
        async for msg in client.receive_response():
            print(msg)

if __name__ == "__main__":
    asyncio.run(main())