# Sprint 2 Retrospective

## What Went Well

The financial ratio engine ran successfully and the computed KPIs were validated through manual spot-checks. The results matched the expected calculations, giving confidence in the ROE, Debt-to-Equity, revenue CAGR, and capital allocation outputs.

## What Was Tricky

One of the main challenges was identifying and fixing a join bug that caused rows to be lost during the KPI calculation process. I also fixed a missing-join issue that resulted in null `book_value_per_share` values before trusting the final results.

## What Surprised Me

BEL and HAL showed ROE values above 3000%. After investigation, this was identified as a real data-quality issue in the source balance-sheet data rather than a problem with the ROE calculation formula. This highlighted the importance of investigating extreme KPI values instead of immediately assuming the calculation is wrong.

## What I Would Do Differently Next Sprint

In the next sprint, I would validate join row counts earlier in the pipeline before reviewing or trusting the calculated outputs. I would also add earlier checks for unexpected nulls and extreme values so that data-quality problems can be detected sooner.