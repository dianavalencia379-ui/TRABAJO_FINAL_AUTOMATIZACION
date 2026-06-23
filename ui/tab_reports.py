# ============================================================
# ui/tab_reports.py — Pestaña Informes
# Centraliza las exportaciones CSV, JSON y PDF del dashboard
# del Dashboard Financiero.
# ============================================================

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from reports.pdf_generator import (
    ReportGenerationError,
    build_report_payload,
    generate_user_report_pdf,
    is_pdf_generation_available,
)


def render(*, selected_user: dict[str, Any] | None, dashboard_data: dict[str, Any]) -> None:
    """
    Renderiza la pestaña de informes y exportaciones del dashboard.

    Secciones:
      1. Resumen exportable con métricas clave
      2. Advertencias del payload del informe
      3. Estructura del informe PDF (expandible)
      4. Descarga de posiciones en CSV
      5. Descarga del advisor HRP en CSV
      6. Generación y descarga del informe PDF completo
      7. Descarga del resumen en JSON
    """
    if not selected_user:
        st.info("Selecciona un usuario para preparar informes.")
        return

    # Extraer snapshots necesarios para los informes
    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]

    # ------------------------------------------------------------
    # Sección 1: Resumen exportable con métricas clave
    # ------------------------------------------------------------
    st.subheader("Resumen exportable")
    pdf_available, pdf_message = is_pdf_generation_available()

    # Construir payload del informe con todos los datos del dashboard
    report_payload = build_report_payload(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )

    # Tabla resumen con los indicadores más relevantes
    report_rows = [
        {"Sección": "Usuario",
         "Valor": selected_user["user_name"]},
        {"Sección": "Email",
         "Valor": selected_user["user_email"]},
        {"Sección": "Valor portfolio",
         "Valor": f"${portfolio_snapshot['portfolio_summary']['total_current_value']:,.2f}"},
        {"Sección": "Rentabilidad acumulada (%)",
         "Valor": f"{evolution_snapshot['metrics']['cumulative_return_pct']:.2f}%"},
        {"Sección": "Activos con acción",
         "Valor": str(
             advisor_snapshot["summary"]["increase_count"] +
             advisor_snapshot["summary"]["reduce_count"]
         )},
    ]
    st.dataframe(pd.DataFrame(report_rows), width="stretch", hide_index=True)
    st.caption("El informe PDF reutiliza los snapshots de portfolio, evolución, HRP y rebalanceo por usuario.")

    # ------------------------------------------------------------
    # Sección 2: Advertencias del payload del informe
    # ------------------------------------------------------------
    if report_payload["warnings"]:
        for warning in report_payload["warnings"]:
            st.warning(warning)

    # ------------------------------------------------------------
    # Sección 3: Estructura del informe PDF (panel expandible)
    # ------------------------------------------------------------
    with st.expander("Estructura del informe PDF", expanded=False):
        # Listar secciones incluidas en el PDF
        st.markdown("\n".join(f"- {section}" for section in report_payload["sections"]))
        st.caption(report_payload["commentary"])

    # ------------------------------------------------------------
    # Sección 4 y 5: Descargas en CSV
    # ------------------------------------------------------------
    positions = portfolio_snapshot.get("positions_table", [])
    advisor_rows = advisor_snapshot.get("advisor_table", [])

    # Botón de descarga de posiciones del portfolio en CSV
    if positions:
        positions_csv = pd.DataFrame(positions).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar posiciones (CSV)",
            data=positions_csv,
            file_name=f"portfolio_{selected_user['user_email'].replace('@', '_at_')}.csv",
            mime="text/csv",
        )

    # Botón de descarga de recomendaciones del advisor HRP en CSV
    if advisor_rows:
        advisor_csv = pd.DataFrame(advisor_rows).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar advisor HRP (CSV)",
            data=advisor_csv,
            file_name=f"advisor_{selected_user['user_email'].replace('@', '_at_')}.csv",
            mime="text/csv",
        )

    # ------------------------------------------------------------
    # Sección 6: Generación y descarga del informe PDF completo
    # ------------------------------------------------------------
    # Clave única en session_state para cachear el PDF por usuario
    pdf_state_key = f"pdf_report::{selected_user['user_email']}"
    action_columns = st.columns((1.2, 1.8))

    with action_columns[0]:
        if pdf_available:
            # Botón para generar el informe PDF
            if st.button("Preparar informe PDF", width="stretch"):
                try:
                    report = generate_user_report_pdf(
                        selected_user=selected_user,
                        dashboard_data=dashboard_data,
                    )
                except ReportGenerationError as exc:
                    # Limpiar estado previo si la generación falla
                    st.session_state.pop(pdf_state_key, None)
                    st.error(str(exc))
                else:
                    # Guardar el PDF en session_state para descarga inmediata
                    st.session_state[pdf_state_key] = report
                    st.success("Informe PDF listo para descargar.")
        else:
            st.warning(pdf_message or "La generación PDF no está disponible en este entorno.")

    with action_columns[1]:
        # Mostrar botón de descarga si el PDF ya fue generado
        cached_report = st.session_state.get(pdf_state_key)
        if cached_report:
            st.download_button(
                label="Descargar informe PDF",
                data=cached_report.content,
                file_name=cached_report.file_name,
                mime="application/pdf",
                width="stretch",
            )
            # Mostrar metadatos del PDF generado
            st.caption(
                f"Generado: {cached_report.generated_at} · "
                f"Secciones incluidas: {len(cached_report.sections)}"
            )
        elif pdf_available:
            st.info("Prepara el informe para habilitar la descarga PDF.")

    # ------------------------------------------------------------
    # Sección 7: Descarga del resumen en formato JSON
    # ------------------------------------------------------------
    # Construir payload JSON con los datos más relevantes del dashboard
    payload = {
        "user": selected_user,
        "portfolio_summary": portfolio_snapshot.get("portfolio_summary", {}),
        "evolution_metrics": evolution_snapshot.get("metrics", {}),
        "advisor_summary": advisor_snapshot.get("summary", {}),
    }
    st.download_button(
        label="Descargar resumen (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"summary_{selected_user['user_email'].replace('@', '_at_')}.json",
        mime="application/json",
    )
