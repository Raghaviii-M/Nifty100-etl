import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.utils import db

st.set_page_config(page_title="Peer Comparison | Nifty 100 Analytics", layout="wide")
st.title("👥 Peer Comparison")

group_names = db.get_peer_group_names()
selected_group = st.selectbox("Select a peer group", group_names)

if selected_group:
    members = db.get_peers(selected_group)
    percentiles = db.get_peer_percentiles(selected_group)

    if members.empty:
        st.warning("No companies found in this peer group.")
    else:
        company_ids = members["company_id"].tolist()
        ratios = pd.concat([db.get_ratios(ticker=c) for c in company_ids])
        latest = ratios[ratios["year"] != "TTM"].sort_values("year").groupby("company_id").last().reset_index()
        latest = latest.merge(members[["company_id", "company_name", "is_benchmark"]], on="company_id", how="left")

        left, right = st.columns([1, 1])
        with left:
            selected_company = st.selectbox("Focus company for radar chart", company_ids)
            row = latest[latest["company_id"] == selected_company]

            if not row.empty:
                axes = ["return_on_equity_pct", "roce_pct", "net_profit_margin_pct",
                        "debt_to_equity", "revenue_cagr_5yr", "pat_cagr_5yr", "composite_quality_score"]
                axes_present = [a for a in axes if a in latest.columns]
                axes_labels = axes_present

                def normed(series, invert=False):
                    valid = series.dropna()
                    if valid.empty or valid.max() == valid.min():
                        return series.apply(lambda x: 50 if pd.notna(x) else 0)
                    lo, hi = valid.quantile(0.1), valid.quantile(0.9)
                    s = ((series.clip(lo, hi) - lo) / (hi - lo) * 100).fillna(0)
                    return 100 - s if invert else s

                scaled = latest.copy()
                for a in axes_present:
                    scaled[a] = normed(latest[a], invert=(a == "debt_to_equity"))

                company_vals = scaled[scaled["company_id"] == selected_company][axes_present].iloc[0].tolist()
                group_avg_vals = scaled[axes_present].mean().tolist()

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=company_vals + [company_vals[0]],
                                                theta=axes_labels + [axes_labels[0]],
                                                fill="toself", name=selected_company))
                fig.add_trace(go.Scatterpolar(r=group_avg_vals + [group_avg_vals[0]],
                                                theta=axes_labels + [axes_labels[0]],
                                                name="Peer Group Avg", line=dict(dash="dash")))
                fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=450)
                st.plotly_chart(fig, use_container_width=True)

        with right:
            st.subheader(f"{selected_group} — All Members")
            display_cols = ["company_id", "company_name", "return_on_equity_pct", "roce_pct",
                             "debt_to_equity", "revenue_cagr_5yr", "composite_quality_score", "is_benchmark"]
            display_cols = [c for c in display_cols if c in latest.columns]
            show_df = latest[display_cols].copy()

            def highlight_benchmark(row):
                if row.get("is_benchmark"):
                    return ["background-color: #FFD966"] * len(row)
                return [""] * len(row)

            st.dataframe(
                show_df.style.apply(highlight_benchmark, axis=1),
                use_container_width=True, hide_index=True,
            )
