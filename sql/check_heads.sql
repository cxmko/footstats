-- sql/check_heads.sql

\echo '==================== COUNTRY ===================='
SELECT * FROM Country LIMIT 3;

\echo '==================== LEAGUE ===================='
SELECT * FROM League LIMIT 3;

\echo '==================== TEAM ===================='
SELECT * FROM Team LIMIT 3;

\echo '==================== PLAYER ===================='
SELECT * FROM Player LIMIT 3;

\echo '==================== MATCH (Core Data) ===================='
SELECT match_api_id, season, date, home_team_api_id, away_team_api_id, home_team_goal, away_team_goal FROM Match LIMIT 3;

\echo '==================== APPEARANCE ===================='
SELECT * FROM Appearance LIMIT 3;

\echo '==================== BETTING ODDS ===================='
SELECT * FROM Betting_Odds LIMIT 3;

\echo '==================== MATCH EVENT ===================='
SELECT * FROM Match_Event LIMIT 3;