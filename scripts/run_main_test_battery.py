# ============================================================
# scripts/run_main_test_battery.py — Batería principal de tests
# Ejecuta los tests de regresión más importantes del proyecto
# Dashboard Financiero usando pytest.
# ============================================================

from __future__ import annotations

from pathlib import Path
import pytest


# ------------------------------------------------------------
# Definición de la batería principal de tests
# ------------------------------------------------------------

# Lista de archivos de test que conforman la batería principal
# Cubre los motores financieros, el generador PDF y el endpoint API
MAIN_TEST_BATTERY = [
    "tests/test_portfolio_engine.py",
    "tests/test_hrp_engine.py",
    "tests/test_pdf_generator.py",
    "tests/test_api_report_endpoint.py",
]


# ------------------------------------------------------------
# Función principal
# ------------------------------------------------------------

def main() -> int:
    """
    Ejecuta la batería principal de tests de regresión del proyecto.

    Retorna el código de salida de pytest:
      0 — todos los tests pasaron
      1 — algún test falló
    """
    # Resolver rutas absolutas desde la raíz del proyecto
    project_root = Path(__file__).resolve().parents[1]
    test_targets = [
        str(project_root / relative_path)
        for relative_path in MAIN_TEST_BATTERY
    ]

    # Mostrar los tests que se van a ejecutar
    print("Ejecutando batería principal de validación (Fase 11):")
    for target in MAIN_TEST_BATTERY:
        print(f" - {target}")

    # Ejecutar pytest con reporte resumido de resultados (-ra)
    return pytest.main(["-ra", *test_targets])


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
