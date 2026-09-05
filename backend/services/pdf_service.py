"""
PDF Report Generator (TRD 6: backend/services/pdf_service.py; PRD 6.8)
Renders a persisted report + its prescriptions into a branded PDF using ReportLab.
"""
import re
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

RISK_COLOR_HEX = {
    "Low": "#2e7d32",
    "Medium": "#ef6c00",
    "High": "#c62828",
}


def _render_ticket_markup(text: str) -> str:
    """
    Gemini returns the sprint ticket as free-form markdown-ish plain text, but
    ReportLab's Paragraph parses its own mini-HTML -- so a stray "<" or "&" in
    the model output raises a parse error and would break PDF generation for the
    whole report. Escape everything first, then re-introduce only the two bits of
    formatting worth keeping: **bold** and line breaks.
    """
    safe = escape(text or "", quote=False)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe, flags=re.DOTALL)
    # Collapse the blank line between markdown blocks so sections don't drift apart.
    safe = re.sub(r"\n{2,}", "\n", safe).strip()
    return safe.replace("\n", "<br/>")


def _is_ticket_fallback(ticket: str, recommended_action: str) -> bool:
    """
    True when the stored ticket carries no more information than the
    recommended_action printed directly above it, in which case rendering the
    block just says the same thing twice. Two ways that happens:
      * the row predates the sprint_ticket column, so finalize_report() stored
        the recommended_action verbatim; or
      * gemini_service fell back on an API failure (a 429 on the free tier is
        routine), which stores "Execute action: {recommended_action}".
    Keep the prefix in sync with gemini_service.render_sprint_tickets().
    """
    action = (recommended_action or "").strip()
    return ticket == action or ticket == f"Execute action: {action}"


def _format_created_at(raw: str) -> str:
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return raw or ""


def generate_report_pdf(report: dict, prescriptions: list, cloud_provider: str = "") -> bytes:
    """
    report: a row from the `reports` table (dict).
    prescriptions: rows from the `prescriptions` table, already ordered by rank_position.
    Returns the finished PDF as raw bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CliPRxTitle", parent=styles["Title"], fontSize=22, spaceAfter=4)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body_style = styles["Normal"]
    action_style = ParagraphStyle("Action", parent=styles["Normal"], spaceBefore=2, spaceAfter=4)
    ticket_style = ParagraphStyle(
        "Ticket", parent=styles["Normal"], fontSize=9, leading=12,
        leftIndent=8, spaceBefore=4, spaceAfter=6,
        borderPadding=0, textColor=colors.HexColor("#333333"),
    )
    ticket_label_style = ParagraphStyle(
        "TicketLabel", parent=styles["Normal"], fontSize=8, spaceBefore=6,
        textColor=colors.grey,
    )

    elements = []

    elements.append(Paragraph("CliPRx Cost Optimization Report", title_style))
    meta_bits = [f"Report ID: {report['id']}", f"Generated: {_format_created_at(report.get('created_at', ''))}"]
    if cloud_provider:
        meta_bits.append(f"Cloud Provider: {cloud_provider.upper()}")
    elements.append(Paragraph(" &nbsp;|&nbsp; ".join(meta_bits), meta_style))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd")))
    elements.append(Spacer(1, 12))

    # Summary section (PRD 6.8: "a summary section with total estimated savings")
    savings_min = report.get("total_savings_min") or 0
    savings_max = report.get("total_savings_max") or 0
    summary_data = [
        ["Estimated Monthly Savings", f"${savings_min:,.2f} - ${savings_max:,.2f}"],
        ["Recommendations", str(report.get("prescription_count", len(prescriptions)))],
        ["Flagged Conflicts", str(report.get("conflict_count", 0))],
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 3.5 * inch])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#eeeeee")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 18))

    if not prescriptions:
        elements.append(Paragraph("No cost-saving recommendations were generated for this report.", body_style))
    else:
        elements.append(Paragraph("Recommendations", styles["Heading1"]))
        for p in prescriptions:
            rank = p.get("rank_position", "-")
            elements.append(Paragraph(f"#{rank} &nbsp;{p['service_name']}", h2_style))

            if p.get("is_conflicted"):
                elements.append(Paragraph(
                    f"<font color='#c62828'><b>CONFLICTED:</b> {p.get('conflict_reason', '')}</font>",
                    body_style,
                ))
                elements.append(Spacer(1, 4))

            elements.append(Paragraph(escape(p["recommended_action"], quote=False), action_style))

            # The Gemini-authored sprint ticket (pipeline stage 7) -- the actual
            # deliverable an engineer picks up.
            ticket = (p.get("sprint_ticket") or "").strip()
            if ticket and not _is_ticket_fallback(ticket, p["recommended_action"]):
                elements.append(Paragraph("SPRINT TICKET", ticket_label_style))
                elements.append(Paragraph(_render_ticket_markup(ticket), ticket_style))

            risk = p.get("risk_level", "Low")
            risk_hex = RISK_COLOR_HEX.get(risk, "#000000")
            detail_data = [[
                Paragraph(f"<b>Savings:</b> ${p['savings_min']:,.2f} - ${p['savings_max']:,.2f}/mo", body_style),
                Paragraph(f"<b>Effort:</b> {p['engineering_hours']} hrs", body_style),
                Paragraph(f"<b>Risk:</b> <font color='{risk_hex}'>{risk}</font>", body_style),
                Paragraph(f"<b>ROI:</b> {p['roi_score']}", body_style),
            ]]
            detail_table = Table(detail_data, colWidths=[1.9 * inch] * 4)
            detail_table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(detail_table)
            elements.append(Paragraph(f"Pattern: {p['pattern_id']}", meta_style))
            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(width="100%", color=colors.HexColor("#eeeeee")))
            elements.append(Spacer(1, 10))

    def _footer(canvas, doc_):
        # PRD 6.8: "a footer identifying it as generated by CliPRx"
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            doc_.pagesize[0] / 2, 0.4 * inch,
            f"Generated by CliPRx  |  Page {doc_.page}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
