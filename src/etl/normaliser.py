"""
Normaliser for the Nifty100 ETL pipeline.

These functions were written AFTER profiling the real source files, so they
handle the actual messy formats found in profitandloss.xlsx, balancesheet.xlsx
and cashflow.xlsx — not a generic guess. Formats observed:

    'Dec 2012'        -> month-name space year   (most common in PL/BS)
    'Mar 2014'        -> month-name space year
    'Mar-13'          -> month-abbrev hyphen 2-digit-year (seen in cashflow.xlsx)
    'TTM'             -> Trailing Twelve Months — not a fixed financial year
    'Mar 2023 15'     -> genuine data-entry garbage (found in AMBUJACEM row) —
                          must NOT be silently guessed; flag for manual review

Output convention: normalized year is a string 'YYYY-MM' representing the
financial year END month, e.g. 'Mar 2014' -> '2014-03'. TTM is passed through
unchanged as the literal string 'TTM' since it is a real, valid label in this
dataset (not an error) — downstream analytics must handle it separately from
fixed fiscal years (e.g. exclude from CAGR calculations).
"""
import re

MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


class YearParseError(ValueError):
    """Raised when a year value cannot be safely parsed (logged, not guessed)."""
    pass


def normalize_year(raw_year) -> str:
    if raw_year is None:
        raise YearParseError("Year is None")

    s = str(raw_year).strip().upper()
    s = re.sub(r"\s+", " ", s)  # collapse multiple spaces

    if s == "TTM":
        return "TTM"

    # 'MAR-13' style (hyphen, 2-digit year) — seen in cashflow.xlsx
    m = re.fullmatch(r"([A-Z]{3})-(\d{2})", s)
    if m:
        mon, yy = m.groups()
        if mon not in MONTHS:
            raise YearParseError(f"Unknown month abbreviation: {raw_year!r}")
        yyyy = 2000 + int(yy) if int(yy) < 70 else 1900 + int(yy)
        return f"{yyyy}-{MONTHS[mon]}"

    # 'MAR 2014' / 'DEC 2012' style (space, 4-digit year) — dominant format
    m = re.fullmatch(r"([A-Z]{3}) (\d{4})", s)
    if m:
        mon, yyyy = m.groups()
        if mon not in MONTHS:
            raise YearParseError(f"Unknown month abbreviation: {raw_year!r}")
        return f"{yyyy}-{MONTHS[mon]}"

    # Bare 4-digit year — assume standard March FY-end (India convention)
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return f"{m.group(1)}-03"

    # Anything else (e.g. 'MAR 2023 15') is genuine garbage — do not guess-fix.
    raise YearParseError(f"Unparseable year value: {raw_year!r}")


def normalize_ticker(raw_ticker) -> str:
    if raw_ticker is None or not str(raw_ticker).strip():
        raise ValueError("Empty ticker")
    t = str(raw_ticker).strip().upper()
    t = re.sub(r"\.(NS|BO)$", "", t)          # strip exchange suffix if present
    t = re.sub(r"[^A-Z0-9&\-]", "", t)        # keep letters/digits/& /- (BAJAJ-AUTO, M&M)
    if not t:
        raise ValueError(f"Ticker normalised to empty string: {raw_ticker!r}")
    return t
