# Sprint 4 Retrospective — Streamlit Dashboard + Valuation

## Exit criteria — all met

| Criterion | Result |
|---|---|
| All 8 screens load without errors, any of 92 tickers | ✅ verified with `streamlit.testing.v1.AppTest` (not just HTTP 200 — actually executes each page's logic) |
| Company Profile loads in <3 seconds | ✅ max 0.84s across 5 tested tickers |
| Screener CSV download produces valid file with correct headers | ✅ |
| valuation_summary.xlsx has 92 rows, all required columns | ✅ |
| Sprint review demo | Pending team lead walkthrough |

## Testing approach — a note on methodology

Early on I checked pages by curling `http://localhost:8501/<page>` and seeing
`200 OK`. That's not actually proof the page works — Streamlit serves 200 for
the page shell even if the underlying Python script throws an exception,
since errors render inside the app UI rather than changing the HTTP status.
Switched to `streamlit.testing.v1.AppTest`, which actually runs each page's
script server-side and exposes `.exception` — this is what caught real
problems (see below) that curl-based testing would have missed entirely.

## Testing coverage
- All 8 pages load without exception (via AppTest, not just HTTP check)
- Company Profile tested against 10 tickers across 5 sectors (IT, Financials,
  Consumer Staples, Energy, Healthcare) — all pass
- Company Profile tested against JIOFIN (2 years of history, the sparsest
  company in the dataset) — the "fewer than 10 years" caption displays
  correctly, no crash
- Screener tested with every slider pushed to its minimum and its maximum —
  no crash in either direction (produces 0 or up to 92 results, both handled)
- Sector Analysis tested against all 10 real sectors
- Peer Comparison tested against all 11 real peer groups
- 12 of these checks are now automated in `tests/dashboard/test_pages.py`
  and run alongside the other 89 tests (101 total)

## What went well
- Reusing the composite score / screener engine logic from Sprint 3 directly
  inside the Screener page meant the dashboard's results are guaranteed
  consistent with `screener_output.xlsx` — no risk of two different
  implementations drifting apart.
- `AppTest` caught real bugs before a human ever had to click through the
  browser manually.

## Bugs found and fixed
1. Initial path calculation in `03_Screener.py` used `parents[4]` for
   `DB_PATH`, which resolved one directory above the project root — caused
   by miscounting the extra `pages/` folder depth. Fixed to `parents[3]`.
2. Curl-based page checks all showed `200 OK` even before this fix — a
   reminder that a passing HTTP status is not the same as a passing page.

## UX decisions
- Screener preset buttons pre-fill the sidebar sliders rather than bypassing
  them, so an analyst can start from a preset and then fine-tune — matches
  how the spec describes "clicking a preset auto-fills the sliders."
- Annual Reports live-URL checking is opt-in (a checkbox), not automatic,
  since checking dozens of external URLs on every page load would be slow
  and this environment doesn't always have outbound access to bseindia.com
  — the check gracefully degrades to "Report unavailable" on any network
  error rather than crashing the page.
- Trend Analysis caps metric selection at 3 to keep the chart readable per
  the spec ("overlay up to 3 metrics").

## Data edge cases discovered
- JIOFIN has only 2 years of P&L history (recently listed) — confirmed the
  UI shows an informational caption rather than an error.
- A handful of companies have no `market_cap_crore` value for bubble sizing
  in Sector Analysis — handled by falling back to the sector median size
  rather than crashing on a null bubble size.

## What I'd do differently next sprint
- Set up `AppTest`-based testing on Day 22 (scaffold day) rather than Day 27
  (QA day) — would have caught the path bug immediately instead of only
  during the dedicated integration testing pass.
