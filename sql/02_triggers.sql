-- sql/03_analytics_test.sql

-- Turn on execution timing in the psql terminal
\timing on

-- Turn off the pager so it doesn't pause with "-- More --"
\pset pager off

-- Automatically switch to vertical expanded display for wide tables
\x auto

-- 1. Greatest Upset Matches
-- Finds matches where the underdog won by 3 or more goals.
-- Calculates the true implied probability percentage (taking in account draws).
SELECT m.date,
       t1.team_long_name AS home_team, t2.team_long_name AS away_team, 
       m.home_team_goal, m.away_team_goal, 
       bo.home_win AS home_odds, bo.draw AS draw_odds, bo.away_win AS away_odds, bo.bookmaker,
       ROUND(CAST(
           (1.0 / CASE 
               WHEN m.home_team_goal > m.away_team_goal THEN bo.home_win
               WHEN m.away_team_goal > m.home_team_goal THEN bo.away_win
           END) 
           / 
           ((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) 
           * 100 
       AS NUMERIC), 2) AS upset_probability
FROM Match m, Team t1, Team t2, Betting_Odds bo
WHERE m.home_team_api_id = t1.team_api_id
  AND m.away_team_api_id = t2.team_api_id
  AND m.match_api_id = bo.match_api_id
  AND ((m.home_team_goal > m.away_team_goal AND bo.home_win > bo.away_win) 
   OR (m.away_team_goal > m.home_team_goal AND bo.away_win > bo.home_win))
  AND ABS(m.home_team_goal - m.away_team_goal) >= 3
ORDER BY upset_probability ASC
LIMIT 15;


-- 2. The "True" Hat-Trick Hunters
-- Finds players who have scored hat-tricks, sorted by the number of DIFFERENT teams they achieved this for.
WITH HatTricks AS (
    SELECT p.player_id, p.player_name, t.team_long_name AS team
    FROM Match_Event me, Player p, Match m, Appearance a, Team t
    WHERE me.player_id = p.player_id
      AND me.match_api_id = m.match_api_id
      AND p.player_id = a.player_id 
      AND m.match_api_id = a.match_api_id
      AND ((a.is_home_team = TRUE AND m.home_team_api_id = t.team_api_id) 
        OR (a.is_home_team = FALSE AND m.away_team_api_id = t.team_api_id))
      AND me.event_type = 'goal'
    GROUP BY p.player_id, p.player_name, t.team_long_name, m.match_api_id
    HAVING COUNT(me.event_id) >= 3
)
SELECT player_name,
       COUNT(DISTINCT team) AS different_teams_with_hattrick,
       COUNT(*) AS total_hattricks
FROM HatTricks
GROUP BY player_id, player_name
ORDER BY different_teams_with_hattrick DESC, total_hattricks DESC
LIMIT 15;


-- 3. "Gaps and Islands": Longest winning streaks
WITH MatchResults AS (
    SELECT home_team_api_id AS team_id, date,
           CASE WHEN home_team_goal > away_team_goal THEN 1 ELSE 0 END AS is_win 
    FROM Match
),
WinGroups AS (
    SELECT team_id, date, is_win,
           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY date) -
           ROW_NUMBER() OVER (PARTITION BY team_id, is_win ORDER BY date) AS streak_group
    FROM MatchResults
)
SELECT t.team_long_name, COUNT(*) AS consecutive_wins
FROM WinGroups wg, Team t
WHERE wg.team_id = t.team_api_id
  AND wg.is_win = 1
GROUP BY t.team_long_name, wg.team_id, wg.streak_group
ORDER BY consecutive_wins DESC
LIMIT 10;


-- 4. Spatial Impact: Central vs Wing Positioning
-- We keep the explicit LEFT OUTER JOIN here because it is required to count appearances with 0 goals, 
-- and it matches the syntax taught on Slide 35 of the course materials.
SELECT p.player_name,
       CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END AS pitch_zone,
       COUNT(DISTINCT a.match_api_id) AS matches_played,
       COUNT(me.event_id) AS goals,
       ROUND(COUNT(me.event_id)::NUMERIC / NULLIF(COUNT(DISTINCT a.match_api_id), 0), 3) AS goals_per_match_ratio
FROM Player p, Appearance a
LEFT OUTER JOIN Match_Event me 
  ON a.match_api_id = me.match_api_id AND me.event_type = 'goal' AND me.player_id = a.player_id
WHERE a.player_id = p.player_id
  AND a.X_coordinate IS NOT NULL
GROUP BY p.player_name, pitch_zone
ORDER BY goals DESC
LIMIT 15;


-- 5. Financial Arbitrage: Bookmaker Margin
SELECT m.date, 
       t1.team_long_name AS home_team, 
       t2.team_long_name AS away_team, 
       bo.bookmaker,
       ROUND(CAST(((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100 AS NUMERIC), 2) AS implied_probability_sum
FROM Betting_Odds bo, Match m, Team t1, Team t2
WHERE bo.match_api_id = m.match_api_id
  AND m.home_team_api_id = t1.team_api_id
  AND m.away_team_api_id = t2.team_api_id
  AND bo.home_win > 0 AND bo.draw > 0 AND bo.away_win > 0
ORDER BY implied_probability_sum ASC
LIMIT 15;


-- 6. The Nemesis Matrix
WITH HeadToHead AS (
    SELECT home_team_api_id AS team_a, away_team_api_id AS team_b,
           COUNT(*) AS games_played,
           SUM(CASE WHEN home_team_goal > away_team_goal THEN 1 ELSE 0 END) AS team_a_wins
    FROM Match
    GROUP BY home_team_api_id, away_team_api_id
)
SELECT t1.team_long_name AS team, 
       t2.team_long_name AS nemesis_team, 
       h2h.games_played,
       ROUND((h2h.team_a_wins::NUMERIC / h2h.games_played) * 100, 2) AS h2h_win_rate_percentage
FROM HeadToHead h2h, Team t1, Team t2
WHERE h2h.team_a = t1.team_api_id
  AND h2h.team_b = t2.team_api_id
  AND h2h.games_played >= 10 
  AND (h2h.team_a_wins::NUMERIC / h2h.games_played) < 0.15
ORDER BY h2h_win_rate_percentage ASC, h2h.games_played DESC
LIMIT 15;


-- 7. Player Dependency
SELECT p.player_name, t.team_long_name,
       COUNT(m.match_api_id) AS matches_with_player
FROM Match m, Team t, Appearance a, Player p
WHERE m.home_team_api_id = t.team_api_id
  AND m.match_api_id = a.match_api_id
  AND a.player_id = p.player_id
GROUP BY p.player_name, t.team_long_name
ORDER BY matches_with_player DESC
LIMIT 10;