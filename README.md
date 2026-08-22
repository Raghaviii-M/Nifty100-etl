# Nifty100 Financial Intelligence Platform — Sprint 1 (Data Foundation)

Builds `nifty100.db` from the 12 real source files (7 core + 5 supporting),
with full normalisation, validation, and audit trails.

## How to run

```bash
pip install -r requirements.txt   # pandas, openpyxl, pytest
python run_pipeline.py            # builds db/nifty100.db + output/*.csv
python -m pytest tests/ -v        # 48 unit tests
```

**Note:** A `Makefile` (`make load`, `make test`) is included for reference,
but on Windows without `make` installed, the pipeline is run directly via
the two commands above.

## What this pipeline actually found in the real data

Profiling the source files (before writing any loader code) surfaced issues
that a generic loader would have silently gotten wrong:

1. **Mixed year formats across files.** `profitandloss.xlsx` /
   `balancesheet.xlsx` mostly use `"Mar 2014"` / `"Dec 2012"` (month name +
   space + year), while `cashflow.xlsx` mixes in `"Mar-13"` (hyphenated,
   2-digit year) for some rows. `normalize_year()` in `src/etl/normaliser.py`
   handles both, plus the special `"TTM"` (Trailing Twelve Months) label,
   which is a *valid* value — not an error — and is passed through so
   downstream analytics can exclude it from CAGR calculations.

2. **Genuine data-entry garbage.** Row 96 of `profitandloss.xlsx`
   (AMBUJACEM) has year value `"Mar 2023 15"` — not a typo pattern worth
   guessing at, so it's rejected and logged rather than silently "fixed."

3. **9 tickers exist in the time-series files but not in `companies.xlsx`**
   (`WIPRO`, `ZOMATO`, `VEDL`, `ULTRACEMCO`, `UNIONBANK`, `UNITDSPR`,
   `ZYDUSLIFE`, `VBL`, `AGTL`). The project spec confirms this is expected:
   the Nifty 100 index has 100 constituents, but the `companies` master
   list was trimmed to 92 "after data availability filter applied" — these
   9 were filtered out, but their historical rows remained in every other
   file. All affected rows are logged to `validation_failures.csv` under
   DQ-03 and excluded from the loaded database, since a foreign key must
   point to a real row.

4. **Real exact-duplicate rows** — 87 in `balancesheet.xlsx` alone (e.g.
   ASIANPAINT has every year 2013–2017 duplicated with a different `id` but
   identical values). Deduplicated on `(company_id, year)`, keeping the
   first occurrence.

5. **`financial_ratios.xlsx`** ships pre-computed (not built from scratch in
   this sprint — Sprint 2 in the project plan recomputes and cross-validates
   these). It has its own 2 orphan tickers (`ULTRACEMCO`, `UNIONBANK`), not
   present in the trimmed 92-company list, handled the same way as above.

## Results after cleaning

| Table | Rows loaded | Rows rejected | Reason |
|---|---|---|---|
| companies | 92 | 0 | — |
| profitandloss | 1,161 | 115 | 99 orphan FK, 13 dup PK, 3 bad year |
| balancesheet | 1,140 | 172 | 80 orphan FK, 87 dup PK, 5 bad year |
| cashflow | 1,056 | 131 | 96 orphan FK, 35 dup PK |
| sectors | 92 | 0 | — |
| stock_prices | 5,520 | 0 | — |
| market_cap | 552 | 0 | — |
| financial_ratios | 1,160 | 24 | orphan FK |
| peer_groups | 56 | 0 | — |
| analysis | 16 | 4 | orphan FK |
| documents | 1,457 | 128 | orphan FK |
| prosandcons | 14 | 2 | orphan FK |

## Validation Summary

`validation_failures.csv` logs **433 CRITICAL** and **118 WARNING** rows.
The 433 CRITICAL rows are the orphan-FK and duplicate-PK rows described
above (the 9 filtered-out tickers plus real duplicate rows) — every one of
them was caught by `run_pipeline.py` and rejected **before** the database
was built, which is exactly why the final database has zero violations:

- `SELECT COUNT(*) FROM companies` → **92**
- `PRAGMA foreign_key_check` → **0 rows**

In other words: the CRITICAL count in the CSV is an audit trail of problems
*found and fixed*, not problems remaining in `nifty100.db`.

The 118 WARNING rows (tax rate outliers, one negative-sales row, one
dividend-payout-over-200% row, etc.) are informational — they stay in the
database for analyst review rather than being rejected, per the spec's own
severity rules.

## Manual Review (Day 06)

Verified 5 companies (TCS, RELIANCE, HDFCBANK, INFY, ITC) directly against
`db/nifty100.db` by querying `profitandloss` and comparing year-over-year
`sales` and `net_profit` values to the source Excel files. All values
matched — e.g. TCS FY23 sales of ₹2,25,458 Cr and net profit of ₹42,303 Cr
line up exactly with `profitandloss.xlsx`.

## Known limitations (documented, not hidden)

- The company count (92) is lower than the raw source data's implied ~100
  because of the pre-existing filter noted above — this is expected, not a
  loader bug.
- `DQ-11` (tax rate 0–60%) flags 108 rows — many are legitimate (negative
  PBT producing a nonsensical tax %, or one-off deferred tax adjustments);
  WARNING-level, kept in the database for analyst review.
- `DQ-16` coverage check flags 1 company with fewer than 5 fiscal years of
  P&L history — expected for a recently-listed company; excluded from
  CAGR-based analytics downstream rather than the whole pipeline.

## Project structure
```
src/etl/normaliser.py   — normalize_year(), normalize_ticker()
src/etl/loader.py       — Excel readers (header=1 for core, header=0 for supporting)
src/etl/validator.py    — DQ rule implementations
run_pipeline.py         — orchestrates load -> normalise -> validate -> build DB
db/schema.sql           — 12-table SQLite schema with FK constraints
tests/etl/              — 48 unit tests (pytest)
notebooks/exploratory_queries.sql — 10 verified queries
output/load_audit.csv   — per-table load statistics
output/validation_failures.csv — all DQ rule violations with severity
```
