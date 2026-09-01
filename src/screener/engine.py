"""
Sprint 3 — Day 15 & 16: Filter Engine + 6 Preset Screeners.
"""
import sqlite3
import yaml
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = path or ROOT / "config" / "screener_config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_screener_universe(conn, latest_only=True) -> pd.DataFrame:
    """Builds the full metric universe: financial_ratios + market_cap + sector + sales."""
    fr = pd.read_sql("SELECT * FROM financial_ratios WHERE year != 'TTM'", conn)
    mc = pd.read_sql("SELECT company_id, year, market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct FROM market_cap", conn)
    pl = pd.read_sql("SELECT company_id, year, sales, net_profit, dividend_payout FROM profitandloss WHERE year != 'TTM'", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    comp = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)

    df = fr.merge(sectors, on="company_id", how="left")
    df = df.merge(comp, on="company_id", how="left")
    df = df.merge(pl, on=["company_id", "year"], how="left")

    # market_cap uses calendar year (int), financial_ratios uses fiscal year string 'YYYY-MM'
    # -> join on the fiscal year's calendar year component
    df["fiscal_year_int"] = df["year"].str.slice(0, 4).astype(int)
    df = df.merge(mc, left_on=["company_id", "fiscal_year_int"], right_on=["company_id", "year"],
                  how="left", suffixes=("", "_mc"))

    if latest_only:
        df = df.sort_values("year").groupby("company_id").last().reset_index()
    return df


def apply_filter(df, metric, condition):
    """condition is a dict like {'min': 15} or {'max': 1.0} or {'equals': 0}."""
    if metric not in df.columns:
        return df  # metric unavailable — skip rather than error
    col = df[metric]
    mask = pd.Series(True, index=df.index)
    if "min" in condition:
        mask &= col >= condition["min"]
    if "max" in condition:
        mask &= col <= condition["max"]
    if "equals" in condition:
        mask &= col == condition["equals"]
    return df[mask]


def run_screen(df: pd.DataFrame, filters: dict, is_financials_col="broad_sector",
               skip_financials_for_de: bool = True) -> pd.DataFrame:
    result = df.copy()
    for metric, condition in filters.items():
        if metric == "debt_to_equity" and "max" in condition and skip_financials_for_de:
            # D/E max filter: skip (i.e. always pass) companies in Financials sector,
            # since high leverage is structurally normal for banks/NBFCs.
            fin_mask = result[is_financials_col] == "Financials"
            passes = result["debt_to_equity"] <= condition["max"]
            result = result[fin_mask | passes]
        elif metric == "interest_coverage" and "min" in condition:
            # Debt Free (interest_coverage is None, icr_label='Debt Free') always passes an ICR min
            debt_free_mask = result["icr_label"] == "Debt Free"
            passes = result["interest_coverage"] >= condition["min"]
            result = result[debt_free_mask | passes]
        else:
            result = apply_filter(result, metric, condition)
    return result.sort_values("composite_quality_score", ascending=False)


def run_preset(df: pd.DataFrame, preset_key: str, config: dict) -> pd.DataFrame:
    preset = config["presets"][preset_key]
    skip_fin = preset.get("skip_financials_for_de", True)
    return run_screen(df, preset["filters"], skip_financials_for_de=skip_fin)


def run_all_presets(df: pd.DataFrame, config: dict, conn=None) -> dict:
    results = {}
    for key in config["presets"]:
        if key == "turnaround_watch":
            if conn is None:
                continue
            df_with_de = add_de_declining_flag(df, conn)
            results[key] = run_turnaround_watch(df_with_de)
        else:
            results[key] = run_preset(df, key, config)
    return results


def add_de_declining_flag(df: pd.DataFrame, conn) -> pd.DataFrame:
    """Adds 'de_declining_yoy' — True if this year's D/E is lower than last year's for the same company."""
    all_fr = pd.read_sql("SELECT company_id, year, debt_to_equity FROM financial_ratios WHERE year != 'TTM'", conn)
    all_fr = all_fr.sort_values(["company_id", "year"])
    all_fr["prev_de"] = all_fr.groupby("company_id")["debt_to_equity"].shift(1)
    all_fr["de_declining_yoy"] = all_fr["debt_to_equity"] < all_fr["prev_de"]
    df = df.merge(all_fr[["company_id", "year", "de_declining_yoy"]], on=["company_id", "year"], how="left")
    return df


def run_turnaround_watch(df: pd.DataFrame) -> pd.DataFrame:
    """Custom logic preset: Revenue CAGR 3yr > 10%, FCF positive latest year, D/E declining YoY."""
    mask = (
        (df["revenue_cagr_3yr"] > 10) &
        (df["free_cash_flow_cr"] > 0) &
        (df["de_declining_yoy"] == True)
    )
    return df[mask].sort_values("composite_quality_score", ascending=False)


def run_custom_screen(df: pd.DataFrame, custom_filters: dict) -> pd.DataFrame:
    """Day 15: supports analyst-defined custom threshold combinations."""
    return run_screen(df, custom_filters)
