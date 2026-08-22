"""
Runs the full Sprint 1 pipeline end-to-end:
  1. Load all 12 Excel files
  2. Normalise company_id / year on the time-series tables
  3. Run DQ rules, write validation_failures.csv
  4. Reject CRITICAL failures (orphan FKs, duplicate PKs) before insert
  5. Build nifty100.db from schema.sql
  6. Load all cleaned tables into SQLite
  7. Write load_audit.csv
"""
import sys
import sqlite3
from pathlib import Path
import pandas as pd

sys.path.insert(0, "src")
from etl.loader import load_all
from etl.normaliser import normalize_year, normalize_ticker, YearParseError
from etl import validator as dq

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
DB_PATH = ROOT / "db" / "nifty100.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"

TIME_SERIES_TABLES = ["profitandloss", "balancesheet", "cashflow"]


def apply_normalisation(tables: dict):
    """Adds company_id_norm / year_norm columns, tracks per-row rejections."""
    audit_rows = []

    # companies master list first, needed for FK checks
    comp = tables["companies"]
    comp["company_id_norm"] = None
    good_idx, bad_idx = [], []
    for i, v in comp["id"].items():
        try:
            comp.at[i, "company_id_norm"] = normalize_ticker(v)
            good_idx.append(i)
        except ValueError:
            bad_idx.append(i)
    audit_rows.append(["companies", len(comp), len(good_idx), len(bad_idx), "bad ticker"])
    tables["companies"] = comp.loc[good_idx].copy()
    tables["companies"]["id"] = tables["companies"]["company_id_norm"]

    for name in TIME_SERIES_TABLES:
        df = tables[name].copy()
        n_in = len(df)
        df["company_id"] = df["company_id"].apply(
            lambda v: normalize_ticker(v) if pd.notna(v) else None
        )
        year_norm, keep = [], []
        for i, v in df["year"].items():
            try:
                year_norm.append(normalize_year(v))
                keep.append(True)
            except YearParseError:
                year_norm.append(None)
                keep.append(False)
        df["year_norm"] = year_norm
        rejected_year = (~pd.Series(keep)).sum()
        df = df[keep].copy()
        # dedup exact duplicate (company_id, year_norm) rows -> keep first
        before_dedup = len(df)
        df = df.drop_duplicates(subset=["company_id", "year_norm"], keep="first")
        rejected_dupe = before_dedup - len(df)
        tables[name] = df
        audit_rows.append([name, n_in, len(df), rejected_year + rejected_dupe,
                            f"{rejected_year} unparseable year, {rejected_dupe} duplicate PK"])

    # supporting tables: normalise company_id where present, no year involved
    for name in ["sectors", "stock_prices", "market_cap", "financial_ratios", "peer_groups"]:
        df = tables[name].copy()
        n_in = len(df)
        df["company_id"] = df["company_id"].apply(
            lambda v: normalize_ticker(v) if pd.notna(v) else None
        )
        tables[name] = df
        audit_rows.append([name, n_in, len(df), 0, ""])

    for name in ["analysis", "documents", "prosandcons"]:
        df = tables[name].copy()
        n_in = len(df)
        df["company_id"] = df["company_id"].apply(
            lambda v: normalize_ticker(v) if pd.notna(v) else None
        )
        tables[name] = df
        audit_rows.append([name, n_in, len(df), 0, ""])

    return tables, audit_rows


def run_dq_rules(tables: dict):
    company_ids = set(tables["companies"]["id"])
    results = []
    results.append(dq.dq01_pk_uniqueness(tables["companies"]))
    for name in TIME_SERIES_TABLES:
        results.append(dq.dq02_composite_pk(tables[name], name))
        results.append(dq.dq03_fk_integrity(tables[name], company_ids, name))
    results.append(dq.dq04_balance_sheet_check(tables["balancesheet"]))
    results.append(dq.dq06_positive_sales(tables["profitandloss"]))
    results.append(dq.dq07_net_cash_check(tables["cashflow"]))
    results.append(dq.dq11_tax_rate_range(tables["profitandloss"]))
    results.append(dq.dq12_dividend_cap(tables["profitandloss"]))
    results.append(dq.dq16_coverage_check(tables["profitandloss"]))
    results.append(dq.dq03_fk_integrity(tables["financial_ratios"], company_ids, "financial_ratios"))
    for name in ["analysis", "documents", "prosandcons"]:
        results.append(dq.dq03_fk_integrity(tables[name], company_ids, name))
    return results


def reject_critical_failures(tables: dict, results: list):
    """Removes rows that failed CRITICAL rules (FK orphans, PK dupes) before insert."""
    rejected_counts = {}
    all_table_names = TIME_SERIES_TABLES + ["financial_ratios", "analysis", "documents", "prosandcons"]
    for r in results:
        if r.severity != "CRITICAL" or r.passed:
            continue
        for name in all_table_names:
            if name in r.description:
                before = len(tables[name])
                if "year_norm" in tables[name].columns and "year_norm" in r.failed_rows.columns:
                    bad_keys = set(zip(r.failed_rows["company_id"], r.failed_rows["year_norm"]))
                    tables[name] = tables[name][
                        ~tables[name].apply(lambda row: (row["company_id"], row["year_norm"]) in bad_keys, axis=1)
                    ]
                else:
                    bad_ids = set(r.failed_rows["company_id"])
                    tables[name] = tables[name][~tables[name]["company_id"].isin(bad_ids)]
                rejected_counts[name] = rejected_counts.get(name, 0) + (before - len(tables[name]))
    return tables, rejected_counts


def build_database(tables: dict):
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")  # off while bulk-loading, verify after
    schema_sql = SCHEMA_PATH.read_text()
    conn.executescript(schema_sql)

    table_col_map = {
        "companies": ["id", "company_logo", "company_name", "chart_link", "about_company",
                      "website", "nse_profile", "bse_profile", "face_value", "book_value",
                      "roce_percentage", "roe_percentage"],
        "sectors": ["company_id", "broad_sector", "sub_sector", "index_weight_pct", "market_cap_category"],
        "profitandloss": ["company_id", "year_norm", "sales", "expenses", "operating_profit",
                           "opm_percentage", "other_income", "interest", "depreciation",
                           "profit_before_tax", "tax_percentage", "net_profit", "eps", "dividend_payout"],
        "balancesheet": ["company_id", "year_norm", "equity_capital", "reserves", "borrowings",
                          "other_liabilities", "total_liabilities", "fixed_assets", "cwip",
                          "investments", "other_asset", "total_assets"],
        "cashflow": ["company_id", "year_norm", "operating_activity", "investing_activity",
                     "financing_activity", "net_cash_flow"],
        "analysis": ["company_id", "compounded_sales_growth", "compounded_profit_growth",
                     "stock_price_cagr", "roe"],
        "documents": ["company_id", "Year", "Annual_Report"],
        "prosandcons": ["company_id", "pros", "cons"],
        "stock_prices": ["company_id", "date", "open_price", "high_price", "low_price",
                          "close_price", "volume", "adjusted_close"],
        "market_cap": ["company_id", "year", "market_cap_crore", "enterprise_value_crore",
                       "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"],
        "financial_ratios": ["company_id", "year", "net_profit_margin_pct", "operating_profit_margin_pct",
                             "return_on_equity_pct", "debt_to_equity", "interest_coverage", "asset_turnover",
                             "free_cash_flow_cr", "capex_cr", "earnings_per_share", "book_value_per_share",
                             "dividend_payout_ratio_pct", "total_debt_cr", "cash_from_operations_cr"],
        "peer_groups": ["peer_group_name", "company_id", "is_benchmark"],
    }
    rename_for_db = {"year_norm": "year"}

    for table, cols in table_col_map.items():
        df = tables[table][cols].rename(columns=rename_for_db)
        df.to_sql(table, conn, if_exists="append", index=False)

    conn.execute("PRAGMA foreign_keys = ON;")
    fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    conn.commit()
    return conn, fk_violations


def main():
    print("Loading 12 source files...")
    tables = load_all(raw_dir=str(ROOT / "data/raw"), supp_dir=str(ROOT / "data/supporting"))

    print("Normalising ticker/year fields...")
    tables, audit_rows = apply_normalisation(tables)

    print("Running DQ rules...")
    results = run_dq_rules(tables)

    OUTPUT.mkdir(exist_ok=True)
    n_failures = dq.write_report(results, str(OUTPUT / "validation_failures.csv"))
    print(f"  {n_failures} DQ failure rows written to output/validation_failures.csv")

    print("Rejecting CRITICAL failures before load...")
    tables, rejected_counts = reject_critical_failures(tables, results)

    print("Building nifty100.db...")
    conn, fk_violations = build_database(tables)

    # final row counts for load_audit.csv
    final_counts = {name: len(df) for name, df in tables.items()}
    audit_df = pd.DataFrame(audit_rows, columns=["table_name", "rows_read", "rows_after_normalisation",
                                                  "rows_rejected", "rejection_reason"])
    audit_df["rows_final"] = audit_df["table_name"].map(final_counts)
    audit_df["critical_rejected"] = audit_df["table_name"].map(rejected_counts).fillna(0).astype(int)
    audit_df.to_csv(OUTPUT / "load_audit.csv", index=False)

    print("\n=== SUMMARY ===")
    print(audit_df.to_string(index=False))
    print(f"\nPRAGMA foreign_key_check violations: {len(fk_violations)}")
    if fk_violations:
        print(fk_violations[:10])

    for r in results:
        status = "PASS" if r.passed else f"FAIL ({len(r.failed_rows)} rows)"
        print(f"  {r.rule_id:6} [{r.severity:8}] {r.description:45} -> {status}")

    conn.close()


if __name__ == "__main__":
    main()
