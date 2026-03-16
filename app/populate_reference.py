# app/populate_reference.py

def populate_reference_tables(sqlite_cursor, pg_cursor):
    print("\n[1/4] Loading Country, League, Team, and Player tables...")
    
    sqlite_cursor.execute("SELECT id, name FROM Country;")
    pg_cursor.executemany("INSERT INTO Country (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;", sqlite_cursor.fetchall())
    
    sqlite_cursor.execute("SELECT id, name, country_id FROM League;")
    pg_cursor.executemany("INSERT INTO League (id, name, country_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", sqlite_cursor.fetchall())
    
    sqlite_cursor.execute("SELECT team_api_id, team_long_name, team_short_name FROM Team;")
    pg_cursor.executemany("INSERT INTO Team (team_api_id, team_long_name, team_short_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", sqlite_cursor.fetchall())
    
    sqlite_cursor.execute("SELECT player_api_id, player_name, birthday, height, weight FROM Player;")
    pg_cursor.executemany("INSERT INTO Player (player_id, player_name, birthday, height, weight) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", sqlite_cursor.fetchall())