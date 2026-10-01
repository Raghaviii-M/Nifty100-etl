import sqlite3
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 50)

conn = sqlite3.connect("db/nifty100.db")
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"]
print("=== DATABASE TABLES ===")
for t in tables:
    cols = pd.read_sql(f"PRAGMA table_info({t})", conn)["name"].tolist()
    n = pd.read_sql(f"SELECT COUNT(*) c FROM {t}", conn)["c"][0]
    print(f"{t} ({n} rows): {cols}")

print("\n=== analysis.xlsx ===")
a = pd.read_excel("data/raw/analysis.xlsx")
print(a.columns.tolist())
print(a.head(5).to_string())

print("\n=== capital_allocation.csv ===")
c = pd.read_csv("output/capital_allocation.csv")
print(c.columns.tolist())
print(c.head(5).to_string())

print("\n=== sample company rows ===")
print(pd.read_sql("SELECT * FROM companies LIMIT 3", conn).to_string())