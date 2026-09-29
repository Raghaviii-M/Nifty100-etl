"""
Sprint 4 — Day 26: Valuation module.

FCF yield, sector-relative overvaluation/discount flags, and the
valuation_summary.xlsx / valuation_flags.csv exports.
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT = ROOT / "output"


def load_valuation_universe(conn) -> pd.DataFrame:
    """Latest-year market_cap + latest-year financial_ratios (for FCF) + sector."""
    mc = pd.read_sql("SELECT * FROM market_cap", conn)
    latest_mc = mc.sort_values("year").groupby("company_id").last().reset_index()

    fr = pd.read_sql("SELECT company_id, year, free_cash_flow_cr FROM financial_ratios WHERE year != 'TTM'", conn)
    latest_fr = fr.sort_values("year").groupby("company_id").last().reset_index()

    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    comp = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)

    df = latest_mc.merge(latest_fr[["company_id", "free_cash_flow_cr"]], on="company_id", how="left")
    df = df.merge(sectors, on="company_id", how="left")
    df = df.merge(comp, on="company_id", how="left")
    return df


def compute_fcf_yield(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fcf_yield_pct"] = df.apply(
        lambda r: (r["free_cash_flow_cr"] / r["market_cap_crore"] * 100)
        if pd.notna(r["free_cash_flow_cr"]) and pd.notna(r["market_cap_crore"]) and r["market_cap_crore"] != 0
        else None,
        axis=1,
    )
    return df


def compute_5yr_median_pe(conn) -> pd.DataFrame:
    mc = pd.read_sql("SELECT company_id, pe_ratio FROM market_cap", conn)
    return mc.groupby("company_id")["pe_ratio"].median().reset_index().rename(
        columns={"pe_ratio": "5yr_median_pe"}
    )


def apply_valuation_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    sector_median_pe = df.groupby("broad_sector")["pe_ratio"].transform("median")
    df["sector_median_pe"] = sector_median_pe
    df["pe_vs_sector_median_pct"] = ((df["pe_ratio"] - df["sector_median_pe"]) / df["sector_median_pe"] * 100)

    def flag(row):
        if pd.isna(row["pe_ratio"]) or pd.isna(row["sector_median_pe"]) or row["sector_median_pe"] == 0:
            return "Fair"
        if row["pe_ratio"] > row["sector_median_pe"] * 1.5:
            return "Caution"
        if row["pe_ratio"] < row["sector_median_pe"] * 0.7:
            return "Discount"
        return "Fair"

    df["flag"] = df.apply(flag, axis=1)
    return df


def build_valuation_summary(conn) -> pd.DataFrame:
    df = load_valuation_universe(conn)
    df = compute_fcf_yield(df)
    median_pe_df = compute_5yr_median_pe(conn)
    df = df.merge(median_pe_df, on="company_id", how="left")
    df = apply_valuation_flags(df)

    return df[[
        "company_id", "company_name", "broad_sector",
        "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield_pct",
        "5yr_median_pe", "pe_vs_sector_median_pct", "flag",
    ]].rename(columns={"broad_sector": "sector", "pe_ratio": "P/E", "pb_ratio": "P/B", "ev_ebitda": "EV/EBITDA"})


def main():
    conn = sqlite3.connect(DB_PATH)
    summary = build_valuation_summary(conn)

    OUTPUT.mkdir(exist_ok=True)
    summary.to_excel(OUTPUT / "valuation_summary.xlsx", index=False)
    print(f"valuation_summary.xlsx written: {len(summary)} rows")

    flagged = summary[summary["flag"].isin(["Caution", "Discount"])]
    flagged.to_csv(OUTPUT / "valuation_flags.csv", index=False)
    print(f"valuation_flags.csv written: {len(flagged)} rows ({(flagged['flag']=='Caution').sum()} Caution, {(flagged['flag']=='Discount').sum()} Discount)")

    conn.close()
    return summary


if __name__ == "__main__":
    main()
