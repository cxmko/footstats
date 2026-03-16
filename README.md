# FootStats: European Soccer Database Architecture

**Author:** Cameron Mouangue  
**Program:** M1 Applied Mathematics and Statistics, Institut Polytechnique de Paris  

---

## Project Overview
FootStats is a comprehensive relational database project designed to process, store, and analyze large-scale European soccer data. Built on PostgreSQL v15, the project encompasses the entire database lifecycle: from conceptual modeling and strict Data Definition Language (DDL) constraints to a custom Python ETL pipeline and advanced Data Warehousing optimization techniques.

## Implementation Phases

### Phase 1 & 2: Modeling and Schema Design
* **Conceptual Design:** The database follows a strictly normalized Entity-Relationship model, breaking down a denormalized Kaggle dataset into core reference tables (`Team`, `Player`, `Match`) and weak entities (`Appearance`, `Betting_Odds`, `Match_Event`).
* **DDL Implementation:** `sql/01_schema.sql` establishes the database schema with rigorous Primary Key and Foreign Key constraints to ensure referential integrity.
* **Active Database Elements:** `sql/02_triggers.sql` implements a PL/pgSQL function and trigger that automatically calculates and updates a team's `total_points` upon the insertion of match results.

### Phase 3: Modular ETL and Data Ingestion
* **Data Extraction & Transformation:** The Python application (`app/main.py`) handles the ingestion bottleneck of the raw dataset. It systematically unpivots extensive lineup arrays and parses complex XML blobs to extract granular match events (e.g., goals, fouls, cards).
* **Data Loading:** The pipeline cleanly ingests over 1.2 million rows into the 3NF PostgreSQL schema. 
* **CLI Interface:** A command-line interface allows users to initialize the database, execute custom SQL, verify table health, and perform a full `TRUNCATE CASCADE` teardown.

### Phase 4: Analytics and Database Optimization
* **Macro-Analytics:** `sql/03_analytics_test.sql` contains 7 computationally demanding analytical queries (e.g., Spatial Impact, Player Dependency, Hat-Trick Hunters). All queries strictly adhere to relational algebra paradigms, utilizing implicit Cartesian cross-product joins per course requirements.
* **OLTP Indexing:** Targeted composite and covering B-Tree indexes were built to optimize selective queries and standard lookups.
* **OLAP Optimization:** To overcome the inherent limitations of standard B-Trees on full-table aggregations, a Data Warehousing architecture was implemented in `sql/04_indexes.sql`. 
* **Pre-Computed Measures:** A generalized Fact Table (`mv_player_match_stats`) was built using a `MATERIALIZED VIEW`. Window Functions (`COUNT() OVER (PARTITION BY...)`) were integrated to shift heavy aggregations to creation time. 
* **Physical Disk Tuning:** The materialized view was physically clustered (`CLUSTER`) on disk and analyzed to guarantee optimal Query Planner routing, reducing execution times for macro-analytics from >1,000ms to <5ms.
* **Benchmarking:** Execution profiling is automated. The optimization script safely routes detailed `EXPLAIN ANALYZE` query plans to a dedicated `log.txt` file for architectural review.

---

## Repository Structure
* `sql/`
  * `01_schema.sql`: Table creation and integrity constraints.
  * `02_triggers.sql`: Automated point-calculation triggers.
  * `03_analytics_test.sql`: Formulated analytical queries.
  * `04_indexes.sql`: B-Tree indexing, Materialized Views, and benchmarking.
* `app/`
  * `main.py`: Modular ETL pipeline and CLI.
  * `db_config.py`: Database connection routing.
* `data/`
  * Source datasets (SQLite/CSV).
* `log.txt`
  * Automated diagnostic output containing physical query execution plans.