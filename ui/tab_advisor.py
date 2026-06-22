from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Renderiza la comparación entre pesos actuales y recomendados por HRP."""
    if not selected_user:
        st.info("Selecciona un usuario para ver el advisor HRP.")
        return

    hrp_snapshot = dashboard_data["hrp_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]
    diagnostics = hrp_snapshot.get("diagnostics", {})
    summary = advisor_snapshot["summary"]

    metric_columns = st.columns(4)
    metric_columns[0].metric("Activos evaluados", int(summary["asset_count"]))
    metric_columns[1].metric("Aumentar", int(summary["increase_count"]))
    metric_columns[2].metric("Reducir", int(summary["reduce_count"]))
    metric_columns[3].metric("Umbral", f"{advisor_snapshot['rebalance_threshold_pct']:.2f}%")

    warnings = advisor_snapshot.get("diagnostics", {}).get("warnings", [])
    for warning in warnings:
        st.warning(warning)

    st.caption(
        f"Fuente de precios: {diagnostics.get('price_source', 'n/d')} · "
        f"Clustering: {diagnostics.get('clustering_method', 'n/d')}"
    )

    comparison_rows = advisor_snapshot.get("advisor_table", [])
    if comparison_rows:
        comparison_frame = pd.DataFrame(comparison_rows)
        chart_frame = comparison_frame.set_index("ticker")[["current_weight_pct", "target_weight_pct"]]
        st.subheader("Pesos actuales vs objetivo")
        st.bar_chart(chart_frame)

        styled_frame = comparison_frame.rename(
            columns={
                "ticker": "Ticker",
                "asset_name": "Activo",
                "current_quantity": "Cantidad",
                "avg_price": "Precio medio",
                "current_value": "Valor actual",
                "target_value": "Valor objetivo",
                "value_delta": "Delta valor",
                "current_weight_pct": "Peso actual (%)",
                "target_weight_pct": "Peso objetivo (%)",
                "difference_pct": "Desviación (%)",
                "action_label": "Acción",
            }
        )
        st.dataframe(
            styled_frame[
                [
                    "Ticker",
                    "Activo",
                    "Cantidad",
                    "Precio medio",
                    "Valor actual",
                    "Valor objetivo",
                    "Delta valor",
                    "Peso actual (%)",
                    "Peso objetivo (%)",
                    "Desviación (%)",
                    "Acción",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No hay suficiente información para construir recomendaciones HRP.")

    with st.expander("Diagnóstico HRP"):
        diagnostics_rows = [
            {"Indicador": "Histórico utilizado", "Valor": str(diagnostics.get("history_rows", 0))},
            {"Indicador": "Periodo precios", "Valor": f"{diagnostics.get('history_start', 'n/d')} → {diagnostics.get('history_end', 'n/d')}"},
            {"Indicador": "Filas de retornos", "Valor": str(diagnostics.get("returns_rows", 0))},
            {"Indicador": "Suma pesos actual", "Valor": f"{diagnostics.get('weights_sum', {}).get('current', 0):.4f}"},
            {"Indicador": "Suma pesos objetivo", "Valor": f"{diagnostics.get('weights_sum', {}).get('recommended', 0):.4f}"},
        ]
        st.dataframe(pd.DataFrame(diagnostics_rows), width="stretch", hide_index=True)