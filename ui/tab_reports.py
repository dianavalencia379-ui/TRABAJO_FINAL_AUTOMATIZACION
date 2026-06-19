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
    if not selected_user:
        st.info("Selecciona un usuario para preparar informes.")
        return

    portfolio_snapshot = dashboard_data["portfolio_snapshot"]
    evolution_snapshot = dashboard_data["evolution_snapshot"]
    advisor_snapshot = dashboard_data["advisor_snapshot"]

    st.subheader("Resumen exportable")
    pdf_available, pdf_message = is_pdf_generation_available()
    report_payload = build_report_payload(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )

    report_rows = [
        {"Sección": "Usuario", "Valor": selected_user["user_name"]},
        {"Sección": "Email", "Valor": selected_user["user_email"]},
        {"Sección": "Valor portfolio", "Valor": portfolio_snapshot["portfolio_summary"]["total_current_value"]},
        {"Sección": "Rentabilidad acumulada (%)", "Valor": evolution_snapshot["metrics"]["cumulative_return_pct"]},
        {"Sección": "Activos con acción", "Valor": advisor_snapshot["summary"]["increase_count"] + advisor_snapshot["summary"]["reduce_count"]},
    ]
    st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)

    st.caption("El informe PDF reutiliza los snapshots de portfolio, evolución, HRP y rebalanceo por usuario.")

    if report_payload["warnings"]:
        for warning in report_payload["warnings"]:
            st.warning(warning)

    with st.expander("Estructura del informe PDF", expanded=False):
        st.markdown("\n".join(f"- {section}" for section in report_payload["sections"]))
        st.caption(report_payload["commentary"])

    positions = portfolio_snapshot.get("positions_table", [])
    advisor_rows = advisor_snapshot.get("advisor_table", [])

    if positions:
        positions_csv = pd.DataFrame(positions).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar posiciones (CSV)",
            data=positions_csv,
            file_name=f"portfolio_{selected_user['user_email'].replace('@', '_at_')}.csv",
            mime="text/csv",
        )

    if advisor_rows:
        advisor_csv = pd.DataFrame(advisor_rows).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar advisor HRP (CSV)",
            data=advisor_csv,
            file_name=f"advisor_{selected_user['user_email'].replace('@', '_at_')}.csv",
            mime="text/csv",
        )

    pdf_state_key = f"pdf_report::{selected_user['user_email']}"
    action_columns = st.columns((1.2, 1.8))

    with action_columns[0]:
        if pdf_available:
            if st.button("Preparar informe PDF", use_container_width=True):
                try:
                    report = generate_user_report_pdf(
                        selected_user=selected_user,
                        dashboard_data=dashboard_data,
                    )
                except ReportGenerationError as exc:
                    st.session_state.pop(pdf_state_key, None)
                    st.error(str(exc))
                else:
                    st.session_state[pdf_state_key] = report
                    st.success("Informe PDF listo para descargar.")
        else:
            st.warning(pdf_message or "La generación PDF no está disponible en este entorno.")

    with action_columns[1]:
        cached_report = st.session_state.get(pdf_state_key)
        if cached_report:
            st.download_button(
                label="Descargar informe PDF",
                data=cached_report.content,
                file_name=cached_report.file_name,
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption(
                f"Generado: {cached_report.generated_at} · Secciones incluidas: {len(cached_report.sections)}"
            )
        elif pdf_available:
            st.info("Prepara el informe para habilitar la descarga PDF.")

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
