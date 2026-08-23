# Nifty100 Financial Intelligence Platform — Sprint 1 + Sprint 2

A data engineering and financial analytics pipeline that transforms 12 real-world Nifty100 source files into a validated SQLite database (`nifty100.db`) with data-quality checks, audit trails, financial analysis, and cash-flow KPIs.

---

## Project Overview

This project builds a reliable financial data foundation for Nifty100 companies.

The pipeline performs:

* Excel data ingestion
* Data normalization
* Ticker and year standardization
* Data-quality validation
* Duplicate detection
* Foreign-key validation
* Rejection and audit logging
* SQLite database creation
* Financial-ratio analysis
* Cash-flow KPI calculations
* Capital-allocation classification
* Automated testing
* Exploratory SQL analysis

The project was completed across **Sprint 1 — Data Foundation** and **Sprint 2 — Financial Intelligence**.

---

# Sprint 1 — Data Foundation

## How to Run

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the ETL pipeline:

```bash
python run_pipeline.py
```

This builds:

```text
db/nifty100.db
```

and generates audit/validation files under:

```text
output/
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

The verified Sprint 1 test run contained **48 passing tests**.

> **Windows note:** A `Makefile` containing commands such as `make load` and `make test` is included for reference. On Windows without `make` installed, run the Python commands directly.

---

## What the Pipeline Found in the Real Data

### 1. Mixed Year Formats

Different source files use different year formats.

Examples include:

```text
Mar 2014
Dec 2012
Mar-13
TTM
```

The `normalize_year()` function in:

```text
src/etl/normaliser.py
```

handles the supported formats.

`TTM` (Trailing Twelve Months) is treated as a valid value rather than an error and can be excluded from CAGR-based calculations where required.

---

### 2. Genuine Data-Entry Error

A row in `profitandloss.xlsx` for AMBUJACEM contained:

```text
Mar 2023 15
```

This did not match a valid year format.

Instead of guessing or silently modifying the value, the pipeline rejects the row and records it in the validation audit trail.

---

### 3. Orphan Tickers

Nine tickers appeared in time-series data but were not present in the trimmed `companies.xlsx` master list:

```text
WIPRO
ZOMATO
VEDL
ULTRACEMCO
UNIONBANK
UNITDSPR
ZYDUSLIFE
VBL
AGTL
```

The project specification states that the company master list was reduced to 92 companies after a data-availability filter.

Historical rows belonging to companies outside the master list were therefore rejected under the appropriate foreign-key data-quality rule.

This prevents invalid company references from entering the final database.

---

### 4. Duplicate Records

The source data contained genuine duplicate records.

For example, `balancesheet.xlsx` contained duplicate rows for ASIANPAINT across multiple years.

Duplicates were detected using the appropriate business key, such as:

```text
(company_id, year)
```

and duplicate records were removed before loading the final database.

---

### 5. Pre-computed Financial Ratios

The source `financial_ratios.xlsx` file contains pre-computed financial ratios.

Sprint 1 loads and validates this information.

Sprint 2 extends the financial-analysis layer by calculating and evaluating additional financial indicators rather than treating the source ratios as the only analytical output.

---

# Sprint 1 Results

| Table            | Rows Loaded | Rows Rejected | Reason                            |
| ---------------- | ----------: | ------------: | --------------------------------- |
| companies        |          92 |             0 | —                                 |
| profitandloss    |       1,161 |           115 | Orphan FK, duplicate PK, bad year |
| balancesheet     |       1,140 |           172 | Orphan FK, duplicate PK, bad year |
| cashflow         |       1,056 |           131 | Orphan FK, duplicate PK           |
| sectors          |          92 |             0 | —                                 |
| stock_prices     |       5,520 |             0 | —                                 |
| market_cap       |         552 |             0 | —                                 |
| financial_ratios |   **1,161** |            24 | Orphan FK                         |
| peer_groups      |          56 |             0 | —                                 |
| analysis         |          16 |             4 | Orphan FK                         |
| documents        |       1,457 |           128 | Orphan FK                         |
| prosandcons      |          14 |             2 | Orphan FK                         |

### Final Database Verification

The final SQLite database contains:

```text
92 companies
```

and:

```text
1,161 financial_ratios rows
```

Foreign-key integrity was verified using:

```sql
PRAGMA foreign_key_check;
```

Result:

```text
0 rows
```

This means the final database contains **zero foreign-key violations**.

---

# Validation Summary

The pipeline produces:

```text
output/validation_failures.csv
```

This file provides an audit trail of rejected or flagged records.

The validation process distinguishes between:

* **CRITICAL** issues — records rejected before database loading
* **WARNING** issues — records retained for analyst review

The presence of validation failures in the CSV does **not** mean those invalid records remain in the final database.

Instead, they demonstrate that the pipeline detected and handled the problems before database creation.

---

# Manual Data Verification

Five companies were manually checked against the source Excel files:

```text
TCS
RELIANCE
HDFCBANK
INFY
ITC
```

Their financial data was queried from `nifty100.db` and compared against the original source files.

The checked values matched the source data.

For example, TCS FY23 values included approximately:

```text
Sales: ₹2,25,458 Cr
Net Profit: ₹42,303 Cr
```

---

# Sprint 2 — Financial Intelligence

Sprint 2 builds on the validated Sprint 1 database and focuses on turning financial data into useful analytical indicators.

The Sprint 2 work includes:

* Cash-flow analysis
* Free Cash Flow calculation
* CFO quality analysis
* Cash-flow trend interpretation
* Capital-allocation classification
* Financial KPI preparation
* Validation of analytical outputs
* Automated testing of financial-analysis functions

---

## Cash-Flow KPIs

The cash-flow analysis uses operating, investing, and related financial information to evaluate the quality and sustainability of a company's cash generation.

### Free Cash Flow

Free Cash Flow is calculated using:

```text
FCF = Operating Cash Flow + Investing Cash Flow
```

The implementation handles missing inputs by returning an unavailable result instead of producing an invalid calculation.

---

## CFO Quality Score

CFO quality compares operating cash flow with profit after tax.

A simplified interpretation is:

```text
CFO / PAT
```

A multi-year average can be used to evaluate whether reported accounting profits are supported by actual operating cash generation.

A stronger and more consistent CFO/PAT relationship generally indicates better earnings quality.

---

## Capital Allocation Classification

Sprint 2 also introduces a classification approach for understanding how companies use generated cash.

The analysis considers factors such as:

* Operating cash generation
* Investing activity
* Free cash flow
* Dividend-related activity
* Cash deployment patterns

This allows companies to be categorized based on their broad capital-allocation behavior.

The classification is intended as an analytical aid rather than an investment recommendation.

---

# Data Quality Philosophy

A major principle of this project is:

> **Do not silently fix data that cannot be reliably inferred.**

The pipeline distinguishes between:

### Normalizable Data

Examples:

```text
Mar 2014
Mar-14
```

These can be standardized using deterministic rules.

### Invalid Data

Examples:

```text
Mar 2023 15
```

These cannot be safely interpreted and are therefore rejected and logged.

This approach keeps the database auditable and prevents incorrect assumptions from entering financial analysis.

---

# Known Limitations

### Company Coverage

The final company master contains:

```text
92 companies
```

rather than the raw source's implied 100 companies.

This is expected because the provided company master was already filtered based on data availability.

---

### Tax Rate Outliers

Some tax-rate records fall outside the expected range.

These can occur because of:

* Negative profit before tax
* Deferred-tax adjustments
* One-time accounting effects

Such records are treated according to the project's data-quality severity rules rather than being automatically deleted.

---

### Historical Coverage

Some companies have fewer historical fiscal years than others.

Companies with insufficient history should be excluded from calculations that require a minimum number of years, such as certain CAGR analyses.

---

# Project Structure

```text
nifty100-etl/
│
├── data/
│   ├── raw/
│   └── supporting/
│
├── db/
│   ├── nifty100.db
│   └── schema.sql
│
├── src/
│   └── etl/
│       ├── normaliser.py
│       ├── loader.py
│       └── validator.py
│
├── tests/
│   └── etl/
│
├── notebooks/
│   └── exploratory_queries.sql
│
├── output/
│   ├── load_audit.csv
│   └── validation_failures.csv
│
├── run_pipeline.py
├── requirements.txt
├── Makefile
└── README.md
```

---

# Key Files

### `run_pipeline.py`

Main ETL orchestration script.

Responsible for coordinating:

```text
Load
  ↓
Normalize
  ↓
Validate
  ↓
Transform
  ↓
Build SQLite Database
  ↓
Generate Audit Reports
```

### `src/etl/normaliser.py`

Contains normalization logic including:

* Year normalization
* Ticker normalization
* Standardization of source values

### `src/etl/loader.py`

Handles Excel file ingestion and source-specific header structures.

### `src/etl/validator.py`

Contains the project's data-quality validation rules.

### `db/schema.sql`

Defines the SQLite database schema and foreign-key relationships.

### `output/load_audit.csv`

Contains per-table loading statistics.

### `output/validation_failures.csv`

Contains rejected and flagged data-quality records.

### `notebooks/exploratory_queries.sql`

Contains verified SQL queries used for exploratory financial analysis.

---

# Database Integrity

The final database was checked using SQLite foreign-key validation.

Command:

```sql
PRAGMA foreign_key_check;
```

Verified result:

```text
0 rows
```

This confirms that rejected orphan records were not loaded into the final relational database.

---

# Testing

The project uses `pytest` for automated testing.

Run:

```bash
python -m pytest tests/ -v
```

The verified Sprint 1 test execution produced:

```text
48 passed
```

Tests cover areas such as:

* Data normalization
* Validation rules
* ETL behavior
* Financial calculations
* Edge cases
* Missing values
* Invalid inputs

---

# Technologies Used

* **Python**
* **Pandas**
* **OpenPyXL**
* **SQLite**
* **SQL**
* **Pytest**
* **Excel**
* **Git / GitHub**

---

# Final Outcome

The project delivers a validated financial data foundation and an analytical layer for Nifty100 companies.

### Key verified outcomes

| Metric                  |                     Result |
| ----------------------- | -------------------------: |
| Companies loaded        |                     **92** |
| Financial ratio rows    |                  **1,161** |
| Foreign-key violations  |                      **0** |
| Verified Sprint 1 tests |              **48 passed** |
| Source files processed  |                     **12** |
| Database                | **SQLite (`nifty100.db`)** |

Sprint 1 establishes a clean, validated, auditable financial database.

Sprint 2 builds on that foundation by adding financial intelligence through cash-flow KPIs, earnings-quality analysis, and capital-allocation analytics.

---

# Conclusion

This project demonstrates how raw financial data can be transformed into a reliable analytical data platform through:

```text
Raw Financial Data
        ↓
Data Profiling
        ↓
Normalization
        ↓
Data Quality Validation
        ↓
Cleaning & Rejection
        ↓
SQLite Database
        ↓
Financial Analysis
        ↓
Cash-Flow KPIs
        ↓
Financial Intelligence
```

The main objective is not simply to load data, but to create a **reliable, validated, auditable, and analysis-ready financial data foundation**.
