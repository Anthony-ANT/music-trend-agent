sql = """
WITH debuts AS (
  SELECT title, artist, primary_artist_used, chart_date AS debut_date, rank AS debut_rank
  FROM `music-trend-agent-508220.music_trends.chart_history`
  WHERE weeks_on_chart = 1
    AND NOT is_release_week_bulk_entry
    AND chart_date <= '2026-07-25'
    AND primary_artist_used IS NOT NULL
),
best_rank AS (
  SELECT d.title, d.artist, d.primary_artist_used, d.debut_date, d.debut_rank,
         MIN(h.rank) AS best_rank_8wk
  FROM debuts d
  JOIN `music-trend-agent-508220.music_trends.chart_history` h
    ON d.title = h.title AND d.artist = h.artist
    AND h.chart_date BETWEEN d.debut_date AND DATE_ADD(d.debut_date, INTERVAL 8 WEEK)
  GROUP BY d.title, d.artist, d.primary_artist_used, d.debut_date, d.debut_rank
),
climbs AS (
  SELECT primary_artist_used,
         title,
         debut_date,
         (debut_rank - best_rank_8wk) AS climb,
         DATE_TRUNC(debut_date, MONTH) AS debut_month
  FROM best_rank
  WHERE (debut_rank - best_rank_8wk) > 0
)
SELECT primary_artist_used,
       COUNT(*) AS climbing_songs,
       COUNT(DISTINCT debut_month) AS distinct_months_active,
       ROUND(AVG(climb), 1) AS avg_climb,
       MAX(climb) AS best_single_climb,
       CASE
         WHEN COUNT(*) = 1 THEN 'One-time'
         WHEN COUNT(DISTINCT debut_month) >= 3 THEN 'Recurring across the year'
         ELSE 'Multiple songs, clustered timing'
       END AS pattern_type
FROM climbs
GROUP BY primary_artist_used
HAVING climbing_songs >= 2
ORDER BY climbing_songs DESC, avg_climb DESC
"""

with open("artist_recurrence.sql", "w") as f:
    f.write(sql)

print("written")