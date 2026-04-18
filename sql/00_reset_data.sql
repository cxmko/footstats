-- sql/00_reset_data.sql
-- Instantly vaporizes the entire schema (tables, views, triggers, and all data).
-- The Python application's ETL pipeline is designed to detect this empty state
-- and will automatically rebuild the architecture from scratch upon next launch.

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;