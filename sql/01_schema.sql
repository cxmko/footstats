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
    player_api_id INT PRIMARY KEY,
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
    minute INT,
    event_type VARCHAR(50),
    PRIMARY KEY (match_api_id, event_id),
    FOREIGN KEY (match_api_id) REFERENCES Match(match_api_id) ON DELETE CASCADE
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
    player_api_id INT,
    match_api_id INT,
    is_home_team BOOLEAN,
    X_coordinate INT,
    Y_coordinate INT,
    PRIMARY KEY (player_api_id, match_api_id),
    FOREIGN KEY (player_api_id) REFERENCES Player(player_api_id) ON DELETE CASCADE,
    FOREIGN KEY (match_api_id) REFERENCES Match(match_api_id) ON DELETE CASCADE
);