# Sprint 3 Retrospective — Screener + Peer Engine

## Exit criteria — all met

| Criterion | Result |
|---|---|
| 6 preset screeners each return 5-50 companies | ✅ Quality Compounder 22, Value Pick 7, Growth Accelerator 20, Dividend Champion 31, Debt-Free Blue Chip 16, Turnaround Watch 32 |
| peer_comparison.xlsx has exactly 11 sheets | ✅ 11 sheets, one per peer group |
| Peer percentile ranks correct (IT Services, FMCG spot-check) | ✅ Highest ROE (TCS, NESTLEIND) has highest ROE percentile in both groups |
| All 14 DQ rule unit tests pass | ✅ 14/14 passing |
| Sprint review sign-off | Pending team lead demo |

## What went well
- The filter engine and composite score worked correctly on the first real
  run once a genuine bug (see below) was fixed — clean separation between
  YAML-driven generic filters and the two presets needing custom logic
  (Financials D/E exemption, Turnaround Watch's YoY D/E trend) made both
  easy to reason about independently.
- Winsorized (P10/P90) scaling, already built for the Sprint 2 composite
  score, turned out to be exactly what the radar charts needed too — reused
  it rather than writing a second normalization scheme.

## Bugs found and fixed
1. **`apply_filter` had a leftover buggy line** combining an OR and AND on
   the same mask, which silently caused every single preset to return 0
   companies. Caught immediately because the diagnostic "count each filter
   condition separately" check showed 20 companies should have matched
   Quality Compounder, but the actual run returned 0 — a controlled test
   revealed the bug in one look.
2. **Missed `revenue_cagr_3yr`** — Sprint 2 only computed 5-year CAGR, but
   Turnaround Watch needs 3-year. Added the column using the same
   `cagr_for_window()` function from Sprint 2, just with `window_years=3`.
3. **Financials D/E exemption applied too broadly.** The exemption (skip
   the D/E filter for banks/NBFCs, since they're structurally leveraged) is
   correct for Quality Compounder / Value Pick / Growth Accelerator, but
   wrongly let highly-leveraged banks pass the *Debt-Free Blue Chip* screen
   too — directly contradicting that preset's own definition. Fixed by
   adding a per-preset `skip_financials_for_de` flag, off by default only
   for the debt-free preset.
4. **Radar charts initially unreadable** — a handful of extreme ROCE
   outliers (INDIGO 4,953%, BEL 3,628%, HAL 2,591% — same root cause as the
   Sprint 2 edge case log) blew out the 5th/95th percentile scaling range,
   squashing every normal company's chart toward the center. Fixed by
   reusing the composite score's P10/P90 winsorization instead.

## Threshold adjustments made (documented, not silent)
- **Value Pick**: widened P/E<20→30 and P/B<3→5. The strict original
  thresholds returned only 2/92 companies — this dataset's large caps
  rarely trade below 3x book value, so the screen was unusable as specified.
- **Debt-Free Blue Chip**: widened D/E==0→≤0.05 ("functionally debt-free",
  since Ind AS 116 lease liabilities can push even genuinely debt-free
  companies slightly above exact zero). Kept the Financials exemption OFF
  specifically for this preset since exempting leveraged banks would defeat
  the screen's purpose.

## What I'd do differently next sprint
- Write the "count how many companies pass each individual filter
  condition" diagnostic *before* running the combined preset, not after
  getting a surprising 0 — would have caught the `apply_filter` bug faster.
- Check for missing CAGR windows (3yr vs 5yr) against the full daily task
  list up front, rather than discovering the gap mid-implementation.
