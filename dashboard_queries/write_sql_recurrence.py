sql = """
WITH debuts AS (
  SELECT title, artist, primary_artist_used, chart_date AS debut_date, rank AS debut_rank, genre_tags
  FROM `music-trend-agent-508220.music_trends.chart_history`
  WHERE weeks_on_chart = 1
    AND NOT is_release_week_bulk_entry
    AND ARRAY_LENGTH(genre_tags) > 0
    AND chart_date <= '2026-07-25'
),
best_rank AS (
  SELECT d.title, d.artist, d.primary_artist_used, d.debut_date, d.debut_rank, d.genre_tags,
         MIN(h.rank) AS best_rank_8wk
  FROM debuts d
  JOIN `music-trend-agent-508220.music_trends.chart_history` h
    ON d.title = h.title AND d.artist = h.artist
    AND h.chart_date BETWEEN d.debut_date AND DATE_ADD(d.debut_date, INTERVAL 8 WEEK)
  GROUP BY d.title, d.artist, d.primary_artist_used, d.debut_date, d.debut_rank, d.genre_tags
),
climbs AS (
  SELECT title, artist, primary_artist_used, debut_date, debut_rank, best_rank_8wk,
         (debut_rank - best_rank_8wk) AS climb,
         DATE_TRUNC(debut_date, MONTH) AS debut_month,
         genre
  FROM best_rank, UNNEST(genre_tags) AS genre
  WHERE (debut_rank - best_rank_8wk) > 0  -- only songs that actually climbed
),
mapped AS (
  SELECT *,
    CASE
      WHEN genre IN ('folk', 'folk pop', 'folk rock', 'singer-songwriter', 'singer/songwriter', 'americana', 'bluegrass')
        THEN 'Folk/Singer-songwriter'
      WHEN genre IN ('country', 'country pop', 'contemporary country', 'nashville sound')
        THEN 'Country/Americana'
      WHEN genre IN ('rock', 'alternative rock', 'alternative', 'alternative/indie rock', 'indie rock',
                      'indie pop', 'psychedelic rock', 'psychedelic pop', 'blues rock', 'soft rock',
                      'roots rock', 'power pop', 'pop punk')
        THEN 'Rock/Alternative'
      WHEN genre IN ('r&b', 'contemporary r&b', 'alternative r&b', 'soul', 'hip hop soul', 'funk', 'disco')
        THEN 'R&B/Soul'
      WHEN genre IN ('pop', 'pop rock', 'dance-pop', 'synth-pop', 'electropop', 'pop soul', 'pop rap')
        THEN 'Pop (core)'
      WHEN genre IN ('electronic', 'dance', 'trap soul')
        THEN 'Dance/Electronic'
      WHEN genre IN ('hip hop', 'hip-hop', 'trap', 'trap rap', 'rap', 'southern hip hop', 'hardcore hip hop')
        THEN 'HipHop/Rap'
      ELSE NULL
    END AS genre_family
  FROM climbs
),
genre_stats AS (
  SELECT genre_family,
         COUNT(*) AS climbing_songs,
         COUNT(DISTINCT primary_artist_used) AS distinct_climbing_artists,
         COUNT(DISTINCT debut_month) AS distinct_months_active,
         MAX(climb) AS biggest_single_climb
  FROM mapped
  WHERE genre_family IS NOT NULL
  GROUP BY genre_family
),
top_artist_share AS (
  SELECT genre_family, primary_artist_used, COUNT(*) AS artist_climb_count,
         ROW_NUMBER() OVER (PARTITION BY genre_family ORDER BY COUNT(*) DESC) AS rn
  FROM mapped
  WHERE genre_family IS NOT NULL
  GROUP BY genre_family, primary_artist_used
)
SELECT g.genre_family,
       g.climbing_songs,
       g.distinct_climbing_artists,
       g.distinct_months_active,
       ROUND(t.artist_climb_count / g.climbing_songs * 100, 1) AS pct_from_top_artist,
       CASE
         WHEN g.distinct_climbing_artists >= 5 AND (t.artist_climb_count / g.climbing_songs) < 0.35
           THEN 'Broad-based / recurring'
         WHEN (t.artist_climb_count / g.climbing_songs) >= 0.5
           THEN 'Concentrated / one breakout act'
         ELSE 'Mixed'
       END AS pattern_type
FROM genre_stats g
JOIN top_artist_share t ON g.genre_family = t.genre_family AND t.rn = 1
ORDER BY g.climbing_songs DESC
"""

with open("recurrence_summary.sql", "w") as f:
    f.write(sql)

print("written")