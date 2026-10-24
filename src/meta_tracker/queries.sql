-- Ten questions about the meta, answered in SQL.
-- Parameters: :format, :month, :pokemon, :limit
-- Each query starts with "-- name: <id>" and a "-- question:" line.

-- name: top_usage
-- question: What were the most used Pokémon this month?
SELECT u.rank, p.name, ROUND(u.usage_pct, 2) AS usage_pct
FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
WHERE u.format = :format AND u.month = :month
ORDER BY u.rank
LIMIT :limit;

-- name: pokemon_trend
-- question: How has one Pokémon's usage changed month by month?
SELECT u.month, u.rank, ROUND(u.usage_pct, 2) AS usage_pct
FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
WHERE u.format = :format AND p.name = :pokemon
ORDER BY u.month;

-- name: biggest_risers
-- question: Which Pokémon gained the most usage since the previous month?
WITH months AS (
    SELECT month, LAG(month) OVER (ORDER BY month) AS prev
    FROM format_months WHERE format = :format
)
SELECT p.name,
       ROUND(COALESCE(prev.usage_pct, 0), 2) AS before_pct,
       ROUND(cur.usage_pct, 2) AS after_pct,
       ROUND(cur.usage_pct - COALESCE(prev.usage_pct, 0), 2) AS change
FROM usage cur
JOIN months m ON m.month = cur.month
JOIN pokemon p ON p.id = cur.pokemon_id
LEFT JOIN usage prev
       ON prev.format = cur.format AND prev.month = m.prev AND prev.pokemon_id = cur.pokemon_id
WHERE cur.format = :format AND cur.month = :month
ORDER BY change DESC
LIMIT :limit;

-- name: biggest_fallers
-- question: Which Pokémon lost the most usage since the previous month?
WITH months AS (
    SELECT month, LAG(month) OVER (ORDER BY month) AS prev
    FROM format_months WHERE format = :format
)
SELECT p.name,
       ROUND(prev.usage_pct, 2) AS before_pct,
       ROUND(COALESCE(cur.usage_pct, 0), 2) AS after_pct,
       ROUND(COALESCE(cur.usage_pct, 0) - prev.usage_pct, 2) AS change
FROM months m
JOIN usage prev ON prev.format = :format AND prev.month = m.prev
JOIN pokemon p ON p.id = prev.pokemon_id
LEFT JOIN usage cur
       ON cur.format = prev.format AND cur.month = m.month AND cur.pokemon_id = prev.pokemon_id
WHERE m.month = :month
ORDER BY change ASC
LIMIT :limit;

-- name: new_to_top_30
-- question: Who broke into the top 30 this month?
WITH months AS (
    SELECT month, LAG(month) OVER (ORDER BY month) AS prev
    FROM format_months WHERE format = :format
)
SELECT p.name, cur.rank, prev.rank AS prev_rank
FROM usage cur
JOIN months m ON m.month = cur.month
JOIN pokemon p ON p.id = cur.pokemon_id
LEFT JOIN usage prev
       ON prev.format = cur.format AND prev.month = m.prev AND prev.pokemon_id = cur.pokemon_id
WHERE cur.format = :format AND cur.month = :month AND cur.rank <= 30
  AND (prev.rank IS NULL OR prev.rank > 30)
ORDER BY cur.rank;

-- name: most_consistent
-- question: Which Pokémon stayed in the top 20 for the most months?
SELECT p.name,
       COUNT(*) AS months_in_top_20,
       ROUND(AVG(u.usage_pct), 2) AS avg_usage_pct,
       MIN(u.rank) AS best_rank
FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
WHERE u.format = :format AND u.rank <= 20
GROUP BY p.name
ORDER BY months_in_top_20 DESC, avg_usage_pct DESC
LIMIT :limit;

-- name: most_volatile
-- question: Whose usage swings the most (standard deviation across months)?
SELECT p.name,
       COUNT(*) AS months,
       ROUND(AVG(u.usage_pct), 2) AS avg_usage_pct,
       ROUND(SQRT(MAX(AVG(u.usage_pct * u.usage_pct) - AVG(u.usage_pct) * AVG(u.usage_pct), 0)), 2)
           AS std_dev
FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
WHERE u.format = :format
GROUP BY p.name
HAVING MAX(u.usage_pct) >= 5
ORDER BY std_dev DESC
LIMIT :limit;

-- name: top_teammates
-- question: Who does this Pokémon get paired with most often?
SELECT t2.name AS teammate, ROUND(t.pct, 1) AS pct_of_teams
FROM teammates t
JOIN pokemon t1 ON t1.id = t.pokemon_id
JOIN pokemon t2 ON t2.id = t.teammate_id
WHERE t.format = :format AND t.month = :month AND t1.name = :pokemon
ORDER BY t.pct DESC
LIMIT :limit;

-- name: top_items_and_moves
-- question: What items and moves does this Pokémon run?
SELECT 'item' AS kind, i.item AS name, ROUND(i.pct, 1) AS pct
FROM items i JOIN pokemon p ON p.id = i.pokemon_id
WHERE i.format = :format AND i.month = :month AND p.name = :pokemon
UNION ALL
SELECT 'move', mv.move, ROUND(mv.pct, 1)
FROM moves mv JOIN pokemon p ON p.id = mv.pokemon_id
WHERE mv.format = :format AND mv.month = :month AND p.name = :pokemon
ORDER BY kind, pct DESC;

-- name: activity
-- question: How many battles were played each month, and how concentrated was the meta?
SELECT fm.month,
       fm.total_battles,
       ROUND(SUM(CASE WHEN u.rank <= 10 THEN u.usage_pct ELSE 0 END) / 6, 1)
           AS top10_share_of_team_slots
FROM format_months fm
JOIN usage u ON u.format = fm.format AND u.month = fm.month
WHERE fm.format = :format
GROUP BY fm.month
ORDER BY fm.month;

-- name: peak_months
-- question: When was each top Pokémon at its peak?
WITH ranked AS (
    SELECT u.pokemon_id, u.month, u.usage_pct,
           ROW_NUMBER() OVER (PARTITION BY u.pokemon_id ORDER BY u.usage_pct DESC) AS rn
    FROM usage u WHERE u.format = :format
)
SELECT p.name, r.month AS peak_month, ROUND(r.usage_pct, 2) AS peak_usage_pct
FROM ranked r JOIN pokemon p ON p.id = r.pokemon_id
WHERE r.rn = 1
ORDER BY r.usage_pct DESC
LIMIT :limit;
