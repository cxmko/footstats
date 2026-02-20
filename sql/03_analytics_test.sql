-- sql/03_analytics_test.sql

-- Turn on execution timing in the psql terminal
\timing on

-- 1. Rolling Volatility of Team Performance
WITH TeamMatches AS (
    SELECT home_team_api_id AS team_id, date, (home_team_goal - away_team_goal) AS goal_diff FROM Match
    UNION ALL
    SELECT away_team_api_id AS team_id, date, (away_team_goal - home_team_goal) AS goal_diff FROM Match
)
SELECT t.team_long_name, tm.date, tm.goal_diff,
       ROUND(AVG(tm.goal_diff) OVER w, 2) AS moving_avg_diff,
       ROUND(STDDEV_POP(tm.goal_diff) OVER w, 2) AS performance_volatility
FROM TeamMatches tm
JOIN Team t ON tm.team_id = t.team_api_id
WINDOW w AS (PARTITION BY tm.team_id ORDER BY tm.date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)
LIMIT 20;

-- 2. "Gaps and Islands": Longest winning streaks
WITH MatchResults AS (
    SELECT home_team_api_id AS team_id, date,
           CASE WHEN home_team_goal > away_team_goal THEN 1 ELSE 0 END AS is_win FROM Match
),
WinGroups AS (
    SELECT team_id, date, is_win,
           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY date) -
           ROW_NUMBER() OVER (PARTITION BY team_id, is_win ORDER BY date) AS streak_group
    FROM MatchResults
)
SELECT t.team_long_name, COUNT(*) AS consecutive_wins
FROM WinGroups wg
JOIN Team t ON wg.team_id = t.team_api_id
WHERE wg.is_win = 1
GROUP BY t.team_long_name, wg.team_id, wg.streak_group
ORDER BY consecutive_wins DESC
LIMIT 10;

-- 3. Spatial Impact: Central vs Wing Positioning
SELECT p.player_name,
       CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END AS pitch_zone,
       COUNT(DISTINCT a.match_api_id) AS matches_played
FROM Appearance a
JOIN Player p ON a.player_api_id = p.player_api_id
LEFT JOIN Match_Event me ON a.match_api_id = me.match_api_id AND me.event_type = 'goal'
WHERE a.X_coordinate IS NOT NULL
GROUP BY p.player_name, pitch_zone
LIMIT 15;

-- 4. Financial Arbitrage: Bookmaker Margin
SELECT m.date, t1.team_long_name AS home_team, bo.bookmaker,
       ROUND(((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100, 2) AS implied_probability_sum
FROM Betting_Odds bo
JOIN Match m ON bo.match_api_id = m.match_api_id
JOIN Team t1 ON m.home_team_api_id = t1.team_api_id
WHERE bo.home_win > 0 AND bo.draw > 0 AND bo.away_win > 0
LIMIT 15;

-- 5. The Nemesis Matrix
WITH HeadToHead AS (
    SELECT home_team_api_id AS team_a, away_team_api_id AS team_b,
           COUNT(*) AS games_played,
           SUM(CASE WHEN home_team_goal > away_team_goal THEN 1 ELSE 0 END) AS team_a_wins
    FROM Match
    GROUP BY home_team_api_id, away_team_api_id
)
SELECT t1.team_long_name AS team, t2.team_long_name AS nemesis_team, h2h.games_played
FROM HeadToHead h2h
JOIN Team t1 ON h2h.team_a = t1.team_api_id
JOIN Team t2 ON h2h.team_b = t2.team_api_id
WHERE h2h.games_played >= 10 AND (h2h.team_a_wins::NUMERIC / h2h.games_played) < 0.15
LIMIT 15;

-- 6. The "Clutch" Factor: Late game events
SELECT t.team_long_name, COUNT(me.event_id) AS late_goals_scored
FROM Match_Event me
JOIN Match m ON me.match_api_id = m.match_api_id
JOIN Team t ON m.home_team_api_id = t.team_api_id
WHERE me.event_type = 'goal' AND me.minute >= 75 AND ABS(m.home_team_goal - m.away_team_goal) <= 1
GROUP BY t.team_long_name
LIMIT 10;

-- 7. Player Dependency
SELECT p.player_name, t.team_long_name,
       COUNT(CASE WHEN a.player_api_id IS NOT NULL THEN 1 END) AS matches_with_player
FROM Match m
JOIN Team t ON m.home_team_api_id = t.team_api_id
LEFT JOIN Appearance a ON m.match_api_id = a.match_api_id
JOIN Player p ON a.player_api_id = p.player_api_id
GROUP BY p.player_name, t.team_long_name
HAVING COUNT(CASE WHEN a.player_api_id IS NOT NULL THEN 1 END) BETWEEN 20 AND 100
LIMIT 10;