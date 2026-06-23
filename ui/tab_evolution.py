# ============================================================
# ui/tab_evolution.py — Pestaña Evolución histórica
# Muestra métricas y series de evolución del portfolio en
# el tiempo, incluyendo rentabilidad y drawdown.
# ============================================================

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """
    Renderiza la pestaña de evolución histórica del portfolio.

    Secciones:
      1. Métricas resumen (fechas, valores, rentabilidad anualizada)
      2. Gráfico de serie histórica de valor total
      3. Gráficos de rentabilidad acumulada y drawdown
      4. Tabla detallada mensual
    """
    # Verificar que hay un usuario seleccionado
    if not selected_user:
        st.info("Selecciona un usuario para revisar la evolución histórica.")
        return

    # Obtener snapshot de evolución y sus componentes
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    metrics = evolution_snapshot["metrics"]
    series = evolution_snapshot.get("series", [])

    # Sección 1: Métricas resumen en 5 columnas
    metric_columns = st.columns(5)
    metric_columns[0].metric("Inicio", metrics["start_date"] or "n/d")
    metric_columns[1].metric("Fin", metrics["end_date"] or "n/d")
    metric_columns[2].metric("Valor inicial", f"${metrics['start_value']:,.2f}")
    metric_columns[3].metric("Valor final", f"${metrics['end_value']:,.2f}")
    metric_columns[4].metric("Rent. anualizada", f"{metrics['annualized_return_pct']:.2f}%")

    # Mostrar advertencia si no hay datos históricos
    if not series:
        st.warning("No hay puntos históricos para este usuario.")
        return

    # Convertir serie a DataFrame indexado por fecha
    series_frame = pd.DataFrame(series).set_index("date")

    # Sección 2: Gráfico de valor total del portfolio en el tiempo
    st.subheader("Serie histórica")
    st.line_chart(series_frame[["total_value"]])

    # Sección 3: Gráficos de rentabilidad acumulada y drawdown en paralelo
    chart_columns = st.columns(2)

    with chart_columns[0]:
        st.subheader("Rentabilidad acumulada (%)")
        st.line_chart(series_frame[["cumulative_return_pct"]])

    with chart_columns[1]:
        # Drawdown: caída desde el máximo histórico (siempre negativo o cero)
        st.subheader("Drawdown (%)")
        st.line_chart(series_frame[["drawdown_pct"]])

    # Sección 4: Tabla detallada con todos los puntos mensuales
    st.subheader("Detalle mensual")
    detail_frame = series_frame.reset_index().rename(
        columns={
            "date": "Fecha",
            "total_value": "Valor total",
            "period_return_pct": "Retorno periodo (%)",
            "cumulative_return_pct": "Retorno acumulado (%)",
            "drawdown_pct": "Drawdown (%)",
            "is_new_peak": "Nuevo máximo",  # True si se alcanzó un nuevo máximo histórico
        }
    )
    st.dataframe(detail_frame, width="stretch", hide_index=True)
