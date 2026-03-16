-- sql/04_indexes.sql

-- Turn off all default timing and pagination for clean output
\timing off
\pset pager off
\x off
SET client_min_messages = warning;

-- Initialize log files
\! del log.txt 2>nul
\! del temp_log.txt 2>nul

\o temp_log.txt
\qecho '========================================================================'
\qecho '        DATABASE OPTIMIZATION DETAILED EXECUTION LOG'
\qecho '========================================================================'
\o
\! type temp_log.txt >> log.txt

\echo '========================================================================'
\echo 'INITIALIZING SYSTEM & QUERY MACROS...'
\echo '========================================================================'

-- Silencing the creation of the reusable query macros
\o temp_log.txt
ANALYZE;

CREATE OR REPLACE VIEW v_q4 AS
WITH PlayerSpatialStats AS (
    SELECT a.player_id, CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END AS pitch_zone,
           COUNT(DISTINCT a.match_api_id) AS matches_played, COUNT(me.event_id) AS goals
    FROM Appearance a
    LEFT OUTER JOIN Match_Event me ON a.match_api_id = me.match_api_id AND me.event_type = 'goal' AND me.player_id = a.player_id
    WHERE a.X_coordinate IS NOT NULL GROUP BY a.player_id, CASE WHEN a.X_coordinate BETWEEN 4 AND 7 THEN 'Central Axis' ELSE 'Wings' END
)
SELECT p.player_name, ps.pitch_zone, ps.matches_played, ps.goals FROM PlayerSpatialStats ps, Player p WHERE ps.player_id = p.player_id ORDER BY ps.goals DESC LIMIT 5;

CREATE OR REPLACE VIEW v_q7 AS
WITH DependencyStats AS (
    SELECT a.player_id, CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END AS team_id, COUNT(m.match_api_id) AS matches_with_player
    FROM Match m, Appearance a WHERE m.match_api_id = a.match_api_id GROUP BY a.player_id, CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END
)
SELECT p.player_name, t.team_long_name, ds.matches_with_player FROM DependencyStats ds, Player p, Team t WHERE ds.player_id = p.player_id AND ds.team_id = t.team_api_id ORDER BY ds.matches_with_player DESC LIMIT 5;

CREATE OR REPLACE VIEW v_q2 AS
WITH HatTrickIDs AS (
    SELECT me.player_id, CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END AS team_id
    FROM Match_Event me, Match m, Appearance a
    WHERE me.match_api_id = m.match_api_id AND me.player_id = a.player_id AND m.match_api_id = a.match_api_id AND me.event_type = 'goal'
    GROUP BY me.player_id, CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END, m.match_api_id HAVING COUNT(me.event_id) >= 3
),
PlayerAggregates AS (
    SELECT player_id, COUNT(DISTINCT team_id) AS different_teams_with_hattrick, COUNT(*) AS total_hattricks
    FROM HatTrickIDs GROUP BY player_id
)
SELECT p.player_name, pa.different_teams_with_hattrick, pa.total_hattricks
FROM PlayerAggregates pa, Player p WHERE pa.player_id = p.player_id ORDER BY pa.different_teams_with_hattrick DESC, pa.total_hattricks DESC LIMIT 5;
\o


\echo ' '
\echo '========================================================================'
\echo 'Q4: SPATIAL IMPACT'
\echo '========================================================================'

\o temp_log.txt
\qecho '\n>>> Q4: BASELINE'
EXPLAIN ANALYZE SELECT * FROM v_q4;
\o
\! type temp_log.txt >> log.txt

\echo '>>> Q4: BASELINE'
\timing on
SELECT * FROM v_q4;
\timing off

\o temp_log.txt
CREATE INDEX IF NOT EXISTS idx_q4_matchevent ON Match_Event(player_id, match_api_id, event_id) WHERE event_type = 'goal';
CREATE INDEX IF NOT EXISTS idx_q4_appearance ON Appearance(player_id, match_api_id, X_coordinate);
ANALYZE Match_Event;
ANALYZE Appearance;
\qecho '\n>>> Q4: INDEXED'
EXPLAIN ANALYZE SELECT * FROM v_q4;
\o
\! type temp_log.txt >> log.txt

\echo ' '
\echo '>>> Q4: INDEXED'
\timing on
SELECT * FROM v_q4;
\timing off

\o temp_log.txt
DROP INDEX IF EXISTS idx_q4_matchevent;
DROP INDEX IF EXISTS idx_q4_appearance;
\o


\echo ' '
\echo '========================================================================'
\echo 'Q7: PLAYER DEPENDENCY'
\echo '========================================================================'

\o temp_log.txt
\qecho '\n>>> Q7: BASELINE'
EXPLAIN ANALYZE SELECT * FROM v_q7;
\o
\! type temp_log.txt >> log.txt

\echo '>>> Q7: BASELINE'
\timing on
SELECT * FROM v_q7;
\timing off

\o temp_log.txt
CREATE INDEX IF NOT EXISTS idx_fail_app_q7 ON Appearance(match_api_id, player_id);
CREATE INDEX IF NOT EXISTS idx_fail_match_q7 ON Match(match_api_id, home_team_api_id, away_team_api_id);
ANALYZE Appearance;
ANALYZE Match;
\qecho '\n>>> Q7: FAILED INDEX'
EXPLAIN ANALYZE SELECT * FROM v_q7;
\o
\! type temp_log.txt >> log.txt

\echo ' '
\echo '>>> Q7: FAILED INDEX'
\timing on
SELECT * FROM v_q7;
\timing off

\o temp_log.txt
DROP INDEX IF EXISTS idx_fail_app_q7;
DROP INDEX IF EXISTS idx_fail_match_q7;
\o


\echo ' '
\echo '========================================================================'
\echo 'Q2: HAT-TRICK HUNTERS'
\echo '========================================================================'

\o temp_log.txt
\qecho '\n>>> Q2: BASELINE'
EXPLAIN ANALYZE SELECT * FROM v_q2;
\o
\! type temp_log.txt >> log.txt

\echo '>>> Q2: BASELINE'
\timing on
SELECT * FROM v_q2;
\timing off

\o temp_log.txt
CREATE INDEX IF NOT EXISTS idx_fail_me_q2 ON Match_Event(event_type, match_api_id, player_id);
ANALYZE Match_Event;
\qecho '\n>>> Q2: FAILED INDEX'
EXPLAIN ANALYZE SELECT * FROM v_q2;
\o
\! type temp_log.txt >> log.txt

\echo ' '
\echo '>>> Q2: FAILED INDEX'
\timing on
SELECT * FROM v_q2;
\timing off

\o temp_log.txt
DROP INDEX IF EXISTS idx_fail_me_q2;
\o


\echo ' '
\echo '========================================================================'
\echo 'SOLUTION: PRE-COMPUTED MATERIALIZED VIEW (Q7 & Q2)'
\echo '========================================================================'

\o temp_log.txt
DROP MATERIALIZED VIEW IF EXISTS mv_player_match_stats CASCADE;
CREATE MATERIALIZED VIEW mv_player_match_stats AS
SELECT a.player_id, p.player_name, a.match_api_id, t.team_long_name AS team_name, COUNT(me.event_id) AS goals_scored,
       COUNT(a.match_api_id) OVER (PARTITION BY a.player_id, t.team_long_name) AS total_matches_for_team
FROM Appearance a
JOIN Match m ON a.match_api_id = m.match_api_id
JOIN Player p ON a.player_id = p.player_id
JOIN Team t ON (CASE WHEN a.is_home_team = TRUE THEN m.home_team_api_id ELSE m.away_team_api_id END) = t.team_api_id
LEFT JOIN Match_Event me ON a.match_api_id = me.match_api_id AND a.player_id = me.player_id AND me.event_type = 'goal'
GROUP BY a.player_id, p.player_name, a.match_api_id, t.team_long_name;

CREATE INDEX idx_mv_q7_superfast ON mv_player_match_stats(total_matches_for_team DESC, player_name, team_name);
CREATE INDEX idx_mv_goals_search ON mv_player_match_stats(goals_scored DESC, player_name, team_name);
CLUSTER mv_player_match_stats USING idx_mv_q7_superfast;
ANALYZE mv_player_match_stats;
\o

\o temp_log.txt
\qecho '\n>>> Q7: PRE-COMPUTED VIEW'
EXPLAIN ANALYZE SELECT player_name, team_name, total_matches_for_team AS matches_with_player FROM mv_player_match_stats GROUP BY player_name, team_name, total_matches_for_team ORDER BY total_matches_for_team DESC LIMIT 5;
\o
\! type temp_log.txt >> log.txt

\echo '>>> Q7: PRE-COMPUTED VIEW'
\timing on
SELECT player_name, team_name, total_matches_for_team AS matches_with_player FROM mv_player_match_stats GROUP BY player_name, team_name, total_matches_for_team ORDER BY total_matches_for_team DESC LIMIT 5;
\timing off


\o temp_log.txt
\qecho '\n>>> Q2: PRE-COMPUTED VIEW'
EXPLAIN ANALYZE WITH HatTricks AS (SELECT player_id, player_name, team_name FROM mv_player_match_stats WHERE goals_scored >= 3) SELECT player_name, COUNT(DISTINCT team_name) AS different_teams_with_hattrick, COUNT(*) AS total_hattricks FROM HatTricks GROUP BY player_id, player_name ORDER BY different_teams_with_hattrick DESC, total_hattricks DESC LIMIT 5;
\o
\! type temp_log.txt >> log.txt

\echo ' '
\echo '>>> Q2: PRE-COMPUTED VIEW'
\timing on
WITH HatTricks AS (
    SELECT player_id, player_name, team_name FROM mv_player_match_stats WHERE goals_scored >= 3
)
SELECT player_name, COUNT(DISTINCT team_name) AS different_teams_with_hattrick, COUNT(*) AS total_hattricks FROM HatTricks
GROUP BY player_id, player_name ORDER BY different_teams_with_hattrick DESC, total_hattricks DESC LIMIT 5;
\timing off


\echo ' '
\echo '========================================================================'
\echo 'CLEANUP'
\echo '========================================================================'
\echo '>>> Dropping all views, materialized views, and temporary files...'
\o temp_log.txt
DROP MATERIALIZED VIEW IF EXISTS mv_player_match_stats CASCADE;
DROP VIEW IF EXISTS v_q4 CASCADE;
DROP VIEW IF EXISTS v_q7 CASCADE;
DROP VIEW IF EXISTS v_q2 CASCADE;
\o
\! del temp_log.txt 2>nul
\echo 'DONE. Check log.txt for all EXPLAIN ANALYZE trees.'