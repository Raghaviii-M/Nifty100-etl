"""
Data quality validator for the Nifty100 ETL pipeline.

Rules implemented here reflect issues actually found by profiling the real
files (not hypothetical ones):

  DQ-01  Company PK uniqueness             -> companies.id must be unique
  DQ-02  (company_id, year) PK uniqueness  -> found real exact-duplicate rows
                                              in balancesheet.xlsx (87 dupes)
  DQ-03  FK integrity                      -> found 9 orphan tickers in
                                              PL/BS/CF that don't exist in
                                              companies.xlsx (e.g. WIPRO,
                                              ZOMATO, VEDL, ULTRACEMCO...)
  DQ-04  Balance sheet balances (<1%)      -> checked: total_assets always
                                              equals total_liabilities exactly
                                              in this dataset (0 violations)
  DQ-06  Positive sales                    -> sales must be > 0
  DQ-07  Net cash consistency              -> net_cash_flow should equal
                                              CFO+CFI+CFF within tolerance
  DQ-11  Tax rate range                    -> 0-60%
  DQ-12  Dividend payout cap               -> flag if > 200%
  DQ-16  Coverage check                    -> companies with < 5 years of data
"""
import pandas as pd


class DQResult:
    def __init__(self, rule_id, description, severity, failed_rows: pd.DataFrame):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.failed_rows = failed_rows

    @property
    def passed(self):
        return len(self.failed_rows) == 0


def dq01_pk_uniqueness(companies: pd.DataFrame) -> DQResult:
    dupes = companies[companies.duplicated(subset=["id"], keep=False)]
    return DQResult("DQ-01", "Company PK uniqueness", "CRITICAL", dupes)


def dq02_composite_pk(df: pd.DataFrame, table_name: str) -> DQResult:
    dupes = df[df.duplicated(subset=["company_id", "year_norm"], keep=False)]
    return DQResult("DQ-02", f"(company_id, year) uniqueness in {table_name}", "CRITICAL", dupes)


def dq03_fk_integrity(df: pd.DataFrame, company_ids: set, table_name: str) -> DQResult:
    orphans = df[~df["company_id"].isin(company_ids)]
    return DQResult("DQ-03", f"FK integrity in {table_name}", "CRITICAL", orphans)


def dq04_balance_sheet_check(bs: pd.DataFrame, tolerance=0.01) -> DQResult:
    diff = (bs["total_assets"] - bs["total_liabilities"]).abs()
    pct = diff / bs["total_assets"].replace(0, pd.NA)
    failed = bs[pct > tolerance]
    return DQResult("DQ-04", "Balance sheet balances within 1%", "WARNING", failed)


def dq06_positive_sales(pl: pd.DataFrame) -> DQResult:
    failed = pl[pl["sales"] <= 0]
    return DQResult("DQ-06", "Positive sales", "WARNING", failed)


def dq07_net_cash_check(cf: pd.DataFrame, tolerance=10) -> DQResult:
    valid = cf.dropna(subset=["operating_activity", "investing_activity",
                               "financing_activity", "net_cash_flow"])
    computed = (valid["operating_activity"] + valid["investing_activity"]
                + valid["financing_activity"])
    diff = (valid["net_cash_flow"] - computed).abs()
    failed = valid[diff > tolerance]
    return DQResult("DQ-07", "Net cash flow consistency (±10 Cr)", "WARNING", failed)


def dq11_tax_rate_range(pl: pd.DataFrame) -> DQResult:
    valid = pl.dropna(subset=["tax_percentage"])
    failed = valid[(valid["tax_percentage"] < 0) | (valid["tax_percentage"] > 60)]
    return DQResult("DQ-11", "Tax rate within 0-60%", "WARNING", failed)


def dq12_dividend_cap(pl: pd.DataFrame) -> DQResult:
    valid = pl.dropna(subset=["dividend_payout"])
    failed = valid[valid["dividend_payout"] > 200]
    return DQResult("DQ-12", "Dividend payout <= 200%", "WARNING", failed)


def dq16_coverage_check(pl: pd.DataFrame, min_years=5) -> DQResult:
    fixed_year_rows = pl[pl["year_norm"] != "TTM"]
    counts = fixed_year_rows.groupby("company_id")["year_norm"].nunique()
    sparse = counts[counts < min_years]
    failed = pd.DataFrame({"company_id": sparse.index, "year_count": sparse.values})
    return DQResult("DQ-16", f"Companies with >= {min_years} years of P&L history", "WARNING", failed)


def write_report(results: list, out_path: str):
    rows = []
    for r in results:
        for _, row in r.failed_rows.iterrows():
            identifier = row.get("company_id", row.get("id", "?"))
            year = row.get("year_norm", row.get("year", ""))
            rows.append({
                "rule_id": r.rule_id,
                "description": r.description,
                "severity": r.severity,
                "company_id": identifier,
                "year": year,
            })
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return len(rows)
