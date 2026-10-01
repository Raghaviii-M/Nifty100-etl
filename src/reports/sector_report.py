import re
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.data_access import ROOT, build_master, company_info

NAVY = colors.HexColor("#1F3A5F")
ss = getSampleStyleSheet()
SMALL = ParagraphStyle("s", parent=ss["BodyText"], fontSize=7, leading=9)
SMALLB = ParagraphStyle("sb", parent=SMALL, textColor=colors.white, fontName="Helvetica-Bold")
METRICS = [("sales", "Revenue"), ("net_profit", "Net Profit"), ("opm", "OPM %"), ("roe", "ROE %"),
           ("roce", "ROCE %"), ("de", "D/E"), ("icr", "ICR"), ("div_yield", "Div Yield %")]


def f(v):
    return "N/A" if pd.isna(v) else f"{v:,.1f}"


def main():
    m = build_master()
    latest = m.sort_values("yr").groupby("company_id").tail(1).set_index("company_id")
    info = company_info().set_index("company_id")
    out = ROOT / "reports" / "sector"
    out.mkdir(parents=True, exist_ok=True)

    for sector, grp in info.groupby("broad_sector"):
        ids = [c for c in grp.index if c in latest.index]
        data = latest.loc[ids]
        story = [Paragraph(f"<b>{escape(str(sector))}</b> sector report", ss["Title"]),
                 Paragraph(f"{len(ids)} companies", ss["BodyText"]), Spacer(1, 6 * mm),
                 Paragraph("<b>Median KPIs</b>", ss["Heading3"])]
        med = Table([[Paragraph(l, SMALLB) for _, l in METRICS],
                     [Paragraph(f(data[c].median()), SMALL) for c, _ in METRICS]],
                    colWidths=[22 * mm] * 8)
        med.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey)]))
        story += [med, PageBreak(), Paragraph("<b>Companies</b>", ss["Heading3"])]

        rows = [[Paragraph("Company", SMALLB)] + [Paragraph(l, SMALLB) for _, l in METRICS]]
        for cid in ids:
            rows.append([Paragraph(escape(str(grp.loc[cid, "company_name"])), SMALL)] +
                        [Paragraph(f(data.loc[cid, c]), SMALL) for c, _ in METRICS])
        t = Table(rows, colWidths=[45 * mm] + [16 * mm] * 8, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t)

        fname = re.sub(r"[^A-Za-z0-9]+", "_", str(sector)).strip("_")
        SimpleDocTemplate(str(out / f"{fname}_report.pdf"), pagesize=A4, leftMargin=15 * mm,
                          rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm).build(story)
        print("done", sector)


if __name__ == "__main__":
    main()