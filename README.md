# FootStats: European Soccer Database Project ⚽

get dataset here : https://www.kaggle.com/datasets/hugomathien/soccer/data
---

## 📊 Project Status Update

Here is a quick breakdown of what has been implemented so far and what is blocking us for the final phases. 

### ✅ Done: Phases 1 & 2 (Modeling & DDL)
* **Conceptual Design:** We have a clean, normalized ER Diagram (Course Style) that breaks down the massive Kaggle dataset into 4 core tables and several weak entities/relationships (like `Appearance` and `Betting_Odds`). 
* **Database Setup:** The PostgreSQL v15 database (`footstats`) is live. 
* **DDL Scripts:** `sql/01_schema.sql` successfully builds all the tables with proper primary/foreign key constraints.
* **Triggers:** `sql/02_triggers.sql` is active. It automatically updates a team's `total_points` whenever a match result is inserted.

### 🚧 WIP: Phases 3 & 4 (Ingestion & Analytics)
Currently, `app/main.py` (Data Ingestion) and the analytics/optimization SQL scripts are heavily WIP. 

**The Bottleneck:** The raw Kaggle SQLite file is a normalization nightmare. The `Match` table has 115 columns, including repeating variables for X/Y coordinates of lineups (`home_player_X1` to `X11`), and the event data (goals, cards, fouls) is trapped in massive raw XML blobs. 

### 🎯 Next Steps & Game Plan
To hit the course requirements for complex queries and optimization, we need heavy data. Here is the plan:

1. **The ETL Push (Phase 3):** We need to update our Python ingestion script to actively unpivot those lineup and betting columns into our `Appearance` and `Betting_Odds` tables. 
2. **Brute-Force the XML:** If we want the really cool statistical queries (like late-game clutch factors), we might have to brute-force parse the XML blobs in Python to populate the `Match_Event` table. 
3. **The Analytics (Phase 4):** Once populated, we will throw 7 computationally demanding queries at the database in `sql/03_analytics.sql` (e.g., spatial impact analysis, betting arbitrages).
4. **The B+Tree Optimization:** We will run `\timing on` to profile all queries, identify the **top 3 slowest ones** (the sequential scan offenders), and build targeted B+Tree indexes in `sql/04_indexes.sql` to drastically cut their execution time. 

**⚠️ Backup Plan:** If we decide parsing the XML and unpivoting the arrays is too time-consuming, we will have to abandon the `Appearance`, `Betting_Odds`, and `Match_Event` tables. However, this means we **must redraw the ER Diagram** to reflect a simpler model and rely on basic team-level analytics. Let's discuss.

---

## 📂 Repository Structure
* `sql/` : Raw SQL files (`01_schema.sql`, `02_triggers.sql`, `03_analytics.sql`, `04_indexes.sql`).
* `app/` : Python application for ETL and user interface.
* `data/` : Data.
