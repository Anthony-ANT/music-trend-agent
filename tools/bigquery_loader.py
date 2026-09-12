import json
import os
import glob
from google.cloud import bigquery
from claude_agent_sdk import tool

SCHEMA = [
    bigquery.SchemaField("chart_date", "DATE"),
    bigquery.SchemaField("rank", "INTEGER"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("artist", "STRING"),
    bigquery.SchemaField("primary_artist_used", "STRING"),
    bigquery.SchemaField("weeks_on_chart", "INTEGER"),
    bigquery.SchemaField("peak_pos", "INTEGER"),
    bigquery.SchemaField("last_pos", "INTEGER"),
    bigquery.SchemaField("is_debut", "BOOLEAN"),
    bigquery.SchemaField("is_reentry_anomaly", "BOOLEAN"),
    bigquery.SchemaField("is_release_week_bulk_entry", "BOOLEAN"),
    bigquery.SchemaField("mbid", "STRING"),
    bigquery.SchemaField("genre_tags", "STRING", mode="REPEATED"),
]

MANIFEST_PATH = "data/staged/.loaded_manifest.json"

def _load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8-sig") as f:
            return set(json.load(f))
    return set()

def _save_manifest(loaded):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(sorted(loaded), f)

async def _load_staged_data():
    staged_files = sorted(glob.glob("data/staged/chart_staged_*.json"))
    if not staged_files:
        return "No staged file found. Run the cleaning/staging tool first."

    latest = staged_files[-1]
    with open(latest) as f:
        rows = json.load(f)

    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    table_id = f"{project_id}.music_trends.chart_history"

    print("\n" + "=" * 60)
    print("BIGQUERY LOAD — APPROVAL REQUIRED")
    print("=" * 60)
    print(f"Source file : {latest}")
    print(f"Target table: {table_id}")
    print(f"Row count   : {len(rows)}")
    print(f"Write mode  : APPEND (adds this week's snapshot to history)")
    print(f"Columns     : {', '.join(f.name for f in SCHEMA)}")
    print("=" * 60)
    confirmation = input("Type YES to proceed with this load, anything else to cancel: ")

    if confirmation.strip() != "YES":
        return "Load cancelled — no changes made to BigQuery."

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
    )

    ndjson_path = latest.replace(".json", "_ndjson.jsonl")
    with open(ndjson_path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    with open(ndjson_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()

    os.remove(ndjson_path)

    return f"Loaded {len(rows)} rows into {table_id} (append mode)."


async def _load_all_staged():
    staged_files = sorted(glob.glob("data/staged/chart_staged_*.json"))
    if not staged_files:
        return "No staged files found."

    already_loaded = _load_manifest()
    to_load = []
    for path in staged_files:
        chart_date = path.split("chart_staged_")[1].replace(".json", "")
        if chart_date not in already_loaded:
            to_load.append((chart_date, path))

    if not to_load:
        return "All staged weeks are already loaded (per local manifest). Nothing to do."

    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    table_id = f"{project_id}.music_trends.chart_history"

    print("\n" + "=" * 60)
    print("BIGQUERY BULK LOAD — APPROVAL REQUIRED")
    print("=" * 60)
    print(f"Target table : {table_id}")
    print(f"Weeks to load: {len(to_load)} ({to_load[0][0]} to {to_load[-1][0]})")
    print(f"Write mode   : APPEND")
    print(f"Columns      : {', '.join(f.name for f in SCHEMA)}")
    print("=" * 60)
    confirmation = input("Type YES to proceed, anything else to cancel: ")

    if confirmation.strip() != "YES":
        return "Load cancelled — no changes made to BigQuery."

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
    )

    total_rows = 0
    for chart_date, path in to_load:
        with open(path) as f:
            rows = json.load(f)

        ndjson_path = path.replace(".json", "_ndjson.jsonl")
        with open(ndjson_path, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

        with open(ndjson_path, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()
        os.remove(ndjson_path)

        already_loaded.add(chart_date)
        total_rows += len(rows)
        print(f"Loaded {chart_date}: {len(rows)} rows", flush=True)

    _save_manifest(already_loaded)
    return f"Loaded {len(to_load)} weeks, {total_rows} total rows, into {table_id}."


@tool(
    "load_staged_data_to_bigquery",
    "Load the latest staged chart data into BigQuery, after human confirmation in the terminal",
    {}
)
async def load_staged_data_to_bigquery(args):
    result_text = await _load_staged_data()
    return {"content": [{"type": "text", "text": result_text}]}


@tool(
    "load_all_staged_data_to_bigquery",
    "Load every not-yet-loaded staged week into BigQuery, after human confirmation",
    {}
)
async def load_all_staged_data_to_bigquery(args):
    result_text = await _load_all_staged()
    return {"content": [{"type": "text", "text": result_text}]}
