# app/main.py
import sys
import os
import psycopg2

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_config import get_sqlite_connection, get_pg_connection
from app.populate_reference import populate_reference_tables
from app.populate_match import populate_match_core_and_odds
from app.populate_events import populate_match_events

def ingest_data():
    print("\n=== Initializing Modular ETL Pipeline ===")
    
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        populate_reference_tables(sqlite_cursor, pg_cursor)
        populate_match_core_and_odds(sqlite_cursor, pg_cursor)
        populate_match_events(sqlite_cursor, pg_cursor)
        
        pg_conn.commit()
        print("\n SUCCESS: Entire database is fully populated!")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"\n CRITICAL ERROR: Transaction rolled back. {e}")
    finally:
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

def check_db_health():
    """Counts rows in core tables to verify ingestion success."""
    print("\n--- Database Health Check ---")
    tables = ['Country', 'League', 'Team', 'Player', 'Match', 'Appearance', 'Match_Event', 'Betting_Odds']
    
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        for table in tables:
            pg_cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = pg_cursor.fetchone()[0]
            print(f"{table.ljust(15)}: {count:,} rows")
    except psycopg2.Error as e:
        print(f"Error reading tables: {e}")
    finally:
        print("-----------------------------\n")
        pg_cursor.close()
        pg_conn.close()

def search_player():
    name = input("Enter part of a player's name (e.g., 'Messi'): ")
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
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

def execute_custom_sql():
    """Allows the user to run raw SQL queries safely."""
    print("\n--- Custom SQL Executor ---")
    print("Type your SQL query below (must be on a single line). Type 'cancel' to go back.")
    query = input("SQL> ")
    
    if query.strip().lower() == 'cancel':
        return
        
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        pg_cursor.execute(query)
        
        # If it's a SELECT query, fetch and print the results
        if pg_cursor.description:
            # Get column names
            colnames = [desc[0] for desc in pg_cursor.description]
            results = pg_cursor.fetchall()
            
            print("\n" + " | ".join(colnames))
            print("-" * (len(colnames) * 15))
            
            for row in results:
                # Format each row item as a string, handling None (NULL) values
                formatted_row = [str(item) if item is not None else "NULL" for item in row]
                print(" | ".join(formatted_row))
            print(f"\n({len(results)} rows returned)")
            
        else:
            # If it's an INSERT/UPDATE/DELETE, commit it
            pg_conn.commit()
            print(f" Query executed successfully. {pg_cursor.rowcount} rows affected.")
            
    except psycopg2.Error as e:
        # Catch SQL syntax errors so the app doesn't crash
        pg_conn.rollback()
        print(f"\n SQL Error: {e.pgerror}")
    finally:
        pg_cursor.close()
        pg_conn.close()

def reset_database():
    """Truncates all tables to reset the database to an empty state."""
    confirm = input(" WARNING: This will delete ALL data. Are you sure? (y/n): ")
    if confirm.lower() != 'y':
        print("Reset cancelled.")
        return
        
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        print("Truncating tables...")
        pg_cursor.execute("TRUNCATE TABLE Country, League, Team, Player CASCADE;")
        pg_conn.commit()
        print(" Database successfully reset and is ready for fresh ingestion.")
    except psycopg2.Error as e:
        pg_conn.rollback()
        print(f" Error resetting database: {e}")
    finally:
        pg_cursor.close()
        pg_conn.close()

def main():
    while True:
        print("\n=== FootStats Application Interface ===")
        print("1. Initialize and Ingest Kaggle Data (Full Pipeline)")
        print("2. Database Health Check (Row Counts)")
        print("3. Search for a Player")
        print("4. View Top Teams (Demonstrates Triggers)")
        print("5. Execute Custom SQL Query")
        print("6. Reset Database (Truncate All Data)")
        print("7. Exit")
        
        choice = input("Select an option (1-7): ")
        
        if choice == '1':
            ingest_data()
        elif choice == '2':
            check_db_health()
        elif choice == '3':
            search_player()
        elif choice == '4':
            view_top_teams()
        elif choice == '5':
            execute_custom_sql()
        elif choice == '6':
            reset_database()
        elif choice == '7':
            print("Exiting application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()