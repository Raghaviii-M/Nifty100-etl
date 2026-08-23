"""
Sprint 2 — Day 12: runs the full ratio engine for all 92 companies across
all available years, and writes results into the financial_ratios table.

The financial_ratios table from Sprint 1 held PRE-COMPUTED values loaded
straight from financial_ratios.xlsx. This script computes our own values
from the raw profitandloss/balancesheet/cashflow tables and replaces them —
which is what Sprint 2 actually asks for. The original pre-loaded values are
kept in a side table (financial_ratios_source) so Day 13 can cross-check
our numbers against them.
"""
import sys
import sqlite3
from pathlib import Path
import pandas as pd

sys.path.insert(0, "src")
from analytics import ratios as R
from analytics.cagr import cagr_for_window
from analytics import cashflow_kpis as CF

ROOT = Path(__file__).parent
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT = ROOT / "output"


def load_merged_data(conn):
    pl = pd.read_sql("SELECT * FROM profitandloss", conn)
    bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    companies = pd.read_sql("SELECT id AS company_id, face_value FROM companies", conn)

    merged = pl.merge(bs, on=["company_id", "year"], how="left", suffixes=("", "_bs"))
    merged = merged.merge(cf, on=["company_id", "year"], how="left", suffixes=("", "_cf"))
    merged = merged.merge(sectors, on="company_id", how="left")
    merged = merged.merge(companies, on="company_id", how="left")
    return merged, pl


def compute_row_ratios(row):
    row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    is_fin = row["broad_sector"] == "Financials"
    ebit = (row.get("operating_profit") or 0) - (row.get("depreciation") or 0)

    npm = R.net_profit_margin(row.get("net_profit"), row.get("sales"))
    opm = R.operating_profit_margin(row.get("operating_profit"), row.get("sales"))
    roe = R.return_on_equity(row.get("net_profit"), row.get("equity_capital"), row.get("reserves"))
    roce = R.return_on_capital_employed(ebit, row.get("equity_capital"), row.get("reserves"), row.get("borrowings"))
    roa = R.return_on_assets(row.get("net_profit"), row.get("total_assets"))

    de = R.debt_to_equity(row.get("borrowings"), row.get("equity_capital"), row.get("reserves"))
    lev_flag = R.high_leverage_flag(de, is_fin)
    icr = R.interest_coverage_ratio(row.get("operating_profit"), row.get("other_income"), row.get("interest"))
    icr_lbl = R.icr_label(icr, row.get("interest"))
    icr_risk = R.icr_risk_flag(icr)
    net_debt = R.net_debt(row.get("borrowings"), row.get("investments"))
    at = R.asset_turnover(row.get("sales"), row.get("total_assets"))

    fcf = CF.free_cash_flow(row.get("operating_activity"), row.get("investing_activity"))
    capex_pct, capex_lbl = CF.capex_intensity(row.get("investing_activity"), row.get("sales"))
    fcf_conv = CF.fcf_conversion_rate(fcf, row.get("operating_profit"))
    pattern_key, pattern_label = CF.capital_allocation_pattern(
        row.get("operating_activity"), row.get("investing_activity"), row.get("financing_activity")
    )

    return {
        "company_id": row["company_id"], "year": row["year"],
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm,
        "opm_mismatch_flag": R.opm_cross_check(opm, row.get("opm_percentage")),
        "return_on_equity_pct": roe,
        "roce_pct": roce,
        "roa_pct": roa,
        "debt_to_equity": de,
        "high_leverage_flag": lev_flag,
        "interest_coverage": icr,
        "icr_label": icr_lbl,
        "icr_risk_flag": icr_risk,
        "net_debt_cr": net_debt,
        "asset_turnover": at,
        "free_cash_flow_cr": fcf,
        "capex_cr": abs(row.get("investing_activity")) if row.get("investing_activity") is not None else None,
        "capex_intensity_pct": capex_pct,
        "capex_intensity_label": capex_lbl,
        "fcf_conversion_pct": fcf_conv,
        "capital_allocation_pattern": pattern_label,
        "earnings_per_share": row.get("eps"),
        "book_value_per_share": (
            ((row.get("equity_capital") or 0) + (row.get("reserves") or 0)) /
            (row.get("equity_capital") / row.get("face_value"))
            if row.get("equity_capital") and row.get("face_value") else None
        ),
        "dividend_payout_ratio_pct": row.get("dividend_payout"),
        "total_debt_cr": row.get("borrowings"),
        "cash_from_operations_cr": row.get("operating_activity"),
    }


def compute_cagr_columns(pl_df):
    out = []
    for company_id, group in pl_df.groupby("company_id"):
        series_sales = dict(zip(group["year"], group["sales"]))
        series_profit = dict(zip(group["year"], group["net_profit"]))
        series_eps = dict(zip(group["year"], group["eps"]))
        fixed_years = sorted(y for y in series_sales if y != "TTM")
        for year in fixed_years:
            rev_cagr, rev_flag = cagr_for_window(series_sales, year, 5)
            pat_cagr, pat_flag = cagr_for_window(series_profit, year, 5)
            eps_cagr, eps_flag = cagr_for_window(series_eps, year, 5)
            out.append({
                "company_id": company_id, "year": year,
                "revenue_cagr_5yr": rev_cagr, "revenue_cagr_5yr_flag": rev_flag,
                "pat_cagr_5yr": pat_cagr, "pat_cagr_5yr_flag": pat_flag,
                "eps_cagr_5yr": eps_cagr, "eps_cagr_5yr_flag": eps_flag,
            })
    return pd.DataFrame(out)


def compute_cfo_quality_5yr(cf_df, pl_df):
    """5-year rolling CFO/PAT quality score per company-year."""
    merged = cf_df.merge(pl_df[["company_id", "year", "net_profit"]], on=["company_id", "year"])
    out = []
    for company_id, group in merged.groupby("company_id"):
        group = group[group["year"] != "TTM"].sort_values("year")
        cfo_list = group["operating_activity"].tolist()
        pat_list = group["net_profit"].tolist()
        years = group["year"].tolist()
        for i, year in enumerate(years):
            window_cfo = cfo_list[max(0, i - 4):i + 1]
            window_pat = pat_list[max(0, i - 4):i + 1]
            score, label = CF.cfo_quality_score(window_cfo, window_pat)
            out.append({"company_id": company_id, "year": year,
                        "cfo_quality_score": score, "cfo_quality_label": label})
    return pd.DataFrame(out)


def composite_quality_score(row):
    """Simple 0-100 composite: 40% ROE, 30% FCF-positive, 30% low leverage."""
    parts, weights = [], []
    if row.get("return_on_equity_pct") is not None:
        parts.append(min(max(row["return_on_equity_pct"], 0), 40) / 40 * 100)
        weights.append(0.4)
    if row.get("free_cash_flow_cr") is not None:
        parts.append(100 if row["free_cash_flow_cr"] > 0 else 0)
        weights.append(0.3)
    if row.get("debt_to_equity") is not None:
        de = row["debt_to_equity"]
        de_score = 100 if de == 0 else max(0, 100 - de * 20)
        parts.append(de_score)
        weights.append(0.3)
    if not parts:
        return None
    return sum(p * w for p, w in zip(parts, weights)) / sum(weights)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    # Preserve Sprint 1's pre-loaded values for Day 13 cross-check
    conn.execute("DROP TABLE IF EXISTS financial_ratios_source;")
    conn.execute("ALTER TABLE financial_ratios RENAME TO financial_ratios_source;")

    merged, pl = load_merged_data(conn)
    print(f"Merged company-year rows available for ratio computation: {len(merged)}")

    ratio_rows = [compute_row_ratios(row.to_dict()) for _, row in merged.iterrows()]
    ratios_df = pd.DataFrame(ratio_rows)

    cagr_df = compute_cagr_columns(pl)
    ratios_df = ratios_df.merge(cagr_df, on=["company_id", "year"], how="left")

    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    cfo_q_df = compute_cfo_quality_5yr(cf, pl)
    ratios_df = ratios_df.merge(cfo_q_df, on=["company_id", "year"], how="left")

    ratios_df["composite_quality_score"] = ratios_df.apply(composite_quality_score, axis=1)

    # Build the new financial_ratios table with the full computed schema
    conn.execute("""
        CREATE TABLE financial_ratios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            year TEXT NOT NULL,
            net_profit_margin_pct REAL,
            operating_profit_margin_pct REAL,
            opm_mismatch_flag BOOLEAN,
            return_on_equity_pct REAL,
            roce_pct REAL,
            roa_pct REAL,
            debt_to_equity REAL,
            high_leverage_flag BOOLEAN,
            interest_coverage REAL,
            icr_label TEXT,
            icr_risk_flag BOOLEAN,
            net_debt_cr REAL,
            asset_turnover REAL,
            free_cash_flow_cr REAL,
            capex_cr REAL,
            capex_intensity_pct REAL,
            capex_intensity_label TEXT,
            fcf_conversion_pct REAL,
            capital_allocation_pattern TEXT,
            earnings_per_share REAL,
            book_value_per_share REAL,
            dividend_payout_ratio_pct REAL,
            total_debt_cr REAL,
            cash_from_operations_cr REAL,
            revenue_cagr_5yr REAL,
            revenue_cagr_5yr_flag TEXT,
            pat_cagr_5yr REAL,
            pat_cagr_5yr_flag TEXT,
            eps_cagr_5yr REAL,
            eps_cagr_5yr_flag TEXT,
            cfo_quality_score REAL,
            cfo_quality_label TEXT,
            composite_quality_score REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
    """)
    ratios_df.to_sql("financial_ratios", conn, if_exists="append", index=False)
    conn.commit()

    n_rows = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    print(f"financial_ratios table populated: {n_rows} rows")

    # capital_allocation.csv
    def sign(x):
        if x is None:
            return "0"
        return "+" if x > 0 else ("-" if x < 0 else "0")
    cf_alloc = cf.copy()
    cf_alloc["cfo_sign"] = cf_alloc["operating_activity"].apply(sign)
    cf_alloc["cfi_sign"] = cf_alloc["investing_activity"].apply(sign)
    cf_alloc["cff_sign"] = cf_alloc["financing_activity"].apply(sign)
    cf_alloc["pattern_label"] = ratios_df.set_index(["company_id", "year"])["capital_allocation_pattern"].reindex(
        pd.MultiIndex.from_frame(cf_alloc[["company_id", "year"]])
    ).values
    cf_alloc[["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]].to_csv(
        OUTPUT / "capital_allocation.csv", index=False
    )
    print(f"output/capital_allocation.csv written: {len(cf_alloc)} rows")

    conn.execute("PRAGMA foreign_keys = ON;")
    fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    print(f"PRAGMA foreign_key_check violations: {len(fk_violations)}")

    conn.close()


if __name__ == "__main__":
    main()
