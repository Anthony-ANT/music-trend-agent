# Music trend agent pipeline

## Purpose
Agent-driven pipeline that discovers, extracts, cleans, loads, and reports on
music chart and metadata trends. Built to demonstrate a reusable agentic ETL
framework — this project's specific question is genre/artist chart-climb speed,
but the pipeline itself should generalize to other datasets later.

## Data sources (v1)
- Billboard Hot 100 (weekly chart position) — recurring, changes weekly
- MusicBrainz (genre, artist metadata) — static reference data, joined in

## v1 analytical question
Which genres or artist types climb the Billboard Hot 100 fastest?

## Warehouse
Google BigQuery. Dataset: `music_trends`. Managed via dbt (see /dbt).

## Conventions
- Raw extracts land in data/raw/, staged/cleaned data in data/staged/
- No agent writes to BigQuery without a human-approved plan first
- Every run appends a summary to /logs/YYYY-MM-DD.md

## Status
- [x] Folder + environment set up
- [x] Anthropic API key configured
- [x] BigQuery project created
- [x] dbt connected
- [ ] Discovery agent built
- [ ] Extraction agent built
- [ ] Cleaning agent built
- [ ] Reporting agent built

## Project locations
- dbt project: dbt/music_trends/music_trends/