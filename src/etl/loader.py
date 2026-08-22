"""
Excel loader for the Nifty100 ETL pipeline.

Confirmed against the real files:
  - The 7 CORE files (companies, profitandloss, balancesheet, cashflow,
    analysis, documents, prosandcons) have a title row at row 0
    ("Bluestock Fintech — Nifty 100 | ... | N records") -> use header=1.
  - The 5 SUPPORTING files (sectors, stock_prices, market_cap,
    financial_ratios, peer_groups) are already clean -> use header=0.
"""
import pandas as pd
from pathlib import Path

CORE_FILES = [
    "companies", "profitandloss", "balancesheet", "cashflow",
    "analysis", "documents", "prosandcons",
]
SUPPORTING_FILES = [
    "sectors", "stock_prices", "market_cap", "financial_ratios", "peer_groups",
]


def load_core_file(raw_dir: Path, name: str) -> pd.DataFrame:
    path = raw_dir / f"{name}.xlsx"
    df = pd.read_excel(path, header=1, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_supporting_file(supp_dir: Path, name: str) -> pd.DataFrame:
    path = supp_dir / f"{name}.xlsx"
    df = pd.read_excel(path, header=0, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_all(raw_dir: str = "data/raw", supp_dir: str = "data/supporting") -> dict:
    raw_dir, supp_dir = Path(raw_dir), Path(supp_dir)
    tables = {}
    for name in CORE_FILES:
        tables[name] = load_core_file(raw_dir, name)
    for name in SUPPORTING_FILES:
        tables[name] = load_supporting_file(supp_dir, name)
    return tables


if __name__ == "__main__":
    tables = load_all()
    for name, df in tables.items():
        print(f"{name:18} rows={len(df):6}  cols={list(df.columns)}")
