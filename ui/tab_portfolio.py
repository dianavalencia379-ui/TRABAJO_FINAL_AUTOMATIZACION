from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


_ACTION_EMOJI = {"increase": "🟢", "reduce": "🔴", "hold": "⚪"}


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Presenta la composición y el detalle completo del portfolio.

    Ademas de mostrar la composicion, esta version agrega analisis de
    concentracion (HHI), un filtro interactivo, y una columna de Accion
    HRP cruzada desde el motor de rebalanceo de Antonio -- asi el usuario
    ve "que tengo" y "que deberia hacer" en la misma tabla, sin cambiar de
    pestaña.
    """
    if not selected_user:
        st.info("Selecciona un usuario para explorar el portfolio.")
        return

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    advisor_snapshot = dashboard_data.get("advisor_snapshot", {})
    user_portfolios = dashboard_data.get("user_portfolios", [])
    asset_rows = portfolio_snapshot.get("composition", {}).get("by_asset", [])
    portfolio_rows = portfolio_snapshot.get("composition", {}).get("by_portfolio", [])
    summary = portfolio_snapshot.get("portfolio_summary", {})
    advisor_table = advisor_snapshot.get("advisor_table", [])

    # --- Indicador de concentracion (Herfindahl-Hirschman Index, HHI) ---
    weights = [float(item.get("weight_pct", 0.0)) / 100.0 for item in asset_rows]
    hhi = sum(weight**2 for weight in weights) if weights else 0.0
    effective_positions = (1.0 / hhi) if hhi > 0 else 0.0

    if hhi == 0.0:
        concentration_label = "n/d"
    elif hhi < 0.15:
        concentration_label = "Baja"
    elif hhi < 0.25:
        concentration_label = "Moderada"
    else:
        concentration_label = "Alta"

    top_metric_columns = st.columns(4)
    top_metric_columns[0].metric(
        "💰 Capital estimado",
        f"${summary.get('total_current_value', 0.0):,.2f}",
        help="Suma del valor actual de todas las posiciones del usuario.",
    )
    top_metric_columns[1].metric(
        "📊 Posiciones",
        int(summary.get("position_count", 0)),
        help="Número de posiciones distintas que componen la cartera.",
    )
    top_metric_columns[2].metric(
        "🧮 Concentración",
        concentration_label,
        help=(
            "Basado en el índice Herfindahl-Hirschman (HHI) de los pesos por activo. "
            f"HHI calculado: {hhi:.3f} (escala 0 a 1; más alto = más concentrado)."
        ),
    )
    top_metric_columns[3].metric(
        "🪙 Posiciones equivalentes",
        f"{effective_positions:.1f}",
        help=(
            "1 / HHI. Indica a cuántas posiciones igualmente ponderadas "
            "equivale la diversificación real de la cartera."
        ),
    )

    if asset_rows:
        top_asset = max(asset_rows, key=lambda item: item.get("weight_pct", 0.0))
        top_weight = float(top_asset.get("weight_pct", 0.0))
        if top_weight >= 30.0:
            st.warning(
                f"⚠️ Concentración alta en un solo activo: **{top_asset.get('ticker', 'n/d')}** "
                f"representa el {top_weight:.2f}% de la cartera."
            )

    st.divider()

    if user_portfolios:
        st.subheader("🗂️ Portfolio(s) del usuario")
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
            width="stretch",
            hide_index=True,
        )

    composition_columns = st.columns(2)

    with composition_columns[0]:
        st.subheader("📊 Composición por activo")
        if asset_rows:
            asset_frame = pd.DataFrame(asset_rows).set_index("label")[["value"]]
            st.bar_chart(asset_frame)
        else:
            st.info("Sin composición por activo disponible.")

    with composition_columns[1]:
        st.subheader("🗂️ Valor por portfolio")
        if portfolio_rows:
            portfolio_frame = pd.DataFrame(portfolio_rows).set_index("label")[["value"]]
            st.bar_chart(portfolio_frame)
        else:
            st.info("Sin composición por portfolio disponible.")

    st.divider()

    st.subheader("📌 Detalle de posiciones")
    positions = portfolio_snapshot.get("positions_table", [])
    if not positions:
        st.warning("El usuario no tiene posiciones cargadas en la base de datos.")
        return

    search_term = st.text_input(
        "🔎 Buscar por ticker o nombre de activo",
        value="",
        placeholder="Ej: AAPL, Visa, Johnson...",
    )

    # --- Cruce con la recomendación del motor de rebalanceo (Antonio) ---
    # Se construye un diccionario ticker -> "emoji + etiqueta" a partir de
    # advisor_table (que ya calcula la accion recomendada por el HRP) y se
    # agrega como columna nueva, sin tocar ningun motor financiero.
    action_by_ticker = {
        item["ticker"]: f"{_ACTION_EMOJI.get(item.get('action'), '⚪')} {item.get('action_label', 'n/d')}"
        for item in advisor_table
    }

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
    positions_frame["Acción HRP"] = positions_frame["Ticker"].map(action_by_ticker).fillna("n/d")

    if search_term:
        mask = (
            positions_frame["Ticker"].str.contains(search_term, case=False, na=False)
            | positions_frame["Activo"].str.contains(search_term, case=False, na=False)
        )
        positions_frame = positions_frame[mask]

    display_columns = [
        "Portfolio",
        "Ticker",
        "Activo",
        "Acción HRP",
        "Cantidad",
        "Precio medio",
        "Precio actual",
        "Coste",
        "Valor actual",
        "Peso (%)",
    ]

    if positions_frame.empty:
        st.info("Ningún activo coincide con la búsqueda.")
    else:
        display_frame = positions_frame[display_columns].copy()

        # --- Fila de totales ---
        # Se suman solo las columnas donde totalizar tiene sentido
        # financiero (Coste, Valor actual, Peso %). Las columnas de texto
        # se dejan en "" pero las NUMERICAS que no se totalizan (Cantidad,
        # Precio medio, Precio actual) deben quedar en None, no en "" --
        # de lo contrario pandas mezcla texto y numeros en la misma
        # columna y Streamlit no puede serializar la tabla (Arrow exige
        # un tipo de dato consistente por columna).
        totals_row: dict[str, Any] = {
            "Portfolio": "",
            "Ticker": "TOTAL",
            "Activo": "",
            "Acción HRP": "",
            "Cantidad": None,
            "Precio medio": None,
            "Precio actual": None,
            "Coste": display_frame["Coste"].sum(),
            "Valor actual": display_frame["Valor actual"].sum(),
            "Peso (%)": display_frame["Peso (%)"].sum(),
        }
        display_frame = pd.concat([display_frame, pd.DataFrame([totals_row])], ignore_index=True)

        st.dataframe(display_frame, width="stretch", hide_index=True)