"""
Sprint 4 — Day 22: Nifty 100 Analytics — main Streamlit entry point.
Run with: streamlit run src/dashboard/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Nifty 100 Financial Intelligence Platform")
st.markdown("""
Welcome. Use the sidebar to navigate between screens:

- **Home** — portfolio-wide summary KPIs and sector breakdown
- **Company Profile** — deep dive into any of the 92 companies
- **Screener** — filter companies by financial criteria, with 6 preset screens
- **Peer Comparison** — compare a company against its peer group
- **Trend Analysis** — multi-year, multi-metric trend charts
- **Sector Analysis** — sector-level bubble charts and benchmarks
- **Capital Allocation Map** — see how all 92 companies allocate cash
- **Annual Reports** — browse annual report links per company

Select a page from the sidebar on the left to get started.
""")
