import os
from google.cloud import bigquery
from claude_agent_sdk import tool

SCHEMA_DESCRIPTION = """
Table: chart_history (dataset: music_trends)
Columns:
- chart_date (DATE)
- rank (INTEGER) — current week's chart position
- title (STRING)
- artist (STRING)
- weeks_on_chart (INTEGER)
- peak_pos (INTEGER)
- last_pos (INTEGER, nullable) — prior week's position; NULL for debuts and re-entry anomalies
- is_debut (BOOLEAN)
- is_reentry_anomaly (BOOLEAN) — true prior position unknown, do not treat as a debut
- is_release_week_bulk_entry (BOOLEAN) — flag for artists dropping 5+ simultaneous debuts (excludes organic movement)
- mbid (STRING, nullable) — MusicBrainz artist ID, NULL if unmatched
- genre_tags (REPEATED STRING) — MusicBrainz community tags, empty array if none recorded

Notes for analysis:
- Climb speed for a song this week = last_pos - rank (positive = moved up), only meaningful where last_pos IS NOT NULL
- Exclude is_release_week_bulk_entry = true rows from genre-level averages — they distort results (one artist dumping an album)
- A song can have multiple genre_tags; use UNNEST to analyze at the genre level
- Only one week of data currently loaded (2026-09-12) — this is a single-week snapshot, not a trend yet
"""

@tool(
    "run_bigquery_query",
    "Run a read-only SQL query against the chart_history table in BigQuery and return the results",
    {"sql": str}
)
async def run_bigquery_query(args):
    sql = args["sql"].strip()

    if not sql.upper().startswith("SELECT"):
        return {"content": [{"type": "text", "text": "Only SELECT queries are allowed. Query rejected."}]}

    client = bigquery.Client()
    try:
        results = client.query(sql).result()
        rows = [dict(row) for row in results]
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Query failed: {e}"}]}

    if not rows:
        return {"content": [{"type": "text", "text": "Query returned no rows."}]}

    return {"content": [{"type": "text", "text": str(rows[:50])}]}  # cap output size