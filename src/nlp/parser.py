import re
import pandas as pd
from src.data_access import ROOT, load, build_master, cagr

OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*(-?[\d.]+)%", re.I)   # task regex (+ negatives)
TTM = re.compile(r"TTM:?\s*(-?[\d.]+)%", re.I)                   # period_years = 0 means TTM
FIELDS = ["compounded_sales_growth", "compounded_profit_growth", "stock_price_cagr", "roe"]


def main():
    df = load("analysis")
    parsed, failures = [], []
    for _, row in df.iterrows():
        for field in FIELDS:
            text = str(row[field]).strip()
            if text in ("", "nan", "None"):
                continue
            matches = [(int(m.group(1)), float(m.group(2))) for m in PATTERN.finditer(text)]
            matches += [(0, float(m.group(1))) for m in TTM.finditer(text)]
            if not matches:
                failures.append({"company_id": row["company_id"], "metric_type": field, "raw_text": text})
            for years, val in matches:
                parsed.append({"company_id": row["company_id"], "metric_type": field,
                               "period_years": years, "value_pct": val})

    pd.DataFrame(parsed).to_csv(OUT / "analysis_parsed.csv", index=False)
    pd.DataFrame(failures, columns=["company_id", "metric_type", "raw_text"]).to_csv(
        OUT / "parse_failures.csv", index=False)
    print(f"parsed={len(parsed)}  failures={len(failures)}")

    # ---- cross-validation against numbers computed from the database ----
    m = build_master()
    source = {"compounded_sales_growth": "sales", "compounded_profit_growth": "net_profit"}
    rows = []
    for r in parsed:
        col = source.get(r["metric_type"])
        if col is None or r["period_years"] == 0:
            continue
        s = m[m.company_id == r["company_id"]][col]
        computed = cagr(s, r["period_years"])
        diff = abs(computed - r["value_pct"]) if pd.notna(computed) else None
        rows.append({**r, "computed_cagr": computed, "diff": diff,
                     "needs_review": bool(diff is not None and diff > 5)})
    pd.DataFrame(rows).to_csv(OUT / "analysis_validation.csv", index=False)
    print("flagged for review:", sum(r["needs_review"] for r in rows))


if __name__ == "__main__":
    main()