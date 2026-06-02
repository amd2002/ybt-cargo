import tempfile
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from pathlib import Path
from app.services.parser import fmt_amount

NAVY  = HexColor("#1a3a5c")
GOLD  = HexColor("#FFD700")
LIGHT = HexColor("#E8EFF8")
GRAY  = HexColor("#F5F5F5")
WHITE = colors.white
BLACK = colors.black
GREEN = HexColor("#d1fae5")
LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "ybt_logo.jpg"

def sty(size=8, bold=False, color=BLACK, align=TA_LEFT):
    return ParagraphStyle("x", fontSize=size, textColor=color,
                          fontName="Helvetica-Bold" if bold else "Helvetica",
                          alignment=align, leading=size*1.4)

def generate_summary_pdf(job: Dict, clients: List[Dict]) -> str:
    """Génère le PDF récapitulatif du conteneur pour les agents terrain."""

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()

    doc = SimpleDocTemplate(
        tmp.name, pagesize=landscape(A4),
        topMargin=1.2*cm, bottomMargin=1.2*cm,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
    )

    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    header_data = [[
        Image(str(LOGO_PATH), width=2.2*cm, height=1.6*cm) if LOGO_PATH.exists()
            else Paragraph("YBT", sty(14, True, NAVY)),
        [
            Paragraph("YBT INTERNATIONAL OCEAN FREIGHT & LOGISTIC", sty(13, True, NAVY)),
            Paragraph("MOB: +8613145750861 / +8613612627740 / +23280983049 / +23276711790", sty(8, color=colors.gray)),
        ],
        [
            Paragraph(f"Conteneur : <b>{job['container_num']}</b>", sty(9, align=TA_RIGHT)),
            Paragraph(f"Chargement : <b>{job['load_date']}</b>", sty(9, align=TA_RIGHT)),
            Paragraph(f"ETA : <b>{job['eta']}</b>", sty(9, align=TA_RIGHT)),
        ]
    ]]
    header_tbl = Table(header_data, colWidths=[3*cm, 16*cm, 8*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Table([[""]], colWidths=[27*cm],
        style=[("LINEBELOW",(0,0),(0,0),2,NAVY),
               ("TOPPADDING",(0,0),(-1,-1),0),
               ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("LISTE DE SUIVI — RÉCUPÉRATION DES COLIS", sty(13, True, NAVY, TA_CENTER)))
    story.append(Spacer(1, 0.4*cm))

    # ── TABLEAU CLIENTS ───────────────────────────────────────────────────────
    headers = ["#", "CLIENT", "TÉLÉPHONE", "DEST.", "MARCHANDISES", "CBM",
               "FREIGHT", "CUSTOM", "TOTAL DÛ", "STATUT", "DATE RÉC.", "SIGNATURE"]

    rows = [headers]
    total_cbm = 0
    total_freight = 0
    total_custom = 0
    total_due = 0

    for i, c in enumerate(clients, 1):
        items_desc = " / ".join(
            it.get("description","")[:25] for it in (c.get("items") or [])[:3]
        )
        if len(c.get("items") or []) > 3:
            items_desc += f" +{len(c['items'])-3}"

        dest_badge = "🇬🇳 GN" if c.get("destination") == "GN" else "🌍 SL"

        rows.append([
            str(i),
            Paragraph(f"<b>{c['name']}</b>", sty(8)),
            c.get("phone","—"),
            dest_badge,
            Paragraph(items_desc, sty(7)),
            fmt_amount(c.get("total_cbm", 0)),
            f"${fmt_amount(c.get('freight', 0))}",
            f"${fmt_amount(c.get('custom', 0))}",
            Paragraph(f"<b>${fmt_amount(c.get('total_due', 0))}</b>", sty(9, True, NAVY, TA_CENTER)),
            "",   # Statut : En attente / Récupéré / Payé
            "",   # Date récupération
            "",   # Signature
        ])

        total_cbm     += c.get("total_cbm", 0)
        total_freight += c.get("freight", 0)
        total_custom  += c.get("custom", 0)
        total_due     += c.get("total_due", 0)

    # Ligne totaux
    rows.append([
        "", Paragraph("<b>TOTAL</b>", sty(9, True)), "", "", "",
        Paragraph(f"<b>{fmt_amount(total_cbm)} m³</b>", sty(9, True, align=TA_CENTER)),
        Paragraph(f"<b>${fmt_amount(total_freight)}</b>", sty(9, True, align=TA_CENTER)),
        Paragraph(f"<b>${fmt_amount(total_custom)}</b>", sty(9, True, align=TA_CENTER)),
        Paragraph(f"<b>${fmt_amount(total_due)}</b>", sty(10, True, NAVY, TA_CENTER)),
        "", "", "",
    ])

    col_w = [0.8*cm, 3.5*cm, 2.8*cm, 1.2*cm, 5*cm, 1.2*cm,
             1.8*cm, 1.8*cm, 2.2*cm, 2.5*cm, 2.2*cm, 2*cm]

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    nb = len(rows)

    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",   (0,0),  (-1,0),   NAVY),
        ("TEXTCOLOR",    (0,0),  (-1,0),   WHITE),
        ("FONTNAME",     (0,0),  (-1,0),   "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),  (-1,0),   7),
        ("ALIGN",        (0,0),  (-1,0),   "CENTER"),
        # Alternating rows
        *[("BACKGROUND", (0,i), (-1,i), GRAY) for i in range(2, nb-1, 2)],
        # Total row
        ("BACKGROUND",   (0,nb-1), (-1,nb-1), GOLD),
        ("FONTNAME",     (0,nb-1), (-1,nb-1), "Helvetica-Bold"),
        # Grid
        ("GRID",         (0,0),  (-1,-1),  0.5, colors.black),
        ("VALIGN",       (0,0),  (-1,-1),  "MIDDLE"),
        ("ALIGN",        (0,0),  (0,-1),   "CENTER"),
        ("ALIGN",        (5,0),  (8,-1),   "CENTER"),
        ("TOPPADDING",   (0,0),  (-1,-1),  4),
        ("BOTTOMPADDING",(0,0),  (-1,-1),  4),
        ("LEFTPADDING",  (0,0),  (-1,-1),  3),
        ("RIGHTPADDING", (0,0),  (-1,-1),  3),
        # Colonnes terrain (fond légèrement coloré)
        ("BACKGROUND",   (9,1),  (11,nb-2), HexColor("#FFFBEB")),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 0.5*cm))

    # ── LÉGENDE ───────────────────────────────────────────────────────────────
    legend = Table([[
        Paragraph("STATUT : &nbsp;&nbsp; ☐ En attente &nbsp;&nbsp; ☐ Récupéré &nbsp;&nbsp; ☐ Payé", sty(8)),
        Paragraph(f"Total clients : <b>{len(clients)}</b> &nbsp;&nbsp; "
                  f"Total CBM : <b>{fmt_amount(total_cbm)} m³</b> &nbsp;&nbsp; "
                  f"Total à encaisser : <b>${fmt_amount(total_due)}</b>", sty(9, True, NAVY, TA_RIGHT)),
    ]], colWidths=[14*cm, 13*cm])
    legend.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(legend)
    story.append(Spacer(1, 0.3*cm))
    story.append(Table([[""]], colWidths=[27*cm],
        style=[("LINEABOVE",(0,0),(0,0),1,NAVY),
               ("TOPPADDING",(0,0),(-1,-1),0),
               ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("YBT International Ocean Freight & Logistic — Foshan, China",
                            sty(7, color=colors.gray, align=TA_CENTER)))

    doc.build(story)
    return tmp.name
