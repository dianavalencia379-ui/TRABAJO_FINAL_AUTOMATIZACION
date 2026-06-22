from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config import settings
from data_layer.db import (
    get_connection,
    get_user_portfolios,
    get_users,
    initialize_database,
)
from domain.evolution_engine import build_evolution_snapshot_from_db
from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot
from domain.rebalance_engine import build_rebalance_advisor_snapshot
from ui import tab_advisor, tab_evolution, tab_overview, tab_portfolio, tab_reports


def _format_user_label(user: dict[str, Any]) -> str:
    """Construye la etiqueta legible de un usuario para el selector lateral."""
    return (
        f"{user['user_name']} · {user['portfolio_count']} portfolio(s) · "
        f"{user['position_count']} posiciones"
    )


@st.cache_data(show_spinner=False)
def load_users() -> list[dict[str, Any]]:
    """Carga los usuarios disponibles junto con sus agregados principales."""
    with get_connection() as connection:
        return [dict(row) for row in get_users(connection)]


@st.cache_data(show_spinner=False)
def load_dashboard_data(
    user_email: str,
    *,
    rebalance_threshold: float,
    prefer_live_data: bool,
) -> dict[str, Any]:
    """Reúne todos los snapshots necesarios para renderizar el dashboard."""
    with get_connection() as connection:
        portfolio_snapshot = build_portfolio_snapshot(
            connection=connection,
            user_email=user_email,
        )
        evolution_snapshot = build_evolution_snapshot_from_db(
            connection=connection,
            user_email=user_email,
        )
        hrp_snapshot = build_hrp_portfolio_snapshot(
            connection=connection,
            user_email=user_email,
            prefer_live_data=prefer_live_data,
        )
        advisor_snapshot = build_rebalance_advisor_snapshot(
            connection=connection,
            user_email=user_email,
            rebalance_threshold=rebalance_threshold,
            prefer_live_data=prefer_live_data,
            portfolio_snapshot=portfolio_snapshot,
            hrp_snapshot=hrp_snapshot,
        )
        user_portfolios = [
            dict(row) for row in get_user_portfolios(connection, user_email=user_email)
        ]

    return {
        "portfolio_snapshot": portfolio_snapshot,
        "evolution_snapshot": evolution_snapshot,
        "hrp_snapshot": hrp_snapshot,
        "advisor_snapshot": advisor_snapshot,
        "user_portfolios": user_portfolios,
    }


def render_sidebar(users: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Renderiza el selector de usuario y devuelve la selección activa."""
    st.sidebar.header("Selección")
    if not users:
        st.sidebar.warning("No hay usuarios disponibles en la base de datos.")
        return None

    labels = [_format_user_label(user) for user in users]
    selected_index = st.sidebar.selectbox(
        "Usuario",
        options=list(range(len(users))),
        format_func=lambda index: labels[index],
    )
    selected_user = users[selected_index]

    st.sidebar.caption(selected_user["user_email"])
    st.sidebar.metric("Capital estimado", f"${selected_user['invested_amount']:,.2f}")
    st.sidebar.metric("Posiciones", int(selected_user["position_count"]))
    st.sidebar.metric("Portfolios", int(selected_user["portfolio_count"]))
    st.sidebar.divider()
    st.sidebar.caption("La interfaz usa los motores de portfolio, evolución, HRP y rebalanceo.")
    return selected_user


def main() -> None:
    """Orquesta la inicialización y el render completo de la app Streamlit."""
    st.set_page_config(
        page_title=settings.app_name,
        page_icon="📊",
        layout="wide",
    )

    try:
        initialization = initialize_database(reset=False)
    except Exception as exc:
        st.title("Dashboard Financiero")
        st.error(f"No fue posible inicializar la base de datos: {exc}")
        st.info("La app no realizó cambios destructivos. Revisa la carpeta data/ o ejecuta scripts/init_db.py.")
        return

    if initialization["seeded"]:
        load_users.clear()
        load_dashboard_data.clear()

    st.title("Dashboard Financiero")
    st.caption("Fase 8 · Selector de usuario, pestañas funcionales e informe PDF descargable")

    st.info(
        f"Entorno: {settings.environment} · Base del proyecto: {settings.base_dir} · "
        f"DB: {initialization['database_path']}"
    )

    users = load_users()
    selected_user = render_sidebar(users)

    if not selected_user:
        st.warning("No fue posible cargar usuarios. Verifica la base de datos o ejecuta scripts/init_db.py.")
        return

    st.sidebar.header("Parámetros")
    prefer_live_data = True
    rebalance_threshold = float(
        st.sidebar.slider(
            "Umbral de rebalanceo (%)",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
        )
    )

    try:
        dashboard_data = load_dashboard_data(
            selected_user["user_email"],
            rebalance_threshold=rebalance_threshold,
            prefer_live_data=prefer_live_data,
        )
    except Exception as exc:
        st.error(f"Error al obtener datos reales de mercado (HRP): {exc}")
        st.info("Por favor, comprueba tu conexión a internet o vuelve a intentarlo más tarde.")
        return

    header_columns = st.columns((1.8, 1.2))
    with header_columns[0]:
        st.subheader(selected_user["user_name"])
        st.write(f"Portfolio principal: {dashboard_data['user_portfolios'][0]['portfolio_name'] if dashboard_data['user_portfolios'] else 'Sin portfolio'}")

    with header_columns[1]:
        summary_frame = pd.DataFrame(
            [
                {
                    "Indicador": "Fuente HRP",
                    "Valor": dashboard_data["hrp_snapshot"].get("diagnostics", {}).get("price_source", "n/d"),
                },
                {
                    "Indicador": "Umbral rebalanceo",
                    "Valor": f"{rebalance_threshold:.2f}%",
                },
            ]
        )
        st.dataframe(summary_frame, width="stretch", hide_index=True)

    tab_labels = ["Resumen", "Portfolio", "Advisor", "Evolución", "Informes"]
    overview_tab, portfolio_tab, advisor_tab, evolution_tab, reports_tab = st.tabs(tab_labels)

    with overview_tab:
        tab_overview.render(selected_user=selected_user, dashboard_data=dashboard_data)

    with portfolio_tab:
        tab_portfolio.render(selected_user=selected_user, dashboard_data=dashboard_data)

    with advisor_tab:
        tab_advisor.render(selected_user=selected_user, dashboard_data=dashboard_data)

    with evolution_tab:
        tab_evolution.render(selected_user=selected_user, dashboard_data=dashboard_data)

    with reports_tab:
        tab_reports.render(selected_user=selected_user, dashboard_data=dashboard_data)


if __name__ == "__main__":
    main()
