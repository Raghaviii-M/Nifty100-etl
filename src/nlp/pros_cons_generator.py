import numpy as np
import pandas as pd
from src.data_access import ROOT, build_master, company_info, cagr, is_financial

OUT = ROOT / "output"


# ---------- helpers ----------
def conf(margin, ref):
    """Confidence 61 at the threshold, rising to 100 as the signal gets stronger."""
    return int(min(100, round(61 + 39 * min(1, max(margin, 0) / max(abs(ref), 1e-9)))))

def streak_conf(n, need):
    return min(100, 65 + 7 * (n - need))

def trailing(mask):
    n = 0
    for v in reversed(list(mask)):
        if v:
            n += 1
        else:
            break
    return n

def last(s):
    s = s.dropna()
    return s.iloc[-1] if len(s) else np.nan

def inc_streak(s): return trailing(s.diff() > 0)
def dec_streak(s): return trailing(s.diff() < 0)


# ---------- PRO rules (each takes d = one company's rows, sorted by year) ----------
def p1(d):  n = trailing(d.roe > 20);  return streak_conf(n, 3) if n >= 3 else 0
def p2(d):  n = trailing(d.fcf > 0);   return streak_conf(n, 5) if n >= 5 else 0
def p3(d):  return 90 if last(d.borrowings) == 0 else 0
def p4(d):  c = cagr(d.sales, 5);      return conf(c - 15, 15) if c > 15 else 0
def p5(d):  v = last(d.opm);           return conf(v - 25, 25) if v > 25 else 0
def p6(d):  c = cagr(d.net_profit, 5); return conf(c - 20, 20) if c > 20 else 0
def p7(d):
    if last(d.borrowings) == 0: return 85
    i = last(d.icr);                   return conf(i - 10, 10) if i > 10 else 0
def p8(d):
    y = last(d.div_yield)
    return conf(y - 2, 2) if y > 2 and last(d.fcf) > 0 else 0
def p9(d):  c = cagr(d.eps, 5);        return conf(c - 15, 15) if c > 15 else 0
def p10(d): n = inc_streak(d.roe);     return streak_conf(n, 3) if n >= 3 else 0
def p11(d):
    s, p = cagr(d.sales, 5), cagr(d.net_profit, 5)
    return conf(p - s, 10) if p > s else 0          # PAT growing faster than revenue
def p12(d):
    n = trailing((d.total_assets.diff() > 0) & (d.borrowings.diff() < 0))
    return streak_conf(n, 2) + 5 if n >= 2 else 0

# ---------- CON rules ----------
def c1(d):  v = last(d.de);            return conf(v - 2, 2) if v > 2 else 0
def c2(d):  n = trailing(d.fcf < 0);   return streak_conf(n, 3) if n >= 3 else 0
def c3(d):  n = dec_streak(d.opm);     return streak_conf(n, 3) if n >= 3 else 0
def c4(d):  return 95 if last(d.net_profit) < 0 else 0
def c5(d):  n = dec_streak(d.sales);   return streak_conf(n, 2) if n >= 2 else 0
def c6(d):  i = last(d.icr);           return conf(1.5 - i, 1.5) if i < 1.5 else 0
def c7(d):  v = last(d.payout);        return conf(v - 100, 100) if v > 100 else 0
def c8(d):  n = inc_streak(d.de);      return streak_conf(n, 3) if n >= 3 else 0
def c9(d):  n = dec_streak(d.eps);     return streak_conf(n, 3) if n >= 3 else 0
def c10(d): v = last(d.roce);          return conf(10 - v, 10) if v < 10 else 0
def c11(d):
    x = last(d.borrowings) / last(d.op_profit) if last(d.op_profit) else np.nan
    return conf(x - 3, 3) if x > 3 else 0
def c12(d): c = cagr(d.sales, 5);      return conf(5 - c, 5) if c < 5 else 0

# (rule_id, type, function, text, is_debt_based)
RULES = [
 ("PRO_1","pro",p1,"Consistently high return on equity above 20% demonstrates exceptional capital efficiency",False),
 ("PRO_2","pro",p2,"Strong free cash flow generation over 5 years signals healthy business fundamentals",False),
 ("PRO_3","pro",p3,"Debt-free balance sheet provides financial flexibility and eliminates interest burden",True),
 ("PRO_4","pro",p4,"Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",False),
 ("PRO_5","pro",p5,"Operating profit margin above 25% indicates strong pricing power and cost discipline",False),
 ("PRO_6","pro",p6,"Net profit compounding at above 20% over 5 years creates significant shareholder value",False),
 ("PRO_7","pro",p7,"Very high interest coverage ratio reflects negligible financial stress from debt servicing",True),
 ("PRO_8","pro",p8,"Consistent dividend yield above 2% backed by positive free cash flow",False),
 ("PRO_9","pro",p9,"Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",False),
 ("PRO_10","pro",p10,"Return on equity improving for 3 consecutive years shows strengthening business quality",False),
 ("PRO_11","pro",p11,"Revenue growing slower than profits shows improving operating leverage and scale benefits",False),
 ("PRO_12","pro",p12,"Growing asset base funded by internal accruals reflects self-sustaining growth",True),
 ("CON_1","con",c1,"Debt-to-equity ratio of {x} is elevated for a non-financial company and warrants monitoring",True),
 ("CON_2","con",c2,"Free cash flow negative for 3 consecutive years raises concern about cash generation quality",False),
 ("CON_3","con",c3,"Operating margins declining for 3 consecutive years suggest pricing or cost pressure",False),
 ("CON_4","con",c4,"Company reported a net loss in the most recent financial year",False),
 ("CON_5","con",c5,"Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",False),
 ("CON_6","con",c6,"Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",True),
 ("CON_7","con",c7,"Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",False),
 ("CON_8","con",c8,"Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",True),
 ("CON_9","con",c9,"Earnings per share declining for 3 consecutive years reflects deteriorating profitability",False),
 ("CON_10","con",c10,"Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",False),
 ("CON_11","con",c11,"Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",True),
 ("CON_12","con",c12,"Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",False),
]


def main():
    m = build_master()
    info = company_info().set_index("company_id")
    rows = []
    for cid, d in m.groupby("company_id"):
        d = d.sort_values("yr").reset_index(drop=True)
        fin = is_financial(info.loc[cid, "broad_sector"]) if cid in info.index else False
        for rid, typ, fn, text, debt_based in RULES:
            if fin and debt_based:
                continue
            try:
                c = fn(d)
            except Exception as e:
                print(f"[error] {cid} {rid}: {e}")
                continue
            if c and c > 60:
                if rid == "CON_1":
                    text = text.format(x=f"{last(d.de):.2f}")
                rows.append({"company_id": cid, "type": typ, "rule_id": rid,
                             "text": text, "confidence_pct": int(c)})
    out = pd.DataFrame(rows, columns=["company_id", "type", "rule_id", "text", "confidence_pct"])
    out.to_csv(OUT / "pros_cons_generated.csv", index=False)
    print("rows written:", len(out))

    # ---- verification: every company needs >=1 pro and >=1 con ----
    for typ in ("pro", "con"):
        have = set(out[out.type == typ].company_id)
        missing = sorted(set(info.index) - have)
        print(f"companies with NO {typ}: {len(missing)} {missing}")


if __name__ == "__main__":
    main()