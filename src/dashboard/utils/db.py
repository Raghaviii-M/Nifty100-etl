"""
Sprint 4 — Day 22: shared, cached data loader for every dashboard screen.

Every function that touches the database is wrapped in @st.cache_data(ttl=600)
so repeated navigation between screens doesn't re-query SQLite every time.
"""
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[3] / "db" / "nifty100.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT c.id AS company_id, c.company_name, c.about_company,
               c.nse_profile, c.bse_profile, s.broad_sector, s.sub_sector
        FROM companies c LEFT JOIN sectors s ON c.id = s.company_id
    """, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_ratios(ticker: str = None, year: str = None) -> pd.DataFrame:
    conn = get_conn()
    query = "SELECT * FROM financial_ratios WHERE 1=1"
    params = []
    if ticker:
        query += " AND company_id = ?"
        params.append(ticker)
    if year:
        query += " AND year = ?"
        params.append(year)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM sectors", conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT pg.*, c.company_name
        FROM peer_groups pg LEFT JOIN companies c ON pg.company_id = c.id
        WHERE pg.peer_group_name = ?
    """, conn, params=[group_name])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_peer_group_names() -> list:
    conn = get_conn()
    names = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name", conn)
    conn.close()
    return names["peer_group_name"].tolist()


@st.cache_data(ttl=600)
def get_peer_percentiles(group_name: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM peer_percentiles WHERE peer_group_name = ?", conn, params=[group_name])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_valuation(ticker: str = None) -> pd.DataFrame:
    conn = get_conn()
    query = "SELECT * FROM market_cap WHERE 1=1"
    params = []
    if ticker:
        query += " AND company_id = ?"
        params.append(ticker)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_pros_cons(ticker: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT pros, cons FROM prosandcons WHERE company_id = ?", conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_documents(ticker: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql('SELECT Year, Annual_Report FROM documents WHERE company_id = ? ORDER BY Year DESC', conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_capital_allocation() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT company_id, year, capital_allocation_pattern
        FROM financial_ratios WHERE year != 'TTM'
    """, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_available_years() -> list:
    conn = get_conn()
    years = pd.read_sql(
        "SELECT DISTINCT year FROM financial_ratios WHERE year != 'TTM' ORDER BY year DESC", conn
    )
    conn.close()
    return years["year"].tolist()
