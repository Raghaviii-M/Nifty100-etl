"""
Sprint 3 — Day 17: Composite Quality Score (0-100).

Weights: Profitability 35% (ROE 15 + ROCE 10 + NPM 10)
         Cash Quality  30% (FCF CAGR 15 + CFO/PAT 10 + FCF-positive flag 5)
         Growth        20% (Revenue CAGR 10 + PAT CAGR 10)
         Leverage      15% (D/E score 10 + ICR score 5)

Each metric is winsorised at P10/P90 (extreme outliers capped) before being
scaled to 0-100, so one freak value (like BEL's 3000% ROE from Sprint 2)
can't blow out the whole score.
"""
import pandas as pd
import numpy as np


def winsorize_and_scale(series: pd.Series, higher_is_better=True) -> pd.Series:
    """Caps at P10/P90, then linearly scales to 0-100."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    p10, p90 = valid.quantile(0.10), valid.quantile(0.90)
    if p90 == p10:
        return pd.Series(50.0, index=series.index).where(series.notna())
    capped = series.clip(lower=p10, upper=p90)
    scaled = (capped - p10) / (p90 - p10) * 100
    if not higher_is_better:
        scaled = 100 - scaled
    return scaled


def compute_composite_scores(df: pd.DataFrame, sector_relative=True) -> pd.DataFrame:
    """
    df must have columns: company_id, year, broad_sector,
    return_on_equity_pct, roce_pct, net_profit_margin_pct,
    revenue_cagr_5yr, pat_cagr_5yr, cfo_quality_score, free_cash_flow_cr,
    debt_to_equity, interest_coverage

    Returns df with a new 'composite_quality_score' column (0-100).
    """
    df = df.copy()

    def scale_group(group):
        roe_s = winsorize_and_scale(group["return_on_equity_pct"])
        roce_s = winsorize_and_scale(group["roce_pct"])
        npm_s = winsorize_and_scale(group["net_profit_margin_pct"])
        profitability = (roe_s * 0.15 + roce_s * 0.10 + npm_s * 0.10) / 0.35

        fcf_cagr_s = winsorize_and_scale(group["revenue_cagr_5yr"])  # proxy: FCF CAGR data not always available, use revenue growth as fallback signal
        cfo_pat_s = winsorize_and_scale(group["cfo_quality_score"])
        fcf_positive = (group["free_cash_flow_cr"] > 0).astype(float) * 100
        cash_quality = (fcf_cagr_s * 0.15 + cfo_pat_s * 0.10 + fcf_positive * 0.05) / 0.30

        rev_cagr_s = winsorize_and_scale(group["revenue_cagr_5yr"])
        pat_cagr_s = winsorize_and_scale(group["pat_cagr_5yr"])
        growth = (rev_cagr_s * 0.10 + pat_cagr_s * 0.10) / 0.20

        de_s = winsorize_and_scale(group["debt_to_equity"], higher_is_better=False)
        icr_s = winsorize_and_scale(group["interest_coverage"])
        icr_s = icr_s.fillna(100)  # Debt Free (ICR=None) treated as best-in-class for scoring
        leverage = (de_s * 0.10 + icr_s * 0.05) / 0.15

        composite = (profitability * 0.35 + cash_quality * 0.30 +
                     growth * 0.20 + leverage * 0.15)
        return composite

    if sector_relative and "broad_sector" in df.columns:
        df["composite_quality_score"] = df.groupby("broad_sector", group_keys=False).apply(scale_group)
    else:
        df["composite_quality_score"] = scale_group(df)

    return df
