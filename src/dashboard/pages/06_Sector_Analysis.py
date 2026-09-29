import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import db

st.set_page_config(page_title="Sector Analysis | Nifty 100 Analytics", layout="wide")
st.title("🏭 Sector Analysis")

sectors_df = db.get_sectors()
sector_list = sorted(sectors_df["broad_sector"].dropna().unique())
selected_sector = st.selectbox("Select a sector", sector_list)

if selected_sector:
    tickers = sectors_df[sectors_df["broad_sector"] == selected_sector]["company_id"].tolist()
    ratios = pd.concat([db.get_ratios(ticker=t) for t in tickers]) if tickers else pd.DataFrame()
    fixed = ratios[ratios["year"] != "TTM"] if not ratios.empty else ratios
    latest = fixed.sort_values("year").groupby("company_id").last().reset_index() if not fixed.empty else fixed

    valuation = db.get_valuation()
    latest_val = valuation.sort_values("year").groupby("company_id").last().reset_index() if not valuation.empty else valuation

    merged = latest.merge(sectors_df[["company_id", "sub_sector"]], on="company_id", how="left")
    merged = merged.merge(latest_val[["company_id", "market_cap_crore"]], on="company_id", how="left")
    pl_latest = pd.concat([db.get_pl(t) for t in tickers]) if tickers else pd.DataFrame()
    if not pl_latest.empty:
        pl_fixed = pl_latest[pl_latest["year"] != "TTM"].sort_values("year").groupby("company_id").last().reset_index()
        merged = merged.merge(pl_fixed[["company_id", "sales"]], on="company_id", how="left")

    if merged.empty or "sales" not in merged.columns:
        st.warning(f"Insufficient data for {selected_sector}.")
    else:
        st.subheader(f"{selected_sector} — Revenue vs ROE")
        plot_df = merged.dropna(subset=["sales", "return_on_equity_pct"])
        if plot_df.empty:
            st.info("No companies with complete data in this sector.")
        else:
            fig = px.scatter(
                plot_df, x="sales", y="return_on_equity_pct",
                size=plot_df["market_cap_crore"].fillna(plot_df["market_cap_crore"].median() if plot_df["market_cap_crore"].notna().any() else 1000),
                color="sub_sector", hover_name="company_id",
                labels={"sales": "Revenue (₹ Cr)", "return_on_equity_pct": "ROE (%)"},
                size_max=50,
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"{selected_sector} — Median KPIs")
        median_metrics = merged[["return_on_equity_pct", "roce_pct", "net_profit_margin_pct",
                                   "debt_to_equity", "revenue_cagr_5yr"]].median()
        fig2 = px.bar(x=median_metrics.index, y=median_metrics.values,
                      labels={"x": "Metric", "y": "Median Value"})
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)
