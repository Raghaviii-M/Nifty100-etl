"""
Sprint 2 — Day 11: Cash Flow KPIs & capital allocation classifier.
"""


def free_cash_flow(operating_activity, investing_activity):
    if operating_activity is None or investing_activity is None:
        return None
    return operating_activity + investing_activity


def cfo_quality_score(cfo_values: list, pat_values: list):
    """Average CFO/PAT ratio over the given years (typically last 5).
    Returns (score, label). None/'Unavailable' if no valid PAT values."""
    ratios = []
    for cfo, pat in zip(cfo_values, pat_values):
        if pat in (None, 0) or cfo is None:
            continue
        ratios.append(cfo / pat)
    if not ratios:
        return None, "Unavailable"
    score = sum(ratios) / len(ratios)
    if score > 1.0:
        label = "High Quality"
    elif score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"
    return score, label


def capex_intensity(investing_activity, sales):
    if sales in (None, 0) or investing_activity is None:
        return None, None
    pct = abs(investing_activity) / sales * 100
    if pct < 3:
        label = "Asset Light"
    elif pct <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"
    return pct, label


def fcf_conversion_rate(fcf, operating_profit):
    if operating_profit in (None, 0) or fcf is None:
        return None
    return fcf / operating_profit * 100


def capital_allocation_pattern(cfo, cfi, cff, cfo_quality_score_value=None):
    """Classifies based on sign of (CFO, CFI, CFF). Returns (pattern_key, label)."""
    def sign(x):
        if x is None:
            return "0"
        return "+" if x > 0 else ("-" if x < 0 else "0")

    s_cfo, s_cfi, s_cff = sign(cfo), sign(cfi), sign(cff)
    key = (s_cfo, s_cfi, s_cff)

    if key == ("+", "-", "-"):
        if cfo_quality_score_value is not None and cfo_quality_score_value > 1.0:
            return key, "Shareholder Returns"
        return key, "Reinvestor"
    if key == ("+", "+", "-"):
        return key, "Liquidating Assets"
    if key == ("-", "+", "+"):
        return key, "Distress Signal"
    if key == ("-", "-", "+"):
        return key, "Growth Funded by Debt"
    if key == ("+", "+", "+"):
        return key, "Cash Accumulator"
    if key == ("-", "-", "-"):
        return key, "Pre-Revenue"
    if key == ("+", "-", "+"):
        return key, "Mixed"
    return key, "Unclassified"
