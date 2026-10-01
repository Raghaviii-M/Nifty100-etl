import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]      # project root
DB_PATH = ROOT / "nifty100.db"                  # <-- CHANGE to your real .db file


def load(table):
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql(f"SELECT * FROM {table}", con)


def year_num(s):
    """Turns 'Mar 2024', '2024-03-31' or 2024 into the number 2024."""
    return pd.to_numeric(s.astype(str).str.extract(r"(\d{4})")[0], errors="coerce")


# new_name: [possible real column names]  <-- edit lists to match YOUR schema
MAPS = {
    "profitandloss": {"sales": ["sales"], "op_profit": ["operating_profit"],
                      "opm": ["opm_percentage"], "interest": ["interest"],
                      "net_profit": ["net_profit"], "eps": ["eps", "eps_in_rs"],
                      "payout": ["dividend_payout", "dividend_payout_pct"]},
    "balancesheet": {"equity_capital": ["equity_capital"], "reserves": ["reserves"],
                     "borrowings": ["borrowings"], "other_liabilities": ["other_liabilities"],
                     "total_assets": ["total_assets", "total_liabilities"]},
    "cashflow": {"cfo": ["operating_activity"], "cfi": ["investing_activity"],
                 "cff": ["financing_activity"], "net_cf": ["net_cash_flow"]},
    "financial_ratios": {"roe": ["return_on_equity_pct", "roe"],
                         "roce": ["return_on_capital_employed_pct", "roce_pct", "roce"]},
    "market_cap": {"div_yield": ["dividend_yield_pct"]},
}


def build_master():
    parts = []
    for table, mapping in MAPS.items():
        df = load(table)
        out = pd.DataFrame({"company_id": df["company_id"], "yr": year_num(df["year"])})
        for new, candidates in mapping.items():
            src = next((c for c in candidates if c in df.columns), None)
            if src is None:
                print(f"[warn] {table}: none of {candidates} found -> '{new}' will be empty")
                out[new] = np.nan
            else:
                out[new] = pd.to_numeric(df[src], errors="coerce")
        parts.append(out.drop_duplicates(["company_id", "yr"]))
    m = parts[0]
    for p in parts[1:]:
        m = m.merge(p, on=["company_id", "yr"], how="left")
    m = m.dropna(subset=["yr"]).sort_values(["company_id", "yr"]).reset_index(drop=True)
    m["equity"] = m.equity_capital + m.reserves
    m["de"] = m.borrowings / m.equity.replace(0, np.nan)
    m["icr"] = m.op_profit / m.interest.replace(0, np.nan)
    m["fcf"] = m.cfo + m.cfi
    return m


def company_info():
    """company_id, company_name, broad_sector (assumes companies.id is the ticker)."""
    c = load("companies").rename(columns={"id": "company_id"})
    s = load("sectors")
    return c[["company_id", "company_name"]].merge(
        s[["company_id", "broad_sector"]], on="company_id", how="left")


def is_financial(sector):
    return any(k in str(sector).lower() for k in ("bank", "financ", "nbfc", "insurance"))


def cagr(series, years):
    s = series.dropna()
    if len(s) <= years:
        return np.nan
    start, end = s.iloc[-(years + 1)], s.iloc[-1]
    if start <= 0 or end <= 0:
        return np.nan
    return ((end / start) ** (1 / years) - 1) * 100