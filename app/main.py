# app/main.py
import sqlite3
import psycopg2
import sys

# --- CONFIGURATION ---
SQLITE_PATH = 'database.sqlite'
# Replace with your actual Postgres credentials
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "footstats"
PG_USER = "postgres"
PG_PASS = "1234"

def get_pg_connection():
    """Establishes a raw connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )

def ingest_data():
    print("Starting raw SQL data ingestion... This might take a moment.")
    
    # 1. Open basic connections
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        # --- Extract & Load COUNTRY ---
        print("-> Loading Country table...")
        sqlite_cursor.execute("SELECT id, name FROM Country;")
        countries = sqlite_cursor.fetchall() # Fetches a list of tuples
        
        # Raw SQL insert using psycopg2's parameterized queries
        pg_cursor.executemany(
            "INSERT INTO Country (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;", 
            countries
        )
        pg_conn.commit() # Must manually commit transactions!

        # --- Extract & Load LEAGUE ---
        print("-> Loading League table...")
        sqlite_cursor.execute("SELECT id, name, country_id FROM League;")
        leagues = sqlite_cursor.fetchall()
        pg_cursor.executemany(
            "INSERT INTO League (id, name, country_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", 
            leagues
        )
        pg_conn.commit()

        # --- Extract & Load TEAM ---
        print("-> Loading Team table...")
        sqlite_cursor.execute("SELECT team_api_id, team_long_name, team_short_name FROM Team;")
        teams = sqlite_cursor.fetchall()
        pg_cursor.executemany(
            "INSERT INTO Team (team_api_id, team_long_name, team_short_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", 
            teams
        )
        pg_conn.commit()

        # --- Extract & Load PLAYER ---
        print("-> Loading Player table...")
        sqlite_cursor.execute("SELECT player_api_id, player_name, birthday, height, weight FROM Player;")
        players = sqlite_cursor.fetchall()
        pg_cursor.executemany(
            "INSERT INTO Player (player_api_id, player_name, birthday, height, weight) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", 
            players
        )
        pg_conn.commit()

        # --- Extract & Load MATCH ---
        print("-> Loading Match table...")
        sqlite_cursor.execute("""
            SELECT match_api_id, league_id, season, date, stage, 
                   home_team_api_id, away_team_api_id, home_team_goal, away_team_goal 
            FROM Match;
        """)
        matches = sqlite_cursor.fetchall()
        pg_cursor.executemany(
            """INSERT INTO Match (match_api_id, league_id, season, date, stage, home_team_api_id, away_team_api_id, home_team_goal, away_team_goal) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;""", 
            matches
        )
        pg_conn.commit()
        
        print("\nSUCCESS: All data ingested using raw SQL cursors!")
        print("Note: The triggers updated the 'total_points' for all teams!\n")
        
    except Exception as e:
        pg_conn.rollback() # Rollback on error (shows good DB practices)
        print(f"\nERROR during ingestion: {e}")
    finally:
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

def search_player():
    name = input("Enter part of a player's name (e.g., 'Messi'): ")
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    # Using parameterized queries (%s) to prevent SQL Injection
    query = "SELECT player_name, birthday, height FROM Player WHERE player_name ILIKE %s LIMIT 5;"
    pg_cursor.execute(query, ('%' + name + '%',))
    
    results = pg_cursor.fetchall()
    
    if not results:
        print("No players found.")
    else:
        print("\n--- Search Results ---")
        for row in results:
            print(f"Name: {row[0]}, Birthday: {row[1]}, Height: {row[2]}cm")
        print("----------------------\n")
        
    pg_cursor.close()
    pg_conn.close()

def view_top_teams():
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    print("\n--- Top 5 Teams by Total Points ---")
    pg_cursor.execute("SELECT team_long_name, total_points FROM Team ORDER BY total_points DESC LIMIT 5;")
    results = pg_cursor.fetchall()
    
    for i, row in enumerate(results, 1):
        print(f"{i}. {row[0]} - {row[1]} points")
    print("-----------------------------------\n")
    
    pg_cursor.close()
    pg_conn.close()

def main():
    while True:
        print("\n=== FootStats Application Interface ===")
        print("1. Initialize and Ingest Kaggle Data (Raw Cursors)")
        print("2. Search for a Player")
        print("3. View Top Teams (Demonstrates Triggers)")
        print("4. Exit")
        
        choice = input("Select an option (1-4): ")
        
        if choice == '1':
            ingest_data()
        elif choice == '2':
            search_player()
        elif choice == '3':
            view_top_teams()
        elif choice == '4':
            print("Exiting application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()