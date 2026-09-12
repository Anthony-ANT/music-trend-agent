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
- [x] Discovery agent built
- [x] Extraction agent built (Billboard + MusicBrainz, retry logic + confidence threshold added)
- [x] Cleaning agent built (join, sentinel fix, release-week bulk flag)
- [x] BigQuery load built and verified (100/100 rows, correct schema, human-approval gate)
- [x] Genre allowlist filter added and verified (304 non-genre tags excluded)
- [x] BigQuery table corrected — old ungoverned genre data replaced with filtered version
- [x] Full backfill loaded: 37 weeks (2026-01-03 to 2026-09-12), 3700 rows
- [x] Genre allowlist + manual override system built and applied (14 confirmed corrections)
- [x] Reporting agent produced a validated multi-week finding

## v1 answer (as of this run)
Country/Americana and Folk/Singer-songwriter climb the Hot 100 fastest in 2026
(n=169 usable songs, ~2x gap vs. Hip-Hop/Rap, survives outlier removal and a
second independent method). Alternative Rock is the single most robust result,
winning on both methods checked.

## Known limitation
MusicBrainz name-collision errors affect an estimated 10-15% of matched artists.
14 confirmed corrections applied via MANUAL_GENRE_OVERRIDES (Junior H, Julia Wolf,
George Birge, J. Cole, Olivia Dean, John, John Morgan, Josiah Queen, Leon Thomas,
Ella Langley, Steve Lacy, Jordan Davis, Dylan Scott, Rod Wave). Pattern observed:
every time the data is queried for a new purpose, 1-2 more surface. Likely still
an undercount in the untested remainder of ~230 unique artists.## Project locations
- dbt project: dbt/music_trends/music_trends/

## Known limitations
- MusicBrainz artist matching is name-based only; same-name collisions
  (e.g. "Julia Wolf" matched to an unrelated German audio-drama artist)
  can pass the confidence threshold. Not currently detected or corrected.