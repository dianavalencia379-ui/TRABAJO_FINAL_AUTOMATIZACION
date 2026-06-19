from __future__ import annotations

import streamlit as st

from config import settings


def main() -> None:
    st.set_page_config(
        page_title=settings.app_name,
        page_icon="📊",
        layout="wide",
    )

    st.title("Dashboard Financiero")
    st.caption("Fase 1 · Estructura base del proyecto")

    st.success("La aplicación Streamlit se ha inicializado correctamente.")

    st.write(
        "Este proyecto servirá como base para gestionar portfolios, advisor HRP, "
        "evolución histórica e informes financieros."
    )

    st.info(
        f"Entorno: {settings.environment} · Base del proyecto: {settings.base_dir}"
    )

    st.subheader("Estructura inicial preparada")
    st.markdown(
        "- `app.py` para la interfaz Streamlit\n"
        "- `api.py` para la API futura con FastAPI\n"
        "- capas `data_layer/`, `domain/`, `ui/`, `reports/`, `scripts/`, `tests/`"
    )


if __name__ == "__main__":
    main()
