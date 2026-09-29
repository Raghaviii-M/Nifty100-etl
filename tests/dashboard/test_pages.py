"""
Sprint 4 — Day 27: Dashboard integration tests.

Uses streamlit.testing.v1.AppTest to actually execute each page's script
(not just check syntax) and confirm no exceptions are raised — this is
the automated version of "test all 8 screens with 10 different tickers".
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import sqlite3
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
PAGES_DIR = ROOT / "src" / "dashboard" / "pages"


def get_conn():
    return sqlite3.connect(DB_PATH)


@pytest.fixture(scope="module")
def sample_tickers():
    conn = get_conn()
    tickers = []
    for sector in ["Information Technology", "Financials", "Consumer Staples", "Energy", "Healthcare"]:
        rows = conn.execute("SELECT company_id FROM sectors WHERE broad_sector=? LIMIT 2", (sector,)).fetchall()
        tickers.extend([r[0] for r in rows])
    conn.close()
    return tickers


def test_home_page_loads():
    at = AppTest.from_file(str(PAGES_DIR / "01_Home.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_company_profile_loads_for_10_cross_sector_tickers(sample_tickers):
    conn = get_conn()
    for ticker in sample_tickers:
        name = conn.execute("SELECT company_name FROM companies WHERE id=?", (ticker,)).fetchone()[0]
        at = AppTest.from_file(str(PAGES_DIR / "02_Company_Profile.py"), default_timeout=30)
        at.run()
        at.selectbox[0].select(f"{ticker} — {name}").run()
        assert not at.exception, f"{ticker} raised: {at.exception}"
    conn.close()


def test_company_profile_handles_sparse_data_company():
    """A company with <5 years of history should not crash the page."""
    conn = get_conn()
    sparse = conn.execute("""
        SELECT company_id FROM profitandloss WHERE year != 'TTM'
        GROUP BY company_id HAVING COUNT(DISTINCT year) < 5 LIMIT 1
    """).fetchone()
    conn.close()
    if not sparse:
        pytest.skip("No sparse-data company found in current dataset")
    ticker = sparse[0]
    conn = get_conn()
    name = conn.execute("SELECT company_name FROM companies WHERE id=?", (ticker,)).fetchone()[0]
    conn.close()
    at = AppTest.from_file(str(PAGES_DIR / "02_Company_Profile.py"), default_timeout=30)
    at.run()
    at.selectbox[0].select(f"{ticker} — {name}").run()
    assert not at.exception


def test_screener_default_load():
    at = AppTest.from_file(str(PAGES_DIR / "03_Screener.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_screener_extreme_slider_values_no_crash():
    at = AppTest.from_file(str(PAGES_DIR / "03_Screener.py"), default_timeout=30)
    at.run()
    for slider in at.slider:
        slider.set_value(slider.min)
    at.run()
    assert not at.exception

    at2 = AppTest.from_file(str(PAGES_DIR / "03_Screener.py"), default_timeout=30)
    at2.run()
    for slider in at2.slider:
        slider.set_value(slider.max)
    at2.run()
    assert not at2.exception


def test_screener_csv_download_button_present():
    at = AppTest.from_file(str(PAGES_DIR / "03_Screener.py"), default_timeout=30)
    at.run()
    buttons = at.get("download_button")
    assert len(buttons) >= 1


def test_peer_comparison_loads_for_all_11_groups():
    conn = get_conn()
    groups = [r[0] for r in conn.execute("SELECT DISTINCT peer_group_name FROM peer_groups").fetchall()]
    conn.close()
    assert len(groups) == 11
    for group in groups:
        at = AppTest.from_file(str(PAGES_DIR / "04_Peer_Comparison.py"), default_timeout=30)
        at.run()
        at.selectbox[0].select(group).run()
        assert not at.exception, f"{group} raised: {at.exception}"


def test_trend_analysis_loads():
    at = AppTest.from_file(str(PAGES_DIR / "05_Trend_Analysis.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_sector_analysis_loads_for_all_sectors():
    conn = get_conn()
    sectors = [r[0] for r in conn.execute("SELECT DISTINCT broad_sector FROM sectors").fetchall()]
    conn.close()
    for sector in sectors:
        at = AppTest.from_file(str(PAGES_DIR / "06_Sector_Analysis.py"), default_timeout=30)
        at.run()
        at.selectbox[0].select(sector).run()
        assert not at.exception, f"{sector} raised: {at.exception}"


def test_capital_allocation_map_loads():
    at = AppTest.from_file(str(PAGES_DIR / "07_Capital_Allocation_Map.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_annual_reports_loads():
    at = AppTest.from_file(str(PAGES_DIR / "08_Annual_Reports.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_company_profile_load_time_under_3_seconds():
    import time
    conn = get_conn()
    tickers = ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ITC"]
    for ticker in tickers:
        name = conn.execute("SELECT company_name FROM companies WHERE id=?", (ticker,)).fetchone()[0]
        start = time.time()
        at = AppTest.from_file(str(PAGES_DIR / "02_Company_Profile.py"), default_timeout=30)
        at.run()
        at.selectbox[0].select(f"{ticker} — {name}").run()
        elapsed = time.time() - start
        assert elapsed < 3.0, f"{ticker} took {elapsed:.2f}s (must be < 3s)"
        assert not at.exception
    conn.close()
