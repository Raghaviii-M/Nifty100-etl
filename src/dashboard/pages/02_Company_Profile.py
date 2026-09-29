import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.utils import db

st.set_page_config(page_title="Company Profile | Nifty 100 Analytics", layout="wide")
st.title("🏢 Company Profile")

companies = db.get_companies()
options = sorted(companies["company_id"] + " — " + companies["company_name"].fillna(""))
search = st.selectbox("Search by ticker or company name", options=[""] + options)

ticker = search.split(" — ")[0] if search else None

if not ticker:
    st.info("Start typing a ticker or company name above to see the profile.")
else:
    row = companies[companies["company_id"] == ticker]
    if row.empty:
        st.error("Ticker not found — please try another")
    else:
        info = row.iloc[0]
        st.header(f"{info['company_name']} ({ticker})")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(info.get("about_company") or "No description available.")
        with c2:
            st.write(f"**Sector:** {info.get('broad_sector', 'N/A')}")
            st.write(f"**Sub-sector:** {info.get('sub_sector', 'N/A')}")
            st.write(f"**NSE Ticker:** {ticker}")

        ratios = db.get_ratios(ticker=ticker)
        fixed = ratios[ratios["year"] != "TTM"].sort_values("year")

        if fixed.empty:
            st.warning("No financial ratio data available for this company.")
        else:
            latest = fixed.iloc[-1]
            st.subheader("Key Metrics (Latest Year)")
            cols = st.columns(6)
            metrics = [
                ("ROE", latest.get("return_on_equity_pct")),
                ("ROCE", latest.get("roce_pct")),
                ("Net Profit Margin", latest.get("net_profit_margin_pct")),
                ("D/E", latest.get("debt_to_equity")),
                ("Revenue CAGR 5yr", latest.get("revenue_cagr_5yr")),
                ("FCF (₹ Cr)", latest.get("free_cash_flow_cr")),
            ]
            for col, (label, value) in zip(cols, metrics):
                if pd.isna(value):
                    col.metric(label, "N/A")
                elif "₹" in label:
                    col.metric(label, f"{value:,.0f}")
                else:
                    col.metric(label, f"{value:.1f}" + ("%" if "%" not in label and label not in ["D/E"] else ""))

            pl = db.get_pl(ticker)
            pl_fixed = pl[pl["year"] != "TTM"].sort_values("year")

            if len(pl_fixed) < 10:
                st.caption(f"ℹ️ Only {len(pl_fixed)} years of data available for this company (fewer than 10).")

            left, right = st.columns(2)
            with left:
                st.subheader("Revenue & Net Profit")
                fig = go.Figure()
                fig.add_bar(x=pl_fixed["year"], y=pl_fixed["sales"], name="Revenue")
                fig.add_bar(x=pl_fixed["year"], y=pl_fixed["net_profit"], name="Net Profit")
                fig.update_layout(barmode="group", height=350)
                st.plotly_chart(fig, use_container_width=True)

            with right:
                st.subheader("ROE & ROCE Trend")
                fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                fig2.add_trace(go.Scatter(x=fixed["year"], y=fixed["return_on_equity_pct"], name="ROE"),
                               secondary_y=False)
                fig2.add_trace(go.Scatter(x=fixed["year"], y=fixed["roce_pct"], name="ROCE"),
                               secondary_y=True)
                fig2.update_layout(height=350)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Pros & Cons")
        pc = db.get_pros_cons(ticker)
        if pc.empty:
            st.caption("No pros/cons data available for this company.")
        else:
            left, right = st.columns(2)
            with left:
                for pro in pc["pros"].dropna():
                    st.success(f"✅ {pro}")
            with right:
                for con in pc["cons"].dropna():
                    st.error(f"❌ {con}")
