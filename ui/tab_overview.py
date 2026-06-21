from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """Muestra el resumen ejecutivo del usuario seleccionado.

    Esta pestaña es la primera pantalla que ve cualquier usuario al entrar
    al dashboard. Su objetivo dentro del proyecto es comunicar, de un
    vistazo y sin tecnicismos, el estado financiero de su cartera -- por
    eso se prioriza el uso de metricas grandes, tarjetas e iconos sobre
    tablas crudas de base de datos (que es justo el problema que la
    interfaz busca resolver para el usuario final).
    """
    if not selected_user:
        st.info("Selecciona un usuario para ver el resumen financiero.")
        return

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]
    summary = portfolio_snapshot["portfolio_summary"]
    metrics = evolution_snapshot["metrics"]
    advisor_summary = advisor_snapshot["summary"]
    advisor_table = advisor_snapshot.get("advisor_table", [])

    # --- Alerta de riesgo (dato calculado por evolution_engine que antes
    # no se usaba en ninguna pestaña) ---
    # Se compara el drawdown actual contra el peor drawdown historico del
    # propio portfolio, en vez de un umbral fijo arbitrario: asi la alerta
    # tiene sentido sin importar si la cartera es muy o poco volatil.
    latest_drawdown = float(metrics.get("latest_drawdown_pct", 0.0))
    max_drawdown = float(metrics.get("max_drawdown_pct", 0.0))

    if latest_drawdown >= -0.01:
        st.success(
            f"🎉 La cartera está en (o muy cerca de) su máximo histórico "
            f"· drawdown actual: {latest_drawdown:.2f}%"
        )
    elif max_drawdown < 0 and abs(latest_drawdown) >= abs(max_drawdown) * 0.9:
        st.warning(
            f"⚠️ La cartera está cerca de su peor caída histórica registrada "
            f"· drawdown actual: {latest_drawdown:.2f}% (máxima caída: {max_drawdown:.2f}%)"
        )
    else:
        st.info(f"La cartera tiene un drawdown actual de {latest_drawdown:.2f}%, dentro de su rango histórico normal.")

    # --- Bloque 1: metricas clave de la cartera ---
    # Se agregan tooltips (help=) para que un usuario sin formacion
    # financiera entienda cada indicador sin salir del dashboard. Esto
    # aporta directamente al objetivo academico de "usabilidad" evaluado
    # en el proyecto.
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "💰 Valor estimado",
        f"${summary['total_current_value']:,.2f}",
        help="Valor de mercado actual de todas las posiciones de la cartera.",
    )
    metric_columns[1].metric(
        "📊 Posiciones",
        int(summary["position_count"]),
        help="Numero de activos distintos que componen la cartera.",
    )
    metric_columns[2].metric(
        "📈 Rentabilidad acumulada",
        f"{metrics['cumulative_return_pct']:.2f}%",
        help="Ganancia o perdida total del portfolio desde el inicio del historico disponible.",
    )
    metric_columns[3].metric(
        "📉 Caida maxima",
        f"{metrics['max_drawdown_pct']:.2f}%",
        help="Mayor caida registrada desde un maximo historico (drawdown). Mide el riesgo asumido.",
    )

    # --- Bloque 1b (NUEVO): mejor/peor periodo y monto a reasignar ---
    # best_period_return_pct y worst_period_return_pct ya los calcula el
    # motor de evolucion (domain/evolution_engine.py) pero no se mostraban
    # en ninguna pestana, aunque el plan original del proyecto los exige
    # explicitamente en la seccion de evolucion historica. El monto a
    # reasignar se deriva de advisor_table (motor de rebalanceo de
    # Antonio): se suman solo los activos a "aumentar" porque el neto de
    # toda la cartera siempre tiende a 0 (es una reasignacion interna, no
    # entra ni sale dinero), asi que el neto solo sirve como verificacion
    # de que el rebalanceo no crea ni destruye valor.
    total_to_reallocate = sum(
        item["value_delta"] for item in advisor_table if item.get("action") == "increase"
    )
    net_check = advisor_summary.get("net_value_delta", 0.0)

    highlight_columns = st.columns(3)
    highlight_columns[0].metric(
        "🏆 Mejor periodo",
        f"{metrics.get('best_period_return_pct', 0.0):.2f}%",
        help="Mejor rentabilidad registrada en un único periodo dentro del histórico.",
    )
    highlight_columns[1].metric(
        "🔻 Peor periodo",
        f"{metrics.get('worst_period_return_pct', 0.0):.2f}%",
        help="Peor rentabilidad registrada en un único periodo dentro del histórico.",
    )
    highlight_columns[2].metric(
        "💱 Monto a reasignar",
        f"${total_to_reallocate:,.2f}",
        help=(
            "Capital total que se movería hacia activos infraponderados según el HRP. "
            f"Verificación de balance (debe ser ≈ $0): {net_check:,.2f}"
        ),
    )

    # --- Bloque 1c: conteo de acciones del advisor, incluyendo los
    # activos en equilibrio (hold_count), que antes no se contaban ---
    detail_columns = st.columns(4)
    detail_columns[0].metric("🗂️ Portfolio(s)", int(summary["portfolio_count"]))
    detail_columns[1].metric(
        "🟢 Activos a aumentar",
        int(advisor_summary["increase_count"]),
        help="Activos donde el peso actual esta por debajo del peso recomendado por el modelo HRP.",
    )
    detail_columns[2].metric(
        "🔴 Activos a reducir",
        int(advisor_summary["reduce_count"]),
        help="Activos donde el peso actual supera al peso recomendado por el modelo HRP.",
    )
    detail_columns[3].metric(
        "⚪ Activos en equilibrio",
        int(advisor_summary.get("hold_count", 0)),
        help="Activos cuya desviación respecto al peso HRP está dentro del umbral tolerado (no requieren acción).",
    )

    st.divider()  # separador visual: cierra el bloque de metricas antes de los graficos

    left_column, right_column = st.columns((1.7, 1.1))

    with left_column:
        st.subheader("📈 Evolución del portfolio")
        series = evolution_snapshot.get("series", [])
        if series:
            history_frame = pd.DataFrame(series).set_index("date")[["total_value"]]
            st.line_chart(history_frame)
        else:
            st.info("No hay histórico disponible para este usuario.")

    with right_column:
        st.subheader("📌 Principales posiciones")
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
            st.dataframe(top_positions, width="stretch", hide_index=True)
        else:
            st.info("No hay posiciones para mostrar.")

    st.divider()

    # --- Bloque 2: estado general ---
    # Antes esta seccion era una tabla cruda tipo base de datos (fila por
    # indicador). Se rediseña como tarjetas con icono + texto: es
    # exactamente el cambio que corresponde al rol de UI Lead, transformar
    # "datos de tabla" en "informacion legible" para el usuario final.
    st.subheader("ℹ️ Estado general")
    info_left, info_right = st.columns(2)

    with info_left:
        st.markdown(f"**👤 Usuario:** {selected_user['user_name']}")
        st.markdown(f"**📧 Email:** {selected_user['user_email']}")
        periodo = (
            f"{metrics['start_date']} → {metrics['end_date']}"
            if metrics["points"]
            else "Sin histórico"
        )
        st.markdown(f"**📅 Periodo analizado:** {periodo}")

    with info_right:
        st.markdown(f"**🎯 Pesos objetivo HRP:** {advisor_summary['asset_count']} activos")
        price_source = dashboard_data["hrp_snapshot"].get("diagnostics", {}).get("price_source", "n/d")
        st.markdown(f"**🔗 Origen de precios HRP:** {price_source}")