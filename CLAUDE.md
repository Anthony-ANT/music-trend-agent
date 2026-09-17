# Music trend agent pipeline

## Purpose
Agent-driven pipeline that discovers, extracts, cleans, loads, and reports on
music chart and metadata trends. Built to demonstrate a reusable agentic ETL
framework — this project's specific question is genre/artist chart-climb speed,
but the pipeline itself should generalize to other datasets later.

## Data sources
- Billboard Hot 100 (weekly chart position) — recurring, changes weekly
- MusicBrainz (genre, artist metadata) — joined in via primary-artist extraction

## v1 analytical question
Which genres or artist types climb the Billboard Hot 100 fastest?

## v1 answer (validated across 37 weeks, 3 independent methods)
Country/Americana and Folk/Singer-songwriter climb the Hot 100 fastest in 2026
(n=169 usable songs, ~2x gap vs. Hip-Hop/Rap, survives outlier removal and a
second independent method). Alternative Rock is the single most robust result,
winning on both methods checked. Supporting findings: genre-level success is
broad-based, not driven by one artist; only 7 artists climbed more than once
all year (Riley Green is the sole sustained repeat performer); Hip-Hop
front-loads ~66% of its climb in the first 2 weeks, while Rock/Country/R&B
build steadily over 8 weeks.

Cohort: debut-only, non-bulk-entry, full 8-week window, min. genre-tag
threshold. 169 of 654 total songs (26%) used — describes newly-debuting,
non-flooded singles, not the chart as a whole.

## Warehouse
Google BigQuery. Dataset: `music_trends`. Managed via dbt (see /dbt).

Tables:
- chart_history — full 37-week raw/staged join, 3,700 rows
- genre_climb_summary — granular tag-level climb stats
- genre_family_climb_summary — headline family-grouped climb stats
- genre_trajectory_shape — flash vs. slow-build pattern by genre family
- genre_recurrence_summary — genre-level artist concentration
- artist_recurrence_summary — which artists climbed more than once

## Project locations
- dbt project: dbt/music_trends/music_trends/
- dashboard_queries/: one-off SQL scripts (+ their Python writers) that built
  the five BigQuery summary views used by the Power BI dashboard
- screenshots/: Power BI dashboard page exports, embedded in README.md
  (dashboard is not published/hosted — screenshots are the only public view)

## Conventions
- Raw extracts land in data/raw/, staged/cleaned data in data/staged/
- No agent writes to BigQuery without a human-approved plan first — enforced
  via a real terminal confirmation prompt in tools/bigquery_loader.py, not
  just a written rule
- Every run appends a summary to /logs/YYYY-MM-DD.md
- Deterministic pipeline stages (extraction, cleaning, loading) run as plain
  Python functions, not through the Claude Agent SDK — zero API cost. Only
  the reporting stage calls the agent, since it's the only stage requiring
  genuine judgment.
- Tool functions are split into a plain async function (e.g. `_load_all_staged`)
  plus a thin `@tool`-decorated wrapper — the plain function is directly
  callable for testing/backfills without going through the agent.

## Known limitation
MusicBrainz artist matching is name-based only; same-name collisions (wrong
real-world person matched) can pass the confidence-score check. This is a
material, recurring issue — not a rare edge case (~10-15% estimated affected
across ~230 unique artists).

14 confirmed corrections applied via MANUAL_GENRE_OVERRIDES in
tools/cleaning_stager.py: Junior H, Julia Wolf, George Birge, J. Cole,
Olivia Dean, John, John Morgan, Josiah Queen, Leon Thomas, Ella Langley,
Steve Lacy, Jordan Davis, Dylan Scott, Rod Wave.

Pattern observed: every new query against the data for a new purpose has
surfaced 1-2 more corrections. Likely still an undercount in the untested
remainder of the artist pool — not resolved by a single exhaustive sweep.

## Status
- [x] Folder + environment set up
- [x] Anthropic API key configured
- [x] BigQuery project created
- [x] dbt connected
- [x] Discovery agent built
- [x] Extraction agent built (Billboard + MusicBrainz, retry logic + confidence threshold)
- [x] Cleaning agent built (join, sentinel fix, release-week bulk flag, genre allowlist + manual overrides)
- [x] BigQuery load built and verified (human-approval gate via terminal confirmation)
- [x] Full backfill loaded: 37 weeks (2026-01-03 to 2026-09-12), 3,700 rows
- [x] Reporting agent produced a validated multi-week finding
- [x] Five BigQuery summary views built for dashboard (dashboard_queries/)
- [x] Power BI dashboard built (2 pages: Genre Climb Speed, Deeper Patterns)
- [x] README written with embedded dashboard screenshots and full methodology
- [ ] Pushed final README + screenshots + dashboard_queries/ to GitHub
- [ ] One more systematic collision sweep (currently ad hoc, not exhaustive)
- [ ] Recurring weekly execution (currently manual, one-time backfill)