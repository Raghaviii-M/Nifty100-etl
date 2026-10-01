import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "nifty100.db"

# ====== EDIT THIS BLOCK USING schema_dump.txt ======
ID_COL, YEAR_COL = "company_id", "year"       # same names in all tables
COMPANY_TABLE = "companies"
# ====== DATABASE SCHEMA MAPPING ======

ID_COL, YEAR_COL = "company_id", "year"

COMPANY_TABLE = "companies"

# companies table uses "id" as the company identifier.
# sector information comes from the sectors table.
COMPANY_COLS = {
    "company_id": "id",
    "company_name": "company_name",
}

# standard_name: (table, real_column_name)
COLMAP = {
    "sales":            ("profitandloss", "sales"),
    "operating_profit": ("profitandloss", "operating_profit"),
    "opm":              ("profitandloss", "opm_percentage"),
    "net_profit":       ("profitandloss", "net_profit"),
    "eps":              ("profitandloss", "eps"),
    "dividend_payout":  ("profitandloss", "dividend_payout"),
    "interest":         ("profitandloss", "interest"),

    "equity":           ("balancesheet", "equity_capital"),
    "borrowings":       ("balancesheet", "borrowings"),
    "other_liab":       ("balancesheet", "other_liabilities"),
    "total_assets":     ("balancesheet", "total_assets"),

    "cfo":              ("cashflow", "operating_activity"),
    "cfi":              ("cashflow", "investing_activity"),
    "cff":              ("cashflow", "financing_activity"),

    "roe":              ("financial_ratios", "return_on_equity_pct"),
    "roce":             ("financial_ratios", "roce_pct"),
    "de":               ("financial_ratios", "debt_to_equity"),
    "icr":              ("financial_ratios", "interest_coverage"),

    # Dividend yield comes from market_cap, not financial_ratios
    "div_yield":        ("market_cap", "dividend_yield_pct"),
}

# ====================================================
# ====================================================

def get_conn():
    return sqlite3.connect(DB)

def read(sql):
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

def load_companies():
    companies = read("""
        SELECT
            id AS company_id,
            company_name
        FROM companies
    """)

    sectors = read("""
        SELECT
            company_id,
            broad_sector AS sector
        FROM sectors
    """)

    df = companies.merge(
        sectors,
        on="company_id",
        how="left"
    )

    return df[["company_id", "company_name", "sector"]]

def build_master():
    """One DataFrame: company_id, year + every standard column above."""
    by_table = {}
    for std, (tbl, col) in COLMAP.items():
        by_table.setdefault(tbl, {})[col] = std
    master = None
    for tbl, m in by_table.items():
        df = read(f"SELECT * FROM {tbl}").rename(columns={**m, ID_COL: "company_id", YEAR_COL: "year"})
        df["year"] = pd.to_numeric(
        df["year"].astype(str).str.extract(r"(\d{4})")[0],errors="coerce").astype("Int64")
        df = df[["company_id", "year", *m.values()]].drop_duplicates(["company_id", "year"])
        master = df if master is None else master.merge(df, on=["company_id", "year"], how="outer")
    return master.sort_values(["company_id", "year"]).reset_index(drop=True)

FIN_WORDS = ("bank", "financ", "insurance", "nbfc")
def is_financial(sector):
    return any(w in str(sector).lower() for w in FIN_WORDS)