import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st
import pandas as pd
from src.screener.engine import load_config, load_screener_universe, run_screen, add_de_declining_flag, run_turnaround_watch
from src.screener.composite_score import compute_composite_scores
import sqlite3

DB_PATH = Path(__file__).resolve().parents[3] / "db" / "nifty100.db"

st.set_page_config(page_title="Screener | Nifty 100 Analytics", layout="wide")
st.title("🔍 Financial Screener")

conn = sqlite3.connect(DB_PATH)
config = load_config()
df = load_screener_universe(conn)
df = compute_composite_scores(df)

PRESET_DEFAULTS = {
    "Quality Compounder": {"roe": 15, "de": 1.0, "fcf": 0, "rev_cagr": 10, "pat_cagr": -100, "opm": -100, "pe": 1000, "pb": 1000, "div_yield": -100, "icr": -100},
    "Value Pick": {"roe": -100, "de": 2.0, "fcf": -10**9, "rev_cagr": -100, "pat_cagr": -100, "opm": -100, "pe": 30, "pb": 5.0, "div_yield": 1, "icr": -100},
    "Growth Accelerator": {"roe": -100, "de": 2.0, "fcf": -10**9, "rev_cagr": 15, "pat_cagr": 20, "opm": -100, "pe": 1000, "pb": 1000, "div_yield": -100, "icr": -100},
    "Dividend Champion": {"roe": -100, "de": 1000, "fcf": 0, "rev_cagr": -100, "pat_cagr": -100, "opm": -100, "pe": 1000, "pb": 1000, "div_yield": 2, "icr": -100},
    "Debt-Free Blue Chip": {"roe": 12, "de": 0.05, "fcf": -10**9, "rev_cagr": -100, "pat_cagr": -100, "opm": -100, "pe": 1000, "pb": 1000, "div_yield": -100, "icr": -100},
}

if "slider_state" not in st.session_state:
    st.session_state.slider_state = {"roe": -100, "de": 10.0, "fcf": -10**9, "rev_cagr": -100,
                                       "pat_cagr": -100, "opm": -100, "pe": 1000, "pb": 1000,
                                       "div_yield": -100, "icr": -100}

st.sidebar.header("Preset Screens")
preset_cols = st.sidebar.columns(2)
preset_names = list(PRESET_DEFAULTS.keys()) + ["Turnaround Watch"]
for i, name in enumerate(preset_names):
    if preset_cols[i % 2].button(name, use_container_width=True):
        if name in PRESET_DEFAULTS:
            st.session_state.slider_state = PRESET_DEFAULTS[name]
        st.session_state.active_preset = name

st.sidebar.header("Custom Filters")
s = st.session_state.slider_state
roe_min = st.sidebar.slider("ROE min (%)", -50, 100, int(s["roe"]) if s["roe"] > -100 else -50)
de_max = st.sidebar.slider("D/E max", 0.0, 10.0, float(s["de"]) if s["de"] < 1000 else 10.0)
fcf_min = st.sidebar.number_input("FCF min (₹ Cr)", value=int(s["fcf"]) if s["fcf"] > -10**9 else -100000)
rev_cagr_min = st.sidebar.slider("Revenue CAGR 5yr min (%)", -50, 100, int(s["rev_cagr"]) if s["rev_cagr"] > -100 else -50)
pat_cagr_min = st.sidebar.slider("PAT CAGR 5yr min (%)", -50, 100, int(s["pat_cagr"]) if s["pat_cagr"] > -100 else -50)
opm_min = st.sidebar.slider("OPM min (%)", -50, 100, int(s["opm"]) if s["opm"] > -100 else -50)
pe_max = st.sidebar.slider("P/E max", 0, 200, int(s["pe"]) if s["pe"] < 1000 else 200)
pb_max = st.sidebar.slider("P/B max", 0.0, 50.0, float(s["pb"]) if s["pb"] < 1000 else 50.0)
div_yield_min = st.sidebar.slider("Dividend Yield min (%)", 0, 20, int(s["div_yield"]) if s["div_yield"] > -100 else 0)
icr_min = st.sidebar.slider("ICR min", -10, 50, int(s["icr"]) if s["icr"] > -100 else -10)

active_preset = st.session_state.get("active_preset")

if active_preset == "Turnaround Watch":
    df_with_de = add_de_declining_flag(df, conn)
    result = run_turnaround_watch(df_with_de)
else:
    filters = {
        "return_on_equity_pct": {"min": roe_min},
        "debt_to_equity": {"max": de_max},
        "free_cash_flow_cr": {"min": fcf_min},
        "revenue_cagr_5yr": {"min": rev_cagr_min},
        "pat_cagr_5yr": {"min": pat_cagr_min},
        "operating_profit_margin_pct": {"min": opm_min},
        "pe_ratio": {"max": pe_max},
        "pb_ratio": {"max": pb_max},
        "dividend_yield_pct": {"min": div_yield_min},
        "interest_coverage": {"min": icr_min},
    }
    skip_fin = active_preset != "Debt-Free Blue Chip"
    result = run_screen(df, filters, skip_financials_for_de=skip_fin)

st.subheader(f"📋 {len(result)} companies match your filters")

display_cols = ["company_id", "company_name", "broad_sector", "composite_quality_score",
                 "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr",
                 "revenue_cagr_5yr", "pe_ratio", "pb_ratio", "dividend_yield_pct"]
display_cols = [c for c in display_cols if c in result.columns]

if result.empty:
    st.warning("No companies match these filters. Try loosening the thresholds.")
else:
    show_df = result[display_cols].fillna("N/A")
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    csv = show_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download results as CSV", data=csv, file_name="screener_results.csv", mime="text/csv")

conn.close()
