from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Colores de acción reutilizados en gráfico y tabla.
_ACTION_STYLES = {
    "Aumentar": "background-color: #d4edda; color: #155724;",
    "Reducir": "background-color: #f8d7da; color: #721c24;",
    "Mantener": "background-color: #fff3cd; color: #856404;",
}


def _style_action(value: str) -> str:
    """Devuelve el CSS de fondo según la acción recomendada."""
    return _ACTION_STYLES.get(value, "")


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

        st.subheader("Pesos actuales vs objetivo (HRP)")

        grouped_bar = go.Figure()
        grouped_bar.add_bar(
            name="Peso actual",
            x=comparison_frame["ticker"],
            y=comparison_frame["current_weight_pct"],
            marker_color="#6c757d",
        )
        grouped_bar.add_bar(
            name="Peso objetivo (HRP)",
            x=comparison_frame["ticker"],
            y=comparison_frame["target_weight_pct"],
            marker_color="#0d6efd",
        )
        grouped_bar.update_layout(
            barmode="group",
            xaxis_title="Ticker",
            yaxis_title="Peso (%)",
            legend_title_text="",
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(grouped_bar, use_container_width=True)

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
        )[
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
        ]

        styler = (
            styled_frame.style.map(_style_action, subset=["Acción"]).format(
                {
                    "Precio medio": "${:,.2f}",
                    "Valor actual": "${:,.2f}",
                    "Valor objetivo": "${:,.2f}",
                    "Delta valor": "${:,.2f}",
                    "Peso actual (%)": "{:.2f}%",
                    "Peso objetivo (%)": "{:.2f}%",
                    "Desviación (%)": "{:+.2f}%",
                }
            )
        )

        st.dataframe(styler, width="stretch", hide_index=True)

    else:
        st.info("No hay suficiente información para construir recomendaciones HRP.")

    st.info(
        "Aviso académico: las recomendaciones del asesor son una simulación con fines "
        "educativos. No constituyen asesoramiento financiero profesional ni una "
        "recomendación real de inversión."
    )

    with st.expander("Diagnóstico HRP"):
        diagnostics_rows = [
            {
                "Indicador": "Histórico utilizado",
                "Valor": str(diagnostics.get("history_rows", 0)),
            },
            {
                "Indicador": "Periodo precios",
                "Valor": f"{diagnostics.get('history_start', 'n/d')} → {diagnostics.get('history_end', 'n/d')}",
            },
            {
                "Indicador": "Filas de retornos",
                "Valor": str(diagnostics.get("returns_rows", 0)),
            },
            {
                "Indicador": "Suma pesos actual",
                "Valor": f"{diagnostics.get('weights_sum', {}).get('current', 0):.4f}",
            },
            {
                "Indicador": "Suma pesos objetivo",
                "Valor": f"{diagnostics.get('weights_sum', {}).get('recommended', 0):.4f}",
            },
        ]

        st.dataframe(
            pd.DataFrame(diagnostics_rows),
            width="stretch",
            hide_index=True,
        )