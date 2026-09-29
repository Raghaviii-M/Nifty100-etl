import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import db

st.set_page_config(page_title="Capital Allocation Map | Nifty 100 Analytics", layout="wide")
st.title("🗺️ Capital Allocation Map")

cap_alloc = db.get_capital_allocation()
companies = db.get_companies()

latest = cap_alloc.sort_values("year").groupby("company_id").last().reset_index()
merged = latest.merge(companies[["company_id", "company_name", "broad_sector"]], on="company_id", how="left")
merged = merged.dropna(subset=["capital_allocation_pattern"])

if merged.empty:
    st.warning("No capital allocation data available.")
else:
    st.caption("Click a pattern segment below to see which companies fall into it.")
    fig = px.treemap(
        merged, path=["capital_allocation_pattern", "company_id"],
        color="capital_allocation_pattern",
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Browse by Pattern")
    patterns = sorted(merged["capital_allocation_pattern"].unique())
    selected_pattern = st.selectbox("Select a pattern", patterns)
    if selected_pattern:
        subset = merged[merged["capital_allocation_pattern"] == selected_pattern]
        st.write(f"**{len(subset)} companies** classified as *{selected_pattern}*:")
        st.dataframe(
            subset[["company_id", "company_name", "broad_sector"]],
            use_container_width=True, hide_index=True,
        )
