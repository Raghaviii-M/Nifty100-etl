import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.utils import db

st.set_page_config(page_title="Trend Analysis | Nifty 100 Analytics", layout="wide")
st.title("📈 Trend Analysis")

companies = db.get_companies()
options = sorted(companies["company_id"] + " — " + companies["company_name"].fillna(""))
search = st.selectbox("Search company", options=[""] + options)
ticker = search.split(" — ")[0] if search else None

METRIC_OPTIONS = {
    "Return on Equity (%)": "return_on_equity_pct",
    "ROCE (%)": "roce_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Debt to Equity": "debt_to_equity",
    "Revenue CAGR 5yr (%)": "revenue_cagr_5yr",
    "Composite Quality Score": "composite_quality_score",
}
selected_labels = st.multiselect("Select up to 3 metrics to overlay", list(METRIC_OPTIONS.keys()),
                                   default=["Return on Equity (%)"], max_selections=3)

if not ticker:
    st.info("Search for a company above to see its trend.")
elif not selected_labels:
    st.info("Select at least one metric.")
else:
    ratios = db.get_ratios(ticker=ticker)
    fixed = ratios[ratios["year"] != "TTM"].sort_values("year")

    if fixed.empty:
        st.warning(f"No trend data available for {ticker}.")
    else:
        fig = go.Figure()
        for label in selected_labels:
            col = METRIC_OPTIONS[label]
            if col not in fixed.columns:
                continue
            series = fixed[col]
            yoy_pct = series.pct_change() * 100
            fig.add_trace(go.Scatter(
                x=fixed["year"], y=series, mode="lines+markers+text", name=label,
                text=[f"{v:+.1f}%" if pd.notna(v) else "" for v in yoy_pct],
                textposition="top center",
            ))
        fig.update_layout(height=500, title=f"{ticker} — {len(fixed)} years of history")
        st.plotly_chart(fig, use_container_width=True)

        if len(fixed) < 10:
            st.caption(f"ℹ️ Only {len(fixed)} years of data available for {ticker}.")
