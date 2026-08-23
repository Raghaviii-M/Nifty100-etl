import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analytics.ratios import (
    net_profit_margin, return_on_equity, return_on_capital_employed,
    debt_to_equity, high_leverage_flag, interest_coverage_ratio, icr_label,
    icr_risk_flag, asset_turnover, opm_cross_check,
)
from analytics.cagr import compute_cagr
from analytics.cashflow_kpis import cfo_quality_score, capex_intensity, capital_allocation_pattern


# 1-2: Net profit margin
def test_npm_normal():
    assert net_profit_margin(100, 1000) == 10.0

def test_npm_zero_sales():
    assert net_profit_margin(100, 0) is None


# 3-4: ROE
def test_roe_normal():
    assert return_on_equity(100, 400, 100) == 20.0

def test_roe_negative_equity():
    assert return_on_equity(100, -50, -50) is None


# 5: ROCE
def test_roce_normal():
    assert return_on_capital_employed(200, 500, 200, 300) == 20.0


# 6: OPM cross-check mismatch
def test_opm_cross_check_mismatch():
    assert opm_cross_check(21.5, 19.0) is True

def test_opm_cross_check_within_tolerance():
    assert opm_cross_check(21.5, 21.0) is False


# 7-8: Debt-to-equity
def test_de_debt_free_returns_zero_not_none():
    assert debt_to_equity(0, 500, 100) == 0.0

def test_de_normal():
    assert debt_to_equity(300, 400, 100) == 0.6


# 9: High leverage flag suppressed for Financials
def test_high_leverage_flag_suppressed_for_financials():
    assert high_leverage_flag(8.0, is_financials_sector=True) is False

def test_high_leverage_flag_triggers_outside_financials():
    assert high_leverage_flag(8.0, is_financials_sector=False) is True


# 10-11: ICR
def test_icr_interest_zero_returns_none():
    assert interest_coverage_ratio(500, 50, 0) is None

def test_icr_label_debt_free():
    assert icr_label(None, 0) == "Debt Free"

def test_icr_normal():
    assert interest_coverage_ratio(500, 50, 100) == 5.5


# 12: ICR risk flag
def test_icr_risk_flag_triggers_below_threshold():
    assert icr_risk_flag(1.2) is True

def test_icr_risk_flag_false_above_threshold():
    assert icr_risk_flag(3.0) is False


# 13: Asset turnover
def test_asset_turnover_zero_assets():
    assert asset_turnover(1000, 0) is None


# 14-19: CAGR — all 6 edge cases
def test_cagr_normal():
    val, flag = compute_cagr(100, 161.05, 5)
    assert flag is None
    assert round(val, 1) == 10.0

def test_cagr_decline_to_loss():
    val, flag = compute_cagr(100, -50, 3)
    assert val is None and flag == "DECLINE_TO_LOSS"

def test_cagr_turnaround():
    val, flag = compute_cagr(-100, 200, 3)
    assert val is None and flag == "TURNAROUND"

def test_cagr_both_negative():
    val, flag = compute_cagr(-100, -50, 3)
    assert val is None and flag == "BOTH_NEGATIVE"

def test_cagr_zero_base():
    val, flag = compute_cagr(0, 100, 3)
    assert val is None and flag == "ZERO_BASE"

def test_cagr_insufficient_data():
    val, flag = compute_cagr(100, 150, 0)
    assert val is None and flag == "INSUFFICIENT"


# 20: Capital allocation pattern classifier
def test_capital_allocation_reinvestor():
    key, label = capital_allocation_pattern(100, -50, -20, cfo_quality_score_value=0.8)
    assert label == "Reinvestor"

def test_capital_allocation_distress():
    key, label = capital_allocation_pattern(-50, 30, 40)
    assert label == "Distress Signal"

def test_cfo_quality_score_high_quality():
    score, label = cfo_quality_score([120, 130], [100, 100])
    assert label == "High Quality"

def test_capex_intensity_asset_light():
    pct, label = capex_intensity(-20, 1000)
    assert label == "Asset Light"
