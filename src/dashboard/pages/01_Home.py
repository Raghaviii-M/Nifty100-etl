import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import db

st.set_page_config(page_title="Home | Nifty 100 Analytics", layout="wide")
st.title("🏠 Home — Portfolio Overview")

years = db.get_available_years()
fixed_years = sorted([y for y in years if y != "TTM"], reverse=True)
selected_year = st.sidebar.selectbox("Year", fixed_years, index=0)

ratios = db.get_ratios(year=selected_year)
companies = db.get_companies()
merged = ratios.merge(companies, on="company_id", how="left")

if merged.empty:
    st.warning(f"No data available for {selected_year}.")
else:
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Avg ROE", f"{merged['return_on_equity_pct'].mean():.1f}%")
    col2.metric("Median D/E", f"{merged['debt_to_equity'].median():.2f}")
    col3.metric("Total Companies", f"{merged['company_id'].nunique()}")
    col4.metric("Median Rev CAGR 5yr", f"{merged['revenue_cagr_5yr'].median():.1f}%"
                if merged['revenue_cagr_5yr'].notna().any() else "N/A")
    col5.metric("Debt-Free Companies", f"{(merged['debt_to_equity'] == 0).sum()}")

    mc = db.get_valuation()
    mc_year = mc[mc["year"] == int(selected_year[:4])] if not mc.empty else mc
    col6.metric("Median P/E", f"{mc_year['pe_ratio'].median():.1f}x" if not mc_year.empty else "N/A")

    st.divider()

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Sector Breakdown")
        sector_counts = merged.groupby("broad_sector")["company_id"].nunique().reset_index()
        sector_counts.columns = ["Sector", "Companies"]
        if not sector_counts.empty:
            fig = px.pie(sector_counts, names="Sector", values="Companies", hole=0.5)
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector data available.")

    with right:
        st.subheader("Top 5 by Composite Quality Score")
        top5 = merged.dropna(subset=["composite_quality_score"]).sort_values(
            "composite_quality_score", ascending=False
        ).head(5)
        if not top5.empty:
            st.dataframe(
                top5[["company_id", "company_name", "broad_sector", "composite_quality_score"]]
                .rename(columns={"company_id": "Ticker", "company_name": "Name",
                                  "broad_sector": "Sector", "composite_quality_score": "Score"}),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No composite scores available for this year.")
