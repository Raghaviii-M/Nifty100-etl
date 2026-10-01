# Sprint 5 Retrospective: Intelligence, NLP & PDF Reports

**Sprint dates:** Day 29-35 (due 17 Sep 2026)
**Epics:** 07 (Cash Flow Intelligence), 08 (Reports), 09 (NLP)
**Target:** 70 SP | **Delivered:** [FILL IN] SP
**Team:** pragyandixit.csit, raghavimurali75, logeshjayaraman
**Status:** [FILL IN: Complete / Partially complete]

---

## 1. Sprint Goal

- NLP module auto-generates pros and cons for all 92 companies with confidence scores
- Cash Flow Intelligence module classifies every company by CFO quality, CapEx intensity and capital allocation pattern
- 92 company tearsheet PDFs and 11 sector PDFs generated with no text overflow or layout errors

**Goal met?** [FILL IN: Yes / Partly / No, with one sentence of explanation]

---

## 2. Deliverables Status

| Deliverable | Status | Notes |
|---|---|---|
| `output/analysis_parsed.csv` | [FILL IN] | Rows parsed: [N] |
| `output/parse_failures.csv` | [FILL IN] | Failures: [N], main reason: [FILL IN] |
| `output/cagr_manual_review.csv` | [FILL IN] | Flagged (>5pp divergence): [N] |
| `output/pros_cons_generated.csv` | [FILL IN] | Total rows: [N]; companies missing a pro or con: [N] |
| `output/cashflow_intelligence.xlsx` | [FILL IN] | Rows: [92?]; columns: [11?] |
| `output/distress_alerts.csv` | [FILL IN] | Companies flagged: [N] |
| `output/pattern_changes.csv` | [FILL IN] | Changes found: [N] |
| `reports/tearsheets/` | [FILL IN] | Files: [N]; skipped: [N]; under 30 KB: [N] |
| `reports/sector/` | [FILL IN] | PDFs: [11?] |
| `reports/portfolio/portfolio_summary.pdf` | [FILL IN] | Pages: [N] |
| `src/nlp/`, `src/reports/` | [FILL IN] | |

---

## 3. Exit Criteria Check

- [ ] `pros_cons_generated.csv` has at least 1 pro and 1 con for every company
- [ ] All tearsheets exist in `reports/tearsheets/` and are at least 30 KB each
- [ ] Visual review of 5 tearsheets: no text overflow, no blank pages
- [ ] `cashflow_intelligence.xlsx` has 92 rows with all required columns
- [ ] Sprint 5 review meeting completed and signed off by team lead

---

## 4. Key Numbers

- Capital allocation distribution (latest year): [FILL IN, e.g. Reinvestor: N, Distress Signal: N, ...]
- CFO quality: High Quality [N] / Moderate [N] / Accrual Risk [N]
- CapEx intensity: Asset Light [N] / Moderate [N] / Capital Intensive [N]
- Companies with distress signal: [N] ([FILL IN names])
- Companies flagged as deleveraging: [N]
- Most frequently triggered pro rule: [FILL IN]
- Most frequently triggered con rule: [FILL IN]
- Tearsheets visually checked: [FILL IN tickers]

---

## 5. What Went Well

- [FILL IN, e.g. the shared `src/common.py` loader meant every script read data the same way]
- [FILL IN, e.g. the rule-per-function design made the 24 pros/cons rules easy to test]
- [FILL IN, e.g. using `Paragraph` cells with fixed column widths prevented text overflow]

---

## 6. What Was Hard / Problems Faced

- [FILL IN, e.g. banks and financial companies: CFO, CapEx or D/E behave differently or are missing]
- [FILL IN, e.g. some analysis.xlsx text entries did not match the regex (see `parse_failures.csv`)]
- [FILL IN, e.g. companies with missing or negative PAT: CFO/PAT ratio and CAGR undefined]
- [FILL IN, e.g. layout issues in tearsheets found during testing and how they were fixed]
- [FILL IN, e.g. unicode arrows rendering as black boxes until a TTF font was registered]

---

## 7. Assumptions and Limitations

- Free cash flow is approximated as CFO minus the absolute value of investing activity (no separate CapEx column) [CONFIRM against your data]
- Net debt for Con Rule 11 is approximated by borrowings (no cash column used), and EBITDA by operating profit [CONFIRM]
- Con Rules 1 and 11 are applied to non-financial companies only
- Confidence score formula: 65 at the rule threshold, increasing with how far the value exceeds it, capped at 100; only rows above 60 are kept [CONFIRM or adjust to what you implemented]
- Parsed CAGRs from the analysis text may differ slightly from computed CAGRs because of different year windows
- [FILL IN any other assumption you made]

---

## 8. Data Quality Notes

- Companies skipped for fewer than 3 years of data: [FILL IN tickers or "none"]
- Companies where a rule could not run because of missing data: [FILL IN]
- Companies that failed PDF generation and why: [FILL IN or "none"]

---

## 9. Action Items for Next Sprint

| Action | Owner | Priority |
|---|---|---|
| [FILL IN] | [FILL IN] | [High/Med/Low] |
| [FILL IN] | [FILL IN] | [High/Med/Low] |
| [FILL IN] | [FILL IN] | [High/Med/Low] |

---

## 10. Demo Notes

Shown to team lead on [DATE]:
- 3 tearsheets: [FILL IN tickers and sectors]
- `cashflow_intelligence.xlsx`
- `pros_cons_generated.csv`

**Feedback received:** [FILL IN]
**Sign-off:** [FILL IN: Approved by NAME on DATE]
