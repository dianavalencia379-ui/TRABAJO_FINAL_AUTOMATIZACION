from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ui.charts import build_area_figure, build_donut_figure, build_waterfall_figure


_MONTH_ABBR = {
    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre",
}


def _format_month(date_str: str | None) -> str:
    """Convierte 'YYYY-MM-DD' en una etiqueta tipo 'agosto 2025'.

    Se usan nombres completos (no abreviaturas) a propósito: la abreviatura
    'ago' (agosto) coincidía con la palabra inglesa 'ago' y el traductor
    automático del navegador la reemplazaba por 'año' en pantalla.
    """
    if not date_str or len(date_str) < 7:
        return "n/d"
    year, month = date_str[:4], date_str[5:7]
    return f"{_MONTH_ABBR.get(month, month)} {year}"


def _windowed_return_pct(series: list[dict[str, Any]], window: int) -> float:
    """Rentabilidad porcentual entre el inicio y el fin de una ventana de
    `window` meses (los últimos `window` puntos de la serie)."""
    if not series:
        return 0.0
    ordered = sorted(series, key=lambda point: point.get("date", ""))
    windowed = ordered[-window:] if len(ordered) > window else ordered
    if not windowed:
        return 0.0
    start_value = float(windowed[0].get("total_value", 0.0))
    end_value = float(windowed[-1].get("total_value", 0.0))
    return ((end_value / start_value) - 1.0) * 100 if start_value else 0.0


def _windowed_metrics(series: list[dict[str, Any]], window: int = 12) -> dict[str, Any]:
    """Drawdown y mejor/peor periodo limitados a los últimos `window` meses.

    El drawdown se recalcula usando solo el pico DENTRO de la ventana, no
    el drawdown_pct ya calculado contra el máximo de TODO el histórico.
    """
    empty_result = {
        "worst_drawdown_pct": 0.0, "worst_drawdown_label": "n/d",
        "best_period_pct": 0.0, "best_period_label": "n/d",
        "worst_period_pct": 0.0, "worst_period_label": "n/d",
    }
    if not series:
        return empty_result

    ordered = sorted(series, key=lambda point: point.get("date", ""))
    windowed = ordered[-window:] if len(ordered) > window else ordered
    if not windowed:
        return empty_result

    running_peak = float(windowed[0].get("total_value", 0.0))
    worst_drawdown_pct = 0.0
    worst_drawdown_date = windowed[0].get("date")
    for point in windowed:
        value = float(point.get("total_value", 0.0))
        running_peak = max(running_peak, value)
        drawdown = ((value / running_peak) - 1.0) * 100 if running_peak else 0.0
        if drawdown < worst_drawdown_pct:
            worst_drawdown_pct = drawdown
            worst_drawdown_date = point.get("date")

    best_point = max(windowed, key=lambda point: point.get("period_return_pct", 0.0))
    worst_point = min(windowed, key=lambda point: point.get("period_return_pct", 0.0))

    return {
        "worst_drawdown_pct": worst_drawdown_pct,
        "worst_drawdown_label": _format_month(worst_drawdown_date),
        "best_period_pct": float(best_point.get("period_return_pct", 0.0)),
        "best_period_label": _format_month(best_point.get("date")),
        "worst_period_pct": float(worst_point.get("period_return_pct", 0.0)),
        "worst_period_label": _format_month(worst_point.get("date")),
    }


def _inject_styles() -> None:
    """Aumenta el tamaño de letra de texto auxiliar (notas, tablas) dentro
    de esta pestaña. No toca colores ni fondos -- eso se mantiene acotado a
    las figuras de matplotlib (ver ui/charts.py), por decisión explícita
    de no alterar el tema visual del resto de la aplicación.
    """
    st.markdown(
        """
        <style>
        [data-testid="stCaptionContainer"] { font-size: 15px !important; }
        [data-testid="stDataFrame"] * { font-size: 14.5px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card_html(icon: str, label: str, value: str, delta: str | None = None) -> str:
    """HTML de una tarjeta KPI con ícono grande y altura fija.

    Se construye a mano (en vez de st.metric) porque st.metric no permite
    controlar el tamaño del ícono/texto ni garantizar la misma altura entre
    tarjetas con y sin texto secundario -- ambas cosas se pidieron
    explícitamente (tarjetas más grandes, misma altura entre filas).
    """
    delta_text = delta if delta else "&nbsp;"
    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:14px;padding:16px 18px;
                display:flex;align-items:center;gap:14px;background:#ffffff;
                min-height:92px;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
      <div style="width:50px;height:50px;min-width:50px;border-radius:50%;
                  background:#eff6ff;display:flex;align-items:center;
                  justify-content:center;font-size:24px;">{icon}</div>
      <div style="overflow:hidden;">
        <div style="font-size:14px;color:#6b7280;font-weight:600;">{label}</div>
        <div style="font-size:23px;font-weight:700;color:#111827;line-height:1.3;">{value}</div>
        <div style="font-size:12.5px;color:#9ca3af;">{delta_text}</div>
      </div>
    </div>
    """


def _kpi_card(column, icon: str, label: str, value: str, *, delta: str | None = None) -> None:
    with column:
        st.markdown(_kpi_card_html(icon, label, value, delta), unsafe_allow_html=True)


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Muestra el resumen ejecutivo del usuario seleccionado."""
    if not selected_user:
        st.info("Selecciona un usuario para ver el resumen financiero.")
        return

    _inject_styles()

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]
    hrp_snapshot = dashboard_data["hrp_snapshot"]
    summary = portfolio_snapshot["portfolio_summary"]
    metrics = evolution_snapshot["metrics"]
    advisor_summary = advisor_snapshot["summary"]
    advisor_table = advisor_snapshot.get("advisor_table", [])
    series = evolution_snapshot.get("series", [])

    window = _windowed_metrics(series, window=12)
    return_12m = _windowed_return_pct(series, window=12)

    # ============================================================
    # Movimiento del Periodo (diagrama esquemático, no escalado)
    # ============================================================
    st.subheader("📊 Movimiento del Periodo")
    if series:
        ordered = sorted(series, key=lambda point: point.get("date", ""))
        period_points = ordered[-12:] if len(ordered) > 12 else ordered
        saldo_inicial = float(period_points[0]["total_value"])
        saldo_final = float(period_points[-1]["total_value"])
        rendimientos = saldo_final - saldo_inicial  # aportes=retiros=gastos=0 hoy

        fig = build_waterfall_figure(
            saldo_inicial=saldo_inicial,
            aportes=0.0,
            rendimientos=rendimientos,
            retiros=0.0,
            gastos=0.0,
            start_label=_format_month(period_points[0]["date"]),
            end_label=_format_month(period_points[-1]["date"]),
        )
        st.pyplot(fig, clear_figure=True)
        st.markdown(
            "💵 **Aportes / Retiros:** \\$0,00 · Sin aportes en los últimos 12 meses. &nbsp; "
            "🧾 **Gastos y comisiones:** \\$0,00 · Portafolio negociado sin gastos de transacción."
        )
    else:
        st.info("No hay histórico disponible para construir el movimiento del periodo.")

    # ============================================================
    # Alerta de riesgo
    # ============================================================
    latest_drawdown = float(metrics.get("latest_drawdown_pct", 0.0))
    max_drawdown = float(metrics.get("max_drawdown_pct", 0.0))

    if latest_drawdown >= -0.01:
        st.success(f"🎉 La cartera está en (o muy cerca de) su máximo histórico · drawdown actual: {latest_drawdown:.2f}%")
    elif max_drawdown < 0 and abs(latest_drawdown) >= abs(max_drawdown) * 0.9:
        st.warning(
            f"⚠️ La cartera está cerca de su peor caída histórica registrada "
            f"· drawdown actual: {latest_drawdown:.2f}% (máxima caída: {max_drawdown:.2f}%)"
        )
    else:
        st.info(f"La cartera tiene un drawdown actual de {latest_drawdown:.2f}%, dentro de su rango histórico normal.")

    st.divider()

    # ============================================================
    # Tarjetas KPI -- dos filas de 3, misma distribución
    # ============================================================
    row1 = st.columns(3)
    _kpi_card(row1[0], "💰", "Valor Portafolio al Cierre", f"${summary['total_current_value']:,.2f}")
    _kpi_card(row1[1], "🛒", "Compras Activas", str(int(summary["position_count"])))
    _kpi_card(row1[2], "📁", "Portafolios Activos", str(int(summary["portfolio_count"])))

    st.write("")

    row2 = st.columns(3)
    _kpi_card(row2[0], "📈", "Rentabilidad 12 meses", f"{return_12m:.2f}%")
    _kpi_card(row2[1], "🏆", "Mejor Periodo 12m", f"{window['best_period_pct']:.2f}%", delta=window["best_period_label"])
    _kpi_card(row2[2], "🔻", "Peor Periodo 12m", f"{window['worst_period_pct']:.2f}%", delta=window["worst_period_label"])

    st.write("")

    # ============================================================
    # Tabla de rendimiento bruto y neto por horizonte
    # ============================================================
    st.subheader("📋 Rendimiento bruto y neto por horizonte")
    horizon_rows = []
    for label, window_size in (("Mes actual", 1), ("Últimos 3 meses", 3), ("Últimos 12 meses", 12)):
        bruto = _windowed_return_pct(series, window_size)
        horizon_rows.append({"Periodo": label, "Rendimiento Bruto": f"{bruto:.2f}%", "Rendimiento Neto": f"{bruto:.2f}%"})
    st.dataframe(pd.DataFrame(horizon_rows), width="stretch", hide_index=True)
    st.markdown("El bruto y el neto coinciden porque el proyecto aún no registra gastos de transacción. La tabla queda lista para cuando ese dato exista.")

    st.divider()

    # ============================================================
    # Recomendación para Rebalanceo
    # ============================================================
    st.subheader("🎯 Recomendación para Rebalanceo")
    total_to_reallocate = sum(item["value_delta"] for item in advisor_table if item.get("action") == "increase")
    net_check = advisor_summary.get("net_value_delta", 0.0)

    row3 = st.columns(4)
    _kpi_card(row3[0], "🟢", "Aumentar", str(int(advisor_summary["increase_count"])))
    _kpi_card(row3[1], "🔴", "Reducir", str(int(advisor_summary["reduce_count"])))
    _kpi_card(row3[2], "⚪", "Mantener", str(int(advisor_summary.get("hold_count", 0))))
    _kpi_card(row3[3], "💱", "Capital a Reasignar", f"${total_to_reallocate:,.2f}", delta=f"verificación ≈ $0: {net_check:,.2f}")

    st.markdown(
        "Activos por debajo del peso recomendado por el modelo HRP se marcan para **aumentar**; "
        "por encima, para **reducir**. El capital a reasignar es el dinero que se movería HACIA "
        "los activos infraponderados (no es una pérdida)."
    )

    st.divider()

    # ============================================================
    # Evolución (histórico completo) + Composición (anillo)
    # ============================================================
    left_column, right_column = st.columns((1.3, 1.0))

    with left_column:
        st.subheader("📈 Evolución del portfolio")
        if series:
            ordered_series = sorted(series, key=lambda point: point.get("date", ""))
            area_fig = build_area_figure(
                dates=[point["date"] for point in ordered_series],
                values=[point["total_value"] for point in ordered_series],
            )
            st.pyplot(area_fig, clear_figure=True)
        else:
            st.info("No hay histórico disponible para este usuario.")

    with right_column:
        st.subheader("🍩 Composición por activo")
        asset_rows = portfolio_snapshot.get("composition", {}).get("by_asset", [])
        if asset_rows:
            donut_fig = build_donut_figure(
                labels=[row["ticker"] for row in asset_rows],
                values=[row["weight_pct"] for row in asset_rows],
                amounts=[row["value"] for row in asset_rows],
            )
            st.pyplot(donut_fig, clear_figure=True)
        else:
            st.info("Sin composición disponible.")

    st.markdown("Histórico completo arriba a la izquierda. Las métricas de mejor/peor periodo de las tarjetas están limitadas a los últimos 12 meses.")

    st.divider()

    # ============================================================
    # Detalle de posiciones, enriquecido con HRP + correlación + totales
    # ============================================================
    st.subheader("📌 Detalle de posiciones")
    positions = portfolio_snapshot.get("positions_table", [])
    if not positions:
        st.info("No hay posiciones para mostrar.")
    else:
        action_emoji = {"increase": "🟢", "reduce": "🔴", "hold": "⚪"}
        advisor_by_ticker = {item["ticker"]: item for item in advisor_table}

        correlation_matrix = hrp_snapshot.get("matrices", {}).get("correlation", {})
        avg_correlation_by_ticker: dict[str, float] = {}
        for ticker, row in correlation_matrix.items():
            others = [value for other_ticker, value in row.items() if other_ticker != ticker]
            avg_correlation_by_ticker[ticker] = (sum(others) / len(others)) if others else 0.0

        enriched_rows = []
        for position in positions:
            ticker = position["ticker"]
            advisor_item = advisor_by_ticker.get(ticker, {})
            action = advisor_item.get("action")
            difference_pct = advisor_item.get("difference_pct")
            avg_correlation = avg_correlation_by_ticker.get(ticker)
            enriched_rows.append(
                {
                    "Portfolio": position["portfolio_name"],
                    "Ticker": ticker,
                    "Activo": position["asset_name"],
                    "Acción HRP": f"{action_emoji.get(action, '⚪')} {advisor_item.get('action_label', 'n/d')}",
                    "Valor actual": position["current_value"],
                    "Peso (%)": position["weight_pct"],
                    "Peso objetivo HRP (%)": advisor_item.get("target_weight_pct"),
                    # Texto preformateado (no NumberColumn): así la fila TOTAL puede
                    # dejar la celda realmente vacía -- con NumberColumn, un NaN se
                    # muestra como el texto literal "None" en esta versión de Streamlit.
                    "Diferencia vs HRP (pp)": f"{difference_pct:+.2f}" if difference_pct is not None else "",
                    "Correlación promedio": f"{avg_correlation:.3f}" if avg_correlation is not None else "",
                }
            )

        positions_frame = pd.DataFrame(enriched_rows)

        totals_row: dict[str, Any] = {
            "Portfolio": "", "Ticker": "TOTAL", "Activo": "", "Acción HRP": "",
            "Valor actual": positions_frame["Valor actual"].sum(),
            "Peso (%)": positions_frame["Peso (%)"].sum(),
            "Peso objetivo HRP (%)": positions_frame["Peso objetivo HRP (%)"].sum(),
            "Diferencia vs HRP (pp)": "",
            "Correlación promedio": "",
        }
        display_frame = pd.concat([positions_frame, pd.DataFrame([totals_row])], ignore_index=True)

        st.dataframe(
            display_frame,
            width="stretch",
            hide_index=True,
            column_config={
                "Valor actual": st.column_config.NumberColumn(format="$%.2f"),
                "Peso (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Peso objetivo HRP (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

    st.divider()

    # ============================================================
    # Estado general
    # ============================================================
    st.subheader("ℹ️ Estado general")
    info_left, info_right = st.columns(2)

    with info_left:
        st.markdown(f"**👤 Usuario:** {selected_user['user_name']}")
        st.markdown(f"**📧 Email:** {selected_user['user_email']}")
        periodo = f"{metrics['start_date']} → {metrics['end_date']}" if metrics["points"] else "Sin histórico"
        st.markdown(f"**📅 Periodo analizado:** {periodo}")

    with info_right:
        st.markdown(f"**🎯 Pesos objetivo HRP:** {advisor_summary['asset_count']} activos")
        price_source = hrp_snapshot.get("diagnostics", {}).get("price_source", "n/d")
        st.markdown(f"**🔗 Origen de precios HRP:** {price_source}")