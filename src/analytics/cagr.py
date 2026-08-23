"""
Sprint 2 — Day 10: CAGR engine.

CAGR = ((end/start)^(1/n) - 1) x 100

Six edge cases, each returns (value, flag):
    positive -> positive   : computed normally,  flag=None
    positive -> negative   : None, flag='DECLINE_TO_LOSS'
    negative -> positive   : None, flag='TURNAROUND'
    negative -> negative   : None, flag='BOTH_NEGATIVE'
    zero base              : None, flag='ZERO_BASE'
    fewer than n years data: None, flag='INSUFFICIENT'
"""


def compute_cagr(start_value, end_value, n_years):
    if n_years is None or n_years <= 0:
        return None, "INSUFFICIENT"
    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value > 0:
        cagr = ((end_value / start_value) ** (1 / n_years) - 1) * 100
        return cagr, None

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    # end_value == 0 with start_value != 0 falls through to here — treat as decline/turnaround-ish;
    # simplest safe answer is to flag it rather than silently compute a 100% decline.
    return None, "ZERO_BASE"


def cagr_for_window(series_by_year: dict, end_year: str, window_years: int):
    """
    series_by_year: {year_str: value}, e.g. {'2019-03': 100, '2020-03': 110, ...}
    Looks up the value `window_years` fiscal years before `end_year`.
    Returns (cagr, flag). flag='INSUFFICIENT' if the start year isn't present.
    """
    years_sorted = sorted(y for y in series_by_year if y != "TTM")
    if end_year not in series_by_year:
        return None, "INSUFFICIENT"
    try:
        end_idx = years_sorted.index(end_year)
    except ValueError:
        return None, "INSUFFICIENT"
    start_idx = end_idx - window_years
    if start_idx < 0:
        return None, "INSUFFICIENT"
    start_year = years_sorted[start_idx]
    return compute_cagr(series_by_year[start_year], series_by_year[end_year], window_years)
