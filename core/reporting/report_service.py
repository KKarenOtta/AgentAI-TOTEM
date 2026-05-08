from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.analytics.aggregators.time_series import build_time_series
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


def _rows_from_named(items: list[dict[str, Any]], first: str, second: str = "count") -> list[list[Any]]:
    rows = [[first, second]]

    for item in items[:10]:
        rows.append([_safe(item.get("name")), _safe(item.get(second))])

    if len(rows) == 1:
        rows.append(["-", "0"])

    return rows


def generate_company_report(company_id: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    build_time_series(company_id)

    data = build_company_dashboard(company_id)
    kpis = data.get("kpis") or {}
    ai = data.get("ai") or {}
    sync = data.get("sync_health") or {}
    sentiment = data.get("sentiment") or {}
    recommendation = data.get("recommendation_feedback") or {}
    campaigns = data.get("campaigns") or []
    stores = data.get("stores") or []
    daily = ((data.get("timeseries") or {}).get("daily") or [])[-10:]

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

    story.append(Paragraph("Sentimento e NPS", h2_style))
    story.append(
        _table(
            [
                ["Métrica", "Valor"],
                ["Registros analisados", _safe(sentiment.get("count"))],
                ["Sentimento médio", _safe(sentiment.get("avg_sentiment_score"))],
            ],
            [220, 250],
        )
    )
    story.append(_table(_rows_from_named(sentiment.get("sentiments") or [], "Sentimento")))
    story.append(_table(_rows_from_named(sentiment.get("frustration_risk") or [], "Risco de frustração")))

    story.append(Paragraph("Reward Learning de Campanhas", h2_style))
    reward_rows = [["Campanha", "Eventos", "Reward", "Cliques", "Conversões"]]
    for item in (recommendation.get("campaigns") or [])[:15]:
        reward_rows.append(
            [
                _safe(item.get("campaign_id")),
                _safe(item.get("events")),
                _safe(item.get("reward_sum")),
                _safe(item.get("clicks")),
                _safe(item.get("conversions")),
            ]
        )
    story.append(_table(reward_rows if len(reward_rows) > 1 else [["Campanha", "Eventos", "Reward", "Cliques", "Conversões"], ["-", "0", "0", "0", "0"]]))

    story.append(Paragraph("Série Temporal Diária", h2_style))
    daily_rows = [["Período", "Sessões", "Interações", "Leads", "NPS"]]
    for item in daily:
        daily_rows.append(
            [
                _safe(item.get("period")),
                _safe(item.get("sessions")),
                _safe(item.get("interactions")),
                _safe(item.get("leads")),
                _safe(item.get("nps")),
            ]
        )
    story.append(_table(daily_rows if len(daily_rows) > 1 else [["Período", "Sessões", "Interações", "Leads", "NPS"], ["-", "0", "0", "0", "0"]]))

    story.append(Paragraph("Intenções Detectadas", h2_style))
    story.append(_table(_rows_from_named(ai.get("intents") or [], "Intenção")))

    story.append(Paragraph("Fontes de Resposta", h2_style))
    story.append(_table(_rows_from_named(ai.get("response_sources") or [], "Fonte")))

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
