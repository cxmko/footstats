# app/db_config.py
import sqlite3
import psycopg2

SQLITE_PATH = 'data/database.sqlite'
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "footstats"
PG_USER = "postgres"
PG_PASS = "1234" 

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_PATH)

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS
    )