-- Sprint 1 exploratory queries — nifty100.db
-- Run with: sqlite3 db/nifty100.db < notebooks/exploratory_queries.sql

-- 1. Total companies loaded
SELECT COUNT(*) FROM companies;

-- 2. Sector-wise company count
SELECT broad_sector, COUNT(*) AS n_companies
FROM sectors GROUP BY broad_sector ORDER BY n_companies DESC;

-- 3. Companies with highest ROE (latest year of financial_ratios per company)
SELECT r.company_id, c.company_name, r.year, r.return_on_equity_pct
FROM financial_ratios r
JOIN companies c ON r.company_id = c.id
WHERE r.year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY r.return_on_equity_pct DESC LIMIT 10;

-- 4. Year-over-year sales for TCS
SELECT year, sales FROM profitandloss WHERE company_id = 'TCS' ORDER BY year;

-- 5. Companies with negative net profit (loss-making years)
SELECT c.company_name, p.year, p.net_profit
FROM profitandloss p JOIN companies c ON p.company_id = c.id
WHERE p.net_profit < 0 ORDER BY p.net_profit ASC;

-- 6. Average monthly trading volume per company in 2024
SELECT company_id, ROUND(AVG(volume)) AS avg_volume
FROM stock_prices WHERE date >= '2024-01-01' AND date < '2025-01-01'
GROUP BY company_id ORDER BY avg_volume DESC LIMIT 10;

-- 7. Companies present in companies table but missing from financial_ratios
SELECT c.id, c.company_name
FROM companies c LEFT JOIN financial_ratios f ON c.id = f.company_id
WHERE f.company_id IS NULL;

-- 8. Balance sheet imbalance check (should return 0 rows in this dataset)
SELECT company_id, year, (total_assets - total_liabilities) AS diff
FROM balancesheet
WHERE ABS(total_assets - total_liabilities) > 0.01 * total_assets;

-- 9. Peer group sizes
SELECT peer_group_name, COUNT(*) AS n_members
FROM peer_groups GROUP BY peer_group_name ORDER BY n_members DESC;

-- 10. Companies with fewer than 5 distinct fiscal years of P&L history
SELECT company_id, COUNT(DISTINCT year) AS yrs
FROM profitandloss WHERE year != 'TTM'
GROUP BY company_id HAVING yrs < 5;
