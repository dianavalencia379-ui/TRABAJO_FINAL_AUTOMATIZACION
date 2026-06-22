"""Generador de PDF acotado a la hoja Resumen.

Independiente de reports/pdf_generator.py a propósito (ese archivo es de
Johanna, para la pestaña Informes) -- este módulo no lo importa ni lo
modifica, así que no hay riesgo de pisar su trabajo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
import re
from typing import Any


class ResumenReportError(RuntimeError):
    """Error controlado para la generación del PDF de Resumen."""


@dataclass(frozen=True)
class GeneratedResumenPdf:
    file_name: str
    content: bytes
    generated_at: str


def is_resumen_pdf_available() -> tuple[bool, str | None]:
    """Verifica si ReportLab está disponible para generar el PDF de Resumen."""
    try:
        _load_reportlab()
    except ResumenReportError as exc:
        return False, str(exc)
    return True, None


def generate_resumen_pdf(*, resumen_data: dict[str, Any]) -> GeneratedResumenPdf:
    """Genera el PDF acotado a lo que muestra la hoja Resumen.

    `resumen_data` ya viene armado por tab_overview.py con los mismos
    valores que se ven en pantalla (no se recalcula nada aquí).
    """
    modules = _load_reportlab()
    colors = modules["colors"]
    pagesizes = modules["pagesizes"]
    styles_module = modules["styles"]
    units = modules["units"]
    platypus = modules["platypus"]

    styles = styles_module.getSampleStyleSheet()
    title_style = styles_module.ParagraphStyle(
        "ResumenTitle", parent=styles["Title"],
        textColor=colors.HexColor("#0F172A"), fontSize=20, spaceAfter=8,
    )
    subtitle_style = styles_module.ParagraphStyle(
        "ResumenSubtitle", parent=styles["Heading2"],
        textColor=colors.HexColor("#334155"), fontSize=11, spaceAfter=12,
    )
    section_style = styles_module.ParagraphStyle(
        "ResumenSection", parent=styles["Heading2"],
        textColor=colors.HexColor("#0F172A"), fontSize=14, spaceBefore=10, spaceAfter=8,
    )
    body_style = styles_module.ParagraphStyle(
        "ResumenBody", parent=styles["BodyText"], leading=15, spaceAfter=8,
    )

    buffer = BytesIO()
    doc = platypus.SimpleDocTemplate(
        buffer, pagesize=pagesizes.LETTER,
        topMargin=1.6 * units.cm, bottomMargin=1.6 * units.cm,
        leftMargin=1.8 * units.cm, rightMargin=1.8 * units.cm,
    )

    elements: list[Any] = []
    generated_at = datetime.now(UTC).isoformat()

    elements.append(platypus.Paragraph("Dashboard_Financiero · Resumen ejecutivo", subtitle_style))
    elements.append(platypus.Paragraph("Resumen Financiero del Portafolio", title_style))
    elements.append(platypus.Paragraph(
        f"Generado: {generated_at} · Portafolio: {resumen_data.get('portfolio_name', 'n/d')} "
        f"· Periodo: {resumen_data.get('periodo', 'n/d')}",
        body_style,
    ))
    elements.append(platypus.Spacer(1, 0.3 * units.cm))

    # Indicadores clave (las 6 tarjetas)
    elements.append(platypus.Paragraph("Indicadores clave", section_style))
    kpi_rows = [["Indicador", "Valor"]] + [[label, value] for label, value in resumen_data.get("kpis", [])]
    elements.append(_build_table(kpi_rows, modules, col_widths=[8.5 * units.cm, 7.5 * units.cm]))
    elements.append(platypus.Spacer(1, 0.3 * units.cm))

    # Rendimiento bruto y neto por horizonte
    elements.append(platypus.Paragraph("Rendimiento bruto y neto por horizonte", section_style))
    horizon_rows = [["Periodo", "Rendimiento Bruto", "Rendimiento Neto"]] + [
        [row["Periodo"], row["Rendimiento Bruto"], row["Rendimiento Neto"]]
        for row in resumen_data.get("horizon_rows", [])
    ]
    elements.append(_build_table(horizon_rows, modules, col_widths=[5.3 * units.cm] * 3))
    elements.append(platypus.Spacer(1, 0.3 * units.cm))

    # Recomendación para Rebalanceo (resumen, no la tabla detallada por activo)
    elements.append(platypus.Paragraph("Recomendación para Rebalanceo", section_style))
    rebalance = resumen_data.get("rebalance_summary", {})
    rebalance_rows = [
        ["Indicador", "Valor"],
        ["Aumentar", str(rebalance.get("increase_count", 0))],
        ["Reducir", str(rebalance.get("reduce_count", 0))],
        ["Mantener", str(rebalance.get("hold_count", 0))],
        ["Capital a reasignar", f"${rebalance.get('total_to_reallocate', 0.0):,.2f}"],
    ]
    elements.append(_build_table(rebalance_rows, modules, col_widths=[8.5 * units.cm, 7.5 * units.cm]))
    elements.append(platypus.Spacer(1, 0.3 * units.cm))

    # Composición por activo
    elements.append(platypus.Paragraph("Composición por activo", section_style))
    composition_rows = [["Ticker", "Valor", "Peso"]] + [
        [item.get("ticker", "n/d"), f"${item.get('value', 0.0):,.2f}", f"{item.get('weight_pct', 0.0):.2f}%"]
        for item in resumen_data.get("composition", [])
    ]
    elements.append(_build_table(composition_rows, modules, col_widths=[5.3 * units.cm] * 3))
    elements.append(platypus.Spacer(1, 0.4 * units.cm))

    elements.append(platypus.Paragraph(
        "Este informe tiene fines académicos y demostrativos. No constituye asesoramiento "
        "financiero ni recomendación de inversión.",
        body_style,
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return GeneratedResumenPdf(
        file_name=_build_resumen_filename(resumen_data),
        content=pdf_bytes,
        generated_at=generated_at,
    )


def _build_resumen_filename(resumen_data: dict[str, Any]) -> str:
    raw_name = str(resumen_data.get("portfolio_name", "portafolio")).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_") or "portafolio"
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"resumen_financiero_{slug}_{stamp}.pdf"


def _build_table(rows: list[list[str]], modules: dict[str, Any], *, col_widths: list[float]):
    colors = modules["colors"]
    platypus = modules["platypus"]
    table = platypus.Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(platypus.TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5F7")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CDD3DA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _load_reportlab() -> dict[str, Any]:
    try:
        from reportlab.lib import colors
        from reportlab.lib import pagesizes
        from reportlab.lib import styles
        from reportlab.lib import units
        from reportlab import platypus
    except ImportError as exc:
        raise ResumenReportError(
            "ReportLab no está instalado en este entorno. Agrega 'reportlab' a requirements.txt."
        ) from exc
    return {
        "colors": colors, "pagesizes": pagesizes, "styles": styles,
        "units": units, "platypus": platypus,
    }