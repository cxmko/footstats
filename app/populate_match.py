# app/populate_match.py

def populate_match_core_and_odds(sqlite_cursor, pg_cursor):
    print("[2/4] Fetching and Unpivoting Match, Appearance, and Betting Data...")
    
    query = """
        SELECT match_api_id, league_id, season, date, stage, home_team_api_id, away_team_api_id, home_team_goal, away_team_goal,
               home_player_1, home_player_2, home_player_3, home_player_4, home_player_5, home_player_6, home_player_7, home_player_8, home_player_9, home_player_10, home_player_11,
               away_player_1, away_player_2, away_player_3, away_player_4, away_player_5, away_player_6, away_player_7, away_player_8, away_player_9, away_player_10, away_player_11,
               home_player_X1, home_player_X2, home_player_X3, home_player_X4, home_player_X5, home_player_X6, home_player_X7, home_player_X8, home_player_X9, home_player_X10, home_player_X11,
               home_player_Y1, home_player_Y2, home_player_Y3, home_player_Y4, home_player_Y5, home_player_Y6, home_player_Y7, home_player_Y8, home_player_Y9, home_player_Y10, home_player_Y11,
               away_player_X1, away_player_X2, away_player_X3, away_player_X4, away_player_X5, away_player_X6, away_player_X7, away_player_X8, away_player_X9, away_player_X10, away_player_X11,
               away_player_Y1, away_player_Y2, away_player_Y3, away_player_Y4, away_player_Y5, away_player_Y6, away_player_Y7, away_player_Y8, away_player_Y9, away_player_Y10, away_player_Y11,
               B365H, B365D, B365A, BWH, BWD, BWA
        FROM Match;
    """
    sqlite_cursor.execute(query)
    
    core_matches, appearances, betting_odds = [], [], []
    
    for row in sqlite_cursor:
        match_id = row[0]
        core_matches.append(row[0:9])
        
        # Unpivot Appearances
        for i in range(11):
            if row[9 + i] is not None:  # Home Player
                appearances.append((row[9 + i], match_id, True, row[31 + i], row[42 + i]))
            if row[20 + i] is not None: # Away Player
                appearances.append((row[20 + i], match_id, False, row[53 + i], row[64 + i]))
        
        # Unpivot Odds
        if row[75] is not None: betting_odds.append((match_id, 'B365', row[75], row[76], row[77]))
        if row[78] is not None: betting_odds.append((match_id, 'BW', row[78], row[79], row[80]))

    print("[3/4] Pushing Match Data to PostgreSQL...")
    pg_cursor.executemany("INSERT INTO Match (match_api_id, league_id, season, date, stage, home_team_api_id, away_team_api_id, home_team_goal, away_team_goal) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", core_matches)
    pg_cursor.executemany("INSERT INTO Appearance (player_id, match_api_id, is_home_team, X_coordinate, Y_coordinate) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", appearances)
    pg_cursor.executemany("INSERT INTO Betting_Odds (match_api_id, bookmaker, home_win, draw, away_win) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", betting_odds)