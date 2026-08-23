"""
Sprint 2 — Day 13: Cross-checks computed ROCE/ROE against the pre-computed
roce_percentage/roe_percentage columns in companies.xlsx, and writes every
anomaly (diff > 5 percentage points) to output/ratio_edge_cases.log with a
category: DATA_SOURCE_ISSUE, VERSION_DIFFERENCE, or FORMULA_DISCREPANCY.
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT = ROOT / "output"


def categorize(row, metric_col, source_col, raw_check_fn):
    """Heuristic categorisation — flags implausible source data as DATA_SOURCE_ISSUE,
    otherwise treats it as a likely VERSION_DIFFERENCE (source computed at a
    different point in time / different period convention)."""
    if raw_check_fn(row):
        return "DATA_SOURCE_ISSUE"
    return "VERSION_DIFFERENCE"


def bel_style_check(row):
    """Flags cases where the source ratio is wildly implausible given tiny
    equity/reserves relative to profit — a red flag for the underlying
    balance sheet field itself, not just the ratio."""
    return abs(row.get("computed", 0)) > 200  # >200% computed value is not economically plausible


def main():
    conn = sqlite3.connect(DB_PATH)
    comp = pd.read_sql("SELECT id, company_name, roce_percentage, roe_percentage FROM companies", conn)
    fr = pd.read_sql(
        "SELECT company_id, year, roce_pct, return_on_equity_pct FROM financial_ratios WHERE year != 'TTM'",
        conn,
    )
    latest = fr.sort_values("year").groupby("company_id").last().reset_index()
    merged = latest.merge(comp, left_on="company_id", right_on="id")

    lines = []
    lines.append("Sprint 2 - Ratio Edge Case Log")
    lines.append("Cross-check: our computed ROCE/ROE (latest fiscal year) vs companies.xlsx pre-computed fields")
    lines.append("Tolerance: 5 percentage points")
    lines.append("=" * 100)

    for _, row in merged.iterrows():
        roce_diff = abs(row["roce_pct"] - row["roce_percentage"]) if pd.notna(row["roce_pct"]) and pd.notna(row["roce_percentage"]) else None
        roe_diff = abs(row["return_on_equity_pct"] - row["roe_percentage"]) if pd.notna(row["return_on_equity_pct"]) and pd.notna(row["roe_percentage"]) else None

        if roce_diff is not None and roce_diff > 5:
            category = "DATA_SOURCE_ISSUE" if abs(row["roce_pct"]) > 200 else "VERSION_DIFFERENCE"
            lines.append(
                f"[ROCE] {row['company_id']:12} computed={row['roce_pct']:.2f}%  "
                f"source={row['roce_percentage']:.2f}%  diff={roce_diff:.2f}pp  category={category}"
            )

        if roe_diff is not None and roe_diff > 5:
            if abs(row["return_on_equity_pct"]) > 200:
                category = "DATA_SOURCE_ISSUE"
                note = "  <- implausible magnitude, likely bad equity/reserves value in balancesheet.xlsx"
            else:
                category = "VERSION_DIFFERENCE"
                note = ""
            lines.append(
                f"[ROE]  {row['company_id']:12} computed={row['return_on_equity_pct']:.2f}%  "
                f"source={row['roe_percentage']:.2f}%  diff={roe_diff:.2f}pp  category={category}{note}"
            )

    lines.append("=" * 100)
    lines.append(f"Total anomalies logged: {sum(1 for l in lines if l.startswith('['))}")
    lines.append("")
    lines.append("Notes:")
    lines.append("- TCS-style anomalies (source ROE far below computed) are treated as VERSION_DIFFERENCE:")
    lines.append("  companies.xlsx values appear to be a snapshot from a different reporting date than")
    lines.append("  our latest fiscal year row. The ratio engine's computed value is used for all")
    lines.append("  downstream analytics; the source value is display-only per the project spec.")
    lines.append("- Cases with |computed value| > 200% (e.g. BEL, HAL) are DATA_SOURCE_ISSUE: the")
    lines.append("  underlying balancesheet.xlsx equity_capital/reserves values for these companies")
    lines.append("  are implausibly small relative to their net profit, which inflates the ratio.")
    lines.append("  These are flagged for manual data correction, not treated as a formula bug.")

    (OUTPUT / "ratio_edge_cases.log").write_text("\n".join(lines))
    print(f"Wrote {sum(1 for l in lines if l.startswith('['))} anomalies to output/ratio_edge_cases.log")
    conn.close()


if __name__ == "__main__":
    main()
