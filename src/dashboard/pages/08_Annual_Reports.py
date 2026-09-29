import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
from dashboard.utils import db

st.set_page_config(page_title="Annual Reports | Nifty 100 Analytics", layout="wide")
st.title("📄 Annual Reports")

companies = db.get_companies()
options = sorted(companies["company_id"] + " — " + companies["company_name"].fillna(""))
search = st.selectbox("Search company", options=[""] + options)
ticker = search.split(" — ")[0] if search else None


def check_url(url, timeout=3):
    """Best-effort URL check — gracefully degrades to 'unavailable' on any error
    (timeout, no network access, 404, etc.) rather than crashing the page."""
    try:
        import requests
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


if not ticker:
    st.info("Search for a company above to see its annual reports.")
else:
    docs = db.get_documents(ticker)
    if docs.empty:
        st.warning(f"No annual report records found for {ticker}.")
    else:
        st.subheader(f"Annual Reports — {ticker}")
        check_live = st.checkbox("Check link availability (may be slow)", value=False)

        for _, row in docs.iterrows():
            year, url = row["Year"], row["Annual_Report"]
            col1, col2, col3 = st.columns([1, 4, 2])
            col1.write(f"**{year}**")
            if pd.isna(url) or not url:
                col2.write("_No link on file_")
                col3.markdown(":red[Report unavailable]")
                continue
            col2.markdown(f"[{url}]({url})")
            if check_live:
                is_valid = check_url(url)
                col3.markdown(":green[Available]" if is_valid else ":red[Report unavailable]")
            else:
                col3.caption("Not checked")
