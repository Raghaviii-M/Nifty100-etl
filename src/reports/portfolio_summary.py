from xml.sax.saxutils import escape

import matplotlib
import pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from src.data_access import ROOT, build_master, company_info

pdfmetrics.registerFont(TTFont("DejaVu", str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")))
ss = getSampleStyleSheet()
CELL = ParagraphStyle("c", parent=ss["BodyText"], fontName="DejaVu", fontSize=11, leading=15)

# (column, label, higher_is_better)
KPIS = [("sales", "Revenue (Cr)", True), ("net_profit", "Net Profit (Cr)", True), ("opm", "OPM %", True),
        ("roe", "ROE %", True), ("roce", "ROCE %", True), ("de", "Debt / Equity", False)]


def arrow(cur, prev, higher_better):
    if pd.isna(cur) or pd.isna(prev) or prev == 0:
        return "<font color='#888888'>–</font>"
    change = (cur - prev) / abs(prev) * 100
    if abs(change) <= 2:
        return "<font color='#888888'>►</font>"
    improved = change > 0 if higher_better else change < 0
    return "<font color='#2E8B57'>▲</font>" if improved else "<font color='#C0392B'>▼</font>"


def main():
    m = build_master()
    info = company_info().set_index("company_id").sort_index()   # alphabetical by ticker
    story = []
    for cid in info.index:
        d = m[m.company_id == cid].sort_values("yr")
        if len(d) < 2:
            continue
        cur, prev = d.iloc[-1], d.iloc[-2]
        story += [Paragraph(f"<b>{escape(str(info.loc[cid, 'company_name']))}</b> ({escape(cid)})", ss["Title"]),
                  Paragraph(f"Sector: {escape(str(info.loc[cid, 'broad_sector']))}", ss["BodyText"]),
                  Spacer(1, 8 * mm)]
        rows = [[Paragraph(label, CELL),
                 Paragraph("N/A" if pd.isna(cur[c]) else f"{cur[c]:,.2f}", CELL),
                 Paragraph(arrow(cur[c], prev[c], hb), CELL)] for c, label, hb in KPIS]
        t = Table(rows, colWidths=[70 * mm, 50 * mm, 20 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey)]))
        story += [t, PageBreak()]

    out = ROOT / "reports" / "portfolio"
    out.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out / "portfolio_summary.pdf"), pagesize=A4).build(story)


if __name__ == "__main__":
    main()