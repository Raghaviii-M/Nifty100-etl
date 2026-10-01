import numpy as np
import pandas as pd
from src.data_access import ROOT, build_master, company_info, cagr, year_num

OUT = ROOT / "output"
CA_CSV = ROOT / "output" / "capital_allocation.csv"      # <-- adjust to where yours is


def cfo_label(x):
    if pd.isna(x): return "N/A"
    return "High Quality" if x > 1.0 else "Moderate" if x >= 0.5 else "Accrual Risk"

def capex_label(x):
    if pd.isna(x): return "N/A"
    return "Asset Light" if x < 3 else "Moderate" if x <= 8 else "Capital Intensive"


def build():
    m = build_master()
    info = company_info().set_index("company_id")
    ca = pd.read_csv(CA_CSV)
    ca["yr"] = year_num(ca["year"])
    latest_pattern = ca.sort_values("yr").groupby("company_id")["pattern"].last()   # <-- 'pattern' column name

    rows = []
    for cid, d in m.groupby("company_id"):
        d = d.sort_values("yr")
        last5 = d.tail(5)
        ratio = (last5.cfo / last5.net_profit.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
        score = ratio.mean()
        cur = d.iloc[-1]
        capex = abs(cur.cfi) / cur.sales * 100 if cur.sales else np.nan
        prev_borrow = d.borrowings.iloc[-2] if len(d) > 1 else np.nan
        rows.append({
            "company_id": cid,
            "sector": info.loc[cid, "broad_sector"] if cid in info.index else None,
            "cfo_quality_score": round(score, 2),
            "cfo_quality_label": cfo_label(score),
            "capex_intensity_pct": round(capex, 2),
            "capex_label": capex_label(capex),
            "fcf_cagr_5yr": cagr(d.fcf, 5),
            "fcf_conversion_pct": cur.fcf / cur.net_profit * 100 if cur.net_profit else np.nan,
            "distress_flag": bool(cur.cfo < 0 and cur.cff > 0),
            "deleveraging_flag": bool(cur.cff < 0 and cur.borrowings < prev_borrow),
            "capital_allocation_label": latest_pattern.get(cid),
            "_cfo": cur.cfo, "_cff": cur.cff, "_np": cur.net_profit,
        })
    df = pd.DataFrame(rows)

    distress = df[df.distress_flag][["company_id", "_cfo", "_cff", "_np"]].rename(
        columns={"_cfo": "cfo", "_cff": "cff", "_np": "latest_net_profit"})
    distress.to_csv(OUT / "distress_alerts.csv", index=False)
    df.drop(columns=["_cfo", "_cff", "_np"]).to_excel(OUT / "cashflow_intelligence.xlsx", index=False)
    print(df.shape, "| distress:", len(distress))


if __name__ == "__main__":
    build()