import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest
from etl.normaliser import normalize_year, normalize_ticker, YearParseError


# ---- normalize_year: 20+ cases -------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Dec 2012", "2012-12"),
    ("Mar 2014", "2014-03"),
    ("Mar 2015", "2015-03"),
    ("Mar 2020", "2020-03"),
    ("Mar 2024", "2024-03"),
    ("dec 2012", "2012-12"),          # lowercase
    (" Mar 2014 ", "2014-03"),        # padding
    ("Mar  2014", "2014-03"),         # double space
    ("Jun 2013", "2013-06"),
    ("Sep 2024", "2024-09"),
    ("Mar-13", "2013-03"),            # hyphen 2-digit style (cashflow.xlsx)
    ("Mar-24", "2024-03"),
    ("mar-13", "2013-03"),
    ("Dec-99", "1999-12"),            # 2-digit year rollover boundary
    ("Dec-69", "2069-12"),
    ("Dec-70", "1970-12"),
    ("2023", "2023-03"),              # bare year -> assume March FY-end
    ("2010", "2010-03"),
    ("TTM", "TTM"),                   # valid special label, not an error
    ("ttm", "TTM"),
])
def test_normalize_year_valid(raw, expected):
    assert normalize_year(raw) == expected


@pytest.mark.parametrize("raw", [
    None,
    "",
    "abcd",
    "Mar 2023 15",     # real garbage found in AMBUJACEM row of profitandloss.xlsx
    "20233",
    "Xyz 2020",        # unknown month abbreviation
    "Mar",             # missing year
    "2023-13",         # invalid month-like suffix, not a supported pattern
])
def test_normalize_year_invalid(raw):
    with pytest.raises(YearParseError):
        normalize_year(raw)


# ---- normalize_ticker: 15+ cases -----------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("TCS", "TCS"),
    ("tcs", "TCS"),
    (" TCS ", "TCS"),
    ("reliance.NS", "RELIANCE"),
    ("reliance.BO", "RELIANCE"),
    ("Reliance.ns", "RELIANCE"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO"),      # hyphen preserved
    ("bajaj-auto", "BAJAJ-AUTO"),
    ("M&M", "M&M"),                    # ampersand preserved
    ("m&m", "M&M"),
    ("ABB", "ABB"),
    ("adanienSOL", "ADANIENSOL"),
    ("  hdfcbank  ", "HDFCBANK"),
    ("tcs!!", "TCS"),                  # strips stray punctuation
    ("tcs@#", "TCS"),
])
def test_normalize_ticker_valid(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "!!!", "@#$"])
def test_normalize_ticker_invalid(raw):
    with pytest.raises(ValueError):
        normalize_ticker(raw)
