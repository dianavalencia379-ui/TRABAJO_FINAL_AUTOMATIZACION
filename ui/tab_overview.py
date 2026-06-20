from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Muestra el resumen ejecutivo del usuario seleccionado."""
    if not selected_user:
        st.info("Selecciona un usuario para ver el resumen financiero.")
        return

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]
    summary = portfolio_snapshot["portfolio_summary"]
    metrics = evolution_snapshot["metrics"]
    advisor_summary = advisor_snapshot["summary"]

    metric_columns = st.columns(4)
    metric_columns[0].metric("Valor estimado", f"${summary['total_current_value']:,.2f}")
    metric_columns[1].metric("Posiciones", int(summary["position_count"]))
    metric_columns[2].metric("Rentabilidad acumulada", f"{metrics['cumulative_return_pct']:.2f}%")
    metric_columns[3].metric("Max drawdown", f"{metrics['max_drawdown_pct']:.2f}%")

    detail_columns = st.columns(3)
    detail_columns[0].metric("Portfolio(s)", int(summary["portfolio_count"]))
    detail_columns[1].metric("Activos a aumentar", int(advisor_summary["increase_count"]))
    detail_columns[2].metric("Activos a reducir", int(advisor_summary["reduce_count"]))

    left_column, right_column = st.columns((1.7, 1.1))

    with left_column:
        st.subheader("Evolución del portfolio")
        series = evolution_snapshot.get("series", [])
        if series:
            history_frame = pd.DataFrame(series).set_index("date")[["total_value"]]
            st.line_chart(history_frame)
        else:
            st.info("No hay histórico disponible para este usuario.")

    with right_column:
        st.subheader("Principales posiciones")
        positions = portfolio_snapshot.get("positions_table", [])[:5]
        if positions:
            top_positions = pd.DataFrame(positions)[["ticker", "asset_name", "current_value", "weight_pct"]]
            top_positions = top_positions.rename(
                columns={
                    "ticker": "Ticker",
                    "asset_name": "Activo",
                    "current_value": "Valor actual",
                    "weight_pct": "Peso (%)",
                }
            )
            st.dataframe(top_positions, use_container_width=True, hide_index=True)
        else:
            st.info("No hay posiciones para mostrar.")

    st.subheader("Estado general")
    status_rows = [
        {"Indicador": "Usuario", "Valor": selected_user["user_name"]},
        {"Indicador": "Email", "Valor": selected_user["user_email"]},
        {"Indicador": "Periodo analizado", "Valor": f"{metrics['start_date']} → {metrics['end_date']}" if metrics["points"] else "Sin histórico"},
        {"Indicador": "Pesos objetivo HRP", "Valor": f"{advisor_summary['asset_count']} activos"},
        {"Indicador": "Origen de precios HRP", "Valor": dashboard_data["hrp_snapshot"].get("diagnostics", {}).get("price_source", "n/d")},
    ]
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
