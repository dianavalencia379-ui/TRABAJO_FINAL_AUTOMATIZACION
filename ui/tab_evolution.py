from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Muestra métricas y series de evolución histórica del portfolio."""
    if not selected_user:
        st.info("Selecciona un usuario para revisar la evolución histórica.")
        return

    evolution_snapshot = dashboard_data["evolution_snapshot"]
    metrics = evolution_snapshot["metrics"]
    series = evolution_snapshot.get("series", [])

    metric_columns = st.columns(5)
    metric_columns[0].metric("Inicio", metrics["start_date"] or "n/d")
    metric_columns[1].metric("Fin", metrics["end_date"] or "n/d")
    metric_columns[2].metric("Valor inicial", f"${metrics['start_value']:,.2f}")
    metric_columns[3].metric("Valor final", f"${metrics['end_value']:,.2f}")
    metric_columns[4].metric("Rent. anualizada", f"{metrics['annualized_return_pct']:.2f}%")

    if not series:
        st.warning("No hay puntos históricos para este usuario.")
        return

    series_frame = pd.DataFrame(series).set_index("date")

    st.subheader("Serie histórica")
    st.line_chart(series_frame[["total_value"]])

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.subheader("Rentabilidad acumulada (%)")
        st.line_chart(series_frame[["cumulative_return_pct"]])

    with chart_columns[1]:
        st.subheader("Drawdown (%)")
        st.line_chart(series_frame[["drawdown_pct"]])

    st.subheader("Detalle mensual")
    detail_frame = series_frame.reset_index().rename(
        columns={
            "date": "Fecha",
            "total_value": "Valor total",
            "period_return_pct": "Retorno periodo (%)",
            "cumulative_return_pct": "Retorno acumulado (%)",
            "drawdown_pct": "Drawdown (%)",
            "is_new_peak": "Nuevo máximo",
        }
    )
    st.dataframe(detail_frame, width="stretch", hide_index=True)
