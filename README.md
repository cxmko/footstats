# FootStats: European Soccer Database Architecture

**Author:** Cameron Mouangue, Jacques Guicheney  
**Program:** M1 Applied Mathematics and Statistics, Institut Polytechnique de Paris  

---

## Project Overview
FootStats is a comprehensive relational database application and command-line dashboard designed to process, store, and analyze large-scale European soccer data. Built on PostgreSQL v15, the application manages a fully normalized dataset containing over 25,000 matches, 10,000 players, and 1.2 million granular events (goals, cards, lineups) across 11 top-tier European countries.

This guide details how to install, configure, and operate the FootStats CLI Dashboard.

---

## Prerequisites & Data Setup

Due to file size constraints, the raw Kaggle dataset is not included in this repository. You must download it before running the ingestion pipeline.

1. **Download the Data:** Download the "European Soccer Database" from Kaggle: https://www.kaggle.com/datasets/hugomathien/soccer
2. **Extract:** Extract the downloaded archive.
3. **Position the File:** Locate the `database.sqlite` file and place it inside the `data/` directory at the root of this project (resulting path: `data/database.sqlite`).

### Database Configuration
Before running the application, configure your PostgreSQL connection credentials.

1. Open your PostgreSQL client (e.g., pgAdmin or psql) and **create a completely blank database** named `footstats`.
2. Open `app/db_config.py` in a text editor.
3. Update the variables to match your local PostgreSQL credentials:
```python
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "footstats" # Ensure this blank database is created on your server!
PG_USER = "postgres" # Change if using a different user
PG_PASS = "your_password_here" # Update this to your local password
```

---

## How to Launch the Dashboard

1. **Install Dependencies:** Ensure Python 3 is installed, then run the following command in your terminal from the root directory:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Application:** Launch the dashboard by running the execution script matching your Operating System:
   * **Windows:** Double-click `run_windows.bat`
   * **macOS / Linux:** Run `bash run_mac.sh` in your terminal.
   * *(Alternatively, you can launch it manually via: `python app/main.py`)*

---

## Feature Guide: Using the Application

The CLI Dashboard is divided into four main operational modules.

### [1] The "Day 1" Automated Deployment (Getting Started)
You do **not** need to manually run SQL scripts to build the tables. 
Upon launching the app for the first time, select **[1] Getting Started**. The application's ETL pipeline is fully autonomous:
* It detects that the database is blank.
* It automatically reads and executes `01_schema.sql` and `02_triggers.sql` to construct the strict DDL relational architecture.
* It parses the Kaggle files, extracts XML blobs, and loads 1.2 million rows into the PostgreSQL tables.
* It synchronizes the Materialized Views for instant analytical querying.

### [2] Find Information (Exploration & Analytics)
This module acts as the read-only analytics engine, powered by optimized B-Tree indexes and Pre-Computed Materialized Views.
* **Profile Search (Player & Team):** Features a smart disambiguation search engine. Look up any player or team to instantly view their season-by-season performance, career aggregations, and league placements.
* **Visualisation Engine:**
  * *Global Distributions:* Bar charts of match volume across European leagues.
  * *Odds Evolution:* Trend lines of Bookmaker confidence over time.
  * *2D Pitch Heatmap:* Dynamically plots a matrix visualizing a specific player's spatial coordinates (e.g., Central Axis vs. Wings) based on their historical match appearances.
* **Macro-Analytics:** Run complex queries to find Top Goalscorers, League Champions, or identify the "Biggest Statistical Upsets" using historical bookmaker arbitrage margins.
* **Match Explorer:** Filter by season and team names to isolate a specific match, allowing you to drill down into the exact minute-by-minute events (goals, cards) and betting odds for that game.

### [3] Database Management (Full CRUD Operations)
A strict, UI-driven data entry module that allows you to safely alter the database while respecting 3NF referential integrity.
* **Create:** Add custom players or teams directly to the database.
* **Relational CSV Importer:** Upload bulk match data (e.g., `data/real_vs_barca.csv`). The pipeline strictly inserts into `Match`, then `Appearance`, and finally `Match_Event` to ensure Foreign Key constraints are never violated.
* **Update:** Modify existing player physical stats or correct team names.
* **Deletion (Cascade):** Delete a specific Match, Player, or Team. Demonstrates the power of `ON DELETE CASCADE` by safely hunting down and erasing all associated weak entities (appearances, goals) without leaving orphan records. Automatically re-synchronizes analytics dashboards post-deletion.

### [4] Advanced Settings (Admin & Defense Demos)
Built for database administrators and academic review.
* **Run Academic Demos:** Automatically executes `04_indexes.sql` inside a temporary sandbox. It benchmarks complex queries (Player Dependency, Hat-Tricks), drops indexes, and routes the physical `EXPLAIN ANALYZE` execution plans to a `log.txt` file for performance review.
* **Execute Custom Raw SQL:** A terminal prompt to run standard SQL commands directly against the database.
* **Database Health Check:** Scans and outputs the current row counts for all active tables.
* **Start Fresh:** Executes a `TRUNCATE CASCADE` command to safely wipe all 1.2 million rows of data while preserving the schema architecture, to redo a fresh ingestion.

---

## Hard Factory Reset (Optional)
If you ever need to completely wipe the project's structural architecture (tables, views, triggers, and data) to start over, you can execute the `sql/00_reset_data.sql` script in your PostgreSQL client. This drops the entire `public` schema. 

Because the Python application is self-healing, simply running **[1] Getting Started** in the CLI afterward will seamlessly rebuild the entire database architecture from scratch.