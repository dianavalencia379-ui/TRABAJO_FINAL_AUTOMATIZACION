# ============================================================
# scripts/validate_rebalance_engine.py — Validación del advisor
# de rebalanceo. Muestra resumen y tabla de acciones por usuario
# en consola para verificación manual.
# ============================================================

from __future__ import annotations

from pprint import pprint

from data_layer.db import initialize_database
from domain.rebalance_engine import build_rebalance_advisor_snapshot


# Usuarios de prueba para validar el advisor de rebalanceo
USER_EMAILS = (
    "dvalenciag@student.universidadviu.com",
    "antonio@example.com",
    "jose@example.com",
)


def main() -> int:
    """
    Ejecuta una validación manual del advisor de rebalanceo para varios usuarios.

    Usa datos simulados (prefer_live_data=False) con ventana de 180 días
    y umbral de rebalanceo del 3% para validación local sin Yahoo Finance.
    """
    # Inicializar base de datos sin resetear datos existentes
    db_result = initialize_database(reset=False)
    print("Base lista:", db_result["is_functional"])

    # Ejecutar el advisor para cada usuario de prueba
    for user_email in USER_EMAILS:
        snapshot = build_rebalance_advisor_snapshot(
            user_email=user_email,
            prefer_live_data=False,  # Usar datos simulados para validación local
            lookback_days=180,       # Ventana de 6 meses de historial de precios
            rebalance_threshold=3,   # Umbral del 3% para clasificar acciones
        )

        print(f"\n=== Rebalance advisor {user_email} ===")

        # Resumen: conteo de acciones (aumentar/reducir/mantener) y totales
        pprint(snapshot["summary"])

        # Tabla detallada: peso actual vs objetivo y acción recomendada por activo
        pprint(snapshot["advisor_table"])

    return 0


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
