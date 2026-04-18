# app/main.py
import sys
import os
import platform
import shutil
import psycopg2
import csv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_config import get_sqlite_connection, get_pg_connection
from app.populate_reference import populate_reference_tables
from app.populate_match import populate_match_core_and_odds
from app.populate_events import populate_match_events

console = Console()

# Dictionaries for Number-Only Menus
LEAGUES = {
    "1": "Belgium Jupiler League", "2": "England Premier League", "3": "France Ligue 1",
    "4": "Germany 1. Bundesliga", "5": "Italy Serie A", "6": "Netherlands Eredivisie",
    "7": "Poland Ekstraklasa", "8": "Portugal Liga ZON Sagres", "9": "Scotland Premier League",
    "10": "Spain LIGA BBVA", "11": "Switzerland Super League"
}

SEASONS = {
    "1": "2008/2009", "2": "2009/2010", "3": "2010/2011", "4": "2011/2012",
    "5": "2012/2013", "6": "2013/2014", "7": "2014/2015", "8": "2015/2016"
}

PLAYERS = {
    "1": "Lionel Messi", "2": "Cristiano Ronaldo", "3": "Zlatan Ibrahimovic", 
    "4": "Eden Hazard", "5": "Wayne Rooney", "6": "Andres Iniesta", "7": "Philipp Lahm"
}

def display_intro():
    intro_text = (
        "[bold cyan]European Soccer Database (2008 - 2016)[/bold cyan]\n\n"
        "This data warehouse contains fully normalized records of over 25,000 matches,\n"
        "10,000 players, and 1.2 million granular events (goals, cards, lineups) \n"
        "across 11 top-tier European countries."
    )
    console.print(Panel(intro_text, title="[System Architecture]", border_style="cyan"))


# =====================================================================
# 1. GETTING STARTED (ETL)
# =====================================================================
def ingest_data():
    console.print("\n[bold cyan]--- Initializing Modular ETL Pipeline ---[/bold cyan]")
    
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    # --- DAY 1 SETUP & SAFETY GUARD ---
    try:
        # Check if the 'team' table exists in the public schema
        pg_cursor.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'team');")
        table_exists = pg_cursor.fetchone()[0]
        
        if table_exists:
            # If it exists, check if it has data
            pg_cursor.execute("SELECT COUNT(*) FROM Team;")
            if pg_cursor.fetchone()[0] > 0:
                console.print("[bold red][ERROR] Database is already populated with data![/bold red]")
                console.print("To wipe the database and safely re-ingest, please use: [bold yellow]Advanced Settings -> Start Fresh[/bold yellow]\n")
                pg_cursor.close()
                pg_conn.close()
                return
        else:
            # The database is completely blank! Let's build the architecture automatically.
            with console.status("[bold magenta]Blank database detected. Building Schema and Triggers from SQL files...[/bold magenta]"):
                with open("sql/01_schema.sql", "r", encoding="utf-8") as schema_file:
                    pg_cursor.execute(schema_file.read())
                with open("sql/02_triggers.sql", "r", encoding="utf-8") as triggers_file:
                    pg_cursor.execute(triggers_file.read())
                pg_conn.commit()
            console.print("[bold green]Database architecture constructed successfully![/bold green]")
            
    except psycopg2.Error as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR] Architecture setup failed: {e}[/bold red]\n")
        pg_cursor.close()
        pg_conn.close()
        return
    except FileNotFoundError as e:
        console.print(f"[bold red][ERROR] Could not find SQL file: {e}[/bold red]")
        pg_cursor.close()
        pg_conn.close()
        return
    # ------------------------------------------------------------
    
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    
    try:
        with console.status("[bold yellow]Extracting, Transforming, and Loading data...[/bold yellow]", spinner="dots"):
            populate_reference_tables(sqlite_cursor, pg_cursor)
            populate_match_core_and_odds(sqlite_cursor, pg_cursor)
            populate_match_events(sqlite_cursor, pg_cursor)
            pg_conn.commit()
            
            # Synchronize the Materialized Views
            pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_team_summary;")
            pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_player_summary;")
            pg_conn.commit()
            
        console.print("[bold green][SUCCESS] Database fully populated and views synchronized![/bold green]\n")
    except Exception as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR] Ingestion Failed: {e}[/bold red]\n")
    finally:
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

def start_fresh():
    """Truncates all tables and triggers a fresh ingestion."""
    console.print("\n[bold red]--- Database Hard Reset ---[/bold red]")
    confirm = Prompt.ask("[bold red]WARNING: This will wipe ALL data and re-ingest from scratch. Are you sure?[/bold red]", choices=["y", "n"], default="n")
    if confirm.lower() != 'y':
        console.print("[yellow]Reset cancelled.[/yellow]\n")
        return
        
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        with console.status("[bold red]Truncating all tables...[/bold red]"):
            # CASCADE ensures all dependent tables are also cleared
            pg_cursor.execute("TRUNCATE TABLE Country, League, Team, Player, Match, Appearance, Match_Event, Betting_Odds CASCADE;")
            pg_conn.commit()
        console.print("[bold green][SUCCESS] Database wiped completely.[/bold green]\n")
        
        # Trigger the ETL pipeline automatically
        ingest_data()
        
    except psycopg2.Error as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR] Reset failed: {e}[/bold red]\n")
    finally:
        pg_cursor.close()
        pg_conn.close()

# =====================================================================
# 2. FIND INFORMATION (DYNAMIC QUERY ENGINE)
# =====================================================================
def execute_and_print(query, params=(), title="Results"):
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        with console.status("[yellow]Crunching numbers...[/yellow]"):
            pg_cursor.execute(query, params)
            colnames = [desc[0] for desc in pg_cursor.description]
            results = pg_cursor.fetchall()
            
            if not results:
                console.print("[yellow]No data found for this combination.[/yellow]\n")
                return

            table_ui = Table(title=title, style="cyan")
            for col in colnames:
                table_ui.add_column(col.replace('_', ' ').title(), style="magenta")
            for row in results:
                formatted_row = [str(item) if item is not None else "NULL" for item in row]
                table_ui.add_row(*formatted_row)
            console.print(table_ui)
    except psycopg2.Error as e:
        console.print(f"[bold red][SQL Error] {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

# --- VISUALIZATION SUB-MENU FUNCTIONS ---

def vis_global_distribution():
    console.print("\n[bold cyan]--- Global Match Distribution ---[/bold cyan]")
    query = """
        SELECT l.name, COUNT(m.match_api_id) as total_matches
        FROM League l, Match m 
        WHERE l.id = m.league_id
        GROUP BY l.name ORDER BY total_matches DESC;
    """
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.execute(query)
        results = pg_cursor.fetchall()
        for league, count in results:
            bar = "█" * int(count / 150) 
            console.print(f"[green]{league.ljust(25)}[/green] | [yellow]{str(count).ljust(5)}[/yellow] | [cyan]{bar}[/cyan]")
        console.print()
    except psycopg2.Error as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def vis_odds_evolution():
    console.print("\n[bold cyan]--- Evolution of Home Win Odds ---[/bold cyan]")
    for k, v in LEAGUES.items(): console.print(f"[{k}] {v}")
    league_id = Prompt.ask("Select League", choices=list(LEAGUES.keys()))
    league_name = LEAGUES[league_id]

    query = """
        SELECT m.season, ROUND(AVG(bo.home_win)::NUMERIC, 2) as avg_home_odds
        FROM Match m, Betting_Odds bo, League l
        WHERE m.match_api_id = bo.match_api_id AND m.league_id = l.id AND l.name = %s
        GROUP BY m.season ORDER BY m.season;
    """
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        with console.status("[yellow]Calculating historical odds...[/yellow]"):
            pg_cursor.execute(query, (league_name,))
            results = pg_cursor.fetchall()
            
            console.print(f"\n[bold magenta]Average Home Win Odds Trend: {league_name}[/bold magenta]")
            for season, odds in results:
                # Multiply by 10 and subtract base for visual scaling
                bar_length = int((float(odds) - 1.5) * 20) if odds else 0
                bar = "█" * max(1, bar_length)
                console.print(f"[cyan]{season}[/cyan] | [yellow]{str(odds).ljust(4)}[/yellow] | [green]{bar}[/green]")
            console.print()
    except psycopg2.Error as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def vis_pitch_heatmap():
    console.print("\n[bold cyan]--- Player Spatial Pitch Heatmap ---[/bold cyan]")
    search_name = Prompt.ask("Enter Player Name to visualize (e.g., 'Ronaldo')")

    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        # 1. Preliminary Disambiguation Search
        pg_cursor.execute(
            "SELECT DISTINCT player_id, player_name FROM Player WHERE player_name ILIKE %s ORDER BY player_name LIMIT 15;", 
            (f"%{search_name}%",)
        )
        matches = pg_cursor.fetchall()

        # 2. Handle Search Results
        if not matches:
            console.print(f"[yellow]No players found matching '{search_name}'.[/yellow]")
            return
        elif len(matches) == 1:
            exact_id, exact_name = matches[0]
        else:
            console.print("\n[bold yellow]Multiple players found. Please select one:[/bold yellow]")
            for i, (p_id, name) in enumerate(matches, 1):
                console.print(f"[{i}] {name} (ID: {p_id})")
            console.print(f"[{len(matches)+1}] Cancel")
            
            choice = Prompt.ask("Select", choices=[str(i) for i in range(1, len(matches) + 2)])
            if choice == str(len(matches) + 1): 
                return
            exact_id, exact_name = matches[int(choice) - 1]

        # 3. Fetch Coordinates for the Selected Player
        with console.status(f"[yellow]Mapping coordinates for {exact_name}...[/yellow]"):
            query = """
                SELECT X_coordinate, Y_coordinate 
                FROM Appearance 
                WHERE player_id = %s AND X_coordinate IS NOT NULL AND Y_coordinate IS NOT NULL;
            """
            pg_cursor.execute(query, (exact_id,))
            results = pg_cursor.fetchall()

        if not results:
            console.print(f"[yellow]No spatial tracking data available for {exact_name}.[/yellow]")
            return

        console.print(f"[bold green]Successfully mapped {len(results)} positional data points for {exact_name}![/bold green]")

        # 4. Terminal Plotting Logic
        # Initialize 11x9 pitch grid (Y is 1-11, X is 1-9)
        grid = [[0 for _ in range(9)] for _ in range(11)]
        max_val = 0
        
        for x, y in results:
            y_idx = min(max(y - 1, 0), 10)
            
            # FIXED: The Kaggle Dataset (from FIFA) maps X=1 to the RIGHT wing 
            # and X=9 to the LEFT wing. We must invert X to print it correctly!
            x_idx = 8 - min(max(x - 1, 0), 8) 
            
            grid[y_idx][x_idx] += 1
            if grid[y_idx][x_idx] > max_val:
                max_val = grid[y_idx][x_idx]

        console.print(f"\n[bold magenta]Attacking Direction [^][/bold magenta]")
        console.print("[dim]------------------------------------[/dim]")
        
        # Print from Y=11 (Attack) down to Y=1 (Defense)
        shades = [' . ', ' ░ ', ' ▒ ', ' ▓ ', ' █ ']
        for row in reversed(grid):
            row_str = ""
            for val in row:
                if val == 0:
                    row_str += "[dim]" + shades[0] + "[/dim]"
                else:
                    # Normalize density
                    intensity = int((val / max_val) * 4)
                    color = "green" if intensity < 2 else "yellow" if intensity < 3 else "red"
                    row_str += f"[{color}]" + shades[intensity] + f"[/{color}]"
            console.print(row_str)
        
        console.print("[dim]------------------------------------[/dim]")
        console.print(f"[bold magenta]Defending Direction [v][/bold magenta]\n")
            
    except psycopg2.Error as e:
        console.print(f"[bold red]Database Error: {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def visualize_data_menu():
    while True:
        console.print("\n[bold cyan]--- Visualisation Engine ---[/bold cyan]")
        console.print("[1] Global Match Distribution (Bar Chart)")
        console.print("[2] Bookmaker Odds Evolution (Trend Line)")
        console.print("[3] Player Spatial Pitch Heatmap (2D Matrix)")
        console.print("[4] Back")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4"])
        if choice == "1": vis_global_distribution()
        elif choice == "2": vis_odds_evolution()
        elif choice == "3": vis_pitch_heatmap()
        elif choice == "4": break


# --- ANALYTICS ENGINES ---

def dynamic_player_analytics():
    console.print(Panel("[bold]Player Analytics Engine[/bold]"))
    
    scope_choice = Prompt.ask("Scope: [1] Global [2] Specific League", choices=["1", "2"])
    league_name = None
    if scope_choice == "2":
        for k, v in LEAGUES.items(): console.print(f"[{k}] {v}")
        league_id = Prompt.ask("Select League", choices=list(LEAGUES.keys()))
        league_name = LEAGUES[league_id]

    time_choice = Prompt.ask("Timeframe: [1] All-Time [2] Specific Season", choices=["1", "2"])
    season_val = None
    if time_choice == "2":
        for k, v in SEASONS.items(): console.print(f"[{k}] {v}")
        season_id = Prompt.ask("Select Season", choices=list(SEASONS.keys()))
        season_val = SEASONS[season_id]

    console.print("\n[1] Top Goalscorers\n[2] Most Cards (Yellow & Red)\n[3] Most Appearances")
    metric = Prompt.ask("Select Metric", choices=["1", "2", "3"])

    base_query = """
        SELECT p.player_name, COUNT(me.event_id) as metric_count
        FROM Match_Event me, Player p, Match m
    """
    where_clauses = ["me.player_id = p.player_id", "me.match_api_id = m.match_api_id"]

    if scope_choice == "2":
        base_query = "SELECT p.player_name, COUNT(me.event_id) as metric_count FROM Match_Event me, Player p, Match m, League l"
        where_clauses.append("m.league_id = l.id")
        
    if metric == "1":
        where_clauses.append("me.event_type = 'goal'")
        title = "Top Goalscorers"
    elif metric == "2":
        where_clauses.append("me.event_type = 'card'")
        title = "Most Cards (Yellow & Red)"
    else:
        base_query = "SELECT p.player_name, COUNT(a.match_api_id) as metric_count FROM Appearance a, Player p, Match m"
        where_clauses = ["a.player_id = p.player_id", "a.match_api_id = m.match_api_id"]
        if scope_choice == "2":
            base_query = "SELECT p.player_name, COUNT(a.match_api_id) as metric_count FROM Appearance a, Player p, Match m, League l"
            where_clauses.append("m.league_id = l.id")
        title = "Most Appearances"

    params = []
    if scope_choice == "2":
        where_clauses.append("l.name ILIKE %s")
        params.append(f"%{league_name}%")
    if time_choice == "2":
        where_clauses.append("m.season = %s")
        params.append(season_val)

    final_query = f"{base_query} WHERE {' AND '.join(where_clauses)} GROUP BY p.player_name ORDER BY metric_count DESC LIMIT 10;"
    time_str = season_val if time_choice == "2" else "All-Time"
    scope_str = league_name if scope_choice == "2" else "Global"
    execute_and_print(final_query, tuple(params), title=f"{title} ({time_str} | {scope_str})")

def dynamic_team_analytics():
    console.print(Panel("[bold]Team Analytics Engine[/bold]"))
    for k, v in SEASONS.items(): console.print(f"[{k}] {v}")
    season_id = Prompt.ask("Select Season to see League Champions", choices=list(SEASONS.keys()))
    season_val = SEASONS[season_id]
    
    query = """
        WITH TeamPoints AS (
            SELECT l.name AS league_name, t.team_long_name AS team_name, SUM(
                CASE 
                    WHEN m.home_team_api_id = t.team_api_id AND m.home_team_goal > m.away_team_goal THEN 3
                    WHEN m.away_team_api_id = t.team_api_id AND m.away_team_goal > m.home_team_goal THEN 3
                    WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 
                END) AS points
            FROM Match m, League l, Team t
            WHERE m.league_id = l.id 
              AND (t.team_api_id = m.home_team_api_id OR t.team_api_id = m.away_team_api_id)
              AND m.season = %s
            GROUP BY l.name, t.team_long_name
        )
        SELECT DISTINCT ON (league_name) league_name, team_name AS champion, points
        FROM TeamPoints
        ORDER BY league_name, points DESC;
    """
    execute_and_print(query, (season_val,), title=f"League Champions in {season_val}")

def match_and_betting_analytics():
    console.print(Panel("[bold]Match & Betting Analytics[/bold]"))
    console.print("[1] Highest Scoring Matches\n[2] Biggest Statistical Upsets\n[3] Bookmaker Arbitrage Margins")
    choice = Prompt.ask("Select Metric", choices=["1", "2", "3"])
    
    if choice == "1":
        query = """
            SELECT m.season, m.date, t1.team_long_name AS home, t2.team_long_name AS away, 
                   (m.home_team_goal + m.away_team_goal) AS total_goals
            FROM Match m, Team t1, Team t2
            WHERE m.home_team_api_id = t1.team_api_id AND m.away_team_api_id = t2.team_api_id
            ORDER BY total_goals DESC LIMIT 10;
        """
        execute_and_print(query, title="Highest Scoring Matches of All Time")
    
    elif choice == "2":
        query = """
            SELECT m.season, t1.team_long_name AS home, t2.team_long_name AS away, 
                   m.home_team_goal, m.away_team_goal, bo.bookmaker,
                   ROUND(CAST((1.0 / CASE WHEN m.home_team_goal > m.away_team_goal THEN bo.home_win ELSE bo.away_win END) / 
                   ((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100 AS NUMERIC), 2) AS upset_prob_percent
            FROM Match m, Team t1, Team t2, Betting_Odds bo
            WHERE m.home_team_api_id = t1.team_api_id AND m.away_team_api_id = t2.team_api_id AND m.match_api_id = bo.match_api_id
              AND ((m.home_team_goal > m.away_team_goal AND bo.home_win > bo.away_win) OR (m.away_team_goal > m.home_team_goal AND bo.away_win > bo.home_win))
              AND ABS(m.home_team_goal - m.away_team_goal) >= 3
            ORDER BY upset_prob_percent ASC LIMIT 10;
        """
        execute_and_print(query, title="Biggest Statistical Upsets (Based on Betting Odds)")

    elif choice == "3":
        query = """
            SELECT m.season, t1.team_long_name AS home, t2.team_long_name AS away, bo.bookmaker,
                   ROUND(CAST(((1.0 / bo.home_win) + (1.0 / bo.draw) + (1.0 / bo.away_win)) * 100 AS NUMERIC), 2) AS implied_probability
            FROM Betting_Odds bo, Match m, Team t1, Team t2
            WHERE bo.match_api_id = m.match_api_id AND m.home_team_api_id = t1.team_api_id AND m.away_team_api_id = t2.team_api_id
              AND bo.home_win > 0 AND bo.draw > 0 AND bo.away_win > 0
            ORDER BY implied_probability ASC LIMIT 10;
        """
        execute_and_print(query, title="Most Favorable Bookmaker Margins (Closest to 100%)")

def search_player_profile():
    console.print("\n[bold cyan]--- Player Profile Search ---[/bold cyan]")
    search_name = Prompt.ask("Enter Player Name (e.g., 'Messi')")

    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.execute("SELECT DISTINCT player_id, player_name FROM Player WHERE player_name ILIKE %s ORDER BY player_name LIMIT 15;", (f"%{search_name}%",))
        matches = pg_cursor.fetchall()
    except psycopg2.Error as e:
        console.print(f"[bold red]Database Error: {e}[/bold red]")
        return
    finally:
        pg_cursor.close()
        pg_conn.close()

    if not matches:
        console.print(f"[yellow]No players found matching '{search_name}'.[/yellow]")
        return
    elif len(matches) == 1:
        exact_id, exact_name = matches[0]
    else:
        console.print("\n[bold yellow]Multiple players found. Please select one:[/bold yellow]")
        for i, (p_id, name) in enumerate(matches, 1):
            console.print(f"[{i}] {name} (ID: {p_id})")
        console.print(f"[{len(matches)+1}] Cancel")
        
        choice = Prompt.ask("Select", choices=[str(i) for i in range(1, len(matches) + 2)])
        if choice == str(len(matches) + 1): return
        exact_id, exact_name = matches[int(choice) - 1]

    query_seasons = "SELECT season, appearances, goals, cards FROM mv_player_summary WHERE player_id = %s ORDER BY season;"
    query_totals = "SELECT SUM(appearances) AS career_appearances, SUM(goals) AS career_goals, SUM(cards) AS career_cards FROM mv_player_summary WHERE player_id = %s;"
    
    execute_and_print(query_seasons, (exact_id,), title=f"Season Stats: {exact_name} (ID: {exact_id})")
    execute_and_print(query_totals, (exact_id,), title=f"Career Totals: {exact_name} (ID: {exact_id})")

def search_team_profile():
    console.print("\n[bold cyan]--- Team Profile Search ---[/bold cyan]")
    search_name = Prompt.ask("Enter Team Name (e.g., 'Arsenal')")

    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.execute("SELECT DISTINCT team_api_id, team_long_name FROM Team WHERE team_long_name ILIKE %s ORDER BY team_long_name LIMIT 15;", (f"%{search_name}%",))
        matches = pg_cursor.fetchall()
    except psycopg2.Error as e:
        console.print(f"[bold red]Database Error: {e}[/bold red]")
        return
    finally:
        pg_cursor.close()
        pg_conn.close()

    if not matches:
        console.print(f"[yellow]No teams found matching '{search_name}'.[/yellow]")
        return
    elif len(matches) == 1:
        exact_id, exact_name = matches[0]
    else:
        console.print("\n[bold yellow]Multiple teams found. Please select one:[/bold yellow]")
        for i, (t_id, name) in enumerate(matches, 1):
            console.print(f"[{i}] {name} (ID: {t_id})")
        console.print(f"[{len(matches)+1}] Cancel")
        
        choice = Prompt.ask("Select", choices=[str(i) for i in range(1, len(matches) + 2)])
        if choice == str(len(matches) + 1): return
        exact_id, exact_name = matches[int(choice) - 1]

    query_seasons = "SELECT season, wins, draws, losses, points, final_placement FROM mv_team_summary WHERE team_long_name = %s ORDER BY season;"
    query_totals = "SELECT SUM(wins) AS all_time_wins, SUM(draws) AS all_time_draws, SUM(losses) AS all_time_losses, SUM(points) AS all_time_points, COUNT(CASE WHEN final_placement = 1 THEN 1 END) AS total_championships FROM mv_team_summary WHERE team_long_name = %s;"
    
    execute_and_print(query_seasons, (exact_name,), title=f"Season Stats: {exact_name} (ID: {exact_id})")
    execute_and_print(query_totals, (exact_name,), title=f"All-Time Totals: {exact_name} (ID: {exact_id})")

def search_match():
    console.print("\n[bold cyan]--- Match Explorer ---[/bold cyan]")
    for k, v in SEASONS.items(): console.print(f"[{k}] {v}")
    season_id = Prompt.ask("Select Season", choices=list(SEASONS.keys()))
    season_val = SEASONS[season_id]

    home_name = Prompt.ask("Enter Home Team Name (or part of it)")
    away_name = Prompt.ask("Enter Away Team Name (or part of it)")

    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()

    try:
        query = """
            SELECT m.match_api_id, m.date, th.team_long_name, ta.team_long_name, m.home_team_goal, m.away_team_goal
            FROM Match m
            JOIN Team th ON m.home_team_api_id = th.team_api_id
            JOIN Team ta ON m.away_team_api_id = ta.team_api_id
            WHERE m.season = %s AND th.team_long_name ILIKE %s AND ta.team_long_name ILIKE %s
            ORDER BY m.date;
        """
        pg_cursor.execute(query, (season_val, f"%{home_name}%", f"%{away_name}%"))
        matches = pg_cursor.fetchall()

        if not matches:
            console.print("[yellow]No matches found for these teams in this season.[/yellow]")
            return

        console.print("\n[bold yellow]Select a match to view details:[/bold yellow]")
        for i, m in enumerate(matches, 1):
            console.print(f"[{i}] {m[1]} | {m[2]} {m[4]} - {m[5]} {m[3]} (Match ID: {m[0]})")
        console.print(f"[{len(matches)+1}] Cancel")

        choice = Prompt.ask("Select", choices=[str(i) for i in range(1, len(matches) + 2)])
        if choice == str(len(matches) + 1): return

        selected_match_id = matches[int(choice)-1][0]
        title_str = f"Match ID: {selected_match_id} | {matches[int(choice)-1][2]} vs {matches[int(choice)-1][3]}"

        execute_and_print("SELECT bookmaker, home_win, draw, away_win FROM Betting_Odds WHERE match_api_id = %s", (selected_match_id,), title=f"Betting Odds - {title_str}")
        
        event_query = """
            SELECT me.minute, me.event_type, p.player_name
            FROM Match_Event me
            JOIN Player p ON me.player_id = p.player_id
            WHERE me.match_api_id = %s
            ORDER BY me.minute;
        """
        execute_and_print(event_query, (selected_match_id,), title=f"Match Events - {title_str}")

    except psycopg2.Error as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def find_info_menu():
    while True:
        console.print("\n[bold cyan]--- Find Information ---[/bold cyan]")
        console.print("[1] Search Player Profile (Career & Season Stats)")
        console.print("[2] Search Team Profile (Standings & Match Records)")
        console.print("[3] Visualisation Engine (Distributions, Heatmaps, Trends)")
        console.print("[4] Player Analytics (Goals, Cards, Apps)")
        console.print("[5] Team Analytics (League Champions)")
        console.print("[6] Match & Betting Analytics (Upsets, Arbitrage)")
        console.print("[7] Search Specific Match Details")
        console.print("[8] Back to Main Menu")
        
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6", "7", "8"])
        if choice == "1": search_player_profile()
        elif choice == "2": search_team_profile()
        elif choice == "3": visualize_data_menu()
        elif choice == "4": dynamic_player_analytics()
        elif choice == "5": dynamic_team_analytics()
        elif choice == "6": match_and_betting_analytics()
        elif choice == "7": search_match()
        elif choice == "8": break



# --- DATABASE MANAGEMENT (FULL CRUD) ---
# --- CREATE ---
def crud_add_player():
    console.print("\n[bold green]--- Add New Player ---[/bold green]")
    try:
        p_id = int(Prompt.ask("Enter New Player ID (e.g., 999999)"))
        p_name = Prompt.ask("Enter Player Name")
        height = float(Prompt.ask("Enter Height (cm)"))
        weight = int(Prompt.ask("Enter Weight (kg)"))
        
        pg_conn = get_pg_connection()
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("INSERT INTO Player (player_id, player_name, height, weight) VALUES (%s, %s, %s, %s);", (p_id, p_name, height, weight))
        pg_conn.commit()
        console.print(f"[bold green][SUCCESS] Player '{p_name}' successfully added.[/bold green]")
    except Exception as e:
        console.print(f"[bold red][ERROR] {e}[/bold red]")
    finally:
        if 'pg_conn' in locals(): pg_conn.close()

def crud_add_team():
    console.print("\n[bold green]--- Add New Team ---[/bold green]")
    try:
        t_id = int(Prompt.ask("Enter New Team API ID (e.g., 999999)"))
        long_name = Prompt.ask("Enter Team Long Name")
        short_name = Prompt.ask("Enter Team Short Name (e.g., 'MUN')")
        
        pg_conn = get_pg_connection()
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("INSERT INTO Team (team_api_id, team_long_name, team_short_name) VALUES (%s, %s, %s);", (t_id, long_name, short_name))
        pg_conn.commit()
        console.print(f"[bold green][SUCCESS] Team '{long_name}' successfully added.[/bold green]")
    except Exception as e:
        console.print(f"[bold red][ERROR] {e}[/bold red]")
    finally:
        if 'pg_conn' in locals(): pg_conn.close()

def crud_add_match_csv():
    console.print("\n[bold green]--- Relational Match Importer (Strict DDL) ---[/bold green]")
    filepath = Prompt.ask("Enter CSV filepath", default="data/real_vs_barca.csv")
    
    if not os.path.exists(filepath):
        console.print(f"[red]File '{filepath}' not found.[/red]")
        return
        
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        with open(filepath, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            
            with console.status("[yellow]Processing relational records...[/yellow]"):
                for row in reader:
                    if not row: continue
                    entity = row[0].strip().upper()
                    
                    if entity == "MATCH":
                        query = "INSERT INTO Match (match_api_id, league_id, season, date, stage, home_team_api_id, away_team_api_id, home_team_goal, away_team_goal) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"
                        pg_cursor.execute(query, tuple(row[1:10]))
                    elif entity == "APPEARANCE":
                        query = "INSERT INTO Appearance (match_api_id, player_id, is_home_team, X_coordinate, Y_coordinate) VALUES (%s, %s, %s, %s, %s);"
                        pg_cursor.execute(query, tuple(row[1:6]))
                    elif entity == "EVENT":
                        query = "INSERT INTO Match_Event (match_api_id, event_id, player_id, minute, event_type) VALUES (%s, %s, %s, %s, %s);"
                        pg_cursor.execute(query, tuple(row[1:6]))
                        
        pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_team_summary;")
        pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_player_summary;")
        pg_conn.commit()
        console.print(f"[bold green][SUCCESS] Complete match record imported from {filepath}.[/bold green]")
        
    except psycopg2.Error as e:
        pg_conn.rollback()
        console.print(f"\n[bold red][SQL Constraint Violation][/bold red] {e}")
        console.print("[yellow]Hint: The database engine may have rejected the CSV because a Team ID or Player ID inside it does not exist in the database yet. You must create them first![/yellow]")
    except Exception as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR][/bold red] {e}")
    finally:
        pg_cursor.close()
        pg_conn.close()

def crud_update_entity():
    console.print("\n[bold yellow]--- Update Entity ---[/bold yellow]")
    choice = Prompt.ask("Update: [1] Player Stats [2] Team Name", choices=["1", "2"])
    
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    try:
        if choice == "1":
            p_id = int(Prompt.ask("Enter exact Player ID"))
            height = float(Prompt.ask("Enter New Height (cm)"))
            weight = int(Prompt.ask("Enter New Weight (kg)"))
            pg_cursor.execute("UPDATE Player SET height = %s, weight = %s WHERE player_id = %s;", (height, weight, p_id))
        else:
            t_id = int(Prompt.ask("Enter exact Team API ID"))
            new_name = Prompt.ask("Enter New Team Long Name")
            pg_cursor.execute("UPDATE Team SET team_long_name = %s WHERE team_api_id = %s;", (new_name, t_id))
            
        if pg_cursor.rowcount == 0:
            console.print("[yellow]Record not found. Use the Search function to find exact IDs.[/yellow]")
        else:
            pg_conn.commit()
            console.print("[bold green][SUCCESS] Record updated successfully![/bold green]")
    except Exception as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR] {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

# --- DELETE ---
def crud_delete_entity():
    console.print("\n[bold red]--- Delete Entity (Nuclear CASCADE) ---[/bold red]")
    console.print("[dim]WARNING: Deleting a Team or Player will wipe all their historical appearances and events![/dim]")
    choice = Prompt.ask("Delete: [1] Player [2] Team [3] Match", choices=["1", "2", "3"])
    
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    
    try:
        if choice == "1":
            p_id = int(Prompt.ask("Enter Player ID to delete"))
            query = "DELETE FROM Player WHERE player_id = %s;"
            target = p_id
        elif choice == "2":
            t_id = int(Prompt.ask("Enter Team API ID to delete"))
            query = "DELETE FROM Team WHERE team_api_id = %s;"
            target = t_id
        else:
            m_id = int(Prompt.ask("Enter Match API ID to delete"))
            query = "DELETE FROM Match WHERE match_api_id = %s;"
            target = m_id
            
        confirm = Prompt.ask(f"[bold red]Type 'YES' to permanently delete ID {target} and all associated data[/bold red]")
        if confirm == 'YES':
            with console.status("[red]Executing cascading deletion...[/red]"):
                pg_cursor.execute(query, (target,))
                if pg_cursor.rowcount == 0:
                    console.print("[yellow]Record not found.[/yellow]")
                else:
                    pg_conn.commit()               
                    pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_team_summary;")
                    pg_cursor.execute("REFRESH MATERIALIZED VIEW mv_player_summary;")
                    pg_conn.commit()                 
                    console.print("[bold green][SUCCESS] Record deleted and dashboards re-synchronized.[/bold green]")
        else:
            console.print("[yellow]Deletion aborted.[/yellow]")
    except Exception as e:
        pg_conn.rollback()
        console.print(f"[bold red][ERROR] {e}[/bold red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def data_management_menu():
    while True:
        console.print("\n[bold magenta]--- Database Management (Full CRUD) ---[/bold magenta]")
        console.print("[1] Create: Add Player")
        console.print("[2] Create: Add Team")
        console.print("[3] Create: Import Match via CSV")
        console.print("[4] Update: Modify Player or Team")
        console.print("[5] Delete: Remove Player, Team, or Match (CASCADE)")
        console.print("[6] Back to Main Menu")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"])
        if choice == "1": crud_add_player()
        elif choice == "2": crud_add_team()
        elif choice == "3": crud_add_match_csv()
        elif choice == "4": crud_update_entity()
        elif choice == "5": crud_delete_entity()
        elif choice == "6": break
# =====================================================================
# 3. ADVANCED SETTINGS (ADMIN)
# =====================================================================
def get_psql_command():
    """Auto-discovers the psql executable path regardless of the user's OS."""
    # 1. Check if psql is already in the system PATH (Standard for Linux/Mac and well-configured Windows)
    if shutil.which("psql"):
        return "psql"
        
    # 2. Auto-scan standard Windows installation paths if missing from PATH
    if platform.system() == "Windows":
        base_path = r"C:\Program Files\PostgreSQL"
        if os.path.exists(base_path):
            # Sort versions descending (e.g., 16, 15, 14) to find the newest installed version
            versions = sorted(os.listdir(base_path), reverse=True)
            for v in versions:
                potential_path = os.path.join(base_path, v, "bin", "psql.exe")
                if os.path.exists(potential_path):
                    return f'"{potential_path}"' # Wrap in quotes to handle spaces in file path
                    
    # 3. Auto-scan standard macOS Enterprise DB paths
    elif platform.system() == "Darwin":
        mac_paths = [
            "/Library/PostgreSQL/15/bin/psql",
            "/Library/PostgreSQL/14/bin/psql",
            "/usr/local/opt/libpq/bin/psql"
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path

    return None

def run_academic_demos():
    console.print("\n[bold magenta]--- Academic Script Execution ---[/bold magenta]")
    console.print("[1] Run 03_analytics_test.sql (7 Complex Analytics Queries)")
    console.print("[2] Run 04_indexes.sql (B-Tree & Materialized View Optimization)")
    console.print("[3] Cancel")
    
    choice = Prompt.ask("Select Script", choices=["1", "2", "3"])
    if choice == "3":
        return
        
    script_path = "sql/03_analytics_test.sql" if choice == "1" else "sql/04_indexes.sql"
    
    # Run the auto-discovery engine
    psql_cmd = get_psql_command()
    
    if not psql_cmd:
        console.print("\n[bold red][ERROR] 'psql' could not be found on this computer.[/bold red]")
        console.print("Please ensure PostgreSQL command line tools are installed.")
        return

    console.print(f"\n[yellow]Executing {script_path} via auto-discovered psql...[/yellow]")
    console.print("[dim]Note: This may prompt for your PostgreSQL user password.[/dim]\n")
    
    try:
        # Assuming standard 'postgres' user and 'footstats' database for academic grading
        cmd = f'{psql_cmd} -U postgres -d footstats -f {script_path}'
        exit_code = os.system(cmd)
        
        if exit_code == 0:
            console.print(f"\n[bold green][SUCCESS] {script_path} executed.[/bold green]")
            if choice == "2":
                console.print("[bold cyan]Check the generated 'log.txt' file in your root folder for the EXPLAIN ANALYZE trees![/bold cyan]")
        else:
            console.print(f"\n[bold red][ERROR] Command failed with exit code {exit_code}.[/bold red]")
            
    except Exception as e:
        console.print(f"[bold red]Execution failed: {e}[/bold red]")

def execute_custom_sql():
    console.print("[dim]Note: This option allows direct SQL execution for administration purposes.[/dim]")
    query = Prompt.ask("\n[bold cyan]SQL[/bold cyan] (Type 'cancel' to exit)")
    if query.strip().lower() != 'cancel':
        execute_and_print(query)

def check_db_health():
    tables = ['Country', 'League', 'Team', 'Player', 'Match', 'Appearance', 'Match_Event', 'Betting_Odds']
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()
    table_ui = Table(title="Database Health Check", style="cyan")
    table_ui.add_column("Table Name", style="magenta"); table_ui.add_column("Row Count", style="green", justify="right")
    try:
        for table in tables:
            pg_cursor.execute(f"SELECT COUNT(*) FROM {table};")
            table_ui.add_row(table, f"{pg_cursor.fetchone()[0]:,}")
        console.print(table_ui)
    except psycopg2.Error:
        console.print("[red]Database not initialized.[/red]")
    finally:
        pg_cursor.close()
        pg_conn.close()

def advanced_settings_menu():
    while True:
        console.print("\n[bold red]--- Advanced Settings ---[/bold red]")
        console.print("[1] Run Academic Query Demos (Performance Showcase)")
        console.print("[2] Execute Custom Raw SQL")
        console.print("[3] Database Health Check")
        console.print("[4] Start Fresh (Wipe Database & Re-ingest)")
        console.print("[5] Back to Main Menu")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"])
        if choice == "1": run_academic_demos()
        elif choice == "2": execute_custom_sql()
        elif choice == "3": check_db_health()
        elif choice == "4": start_fresh()
        elif choice == "5": break

# =====================================================================
# MAIN MENU
# =====================================================================
def main():
    display_intro()
    while True:
        menu_text = (
            "[1] Getting Started (Run Ingestion)\n"
            "[2] Find Information (Explore Database)\n"
            "[3] Database Management (Full CRUD Operations)\n"
            "[4] Advanced Settings (Admin & Defense Demos)\n"
            "[5] Exit"
        )
        console.print(Panel(menu_text, title="[bold cyan] FootStats Analytics Dashboard[/bold cyan]", expand=False))
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])
        
        if choice == '1': ingest_data()
        elif choice == '2': find_info_menu()
        elif choice == '3': data_management_menu()
        elif choice == '4': advanced_settings_menu()
        elif choice == '5':
            console.print("[bold green]Exiting application. Goodbye![/bold green]")
            sys.exit(0)


if __name__ == "__main__":
    main()