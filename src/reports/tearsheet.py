import io
import sys
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from src.data_access import ROOT, build_master, company_info

NAVY = colors.HexColor("#1F3A5F")
ss = getSampleStyleSheet()
TITLE = ParagraphStyle("t", parent=ss["Title"], textColor=colors.white, fontSize=18, leading=22, alignment=0)
H2 = ParagraphStyle("h2", parent=ss["Heading3"], textColor=NAVY, spaceBefore=6, spaceAfter=3)
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=11)
TILE = ParagraphStyle("tile", parent=ss["BodyText"], fontSize=9, leading=14, alignment=1)


def fmt(v, suffix="", dec=1):
    return "N/A" if v is None or pd.isna(v) else f"{v:,.{dec}f}{suffix}"


def fig_img(fig, w, h):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w * mm, height=h * mm)


def new_fig(w, h):
    return plt.subplots(figsize=(w / 25.4, h / 25.4))


def bar_chart(d, col, title, color, w=88, h=55):
    fig, ax = new_fig(w, h)
    ax.bar(d.yr.astype(int).astype(str), d[col].fillna(0), color=color)
    ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=6)
    plt.setp(ax.get_xticklabels(), rotation=60)
    return fig_img(fig, w, h)


def roe_roce_chart(d, w=180, h=60):
    fig, ax = new_fig(w, h)
    x = d.yr.astype(int).astype(str)
    ax.plot(x, d.roe, color="#1F3A5F", marker="o", label="ROE %")
    ax.set_ylabel("ROE %", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, d.roce, color="#E07B00", marker="s", label="ROCE %")
    ax2.set_ylabel("ROCE %", fontsize=7)
    ax.set_title("ROE and ROCE", fontsize=8)
    ax.tick_params(labelsize=6); ax2.tick_params(labelsize=6)
    fig.legend(fontsize=6, loc="upper left")
    return fig_img(fig, w, h)


def balance_chart(d, w=88, h=60):
    fig, ax = new_fig(w, h)
    x = d.yr.astype(int).astype(str)
    eq, br, ol = d.equity.fillna(0), d.borrowings.fillna(0), d.other_liabilities.fillna(0)
    ax.bar(x, eq, label="Equity", color="#1F3A5F")
    ax.bar(x, br, bottom=eq, label="Borrowings", color="#C0392B")
    ax.bar(x, ol, bottom=eq + br, label="Other liab.", color="#95A5A6")
    ax.set_title("Balance sheet composition", fontsize=8)
    ax.legend(fontsize=5); ax.tick_params(labelsize=6)
    plt.setp(ax.get_xticklabels(), rotation=60)
    return fig_img(fig, w, h)


def waterfall_chart(row, w=88, h=60):
    fig, ax = new_fig(w, h)
    cfo, cfi, cff = [0 if pd.isna(v) else v for v in (row.cfo, row.cfi, row.cff)]
    net = cfo + cfi + cff
    labels = ["CFO", "CFI", "CFF", "Net"]
    heights = [cfo, cfi, cff, net]
    bottoms = [0, cfo, cfo + cfi, 0]
    cols = ["#2E8B57" if v >= 0 else "#C0392B" for v in heights]
    ax.bar(labels, heights, bottom=bottoms, color=cols)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Cash flow (latest year)", fontsize=8)
    ax.tick_params(labelsize=6)
    return fig_img(fig, w, h)


def bullets(items, color):
    if not items:
        return [Paragraph("No significant signals.", BODY)]
    return [Paragraph(escape(t), BODY, bulletText="•") for t in items]


def build_tearsheet(cid, master, info, pc, ca_label, out_path):
    d = master[master.company_id == cid].sort_values("yr").tail(10)
    cur = d.iloc[-1]
    name = info.loc[cid, "company_name"] if cid in info.index else cid

    story = []
    header = Table([[Paragraph(f"{escape(str(name))} <font size=11>({escape(cid)})</font>", TITLE)]],
                   colWidths=[180 * mm])
    header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                                ("TOPPADDING", (0, 0), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [header, Spacer(1, 5 * mm)]

    kpis = [("Revenue (Cr)", fmt(cur.sales, "", 0)), ("Net Profit (Cr)", fmt(cur.net_profit, "", 0)),
            ("ROE", fmt(cur.roe, "%")), ("ROCE", fmt(cur.roce, "%")),
            ("OPM", fmt(cur.opm, "%")), ("Debt / Equity", fmt(cur.de, "", 2))]
    cells = [Paragraph(f"<font size=7 color='#666666'>{l}</font><br/><font size=13><b>{v}</b></font>", TILE)
             for l, v in kpis]
    tiles = Table([cells[:3], cells[3:]], colWidths=[60 * mm] * 3, rowHeights=[18 * mm] * 2)
    tiles.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                               ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F9")),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [tiles, Spacer(1, 5 * mm)]
    story += [Table([[bar_chart(d, "sales", "Revenue (Cr)", "#1F3A5F"),
                      bar_chart(d, "net_profit", "Net Profit (Cr)", "#2E8B57")]],
                    colWidths=[90 * mm, 90 * mm])]
    story += [Spacer(1, 4 * mm), roe_roce_chart(d), PageBreak()]

    # ---------------- page 2 ----------------
    story += [Paragraph("Balance sheet & cash flow", H2),
              Table([[balance_chart(d), waterfall_chart(cur)]], colWidths=[90 * mm, 90 * mm]),
              Spacer(1, 3 * mm)]
    mine = pc[pc.company_id == cid].sort_values("confidence_pct", ascending=False)
    pros = mine[mine.type == "pro"].head(5).text.tolist()
    cons = mine[mine.type == "con"].head(5).text.tolist()
    story += [Paragraph("<font color='#2E8B57'>Pros</font>", H2)] + bullets(pros, "green")
    story += [Paragraph("<font color='#C0392B'>Cons</font>", H2)] + bullets(cons, "red")
    badge = Table([[Paragraph(f"<font color='white'><b>Capital allocation: {escape(str(ca_label))}</b></font>", BODY)]],
                  colWidths=[180 * mm])
    badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                               ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [Spacer(1, 6 * mm), badge]

    SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                      topMargin=12 * mm, bottomMargin=12 * mm).build(story)


def load_inputs():
    master = build_master()
    info = company_info().set_index("company_id")
    pc = pd.read_csv(ROOT / "output" / "pros_cons_generated.csv")
    ca = pd.read_excel(ROOT / "output" / "cashflow_intelligence.xlsx").set_index("company_id")["capital_allocation_label"]
    return master, info, pc, ca


if __name__ == "__main__":
    master, info, pc, ca = load_inputs()
    test_ids = sys.argv[1:] or ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]
    out_dir = ROOT / "reports" / "tearsheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    for cid in test_ids:
        build_tearsheet(cid, master, info, pc, ca.get(cid, "N/A"), out_dir / f"{cid}_tearsheet.pdf")
        print("done", cid)

def batch():
    from pypdf import PdfReader
    master, info, pc, ca = load_inputs()
    out_dir = ROOT / "reports" / "tearsheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    skipped, errors = [], []
    for cid in sorted(info.index):
        n_years = master[(master.company_id == cid) & master.sales.notna()].shape[0]
        if n_years < 3:
            skipped.append({"company_id": cid, "years_of_data": n_years})
            continue
        path = out_dir / f"{cid}_tearsheet.pdf"
        try:
            build_tearsheet(cid, master, info, pc, ca.get(cid, "N/A"), path)
            pages = len(PdfReader(str(path)).pages)
            if pages != 2:
                errors.append({"company_id": cid, "problem": f"{pages} pages"})
        except Exception as e:
            errors.append({"company_id": cid, "problem": str(e)})
    pd.DataFrame(skipped, columns=["company_id", "years_of_data"]).to_csv(
        ROOT / "output" / "skipped_tearsheets.csv", index=False)
    pd.DataFrame(errors, columns=["company_id", "problem"]).to_csv(
        ROOT / "output" / "tearsheet_errors.csv", index=False)
    print("skipped:", len(skipped), "errors:", len(errors))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        batch()
    else:
        master, info, pc, ca = load_inputs()
        out_dir = ROOT / "reports" / "tearsheets"
        out_dir.mkdir(parents=True, exist_ok=True)
        for cid in (sys.argv[1:] or ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]):
            build_tearsheet(cid, master, info, pc, ca.get(cid, "N/A"), out_dir / f"{cid}_tearsheet.pdf")