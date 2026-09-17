
WITH debuts AS (
  SELECT title, artist, chart_date AS debut_date, rank AS debut_rank, genre_tags
  FROM `music-trend-agent-508220.music_trends.chart_history`
  WHERE weeks_on_chart = 1
    AND NOT is_release_week_bulk_entry
    AND ARRAY_LENGTH(genre_tags) > 0
    AND chart_date <= '2026-07-25'
),
weekly_positions AS (
  SELECT d.title, d.artist, d.debut_date, d.debut_rank, d.genre_tags,
         h.rank,
         DATE_DIFF(h.chart_date, d.debut_date, WEEK) AS week_number
  FROM debuts d
  JOIN `music-trend-agent-508220.music_trends.chart_history` h
    ON d.title = h.title AND d.artist = h.artist
    AND h.chart_date BETWEEN d.debut_date AND DATE_ADD(d.debut_date, INTERVAL 8 WEEK)
),
song_shape AS (
  SELECT title, artist, debut_rank, genre_tags,
         MIN(rank) AS best_rank_8wk,
         MIN(CASE WHEN week_number <= 2 THEN rank END) AS best_rank_by_wk2,
         MIN(CASE WHEN week_number >= 5 THEN rank END) AS best_rank_wk5_to_8,
         MAX(week_number) AS weeks_observed
  FROM weekly_positions
  GROUP BY title, artist, debut_rank, genre_tags
),
shaped AS (
  SELECT title, artist, debut_rank, genre_tags,
         (debut_rank - best_rank_8wk) AS total_climb,
         (debut_rank - best_rank_by_wk2) AS early_climb,
         weeks_observed
  FROM song_shape
  WHERE best_rank_by_wk2 IS NOT NULL
    AND best_rank_wk5_to_8 IS NOT NULL
    AND (debut_rank - best_rank_8wk) > 0
    AND weeks_observed >= 5
),
tagged AS (
  SELECT title, artist, total_climb, early_climb, tag
  FROM shaped, UNNEST(genre_tags) AS tag
),
mapped AS (
  SELECT title, artist, total_climb, early_climb,
    CASE
      WHEN tag IN ('folk', 'folk pop', 'folk rock', 'singer-songwriter', 'singer/songwriter', 'americana', 'bluegrass')
        THEN 'Folk/Singer-songwriter'
      WHEN tag IN ('country', 'country pop', 'contemporary country', 'nashville sound')
        THEN 'Country/Americana'
      WHEN tag IN ('rock', 'alternative rock', 'alternative', 'alternative/indie rock', 'indie rock',
                   'indie pop', 'psychedelic rock', 'psychedelic pop', 'blues rock', 'soft rock',
                   'roots rock', 'power pop', 'pop punk')
        THEN 'Rock/Alternative'
      WHEN tag IN ('r&b', 'contemporary r&b', 'alternative r&b', 'soul', 'hip hop soul', 'funk', 'disco')
        THEN 'R&B/Soul'
      WHEN tag IN ('pop', 'pop rock', 'dance-pop', 'synth-pop', 'electropop', 'pop soul', 'pop rap')
        THEN 'Pop (core)'
      WHEN tag IN ('electronic', 'dance', 'trap soul')
        THEN 'Dance/Electronic'
      WHEN tag IN ('hip hop', 'hip-hop', 'trap', 'trap rap', 'rap', 'southern hip hop', 'hardcore hip hop')
        THEN 'HipHop/Rap'
      ELSE NULL
    END AS genre_family
  FROM tagged
)
SELECT genre_family,
       COUNT(*) AS n_songs,
       ROUND(AVG(total_climb), 1) AS avg_total_climb,
       ROUND(AVG(early_climb), 1) AS avg_early_climb_wk1_2,
       ROUND(AVG(early_climb) / NULLIF(AVG(total_climb), 0) * 100, 1) AS pct_climb_happens_early,
       CASE
         WHEN AVG(early_climb) / NULLIF(AVG(total_climb), 0) >= 0.7 THEN 'Flash - climbs fast, early peak'
         WHEN AVG(early_climb) / NULLIF(AVG(total_climb), 0) <= 0.4 THEN 'Slow-build - climbs steadily over time'
         ELSE 'Mixed pattern'
       END AS shape_type
FROM mapped
WHERE genre_family IS NOT NULL
GROUP BY genre_family
HAVING n_songs >= 5
ORDER BY pct_climb_happens_early DESC
