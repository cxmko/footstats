-- sql/03_analytics_test.sql

-- Turn on execution timing in the psql terminal
\timing on
\pset pager off
\x auto

-- 1. Greatest Upset Matches (Unchanged, highly selective implicit join)
SELECT m.date,
       t1.team_long_name AS home_team, t2.team_long_name AS away_team, 
       m.home_team_goal, m.away_team_goal, 
       bo.home_win AS home_odds, bo.draw AS draw_odds, bo.away_win AS away_odds, bo.bookmaker,
       ROUND(CAST(
           (1.0 / CASE 
               WHEN m.home_team_goal > m.away_team_goal THEN bo.home_win
               WHEN m.away_team_goal > m.home_team_goal THEN bo.away_win
           END) 
           / ((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100 
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


-- 2. The "True" Hat-Trick Hunters (Strict Implicit Joins)
WITH HatTrickIDs AS (
    SELECT me.player_id, 
           CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END AS team_id
    FROM Match_Event me, Match m, Appearance a
    WHERE me.match_api_id = m.match_api_id
      AND me.player_id = a.player_id 
      AND m.match_api_id = a.match_api_id
      AND me.event_type = 'goal'
    GROUP BY me.player_id, 
             CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END, 
             m.match_api_id
    HAVING COUNT(me.event_id) >= 3
),
PlayerAggregates AS (
    SELECT player_id,
           COUNT(DISTINCT team_id) AS different_teams_with_hattrick,
           COUNT(*) AS total_hattricks
    FROM HatTrickIDs
    GROUP BY player_id
)
SELECT p.player_name, pa.different_teams_with_hattrick, pa.total_hattricks
FROM PlayerAggregates pa, Player p
WHERE pa.player_id = p.player_id
ORDER BY pa.different_teams_with_hattrick DESC, pa.total_hattricks DESC
LIMIT 15;


-- 3. "Gaps and Islands": Longest winning streaks (Strict Implicit Joins)
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
),
TeamStreaks AS (
    SELECT team_id, COUNT(*) AS consecutive_wins
    FROM WinGroups
    WHERE is_win = 1
    GROUP BY team_id, streak_group
)
SELECT t.team_long_name, ts.consecutive_wins
FROM TeamStreaks ts, Team t
WHERE ts.team_id = t.team_api_id
ORDER BY ts.consecutive_wins DESC
LIMIT 10;


-- 4. Spatial Impact: Central vs Wing Positioning
WITH PlayerSpatialStats AS (
    SELECT a.player_id,
           CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END AS pitch_zone,
           COUNT(DISTINCT a.match_api_id) AS matches_played,
           COUNT(me.event_id) AS goals
    FROM Appearance a
    LEFT OUTER JOIN Match_Event me 
      ON a.match_api_id = me.match_api_id AND me.event_type = 'goal' AND me.player_id = a.player_id
    WHERE a.X_coordinate IS NOT NULL
    GROUP BY a.player_id, CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END
)
SELECT p.player_name, ps.pitch_zone, ps.matches_played, ps.goals,
       ROUND(ps.goals::NUMERIC / NULLIF(ps.matches_played, 0), 3) AS goals_per_match_ratio
FROM PlayerSpatialStats ps, Player p
WHERE ps.player_id = p.player_id
ORDER BY ps.goals DESC
LIMIT 15;


-- 5. Financial Arbitrage: Bookmaker Margin
SELECT m.date, t1.team_long_name AS home_team, t2.team_long_name AS away_team, bo.bookmaker,
       ROUND(CAST(((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100 AS NUMERIC), 2) AS implied_probability_sum
FROM Betting_Odds bo, Match m, Team t1, Team t2
WHERE bo.match_api_id = m.match_api_id AND m.home_team_api_id = t1.team_api_id AND m.away_team_api_id = t2.team_api_id
  AND bo.home_win > 0 AND bo.draw > 0 AND bo.away_win > 0
ORDER BY implied_probability_sum ASC
LIMIT 15;


-- 6. The Nemesis Matrix
WITH HeadToHead AS (
    SELECT home_team_api_id AS team_a, away_team_api_id AS team_b, COUNT(*) AS games_played,
           SUM(CASE WHEN home_team_goal > away_team_goal THEN 1 ELSE 0 END) AS team_a_wins
    FROM Match
    GROUP BY home_team_api_id, away_team_api_id
)
SELECT t1.team_long_name AS team, t2.team_long_name AS nemesis_team, h2h.games_played,
       ROUND((h2h.team_a_wins::NUMERIC / h2h.games_played) * 100, 2) AS h2h_win_rate_percentage
FROM HeadToHead h2h, Team t1, Team t2
WHERE h2h.team_a = t1.team_api_id AND h2h.team_b = t2.team_api_id
  AND h2h.games_played >= 10 AND (h2h.team_a_wins::NUMERIC / h2h.games_played) < 0.15
ORDER BY h2h_win_rate_percentage ASC, h2h.games_played DESC
LIMIT 15;


-- 7. Player Dependency (Strict Implicit Joins & Mathematically Corrected)
WITH DependencyStats AS (
    SELECT a.player_id, 
           CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END AS team_id, 
           COUNT(m.match_api_id) AS matches_with_player
    FROM Match m, Appearance a
    WHERE m.match_api_id = a.match_api_id
    GROUP BY a.player_id, CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END
)
SELECT p.player_name, t.team_long_name, ds.matches_with_player
FROM DependencyStats ds, Player p, Team t
WHERE ds.player_id = p.player_id AND ds.team_id = t.team_api_id
ORDER BY ds.matches_with_player DESC
LIMIT 10;