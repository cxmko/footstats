-- sql/00_reset_data.sql
-- Instantly vaporizes all data across all tables while preserving the schema and triggers.

TRUNCATE TABLE Country, League, Team, Player CASCADE;