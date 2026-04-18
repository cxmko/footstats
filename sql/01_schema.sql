-- sql/01_schema.sql

-- 1. Core Reference Tables
CREATE TABLE Country (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE League (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country_id INT NOT NULL,
    FOREIGN KEY (country_id) REFERENCES Country(id) ON DELETE CASCADE
);

CREATE TABLE Team (
    team_api_id INT PRIMARY KEY,
    team_long_name VARCHAR(255),
    team_short_name VARCHAR(50),
    total_points INT DEFAULT 0
);

CREATE TABLE Player (
    player_id INT PRIMARY KEY,
    player_name VARCHAR(255),
    birthday DATE,
    height FLOAT,
    weight INT
);

-- 2. Main Fact Table
CREATE TABLE Match (
    match_api_id INT PRIMARY KEY,
    league_id INT NOT NULL,
    season VARCHAR(50),
    date DATE,
    stage INT,
    home_team_api_id INT NOT NULL,
    away_team_api_id INT NOT NULL,
    home_team_goal INT,
    away_team_goal INT,
    FOREIGN KEY (league_id) REFERENCES League(id),
    FOREIGN KEY (home_team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (away_team_api_id) REFERENCES Team(team_api_id)
);

-- 3. Weak Entities (Composite Primary Keys)
CREATE TABLE Match_Event (
    match_api_id INT,
    event_id INT,
    player_id INT,
    minute INT,
    event_type VARCHAR(50),
    PRIMARY KEY (match_api_id, event_id),
    FOREIGN KEY (match_api_id) REFERENCES Match(match_api_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES Player(player_id) ON DELETE CASCADE
);

CREATE TABLE Betting_Odds (
    match_api_id INT,
    bookmaker VARCHAR(50),
    home_win FLOAT,
    draw FLOAT,
    away_win FLOAT,
    PRIMARY KEY (match_api_id, bookmaker),
    FOREIGN KEY (match_api_id) REFERENCES Match(match_api_id) ON DELETE CASCADE
);

-- 4. Many-to-Many Relationship Table
CREATE TABLE Appearance (
    player_id INT,
    match_api_id INT,
    is_home_team BOOLEAN,
    X_coordinate INT,
    Y_coordinate INT,
    PRIMARY KEY (player_id, match_api_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id) ON DELETE CASCADE,
    FOREIGN KEY (match_api_id) REFERENCES Match(match_api_id) ON DELETE CASCADE
);


CREATE MATERIALIZED VIEW mv_player_summary AS
SELECT p.player_id, p.player_name, m.season, COUNT(DISTINCT a.match_api_id) as appearances,
       COUNT(CASE WHEN me.event_type = 'goal' THEN 1 END) as goals,
       COUNT(CASE WHEN me.event_type = 'card' THEN 1 END) as cards
FROM Player p
JOIN Appearance a ON p.player_id = a.player_id
JOIN Match m ON a.match_api_id = m.match_api_id
LEFT JOIN Match_Event me ON a.match_api_id = me.match_api_id AND p.player_id = me.player_id
GROUP BY p.player_id, p.player_name, m.season;

CREATE UNIQUE INDEX idx_mv_player_id_season ON mv_player_summary(player_id, season);
CREATE INDEX idx_mv_player_name ON mv_player_summary(player_name);

CREATE MATERIALIZED VIEW mv_team_summary AS
WITH TeamSeasonStats AS (
    SELECT l.name as league_name, m.season, t.team_long_name,
        SUM(CASE WHEN m.home_team_api_id = t.team_api_id AND m.home_team_goal > m.away_team_goal THEN 1
                 WHEN m.away_team_api_id = t.team_api_id AND m.away_team_goal > m.home_team_goal THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 END) as draws,
        SUM(CASE WHEN m.home_team_api_id = t.team_api_id AND m.home_team_goal < m.away_team_goal THEN 1
                 WHEN m.away_team_api_id = t.team_api_id AND m.away_team_goal < m.home_team_goal THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN m.home_team_api_id = t.team_api_id AND m.home_team_goal > m.away_team_goal THEN 3
                 WHEN m.away_team_api_id = t.team_api_id AND m.away_team_goal > m.home_team_goal THEN 3
                 WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 END) as points
    FROM Match m JOIN League l ON m.league_id = l.id
    JOIN Team t ON t.team_api_id = m.home_team_api_id OR t.team_api_id = m.away_team_api_id
    GROUP BY l.name, m.season, t.team_long_name
)
SELECT league_name, season, team_long_name, wins, draws, losses, points,
       RANK() OVER (PARTITION BY league_name, season ORDER BY points DESC) as final_placement
FROM TeamSeasonStats;

CREATE UNIQUE INDEX idx_mv_team_season ON mv_team_summary(team_long_name, season);