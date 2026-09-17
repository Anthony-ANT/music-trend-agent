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
)
SELECT genre,
       COUNT(*) AS n_songs,
       ROUND(AVG(climb), 2) AS mean_climb,
       COUNTIF(climb > 0) AS songs_climbed,
       ROUND(COUNTIF(climb > 0) / COUNT(*) * 100, 1) AS pct_climbed
FROM climbs
GROUP BY genre
HAVING n_songs >= 8
ORDER BY pct_climbed DESC
"""

with open("genre_climb.sql", "w") as f:
    f.write(sql)

print("written")