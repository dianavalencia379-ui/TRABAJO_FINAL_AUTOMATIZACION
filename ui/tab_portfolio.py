from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Presenta la composición y el detalle completo del portfolio."""
    if not selected_user:
        st.info("Selecciona un usuario para explorar el portfolio.")
        return

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    user_portfolios = dashboard_data.get("user_portfolios", [])

    if user_portfolios:
        st.subheader("Portfolio(s) del usuario")
        portfolios_frame = pd.DataFrame(user_portfolios).rename(
            columns={
                "portfolio_name": "Portfolio",
                "position_count": "Posiciones",
                "invested_amount": "Capital estimado",
                "created_at": "Creado",
            }
        )
        st.dataframe(
            portfolios_frame[["Portfolio", "Posiciones", "Capital estimado", "Creado"]],
            use_container_width=True,
            hide_index=True,
        )

    composition_columns = st.columns(2)
    asset_rows = portfolio_snapshot.get("composition", {}).get("by_asset", [])
    portfolio_rows = portfolio_snapshot.get("composition", {}).get("by_portfolio", [])

    with composition_columns[0]:
        st.subheader("Composición por activo")
        if asset_rows:
            asset_frame = pd.DataFrame(asset_rows).set_index("label")[["value"]]
            st.bar_chart(asset_frame)
        else:
            st.info("Sin composición por activo disponible.")

    with composition_columns[1]:
        st.subheader("Valor por portfolio")
        if portfolio_rows:
            portfolio_frame = pd.DataFrame(portfolio_rows).set_index("label")[["value"]]
            st.bar_chart(portfolio_frame)
        else:
            st.info("Sin composición por portfolio disponible.")

    st.subheader("Detalle de posiciones")
    positions = portfolio_snapshot.get("positions_table", [])
    if not positions:
        st.warning("El usuario no tiene posiciones cargadas en la base de datos.")
        return

    positions_frame = pd.DataFrame(positions).rename(
        columns={
            "portfolio_name": "Portfolio",
            "ticker": "Ticker",
            "asset_name": "Activo",
            "quantity": "Cantidad",
            "avg_price": "Precio medio",
            "current_price": "Precio actual",
            "cost_basis": "Coste",
            "current_value": "Valor actual",
            "weight_pct": "Peso (%)",
        }
    )
    st.dataframe(
        positions_frame[
            [
                "Portfolio",
                "Ticker",
                "Activo",
                "Cantidad",
                "Precio medio",
                "Precio actual",
                "Coste",
                "Valor actual",
                "Peso (%)",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
