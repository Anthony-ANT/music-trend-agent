sql = """
WITH debuts AS (
  SELECT title, artist, chart_date AS debut_date, rank AS debut_rank, genre_tags
  FROM `music-trend-agent-508220.music_trends.chart_history`
  WHERE weeks_on_chart = 1
    AND NOT is_release_week_bulk_entry
    AND ARRAY_LENGTH(genre_tags) > 0
    AND chart_date <= '2026-07-25'
),
best_rank AS (
  SELECT d.title, d.artist, d.debut_rank, d.genre_tags,
         MIN(h.rank) AS best_rank_8wk
  FROM debuts d
  JOIN `music-trend-agent-508220.music_trends.chart_history` h
    ON d.title = h.title AND d.artist = h.artist
    AND h.chart_date BETWEEN d.debut_date AND DATE_ADD(d.debut_date, INTERVAL 8 WEEK)
  GROUP BY d.title, d.artist, d.debut_rank, d.genre_tags
),
climbs AS (
  SELECT title, artist, debut_rank, best_rank_8wk,
         (debut_rank - best_rank_8wk) AS climb,
         genre
  FROM best_rank, UNNEST(genre_tags) AS genre
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
      WHEN genre IN ('hip hop', 'hip-hop', 'trap', 'trap rap', 'rap', 'southern hip hop',
                      'hardcore hip hop')
        THEN 'HipHop/Rap'
      ELSE NULL
    END AS genre_family
  FROM climbs
)
SELECT genre_family,
       COUNT(*) AS n_songs,
       COUNT(DISTINCT artist) AS n_artists,
       ROUND(AVG(climb), 2) AS mean_climb,
       COUNTIF(climb > 0) AS songs_climbed,
       ROUND(COUNTIF(climb > 0) / COUNT(*) * 100, 1) AS pct_climbed
FROM mapped
WHERE genre_family IS NOT NULL
GROUP BY genre_family
ORDER BY pct_climbed DESC
"""

with open("genre_family_climb.sql", "w") as f:
    f.write(sql)

print("written")