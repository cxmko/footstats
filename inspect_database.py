import sqlite3
import pandas as pd

# Connect to the Kaggle SQLite file
conn = sqlite3.connect('database.sqlite')

# Get all table names
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)

# Print every column for every table
with open('log.txt', 'w') as f:
    for table in tables['name']:
        f.write(f"\n--- {table} ---\n")
        columns = pd.read_sql(f"PRAGMA table_info({table});", conn)
        f.write(str(columns['name'].tolist()) + "\n")
