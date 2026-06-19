"""Generador reusable de informes PDF por usuario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
import importlib
from pathlib import Path
import re
from typing import Any


class ReportGenerationError(RuntimeError):
    """Error controlado para generación de informes."""


@dataclass(frozen=True)
class GeneratedPdfReport:
    file_name: str
    content: bytes
    generated_at: str
    warnings: list[str]
    sections: list[str]


def is_pdf_generation_available() -> tuple[bool, str | None]:
    try:
        _load_reportlab()
    except ReportGenerationError as exc:
        return False, str(exc)
    return True, None


def build_report_payload(
    *,
    selected_user: dict[str, Any],
    dashboard_data: dict[str, Any],
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    portfolio_snapshot = dashboard_data.get("portfolio_snapshot", {})
    evolution_snapshot = dashboard_data.get("evolution_snapshot", {})
    hrp_snapshot = dashboard_data.get("hrp_snapshot", {})
    advisor_snapshot = dashboard_data.get("advisor_snapshot", {})
    user_portfolios = dashboard_data.get("user_portfolios", [])

    portfolio_summary = portfolio_snapshot.get("portfolio_summary", {})
    evolution_metrics = evolution_snapshot.get("metrics", {})
    advisor_summary = advisor_snapshot.get("summary", {})
    hrp_diagnostics = hrp_snapshot.get("diagnostics", {})
    advisor_diagnostics = advisor_snapshot.get("diagnostics", {})

    warnings = [
        *hrp_diagnostics.get("warnings", []),
        *advisor_diagnostics.get("warnings", []),
    ]
    warnings = _deduplicate_strings(warnings)

    positions = portfolio_snapshot.get("positions_table", [])
    composition = portfolio_snapshot.get("composition", {}).get("by_asset", [])
    evolution_series = evolution_snapshot.get("series", [])
    weights_table = hrp_snapshot.get("weights_table", [])
    advisor_table = advisor_snapshot.get("advisor_table", [])

    report_rows = {
        "user_rows": [
            ["Usuario", selected_user.get("user_name", "n/d")],
            ["Email", selected_user.get("user_email", "n/d")],
            ["Portfolios", str(portfolio_summary.get("portfolio_count", 0))],
            ["Posiciones", str(portfolio_summary.get("position_count", 0))],
            ["Valor total", _format_currency(portfolio_summary.get("total_current_value", 0.0))],
            ["Coste total", _format_currency(portfolio_summary.get("total_cost_basis", 0.0))],
            ["Rentabilidad acumulada", _format_pct(evolution_metrics.get("cumulative_return_pct", 0.0))],
            ["Rentabilidad anualizada", _format_pct(evolution_metrics.get("annualized_return_pct", 0.0))],
            ["Máximo drawdown", _format_pct(evolution_metrics.get("max_drawdown_pct", 0.0))],
            ["Fuente HRP", str(hrp_diagnostics.get("price_source", "n/d"))],
        ],
        "portfolio_rows": [
            [
                item.get("portfolio_name", "n/d"),
                str(item.get("position_count", 0)),
                _format_currency(item.get("invested_amount", 0.0)),
                str(item.get("created_at", "n/d")),
            ]
            for item in user_portfolios
        ],
        "composition_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_number(item.get("quantity", 0.0), 2),
                _format_currency(item.get("value", 0.0)),
                _format_pct(item.get("weight_pct", 0.0)),
            ]
            for item in composition
        ],
        "position_rows": [
            [
                item.get("portfolio_name", "n/d"),
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_number(item.get("quantity", 0.0), 2),
                _format_currency(item.get("current_value", 0.0)),
                _format_pct(item.get("weight_pct", 0.0)),
            ]
            for item in positions
        ],
        "evolution_metric_rows": [
            ["Inicio", str(evolution_metrics.get("start_date") or "n/d")],
            ["Fin", str(evolution_metrics.get("end_date") or "n/d")],
            ["Valor inicial", _format_currency(evolution_metrics.get("start_value", 0.0))],
            ["Valor final", _format_currency(evolution_metrics.get("end_value", 0.0))],
            ["Puntos históricos", str(evolution_metrics.get("points", 0))],
            ["Mejor periodo", _format_pct(evolution_metrics.get("best_period_return_pct", 0.0))],
            ["Peor periodo", _format_pct(evolution_metrics.get("worst_period_return_pct", 0.0))],
            ["Drawdown actual", _format_pct(evolution_metrics.get("latest_drawdown_pct", 0.0))],
        ],
        "evolution_rows": [
            [
                item.get("date", "n/d"),
                _format_currency(item.get("total_value", 0.0)),
                _format_pct(item.get("period_return_pct", 0.0)),
                _format_pct(item.get("cumulative_return_pct", 0.0)),
                _format_pct(item.get("drawdown_pct", 0.0)),
            ]
            for item in evolution_series[-12:]
        ],
        "current_weight_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_pct(float(item.get("current_weight", 0.0)) * 100.0),
                _format_currency(item.get("current_value", 0.0)),
            ]
            for item in sorted(weights_table, key=lambda row: float(row.get("current_weight", 0.0)), reverse=True)
        ],
        "hrp_weight_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_pct(float(item.get("recommended_weight", 0.0)) * 100.0),
                _format_pct(float(item.get("difference", 0.0)) * 100.0),
            ]
            for item in sorted(weights_table, key=lambda row: float(row.get("recommended_weight", 0.0)), reverse=True)
        ],
        "rebalance_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_pct(item.get("current_weight_pct", 0.0)),
                _format_pct(item.get("target_weight_pct", 0.0)),
                _format_currency(item.get("value_delta", 0.0)),
                item.get("action_label", "n/d"),
            ]
            for item in advisor_table
        ],
        "diagnostic_rows": [
            ["Fuente de precios HRP", str(hrp_diagnostics.get("price_source", "n/d"))],
            ["Histórico usado", str(hrp_diagnostics.get("history_rows", 0))],
            ["Periodo de precios", f"{hrp_diagnostics.get('history_start', 'n/d')} → {hrp_diagnostics.get('history_end', 'n/d')}"],
            ["Filas de retornos", str(hrp_diagnostics.get("returns_rows", 0))],
            ["Clustering", str(hrp_diagnostics.get("clustering_method", "n/d"))],
            ["Umbral rebalanceo", _format_pct(advisor_snapshot.get("rebalance_threshold_pct", 0.0))],
        ],
    }

    sections = [
        "Datos del usuario",
        "Portfolio",
        "Composición",
        "Valor total",
        "Evolución histórica",
        "Pesos actuales",
        "Pesos HRP",
        "Tabla de rebalanceo",
        "Comentario final",
        "Aviso académico",
    ]

    return {
        "generated_at": generated_at,
        "file_name": build_report_filename(selected_user),
        "title": "Informe financiero por usuario",
        "subtitle": f"Usuario: {selected_user.get('user_name', 'n/d')}",
        "warnings": warnings,
        "sections": sections,
        "user": {
            "name": selected_user.get("user_name", "n/d"),
            "email": selected_user.get("user_email", "n/d"),
        },
        "summary": {
            "portfolio_summary": portfolio_summary,
            "evolution_metrics": evolution_metrics,
            "advisor_summary": advisor_summary,
            "hrp_diagnostics": hrp_diagnostics,
        },
        "tables": report_rows,
        "commentary": _build_final_comment(
            portfolio_summary=portfolio_summary,
            evolution_metrics=evolution_metrics,
            advisor_summary=advisor_summary,
            warnings=warnings,
        ),
        "academic_notice": (
            "Este informe tiene fines académicos y demostrativos. "
            "No constituye asesoramiento financiero, recomendación de inversión ni validación profesional del riesgo."
        ),
    }


def generate_user_report_pdf(
    *,
    selected_user: dict[str, Any],
    dashboard_data: dict[str, Any],
) -> GeneratedPdfReport:
    payload = build_report_payload(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )
    modules = _load_reportlab()

    colors = modules["colors"]
    pagesizes = modules["pagesizes"]
    styles_module = modules["styles"]
    units = modules["units"]
    platypus = modules["platypus"]

    styles = styles_module.getSampleStyleSheet()
    title_style = styles_module.ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#0F172A"),
        fontSize=20,
        spaceAfter=8,
    )
    subtitle_style = styles_module.ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#334155"),
        fontSize=11,
        spaceAfter=12,
    )
    section_style = styles_module.ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0F172A"),
        fontSize=14,
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = styles_module.ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=8,
    )
    warning_style = styles_module.ParagraphStyle(
        "ReportWarning",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#92400E"),
        backColor=colors.HexColor("#FEF3C7"),
        borderPadding=8,
        leading=14,
        spaceAfter=8,
    )
    footnote_style = styles_module.ParagraphStyle(
        "ReportFootnote",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#475569"),
        fontSize=9,
        leading=12,
    )

    buffer = BytesIO()
    document = platypus.SimpleDocTemplate(
        buffer,
        pagesize=pagesizes.landscape(pagesizes.A4),
        leftMargin=18 * units.mm,
        rightMargin=18 * units.mm,
        topMargin=16 * units.mm,
        bottomMargin=14 * units.mm,
        title=payload["title"],
        author="Dashboard_Financiero",
        subject="Informe PDF por usuario",
    )

    story: list[Any] = []
    story.append(platypus.Paragraph(payload["title"], title_style))
    story.append(platypus.Paragraph(payload["subtitle"], subtitle_style))
    story.append(
        platypus.Paragraph(
            f"Generado: {payload['generated_at']} · Secciones: {', '.join(payload['sections'])}",
            footnote_style,
        )
    )
    story.append(platypus.Spacer(1, 8))

    if payload["warnings"]:
        story.append(platypus.Paragraph("<b>Advertencias de datos</b>", section_style))
        for warning in payload["warnings"]:
            story.append(platypus.Paragraph(_escape(warning), warning_style))

    story.append(platypus.Paragraph("Datos del usuario y valor total", section_style))
    story.append(_build_table(modules, ["Campo", "Valor"], payload["tables"]["user_rows"], [120, 220]))

    story.append(platypus.Paragraph("Portfolio del usuario", section_style))
    story.append(
        _build_table(
            modules,
            ["Portfolio", "Posiciones", "Capital estimado", "Creado"],
            payload["tables"]["portfolio_rows"] or [["Sin portfolios", "0", "$0.00", "n/d"]],
            [180, 80, 120, 110],
        )
    )

    story.append(platypus.Paragraph("Composición actual", section_style))
    story.append(
        _build_table(
            modules,
            ["Ticker", "Activo", "Cantidad", "Valor", "Peso"],
            payload["tables"]["composition_rows"] or [["n/d", "Sin datos", "0", "$0.00", "0.00%"]],
            [70, 190, 80, 100, 70],
        )
    )

    story.append(platypus.Paragraph("Posiciones y valor total", section_style))
    story.append(
        _build_table(
            modules,
            ["Portfolio", "Ticker", "Activo", "Cantidad", "Valor actual", "Peso"],
            payload["tables"]["position_rows"] or [["n/d", "n/d", "Sin posiciones", "0", "$0.00", "0.00%"]],
            [130, 60, 180, 70, 100, 70],
        )
    )

    story.append(platypus.Paragraph("Evolución histórica", section_style))
    story.append(_build_table(modules, ["Métrica", "Valor"], payload["tables"]["evolution_metric_rows"], [150, 160]))
    story.append(platypus.Spacer(1, 6))
    story.append(
        _build_table(
            modules,
            ["Fecha", "Valor total", "Retorno periodo", "Retorno acumulado", "Drawdown"],
            payload["tables"]["evolution_rows"] or [["n/d", "$0.00", "0.00%", "0.00%", "0.00%"]],
            [90, 100, 100, 110, 90],
        )
    )

    story.append(platypus.PageBreak())
    story.append(platypus.Paragraph("Pesos actuales", section_style))
    story.append(
        _build_table(
            modules,
            ["Ticker", "Activo", "Peso actual", "Valor actual"],
            payload["tables"]["current_weight_rows"] or [["n/d", "Sin datos", "0.00%", "$0.00"]],
            [70, 220, 90, 100],
        )
    )

    story.append(platypus.Paragraph("Pesos HRP recomendados", section_style))
    story.append(
        _build_table(
            modules,
            ["Ticker", "Activo", "Peso HRP", "Desvío vs actual"],
            payload["tables"]["hrp_weight_rows"] or [["n/d", "Sin datos", "0.00%", "0.00%"]],
            [70, 220, 90, 100],
        )
    )

    story.append(platypus.Paragraph("Tabla de rebalanceo", section_style))
    story.append(
        _build_table(
            modules,
            ["Ticker", "Activo", "Peso actual", "Peso objetivo", "Delta valor", "Acción"],
            payload["tables"]["rebalance_rows"] or [["n/d", "Sin datos", "0.00%", "0.00%", "$0.00", "Mantener"]],
            [60, 200, 85, 90, 95, 75],
        )
    )

    story.append(platypus.Paragraph("Comentario final", section_style))
    story.append(platypus.Paragraph(_escape(payload["commentary"]), body_style))

    story.append(platypus.Paragraph("Diagnóstico de soporte", section_style))
    story.append(_build_table(modules, ["Indicador", "Valor"], payload["tables"]["diagnostic_rows"], [150, 240]))

    story.append(platypus.Paragraph("Aviso académico", section_style))
    story.append(platypus.Paragraph(_escape(payload["academic_notice"]), footnote_style))

    document.build(story, onFirstPage=_page_header_footer(modules), onLaterPages=_page_header_footer(modules))

    return GeneratedPdfReport(
        file_name=payload["file_name"],
        content=buffer.getvalue(),
        generated_at=payload["generated_at"],
        warnings=payload["warnings"],
        sections=payload["sections"],
    )


def build_report_filename(selected_user: dict[str, Any]) -> str:
    raw_email = str(selected_user.get("user_email", "usuario")).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw_email).strip("_") or "usuario"
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"informe_{slug}_{stamp}.pdf"


def persist_generated_report(report: GeneratedPdfReport, *, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / report.file_name
    file_path.write_bytes(report.content)
    return file_path


def _build_final_comment(
    *,
    portfolio_summary: dict[str, Any],
    evolution_metrics: dict[str, Any],
    advisor_summary: dict[str, Any],
    warnings: list[str],
) -> str:
    total_value = _format_currency(portfolio_summary.get("total_current_value", 0.0))
    cumulative_return = _format_pct(evolution_metrics.get("cumulative_return_pct", 0.0))
    annualized_return = _format_pct(evolution_metrics.get("annualized_return_pct", 0.0))
    increase_count = int(advisor_summary.get("increase_count", 0) or 0)
    reduce_count = int(advisor_summary.get("reduce_count", 0) or 0)
    hold_count = int(advisor_summary.get("hold_count", 0) or 0)

    base_comment = (
        f"El portfolio consolida un valor estimado de {total_value}, con una rentabilidad acumulada de {cumulative_return} "
        f"y anualizada de {annualized_return}. El advisor identifica {increase_count} activos para aumentar, "
        f"{reduce_count} para reducir y {hold_count} para mantener."
    )
    if warnings:
        return f"{base_comment} El informe incorpora advertencias de datos: {'; '.join(warnings)}."
    return base_comment


def _build_table(
    modules: dict[str, Any],
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
) -> Any:
    colors = modules["colors"]
    platypus = modules["platypus"]

    table = platypus.Table([headers, *rows], colWidths=widths, repeatRows=1)
    table.setStyle(
        platypus.TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _page_header_footer(modules: dict[str, Any]):
    colors = modules["colors"]

    def _callback(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(document.leftMargin, 16, "Dashboard_Financiero · Informe PDF")
        canvas.drawRightString(document.pagesize[0] - document.rightMargin, 16, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    return _callback


def _load_reportlab() -> dict[str, Any]:
    try:
        return {
            "colors": importlib.import_module("reportlab.lib.colors"),
            "pagesizes": importlib.import_module("reportlab.lib.pagesizes"),
            "styles": importlib.import_module("reportlab.lib.styles"),
            "units": importlib.import_module("reportlab.lib.units"),
            "platypus": importlib.import_module("reportlab.platypus"),
        }
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ReportGenerationError(
            "La generación PDF requiere ReportLab. Instala dependencias con requirements.txt para habilitar la descarga."
        ) from exc


def _format_currency(value: Any) -> str:
    return f"${float(value or 0.0):,.2f}"


def _format_pct(value: Any) -> str:
    return f"{float(value or 0.0):,.2f}%"


def _format_number(value: Any, digits: int = 2) -> str:
    return f"{float(value or 0.0):,.{digits}f}"


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _deduplicate_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique
