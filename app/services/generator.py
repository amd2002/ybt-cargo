import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from app.services.parser import fmt_amount

NAVY   = HexColor("#1a3a5c")
GOLD   = HexColor("#FFD700")
WHITE  = colors.white
BLACK  = colors.black
LIGHT  = HexColor("#E8EFF8")
NOTICE = HexColor("#EEF4FF")

LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "ybt_logo.jpg"

def generate_invoice_pdf(client: Dict[str, Any], container_num: str,
                          load_date: str, eta: str) -> str:
    """Génère une facture PDF avec reportlab et retourne son chemin."""

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()

    doc = SimpleDocTemplate(
        tmp.name, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
    )

    styles = getSampleStyleSheet()
    def sty(size=9, bold=False, color=BLACK, align=TA_LEFT):
        return ParagraphStyle("x", fontSize=size, textColor=color,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              alignment=align, leading=size*1.3)

    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    header_data = [[
        Image(str(LOGO_PATH), width=2.5*cm, height=1.9*cm) if LOGO_PATH.exists()
            else Paragraph("YBT", sty(14, True, NAVY)),
        [
            Paragraph("YBT INTERNATIONAL OCEAN FREIGHT & LOGISTIC", sty(12, True, NAVY)),
            # Paragraph("佛山市南海区里水镇里官路赤山段 72 号 A5 仓库", sty(8, color=colors.gray)),
            Paragraph("No.72 Chishan Section, Li guan Road, Lishui Town, Nanhai District, Foshan City", sty(8, color=colors.gray)),
            Paragraph("MOB: +8613145750861 / +8613612627740 / +23280983049 / +23276711790", sty(8, color=colors.gray)),
        ]
    ]]
    header_tbl = Table(header_data, colWidths=[3*cm, 14*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Ligne séparatrice
    story.append(Table([[""]], colWidths=[17*cm],
        style=[("LINEBELOW",(0,0),(0,0),2,NAVY),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1, 0.3*cm))

    # Date + titre
    story.append(Paragraph(f"40HQ GROUPAGE &nbsp;&nbsp;&nbsp; {load_date}",
                            sty(9, True, align=TA_RIGHT)))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("LOADING INVOICE", sty(16, True, NAVY, TA_CENTER)))
    story.append(Spacer(1, 0.4*cm))

    # ── Notice ────────────────────────────────────────────────────────────────
    notice_data = [[
        Paragraph("ALL INVOICE ARE EXPECTED TO BE PAID TWO WEEK BEFORE EXPECTED DELIVERY DATE<br/>"
                  "KINDLY CONTACT THE NUMBERS BELOW FOR PAYMENT AND GET A RECEIPT OF ALL PAYMENT "
                  "MADE IN ORDER TO CLAIM OR COLLECT YOUR GOODS<br/>"
                  "<b>MR IBRAHIM : +23276711790 &nbsp;&nbsp;&nbsp; MR EDDIE : +23280983049</b>",
                  sty(8, color=NAVY))
    ]]
    notice_tbl = Table(notice_data, colWidths=[17*cm])
    notice_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NOTICE),
        ("BOX", (0,0), (-1,-1), 0.5, NAVY),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(notice_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Calculs ───────────────────────────────────────────────────────────────
    total_cbm = client["total_cbm"]
    freight   = client["freight"]
    custom    = client["custom"]
    total_due = client["total_due"]
    rate      = client.get("rate", 280)

    items_active = [i for i in client["items"] if float(i.get("cbm", 0)) > 0]
    desc_lines   = "\n".join(f"• {it['description']}  ({it['quantity']})" for it in items_active)
    total_qty    = sum(int(str(it.get("quantity","1")).replace("托","").strip() or 1)
                       for it in client["items"] if str(it.get("quantity","")).strip().isdigit()
                       or True)

    # ── Tableau principal ─────────────────────────────────────────────────────
    headers = ["CUSTOMER\nNAME", "CONTAINER\n#", "DESCRIPTION", "QTY", "CBM",
               "FREIGHT", "CUSTOM", "ETA"]
    client_cell = f"{client['name']}\n{client.get('phone','')}"
    desc_cell   = desc_lines
    eta_cell    = f"Estimated\nArrival\n{eta}"

    row_data = [headers, [
        Paragraph(client_cell.replace("\n","<br/>"), sty(8)),
        Paragraph(container_num, sty(8, align=TA_CENTER)),
        Paragraph(desc_cell.replace("\n","<br/>"), sty(7)),
        Paragraph(str(total_qty), sty(8, align=TA_CENTER)),
        Paragraph(fmt_amount(total_cbm), sty(8, align=TA_CENTER)),
        Paragraph(f"${fmt_amount(freight)}", sty(8, True, NAVY, TA_CENTER)),
        Paragraph(f"${fmt_amount(custom)}", sty(8, True, NAVY, TA_CENTER)),
        Paragraph(eta_cell.replace("\n","<br/>"), sty(8, align=TA_CENTER)),
    ], ["","","","","","","",""], ["","","","","","","",""]]

    col_w = [3*cm, 2.5*cm, 4.5*cm, 1.2*cm, 1.3*cm, 1.5*cm, 1.5*cm, 1.8*cm]
    main_tbl = Table(row_data, colWidths=col_w, rowHeights=[0.8*cm, None, 0.7*cm, 0.7*cm])
    main_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 7),
        ("ALIGN",      (0,0), (-1,0), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,1), (0,1), HexColor("#F0F4FA")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0), (-1,-1), 4),
    ]))
    story.append(main_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ── Récapitulatif ─────────────────────────────────────────────────────────
    sum_data = [
        ["Total CBM",     fmt_amount(total_cbm) + " m³"],
        ["Tarif ($/CBM)", f"${fmt_amount(rate)}"],
        ["Freight",       f"${fmt_amount(freight)}"],
        ["Custom",        f"${fmt_amount(custom)}"],
        ["TOTAL TO PAYE", f"${fmt_amount(total_due)}"],
    ]
    sum_tbl = Table(sum_data, colWidths=[4*cm, 3*cm], hAlign="RIGHT")
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,3), LIGHT),
        ("BACKGROUND", (0,4), (-1,4), GOLD),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",   (0,4), (-1,4), "Helvetica-Bold"),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN",      (1,0), (1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("TEXTCOLOR",  (0,4), (-1,4), NAVY),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Table([[""]], colWidths=[17*cm],
        style=[("LINEABOVE",(0,0),(0,0),1,NAVY),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("YBT International Ocean Freight & Logistic — Foshan, China",
                            sty(7, color=colors.gray, align=TA_CENTER)))

    doc.build(story)
    return tmp.name