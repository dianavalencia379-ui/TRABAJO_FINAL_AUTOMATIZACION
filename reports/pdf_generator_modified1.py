# ============================================================
# reports/pdf_generator_modified1.py — Generador PDF mejorado
# Versión extendida con gráficos (torta, línea, barras),
# tablas dinámicas adaptativas y estilos corporativos.
# ============================================================

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from io import BytesIO
import importlib
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Sequence


# ------------------------------------------------------------
# Excepciones y modelos de datos
# ------------------------------------------------------------

class ReportGenerationError(RuntimeError):
    """Error controlado para fallos en la generación de informes PDF."""


@dataclass(frozen=True)
class GeneratedPdfReport:
    """Resultado inmutable de una generación de informe PDF."""
    file_name: str       # Nombre del archivo PDF
    content: bytes       # Contenido binario del PDF
    generated_at: str    # Timestamp ISO de generación
    warnings: list[str]  # Advertencias registradas
    sections: list[str]  # Secciones incluidas en el informe


# ------------------------------------------------------------
# Paleta de colores corporativa
# ------------------------------------------------------------

# Colores principales reutilizados en tablas y gráficos
_PALETTE_HEX = (
    "#2563EB", "#16A34A", "#D97706", "#DC2626", "#7C3AED",
    "#0891B2", "#DB2777", "#65A30D", "#475569", "#CA8A04",
)
_INK = "#0F172A"        # Color principal de texto (casi negro)
_MUTED = "#475569"      # Color de texto secundario (gris)
_GRID = "#CBD5E1"       # Color de bordes de tablas
_POSITIVE = "#15803D"   # Color para valores positivos (verde)
_NEGATIVE = "#B91C1C"   # Color para valores negativos (rojo)


# ------------------------------------------------------------
# Carga de dependencias ReportLab (con caché)
# ------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_reportlab() -> dict[str, Any]:
    """
    Importa una sola vez los módulos de ReportLab requeridos.
    Usa lru_cache para evitar reimportaciones en llamadas sucesivas.
    Lanza ReportGenerationError si ReportLab no está instalado.
    """
    try:
        return {
            "colors":     importlib.import_module("reportlab.lib.colors"),
            "pagesizes":  importlib.import_module("reportlab.lib.pagesizes"),
            "styles":     importlib.import_module("reportlab.lib.styles"),
            "units":      importlib.import_module("reportlab.lib.units"),
            "platypus":   importlib.import_module("reportlab.platypus"),
            "shapes":     importlib.import_module("reportlab.graphics.shapes"),
            "piecharts":  importlib.import_module("reportlab.graphics.charts.piecharts"),
            "linecharts": importlib.import_module("reportlab.graphics.charts.linecharts"),
            "barcharts":  importlib.import_module("reportlab.graphics.charts.barcharts"),
            "legends":    importlib.import_module("reportlab.graphics.charts.legends"),
        }
    except ImportError as exc:
        raise ReportGenerationError(
            "La generación PDF requiere ReportLab. "
            "Instala dependencias con requirements.txt para habilitar la descarga."
        ) from exc


def is_pdf_generation_available() -> tuple[bool, str | None]:
    """
    Verifica si ReportLab está disponible.
    Retorna (True, None) si está disponible, o (False, mensaje) si no.
    """
    try:
        _load_reportlab()
    except ReportGenerationError as exc:
        return False, str(exc)
    return True, None


# ------------------------------------------------------------
# Funciones auxiliares de formato y conversión
# ------------------------------------------------------------

# Expresión regular para extraer números de textos formateados
_NUMERIC_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _to_float(value: Any, default: float = 0.0) -> float:
    """
    Convierte cualquier valor a float de forma segura.
    Maneja strings con $, % y comas. Retorna default si falla.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(
            str(value).replace(",", "").replace("%", "").replace("$", "").strip()
        )
    except (TypeError, ValueError):
        return default


def _format_currency(value: Any) -> str:
    """Formatea un valor como importe monetario en dólares."""
    return f"${_to_float(value):,.2f}"


def _format_pct(value: Any) -> str:
    """Formatea un valor numérico como porcentaje legible."""
    return f"{_to_float(value):,.2f}%"


def _format_number(value: Any, digits: int = 2) -> str:
    """Formatea un número con la cantidad indicada de decimales."""
    return f"{_to_float(value):,.{digits}f}"


def _escape(value: str) -> str:
    """Escapa caracteres reservados XML antes de insertarlos en párrafos PDF."""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _deduplicate_strings(values: Iterable[str]) -> list[str]:
    """Elimina avisos repetidos preservando el orden original."""
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _cell_sign(text: Any) -> int:
    """
    Detecta el signo de un valor formateado en una celda.
    Retorna +1 (positivo), -1 (negativo) o 0 (cero/no numérico).
    """
    match = _NUMERIC_RE.search(str(text).replace("\u2212", "-"))
    if not match:
        return 0
    number = _to_float(match.group())
    return (number > 0) - (number < 0)


# ------------------------------------------------------------
# Tabla dinámica (pivot)
# ------------------------------------------------------------

def build_pivot_table(
    rows: Sequence[dict[str, Any]],
    *,
    group_by: str,
    value_key: str | None = None,
    agg: str = "sum",
    label_default: str = "n/d",
) -> list[dict[str, Any]]:
    """
    Construye una tabla pivote agrupando filas por una clave.

    Parámetros:
      group_by      — campo para agrupar
      value_key     — campo numérico a agregar
      agg           — función de agregación: 'sum', 'avg', 'max', 'min'
      label_default — valor por defecto para claves vacías
    """
    buckets: "OrderedDict[str, list[float]]" = OrderedDict()
    for row in rows:
        key = str(row.get(group_by, label_default) or label_default)
        measure = _to_float(row.get(value_key)) if value_key else 0.0
        buckets.setdefault(key, []).append(measure)

    result: list[dict[str, Any]] = []
    for key, measures in buckets.items():
        if agg == "sum":
            value = sum(measures)
        elif agg == "avg":
            value = sum(measures) / len(measures) if measures else 0.0
        elif agg == "max":
            value = max(measures) if measures else 0.0
        elif agg == "min":
            value = min(measures) if measures else 0.0
        else:
            raise ValueError(f"Agregación no soportada: {agg}")
        result.append({"group": key, "count": len(measures), "value": value})

    # Ordenar por valor descendente
    result.sort(key=lambda item: item["value"], reverse=True)
    return result


# ------------------------------------------------------------
# Construcción del payload del informe
# ------------------------------------------------------------

def build_report_payload(
    *,
    selected_user: dict[str, Any],
    dashboard_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Arma la estructura intermedia usada para renderizar el informe PDF.
    Incluye tablas formateadas, datos para gráficos y pivot tables.
    """
    generated_at = datetime.now(UTC).isoformat()

    # Extraer snapshots del dashboard
    portfolio_snapshot = dashboard_data.get("portfolio_snapshot", {})
    evolution_snapshot = dashboard_data.get("evolution_snapshot", {})
    hrp_snapshot = dashboard_data.get("hrp_snapshot", {})
    advisor_snapshot = dashboard_data.get("advisor_snapshot", {})
    user_portfolios = dashboard_data.get("user_portfolios", [])

    # Resúmenes de cada snapshot
    portfolio_summary = portfolio_snapshot.get("portfolio_summary", {})
    evolution_metrics = evolution_snapshot.get("metrics", {})
    advisor_summary = advisor_snapshot.get("summary", {})
    hrp_diagnostics = hrp_snapshot.get("diagnostics", {})
    advisor_diagnostics = advisor_snapshot.get("diagnostics", {})

    # Consolidar y deduplicar advertencias
    warnings = _deduplicate_strings([
        *hrp_diagnostics.get("warnings", []),
        *advisor_diagnostics.get("warnings", []),
    ])

    # Extraer datos de tablas
    positions = portfolio_snapshot.get("positions_table", [])
    composition = portfolio_snapshot.get("composition", {}).get("by_asset", [])
    evolution_series = evolution_snapshot.get("series", [])
    weights_table = hrp_snapshot.get("weights_table", [])
    advisor_table = advisor_snapshot.get("advisor_table", [])

    # Construir filas formateadas para cada sección del informe
    report_rows = {
        # Datos generales del usuario
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
        # Portfolios del usuario
        "portfolio_rows": [
            [
                item.get("portfolio_name", "n/d"),
                str(item.get("position_count", 0)),
                _format_currency(item.get("invested_amount", 0.0)),
                str(item.get("created_at", "n/d")),
            ]
            for item in user_portfolios
        ],
        # Composición por activo
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
        # Posiciones del portfolio
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
        # Métricas de evolución histórica
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
        # Serie histórica (últimos 12 puntos)
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
        # Pesos actuales ordenados de mayor a menor
        "current_weight_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_pct(_to_float(item.get("current_weight", 0.0)) * 100.0),
                _format_currency(item.get("current_value", 0.0)),
            ]
            for item in sorted(
                weights_table,
                key=lambda row: _to_float(row.get("current_weight", 0.0)),
                reverse=True
            )
        ],
        # Pesos HRP recomendados ordenados de mayor a menor
        "hrp_weight_rows": [
            [
                item.get("ticker", "n/d"),
                item.get("asset_name", "n/d"),
                _format_pct(_to_float(item.get("recommended_weight", 0.0)) * 100.0),
                _format_pct(_to_float(item.get("difference", 0.0)) * 100.0),
            ]
            for item in sorted(
                weights_table,
                key=lambda row: _to_float(row.get("recommended_weight", 0.0)),
                reverse=True
            )
        ],
        # Tabla de rebalanceo con acciones
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
        # Diagnóstico técnico HRP
        "diagnostic_rows": [
            ["Fuente de precios HRP", str(hrp_diagnostics.get("price_source", "n/d"))],
            ["Histórico usado", str(hrp_diagnostics.get("history_rows", 0))],
            ["Periodo de precios", f"{hrp_diagnostics.get('history_start', 'n/d')} → {hrp_diagnostics.get('history_end', 'n/d')}"],
            ["Filas de retornos", str(hrp_diagnostics.get("returns_rows", 0))],
            ["Clustering", str(hrp_diagnostics.get("clustering_method", "n/d"))],
            ["Umbral rebalanceo", _format_pct(advisor_snapshot.get("rebalance_threshold_pct", 0.0))],
        ],
    }

    # Tabla dinámica (pivot) por portfolio
    pivot = build_pivot_table(
        positions, group_by="portfolio_name", value_key="current_value", agg="sum"
    )
    total_pivot_value = sum(item["value"] for item in pivot)
    report_rows["pivot_portfolio_rows"] = [
        [
            item["group"],
            str(item["count"]),
            _format_currency(item["value"]),
            _format_pct((item["value"] / total_pivot_value * 100.0) if total_pivot_value else 0.0),
        ]
        for item in pivot
    ]
    # Fila de totales del pivot
    report_rows["pivot_portfolio_total"] = [
        "Total",
        str(sum(item["count"] for item in pivot)),
        _format_currency(total_pivot_value),
        _format_pct(100.0 if total_pivot_value else 0.0),
    ]

    # Filas de totales para composición y posiciones
    composition_total_value = sum(_to_float(item.get("value", 0.0)) for item in composition)
    positions_total_value = sum(_to_float(item.get("current_value", 0.0)) for item in positions)
    report_rows["composition_total"] = [
        "", "Total", "", _format_currency(composition_total_value),
        _format_pct(100.0 if composition_total_value else 0.0)
    ]
    report_rows["position_total"] = [
        "", "", "Total", "", _format_currency(positions_total_value),
        _format_pct(100.0 if positions_total_value else 0.0)
    ]

    # Datos para gráficos del informe
    chart_data = {
        # Gráfico de torta: composición por activo
        "composition_pie": [
            (str(item.get("asset_name") or item.get("ticker") or "n/d"), _to_float(item.get("weight_pct", 0.0)))
            for item in composition
            if _to_float(item.get("weight_pct", 0.0)) > 0
        ],
        # Gráfico de línea: evolución histórica
        "evolution_line": {
            "dates": [str(item.get("date", "")) for item in evolution_series],
            "values": [_to_float(item.get("total_value", 0.0)) for item in evolution_series],
        },
        # Gráfico de barras: pesos actuales vs HRP
        "weights_compare": [
            {
                "ticker": str(item.get("ticker", "n/d")),
                "current": _to_float(item.get("current_weight", 0.0)) * 100.0,
                "recommended": _to_float(item.get("recommended_weight", 0.0)) * 100.0,
            }
            for item in sorted(
                weights_table,
                key=lambda r: _to_float(r.get("recommended_weight", 0.0)),
                reverse=True
            )
        ],
    }

    # Secciones del informe
    sections = [
        "Datos del usuario", "Resumen por portafolio (dinámico)", "Portfolio",
        "Composición", "Valor total", "Evolución histórica", "Pesos actuales",
        "Pesos HRP", "Tabla de rebalanceo", "Comentario final", "Aviso académico",
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
        "charts": chart_data,
        "commentary": _build_final_comment(
            portfolio_summary=portfolio_summary,
            evolution_metrics=evolution_metrics,
            advisor_summary=advisor_summary,
            warnings=warnings,
        ),
        "academic_notice": (
            "Este informe tiene fines académicos y demostrativos. "
            "No constituye asesoramiento financiero, recomendación de inversión "
            "ni validación profesional del riesgo."
        ),
    }


# ------------------------------------------------------------
# Construcción de estilos tipográficos
# ------------------------------------------------------------

def _build_styles(modules: dict[str, Any], payload_title: str) -> dict[str, Any]:
    """Construye la hoja de estilos del informe una sola vez."""
    styles_module = modules["styles"]
    colors = modules["colors"]
    base = styles_module.getSampleStyleSheet()

    def _style(name: str, parent: str, **kwargs: Any) -> Any:
        """Crea un estilo personalizado basado en uno existente."""
        return styles_module.ParagraphStyle(name, parent=base[parent], **kwargs)

    return {
        "title":    _style("ReportTitle",    "Title",    textColor=colors.HexColor(_INK),    fontSize=20, spaceAfter=8),
        "subtitle": _style("ReportSubtitle", "Heading2", textColor=colors.HexColor("#334155"), fontSize=11, spaceAfter=12),
        "section":  _style("ReportSection",  "Heading2", textColor=colors.HexColor(_INK),    fontSize=14, spaceBefore=10, spaceAfter=8),
        "body":     _style("ReportBody",     "BodyText", leading=15, spaceAfter=8),
        "warning":  _style("ReportWarning",  "BodyText", textColor=colors.HexColor("#92400E"), backColor=colors.HexColor("#FEF3C7"), borderPadding=8, leading=14, spaceAfter=8),
        "footnote": _style("ReportFootnote", "BodyText", textColor=colors.HexColor(_MUTED),  fontSize=9, leading=12),
        "caption":  _style("ReportCaption",  "BodyText", textColor=colors.HexColor(_MUTED),  fontSize=9, leading=11, spaceBefore=2, spaceAfter=10, alignment=1),
    }


# ------------------------------------------------------------
# Tablas adaptativas
# ------------------------------------------------------------

def _adaptive_widths(widths: Sequence[int], available: float) -> list[float]:
    """Reescala los anchos de columna para llenar el ancho disponible del documento."""
    total = float(sum(widths)) or 1.0
    return [w / total * available for w in widths]


def _build_dynamic_table(
    modules: dict[str, Any],
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    widths: Sequence[int],
    *,
    available_width: float,
    signed_columns: Sequence[int] = (),
    action_column: int | None = None,
    total_row: Sequence[str] | None = None,
    fallback_row: Sequence[str] | None = None,
) -> Any:
    """
    Crea una tabla ReportLab adaptativa con estilos dinámicos.

    Características:
      - Anchos de columna escalados al ancho disponible
      - Colorea celdas con valores positivos/negativos (signed_columns)
      - Colorea y enfatiza la columna de acción HRP (action_column)
      - Agrega fila de totales destacada (total_row)
      - Muestra fila de fallback si no hay datos (fallback_row)
    """
    colors = modules["colors"]
    platypus = modules["platypus"]

    # Usar fallback si no hay filas de datos
    body = list(rows) if rows else [list(fallback_row or (["Sin datos"] + [""] * (len(headers) - 1)))]
    table_data: list[list[str]] = [list(headers), *[list(r) for r in body]]

    # Agregar fila de totales al final si se proporcionó
    if total_row is not None:
        table_data.append(list(total_row))

    # Escalar anchos al ancho disponible del documento
    scaled = _adaptive_widths(widths, available_width)
    table = platypus.Table(table_data, colWidths=scaled, repeatRows=1)

    # Estilo base de la tabla
    style: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_INK)),     # Cabecera oscura
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),                # Texto cabecera blanco
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),             # Fuente cabecera negrita
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(_GRID)),    # Bordes grises
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [                       # Filas alternadas
            colors.HexColor("#FFFFFF"),
            colors.HexColor("#F8FAFC"),
        ]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    # Colorear celdas con signo en columnas indicadas
    for r_offset, row in enumerate(body, start=1):
        for col in signed_columns:
            if col < len(row):
                sign = _cell_sign(row[col])
                if sign > 0:
                    style.append(("TEXTCOLOR", (col, r_offset), (col, r_offset), colors.HexColor(_POSITIVE)))
                elif sign < 0:
                    style.append(("TEXTCOLOR", (col, r_offset), (col, r_offset), colors.HexColor(_NEGATIVE)))

        # Colorear columna de acción según el tipo de recomendación
        if action_column is not None and action_column < len(row):
            label = str(row[action_column]).lower()
            if any(k in label for k in ("aument", "increase", "comprar", "buy")):
                color = _POSITIVE
            elif any(k in label for k in ("reduc", "reduce", "vender", "sell")):
                color = _NEGATIVE
            else:
                color = _MUTED
            style.append(("TEXTCOLOR", (action_column, r_offset), (action_column, r_offset), colors.HexColor(color)))
            style.append(("FONTNAME", (action_column, r_offset), (action_column, r_offset), "Helvetica-Bold"))

    # Estilo especial para la fila de totales
    if total_row is not None:
        last = len(table_data) - 1
        style += [
            ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
            ("BACKGROUND", (0, last), (-1, last), colors.HexColor("#E2E8F0")),
            ("LINEABOVE", (0, last), (-1, last), 1.0, colors.HexColor(_INK)),
        ]

    table.setStyle(platypus.TableStyle(style))
    return table


# ------------------------------------------------------------
# Gráficos ReportLab
# ------------------------------------------------------------

def _placeholder(modules: dict[str, Any], message: str, styles: dict[str, Any]) -> Any:
    """Muestra un mensaje de placeholder cuando no hay datos para graficar."""
    return modules["platypus"].Paragraph(_escape(message), styles["caption"])


def _build_pie_chart(
    modules: dict[str, Any],
    pairs: Sequence[tuple[str, float]],
    width: float,
    max_slices: int = 8,
) -> Any:
    """
    Construye un gráfico de torta con leyenda lateral.
    Agrupa en 'Otros' las porciones que excedan max_slices.
    """
    shapes = modules["shapes"]
    piecharts = modules["piecharts"]
    colors = modules["colors"]
    legends = modules["legends"]

    # Ordenar por valor y agrupar excedente en 'Otros'
    ordered = sorted(pairs, key=lambda p: p[1], reverse=True)
    if len(ordered) > max_slices:
        head = ordered[: max_slices - 1]
        rest_value = sum(v for _, v in ordered[max_slices - 1:])
        ordered = [*head, ("Otros", rest_value)]

    drawing = shapes.Drawing(width, 220)
    pie = piecharts.Pie()
    pie.x, pie.y = 20, 25
    pie.width, pie.height = 170, 170
    pie.data = [max(v, 0.0001) for _, v in ordered]  # Evitar valor 0 en pie
    pie.labels = None
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1

    # Asignar color de paleta a cada porción
    for i, _ in enumerate(ordered):
        pie.slices[i].fillColor = colors.HexColor(_PALETTE_HEX[i % len(_PALETTE_HEX)])
    drawing.add(pie)

    # Leyenda lateral con nombre y porcentaje de cada porción
    legend = legends.Legend()
    legend.x, legend.y = 215, 185
    legend.dx = legend.dy = 8
    legend.fontName = "Helvetica"
    legend.fontSize = 8
    legend.deltay = 13
    legend.alignment = "right"
    legend.columnMaximum = 8
    legend.colorNamePairs = [
        (colors.HexColor(_PALETTE_HEX[i % len(_PALETTE_HEX)]), f"{label}  {value:,.1f}%")
        for i, (label, value) in enumerate(ordered)
    ]
    drawing.add(legend)
    return drawing


def _build_line_chart(
    modules: dict[str, Any],
    dates: Sequence[str],
    values: Sequence[float],
    width: float,
    max_points: int = 24,
) -> Any:
    """
    Construye un gráfico de línea para la evolución del valor total del portfolio.
    Reduce el número de puntos si supera max_points para mejorar legibilidad.
    """
    shapes = modules["shapes"]
    linecharts = modules["linecharts"]
    colors = modules["colors"]

    # Reducir puntos si hay demasiados
    if len(values) > max_points:
        step = len(values) / max_points
        idx = [int(i * step) for i in range(max_points)]
        idx[-1] = len(values) - 1
        dates = [dates[i] for i in idx]
        values = [values[i] for i in idx]

    drawing = shapes.Drawing(width, 230)
    chart = linecharts.HorizontalLineChart()
    chart.x, chart.y = 45, 35
    chart.width, chart.height = width - 70, 160
    chart.data = [list(values)]
    chart.lines[0].strokeColor = colors.HexColor(_PALETTE_HEX[0])
    chart.lines[0].strokeWidth = 2
    chart.lineLabelFormat = None
    chart.joinedLines = 1

    # Configurar eje de valores con margen del 10%
    lo, hi = (min(values), max(values)) if values else (0.0, 1.0)
    span = (hi - lo) or (abs(hi) or 1.0)
    chart.valueAxis.valueMin = lo - span * 0.1
    chart.valueAxis.valueMax = hi + span * 0.1
    chart.valueAxis.valueStep = span / 4 if span else 1.0
    chart.valueAxis.labelTextFormat = lambda v: f"${v:,.0f}"
    chart.valueAxis.labels.fontSize = 7

    # Mostrar solo fechas clave en el eje X para evitar saturación
    n = len(dates)
    keep = {0, n - 1, n // 2, n // 4, (3 * n) // 4} if n else set()
    chart.categoryAxis.categoryNames = [d if i in keep else "" for i, d in enumerate(dates)]
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.dy = -4
    drawing.add(chart)
    return drawing


def _build_bar_chart(
    modules: dict[str, Any],
    items: Sequence[dict[str, Any]],
    width: float,
    max_bars: int = 8,
) -> Any:
    """
    Construye barras agrupadas comparando peso actual vs peso HRP recomendado (%).
    Limita a max_bars activos para mantener legibilidad.
    """
    shapes = modules["shapes"]
    barcharts = modules["barcharts"]
    colors = modules["colors"]
    legends = modules["legends"]

    items = list(items)[:max_bars]
    drawing = shapes.Drawing(width, 250)
    chart = barcharts.VerticalBarChart()
    chart.x, chart.y = 40, 55
    chart.width, chart.height = width - 70, 160

    # Dos series: peso actual y peso recomendado
    chart.data = [
        [it["current"] for it in items],
        [it["recommended"] for it in items],
    ]
    chart.categoryAxis.categoryNames = [it["ticker"] for it in items]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.bars[0].fillColor = colors.HexColor(_PALETTE_HEX[0])  # Azul: peso actual
    chart.bars[1].fillColor = colors.HexColor(_PALETTE_HEX[1])  # Verde: peso HRP
    chart.barWidth = 6
    chart.groupSpacing = 8

    # Configurar eje de valores con margen del 15%
    all_vals = [v for serie in chart.data for v in serie] or [0.0]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(all_vals) * 1.15 or 1.0
    chart.valueAxis.valueStep = (max(all_vals) * 1.15 / 4) or 1.0
    chart.valueAxis.labelTextFormat = lambda v: f"{v:,.0f}%"
    chart.valueAxis.labels.fontSize = 7
    drawing.add(chart)

    # Leyenda de colores
    legend = legends.Legend()
    legend.x, legend.y = 40, 235
    legend.dx = legend.dy = 8
    legend.fontName = "Helvetica"
    legend.fontSize = 8
    legend.alignment = "right"
    legend.columnMaximum = 1
    legend.deltax = 130
    legend.colorNamePairs = [
        (colors.HexColor(_PALETTE_HEX[0]), "Peso actual"),
        (colors.HexColor(_PALETTE_HEX[1]), "Peso HRP"),
    ]
    drawing.add(legend)
    return drawing


# ------------------------------------------------------------
# Cabecera y pie de página
# ------------------------------------------------------------

def _page_header_footer(modules: dict[str, Any]) -> Callable[[Any, Any], None]:
    """Devuelve el callback que dibuja cabecera y pie en cada página del PDF."""
    colors = modules["colors"]

    def _callback(canvas: Any, document: Any) -> None:
        """Pinta el nombre del proyecto y el número de página."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor(_MUTED))
        canvas.drawString(document.leftMargin, 16, "Dashboard_Financiero · Informe PDF")
        canvas.drawRightString(
            document.pagesize[0] - document.rightMargin, 16,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    return _callback


# ------------------------------------------------------------
# Ensamblado del story (contenido del PDF)
# ------------------------------------------------------------

def _assemble_story(
    modules: dict[str, Any],
    payload: dict[str, Any],
    styles: dict[str, Any],
    available_width: float,
) -> list[Any]:
    """
    Construye la lista de flowables del informe en orden lógico.
    Cada sección agrega párrafos, tablas y gráficos al story.
    """
    platypus = modules["platypus"]
    tables = payload["tables"]
    charts = payload["charts"]
    story: list[Any] = []

    def section(title: str) -> None:
        """Agrega un encabezado de sección al story."""
        story.append(platypus.Paragraph(title, styles["section"]))

    def caption(text: str) -> None:
        """Agrega un pie de gráfico centrado al story."""
        story.append(platypus.Paragraph(text, styles["caption"]))

    # Portada del informe
    story.append(platypus.Paragraph(payload["title"], styles["title"]))
    story.append(platypus.Paragraph(payload["subtitle"], styles["subtitle"]))
    story.append(platypus.Paragraph(
        f"Generado: {payload['generated_at']} · Secciones: {', '.join(payload['sections'])}",
        styles["footnote"],
    ))
    story.append(platypus.Spacer(1, 8))

    # Advertencias de datos
    if payload["warnings"]:
        section("<b>Advertencias de datos</b>")
        for warning in payload["warnings"]:
            story.append(platypus.Paragraph(_escape(warning), styles["warning"]))

    # Sección: Datos del usuario
    section("Datos del usuario y valor total")
    story.append(_build_dynamic_table(
        modules, ["Campo", "Valor"], tables["user_rows"], [120, 220],
        available_width=available_width
    ))

    # Sección: Resumen dinámico (pivot) por portfolio
    section("Resumen dinámico por portafolio")
    story.append(_build_dynamic_table(
        modules,
        ["Portafolio", "Posiciones", "Valor consolidado", "Peso"],
        tables["pivot_portfolio_rows"],
        [200, 90, 130, 90],
        available_width=available_width,
        total_row=tables["pivot_portfolio_total"],
        fallback_row=["Sin portafolios", "0", "$0.00", "0.00%"],
    ))

    # Sección: Portfolio del usuario
    section("Portfolio del usuario")
    story.append(_build_dynamic_table(
        modules,
        ["Portfolio", "Posiciones", "Capital estimado", "Creado"],
        tables["portfolio_rows"],
        [180, 80, 120, 110],
        available_width=available_width,
        fallback_row=["Sin portfolios", "0", "$0.00", "n/d"],
    ))

    # Sección: Composición con gráfico de torta
    section("Composición actual")
    if charts["composition_pie"]:
        story.append(_build_pie_chart(modules, charts["composition_pie"], available_width))
        caption("Distribución del portafolio por activo (ponderación %).")
    else:
        story.append(_placeholder(modules, "Sin datos de composición para graficar.", styles))
    story.append(_build_dynamic_table(
        modules,
        ["Ticker", "Activo", "Cantidad", "Valor", "Peso"],
        tables["composition_rows"],
        [70, 190, 80, 100, 70],
        available_width=available_width,
        total_row=tables["composition_total"],
        fallback_row=["n/d", "Sin datos", "0", "$0.00", "0.00%"],
    ))

    # Sección: Posiciones
    section("Posiciones y valor total")
    story.append(_build_dynamic_table(
        modules,
        ["Portfolio", "Ticker", "Activo", "Cantidad", "Valor actual", "Peso"],
        tables["position_rows"],
        [130, 60, 180, 70, 100, 70],
        available_width=available_width,
        total_row=tables["position_total"],
        fallback_row=["n/d", "n/d", "Sin posiciones", "0", "$0.00", "0.00%"],
    ))

    # Nueva página para evolución histórica
    story.append(platypus.PageBreak())
    section("Evolución histórica")
    if charts["evolution_line"]["values"]:
        story.append(_build_line_chart(
            modules,
            charts["evolution_line"]["dates"],
            charts["evolution_line"]["values"],
            available_width
        ))
        caption("Evolución del valor total del portafolio a lo largo del tiempo.")
    else:
        story.append(_placeholder(modules, "Sin serie histórica para graficar.", styles))
    story.append(_build_dynamic_table(
        modules, ["Métrica", "Valor"], tables["evolution_metric_rows"],
        [150, 160], available_width=available_width
    ))
    story.append(platypus.Spacer(1, 6))
    story.append(_build_dynamic_table(
        modules,
        ["Fecha", "Valor total", "Retorno periodo", "Retorno acumulado", "Drawdown"],
        tables["evolution_rows"],
        [90, 100, 100, 110, 90],
        available_width=available_width,
        signed_columns=[2, 3, 4],  # Colorear columnas con signo
        fallback_row=["n/d", "$0.00", "0.00%", "0.00%", "0.00%"],
    ))

    # Nueva página para pesos y rebalanceo
    story.append(platypus.PageBreak())
    section("Pesos actuales vs. HRP recomendado")
    if charts["weights_compare"]:
        story.append(_build_bar_chart(modules, charts["weights_compare"], available_width))
        caption("Comparación de la ponderación actual frente a la recomendada por HRP.")
    else:
        story.append(_placeholder(modules, "Sin pesos para comparar.", styles))

    section("Pesos actuales")
    story.append(_build_dynamic_table(
        modules,
        ["Ticker", "Activo", "Peso actual", "Valor actual"],
        tables["current_weight_rows"],
        [70, 220, 90, 100],
        available_width=available_width,
        fallback_row=["n/d", "Sin datos", "0.00%", "$0.00"],
    ))

    section("Pesos HRP recomendados")
    story.append(_build_dynamic_table(
        modules,
        ["Ticker", "Activo", "Peso HRP", "Desvío vs actual"],
        tables["hrp_weight_rows"],
        [70, 220, 90, 100],
        available_width=available_width,
        signed_columns=[3],  # Colorear desviación según signo
        fallback_row=["n/d", "Sin datos", "0.00%", "0.00%"],
    ))

    section("Tabla de rebalanceo")
    story.append(_build_dynamic_table(
        modules,
        ["Ticker", "Activo", "Peso actual", "Peso objetivo", "Delta valor", "Acción"],
        tables["rebalance_rows"],
        [60, 200, 85, 90, 95, 75],
        available_width=available_width,
        signed_columns=[4],   # Colorear delta de valor
        action_column=5,       # Colorear columna de acción
        fallback_row=["n/d", "Sin datos", "0.00%", "0.00%", "$0.00", "Mantener"],
    ))

    # Secciones de cierre
    section("Comentario final")
    story.append(platypus.Paragraph(_escape(payload["commentary"]), styles["body"]))
    section("Diagnóstico de soporte")
    story.append(_build_dynamic_table(
        modules, ["Indicador", "Valor"], tables["diagnostic_rows"],
        [150, 240], available_width=available_width
    ))
    section("Aviso académico")
    story.append(platypus.Paragraph(_escape(payload["academic_notice"]), styles["footnote"]))
    return story


# ------------------------------------------------------------
# Función principal de generación del PDF
# ------------------------------------------------------------

def generate_user_report_pdf(
    *,
    selected_user: dict[str, Any],
    dashboard_data: dict[str, Any],
) -> GeneratedPdfReport:
    """
    Genera el binario PDF final a partir de los snapshots del usuario.
    Ensambla el story y construye el documento con ReportLab.
    """
    payload = build_report_payload(selected_user=selected_user, dashboard_data=dashboard_data)
    modules = _load_reportlab()

    pagesizes = modules["pagesizes"]
    units = modules["units"]
    platypus = modules["platypus"]
    styles = _build_styles(modules, payload["title"])

    # Crear documento PDF en A4 horizontal
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

    # Calcular ancho disponible y construir el story
    available_width = document.width
    story = _assemble_story(modules, payload, styles, available_width)
    page_decorator = _page_header_footer(modules)

    # Aplicar cabecera/pie en todas las páginas
    document.build(story, onFirstPage=page_decorator, onLaterPages=page_decorator)

    return GeneratedPdfReport(
        file_name=payload["file_name"],
        content=buffer.getvalue(),
        generated_at=payload["generated_at"],
        warnings=payload["warnings"],
        sections=payload["sections"],
    )


# ------------------------------------------------------------
# Utilidades de archivo
# ------------------------------------------------------------

def build_report_filename(selected_user: dict[str, Any]) -> str:
    """Construye un nombre de archivo estable y seguro para el PDF."""
    raw_email = str(selected_user.get("user_email", "usuario")).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw_email).strip("_") or "usuario"
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"informe_{slug}_{stamp}.pdf"


def persist_generated_report(report: GeneratedPdfReport, *, output_dir: Path) -> Path:
    """Guarda el PDF generado en disco y devuelve su ruta final."""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / report.file_name
    file_path.write_bytes(report.content)
    return file_path


# ------------------------------------------------------------
# Comentario final automático
# ------------------------------------------------------------

def _build_final_comment(
    *,
    portfolio_summary: dict[str, Any],
    evolution_metrics: dict[str, Any],
    advisor_summary: dict[str, Any],
    warnings: list[str],
) -> str:
    """Resume en texto el estado del portfolio y las alertas del informe."""
    total_value = _format_currency(portfolio_summary.get("total_current_value", 0.0))
    cumulative_return = _format_pct(evolution_metrics.get("cumulative_return_pct", 0.0))
    annualized_return = _format_pct(evolution_metrics.get("annualized_return_pct", 0.0))
    increase_count = int(_to_float(advisor_summary.get("increase_count", 0)))
    reduce_count = int(_to_float(advisor_summary.get("reduce_count", 0)))
    hold_count = int(_to_float(advisor_summary.get("hold_count", 0)))

    base_comment = (
        f"El portfolio consolida un valor estimado de {total_value}, con una rentabilidad "
        f"acumulada de {cumulative_return} y anualizada de {annualized_return}. El advisor "
        f"identifica {increase_count} activos para aumentar, {reduce_count} para reducir y "
        f"{hold_count} para mantener."
    )
    if warnings:
        return f"{base_comment} El informe incorpora advertencias de datos: {'; '.join(warnings)}."
    return base_comment
