from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.dashboard.service import build_company_dashboard


REPORT_DIR = Path("data/reports")


def _safe(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def _table(rows: list[list[Any]], widths: list[int] | None = None) -> Table:
    table = Table(rows, colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )
    return table


def generate_company_report(company_id: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    data = build_company_dashboard(company_id)
    kpis = data.get("kpis") or {}
    ai = data.get("ai") or {}
    sync = data.get("sync_health") or {}
    campaigns = data.get("campaigns") or []
    stores = data.get("stores") or []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORT_DIR / f"{company_id}_executive_report_{timestamp}.pdf"

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TotemTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "TotemH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "TotemBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    story = []

    story.append(Paragraph(f"Relatório Executivo TOTEM • {company_id}", title_style))
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", body_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumo Executivo", h2_style))
    story.append(
        _table(
            [
                ["Indicador", "Valor"],
                ["Sessões", _safe(kpis.get("sessions"))],
                ["Interações", _safe(kpis.get("interactions"))],
                ["Leads", _safe(kpis.get("leads"))],
                ["Consentimentos LGPD", _safe(kpis.get("consents"))],
                ["Cupons emitidos", _safe(kpis.get("issued"))],
                ["Cupons resgatados", _safe(kpis.get("redeemed"))],
                ["Conversão", f"{_safe(kpis.get('conversion'))}%"],
                ["NPS médio", _safe(kpis.get("nps_avg"))],
                ["Latência média", f"{_safe(kpis.get('avg_latency'))}s"],
            ],
            [220, 250],
        )
    )

    story.append(Paragraph("IA Operacional", h2_style))
    story.append(
        _table(
            [
                ["Métrica", "Valor"],
                ["Semantic hit rate", f"{_safe(ai.get('semantic_hit_rate'))}%"],
                ["Fallback LLM", f"{_safe(ai.get('fallback_rate'))}%"],
            ],
            [220, 250],
        )
    )

    story.append(Paragraph("Intenções Detectadas", h2_style))
    intent_rows = [["Intenção", "Ocorrências"]]
    for row in ai.get("intents") or []:
        intent_rows.append([_safe(row.get("name")), _safe(row.get("count"))])
    story.append(_table(intent_rows if len(intent_rows) > 1 else [["Intenção", "Ocorrências"], ["-", "0"]]))

    story.append(Paragraph("Fontes de Resposta", h2_style))
    source_rows = [["Fonte", "Ocorrências"]]
    for row in ai.get("response_sources") or []:
        source_rows.append([_safe(row.get("name")), _safe(row.get("count"))])
    story.append(_table(source_rows if len(source_rows) > 1 else [["Fonte", "Ocorrências"], ["-", "0"]]))

    story.append(Paragraph("Campanhas", h2_style))
    campaign_rows = [["Campanha", "Impressões", "Emitidos", "Resgatados", "CTR", "Conversão"]]
    for item in campaigns[:20]:
        campaign_rows.append(
            [
                _safe(item.get("campaign_id")),
                _safe(item.get("impressions")),
                _safe(item.get("issued")),
                _safe(item.get("redeemed")),
                f"{_safe(item.get('ctr'))}%",
                f"{_safe(item.get('conversion'))}%",
            ]
        )
    story.append(_table(campaign_rows if len(campaign_rows) > 1 else [["Campanha", "Impressões", "Emitidos", "Resgatados", "CTR", "Conversão"], ["-", "0", "0", "0", "0%", "0%"]]))

    story.append(Paragraph("Resgates por Loja", h2_style))
    store_rows = [["Loja", "Resgates"]]
    for item in stores[:20]:
        store_rows.append([_safe(item.get("store_id")), _safe(item.get("redeemed"))])
    story.append(_table(store_rows if len(store_rows) > 1 else [["Loja", "Resgates"], ["-", "0"]]))

    story.append(Paragraph("Saúde da Sincronização", h2_style))
    story.append(
        _table(
            [
                ["Status", "Quantidade"],
                ["Pendente", _safe(sync.get("pending"))],
                ["Falhou", _safe(sync.get("failed"))],
                ["Sincronizado", _safe(sync.get("synced"))],
                ["Total", _safe(sync.get("total"))],
            ],
            [220, 250],
        )
    )

    doc.build(story)
    return out
