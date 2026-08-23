"""
Sprint 2 — Day 08 & 09: Profitability, Leverage & Efficiency ratios.

Each function takes the raw numeric inputs (not a whole row) so they're easy
to unit test in isolation. All return None (not 0, not NaN) when the
denominator makes the ratio undefined — this matters because a screener
downstream must be able to tell "0% margin" apart from "can't be computed."
"""


def net_profit_margin(net_profit, sales):
    if sales is None or sales == 0 or net_profit is None:
        return None
    return net_profit / sales * 100


def operating_profit_margin(operating_profit, sales):
    if sales is None or sales == 0 or operating_profit is None:
        return None
    return operating_profit / sales * 100


def opm_cross_check(computed_opm, reported_opm_pct, tolerance=1.0):
    """Returns True if computed OPM differs from the reported opm_percentage
    field by more than `tolerance` percentage points (i.e. a mismatch worth logging)."""
    if computed_opm is None or reported_opm_pct is None:
        return False
    return abs(computed_opm - reported_opm_pct) > tolerance


def return_on_equity(net_profit, equity_capital, reserves):
    equity_total = (equity_capital or 0) + (reserves or 0)
    if equity_total <= 0:
        return None
    return net_profit / equity_total * 100


def return_on_capital_employed(ebit, equity_capital, reserves, borrowings):
    capital_employed = (equity_capital or 0) + (reserves or 0) + (borrowings or 0)
    if capital_employed <= 0:
        return None
    return ebit / capital_employed * 100


def return_on_assets(net_profit, total_assets):
    if total_assets is None or total_assets == 0 or net_profit is None:
        return None
    return net_profit / total_assets * 100


def debt_to_equity(borrowings, equity_capital, reserves):
    equity_total = (equity_capital or 0) + (reserves or 0)
    if borrowings in (None, 0):
        return 0.0   # explicitly 0, not None — debt-free is a real, meaningful value
    if equity_total <= 0:
        return None  # can't compute a ratio against non-positive equity
    return borrowings / equity_total


def high_leverage_flag(de_ratio, is_financials_sector, threshold=5.0):
    """High D/E is structurally normal for banks/NBFCs — only flag outside Financials."""
    if de_ratio is None or is_financials_sector:
        return False
    return de_ratio > threshold


def interest_coverage_ratio(operating_profit, other_income, interest):
    if interest in (None, 0):
        return None  # debt-free — use icr_label='Debt Free' instead of a numeric value
    return ((operating_profit or 0) + (other_income or 0)) / interest


def icr_label(icr_value, interest):
    if interest in (None, 0):
        return "Debt Free"
    return None


def icr_risk_flag(icr_value, threshold=1.5):
    if icr_value is None:
        return False
    return icr_value < threshold


def net_debt(borrowings, investments):
    return (borrowings or 0) - (investments or 0)


def asset_turnover(sales, total_assets):
    if total_assets is None or total_assets == 0 or sales is None:
        return None
    return sales / total_assets
