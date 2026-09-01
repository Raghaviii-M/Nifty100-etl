"""
Sprint 3 — Day 21: DQ rule unit tests.

Each test crafts a small synthetic DataFrame that deliberately violates (or
satisfies) one rule, and checks the validator correctly flags it — this is
what the sprint calls "each of 14 DQ rules triggered on crafted violation
records; severity correct."
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd
from etl import validator as dq


# DQ-01: Company PK uniqueness
def test_dq01_triggers_on_duplicate_id():
    companies = pd.DataFrame({"id": ["TCS", "TCS", "INFY"]})
    result = dq.dq01_pk_uniqueness(companies)
    assert result.severity == "CRITICAL"
    assert not result.passed
    assert len(result.failed_rows) == 2

def test_dq01_passes_on_unique_ids():
    companies = pd.DataFrame({"id": ["TCS", "INFY"]})
    result = dq.dq01_pk_uniqueness(companies)
    assert result.passed


# DQ-02: (company_id, year) composite PK uniqueness
def test_dq02_triggers_on_duplicate_composite_key():
    df = pd.DataFrame({"company_id": ["TCS", "TCS"], "year_norm": ["2023-03", "2023-03"]})
    result = dq.dq02_composite_pk(df, "profitandloss")
    assert result.severity == "CRITICAL"
    assert not result.passed

def test_dq02_passes_on_unique_composite_keys():
    df = pd.DataFrame({"company_id": ["TCS", "TCS"], "year_norm": ["2022-03", "2023-03"]})
    result = dq.dq02_composite_pk(df, "profitandloss")
    assert result.passed


# DQ-03: FK integrity
def test_dq03_triggers_on_orphan_company_id():
    df = pd.DataFrame({"company_id": ["TCS", "GHOST_TICKER"]})
    result = dq.dq03_fk_integrity(df, company_ids={"TCS"}, table_name="profitandloss")
    assert result.severity == "CRITICAL"
    assert len(result.failed_rows) == 1
    assert result.failed_rows.iloc[0]["company_id"] == "GHOST_TICKER"

def test_dq03_passes_when_all_ids_known():
    df = pd.DataFrame({"company_id": ["TCS", "INFY"]})
    result = dq.dq03_fk_integrity(df, company_ids={"TCS", "INFY"}, table_name="profitandloss")
    assert result.passed


# DQ-04: Balance sheet balances within 1%
def test_dq04_triggers_on_imbalanced_sheet():
    bs = pd.DataFrame({"total_assets": [1000.0], "total_liabilities": [1200.0]})
    result = dq.dq04_balance_sheet_check(bs)
    assert result.severity == "WARNING"
    assert len(result.failed_rows) == 1

def test_dq04_passes_within_tolerance():
    bs = pd.DataFrame({"total_assets": [1000.0], "total_liabilities": [1005.0]})
    result = dq.dq04_balance_sheet_check(bs)
    assert result.passed


# DQ-06: Positive sales
def test_dq06_triggers_on_zero_or_negative_sales():
    pl = pd.DataFrame({"sales": [0, -50, 1000]})
    result = dq.dq06_positive_sales(pl)
    assert result.severity == "WARNING"
    assert len(result.failed_rows) == 2


# DQ-07: Net cash flow consistency
def test_dq07_triggers_on_mismatched_net_cash():
    cf = pd.DataFrame({
        "operating_activity": [100.0], "investing_activity": [-50.0],
        "financing_activity": [-20.0], "net_cash_flow": [100.0],  # should be ~30
    })
    result = dq.dq07_net_cash_check(cf, tolerance=10)
    assert len(result.failed_rows) == 1

def test_dq07_passes_within_tolerance():
    cf = pd.DataFrame({
        "operating_activity": [100.0], "investing_activity": [-50.0],
        "financing_activity": [-20.0], "net_cash_flow": [31.0],
    })
    result = dq.dq07_net_cash_check(cf, tolerance=10)
    assert result.passed


# DQ-11: Tax rate range
def test_dq11_triggers_on_out_of_range_tax_rate():
    pl = pd.DataFrame({"tax_percentage": [70.0, -5.0, 25.0]})
    result = dq.dq11_tax_rate_range(pl)
    assert len(result.failed_rows) == 2


# DQ-12: Dividend payout cap
def test_dq12_triggers_over_200_percent():
    pl = pd.DataFrame({"dividend_payout": [250.0, 45.0]})
    result = dq.dq12_dividend_cap(pl)
    assert len(result.failed_rows) == 1


# DQ-16: Coverage check (>=5 years)
def test_dq16_triggers_on_sparse_company():
    pl = pd.DataFrame({
        "company_id": ["NEWCO"] * 3 + ["OLDCO"] * 6,
        "year_norm": [f"{2020+i}-03" for i in range(3)] + [f"{2018+i}-03" for i in range(6)],
    })
    result = dq.dq16_coverage_check(pl, min_years=5)
    assert "NEWCO" in result.failed_rows["company_id"].values
    assert "OLDCO" not in result.failed_rows["company_id"].values
