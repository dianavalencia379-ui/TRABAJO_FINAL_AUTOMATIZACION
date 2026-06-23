# ============================================================
# scripts/validate_hrp_engine.py — Validación del motor HRP
# Ejecuta el algoritmo HRP para varios usuarios y muestra
# diagnósticos y pesos recomendados en consola.
# ============================================================

from __future__ import annotations

from pprint import pprint

from data_layer.db import initialize_database
from domain.hrp_engine import build_hrp_portfolio_snapshot


# Usuarios de prueba para validar el motor HRP
USER_EMAILS = (
    "dvalenciag@student.universidadviu.com",
    "antonio@example.com",
    "jose@example.com",
)


def main() -> int:
    """
    Ejecuta una validación manual del snapshot HRP para varios usuarios.

    Usa datos simulados (prefer_live_data=False) con ventana de 180 días
    para validar el algoritmo sin depender de conexión a Yahoo Finance.
    """
    # Inicializar base de datos sin resetear datos existentes
    db_result = initialize_database(reset=False)
    print("Base lista:", db_result["is_functional"])

    # Ejecutar HRP para cada usuario de prueba
    for user_email in USER_EMAILS:
        snapshot = build_hrp_portfolio_snapshot(
            user_email=user_email,
            prefer_live_data=False,  # Usar datos simulados para validación local
            lookback_days=180,       # Ventana de 6 meses de historial
        )

        print(f"\n=== HRP {user_email} ===")

        # Mostrar diagnósticos: fuente de precios, clustering, advertencias
        pprint(snapshot["diagnostics"])

        # Mostrar tabla de pesos: actual vs recomendado por HRP
        pprint(snapshot["weights_table"])

    return 0


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
