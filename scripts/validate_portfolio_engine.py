# ============================================================
# scripts/validate_portfolio_engine.py — Validación del motor
# de portfolio. Muestra resumen, posiciones y composición
# en consola para verificación manual.
# ============================================================

from __future__ import annotations

from pprint import pprint
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_layer.db import initialize_database
from domain.portfolio_engine import build_portfolio_snapshot


def main() -> int:
    """
    Ejecuta una validación manual del snapshot consolidado de portfolio.

    Muestra en consola:
      - Resumen global del portfolio (valor, posiciones, portfolios)
      - Top 5 posiciones por valor actual
      - Composición desglosada por portfolio
    """
    # Inicializar base de datos sin resetear datos existentes
    db_result = initialize_database(reset=False)

    # Construir snapshot consolidado de todos los portfolios
    snapshot = build_portfolio_snapshot()

    # Mostrar estado de la base de datos
    print("Base lista:", db_result["is_functional"])

    # Resumen global: valor total, número de posiciones y portfolios
    print("Resumen portfolio:")
    pprint(snapshot["portfolio_summary"])

    # Las 5 posiciones de mayor valor actual
    print("Top 5 posiciones:")
    pprint(snapshot["positions_table"][:5])

    # Distribución del capital entre los distintos portfolios
    print("Composición por portfolio:")
    pprint(snapshot["composition"]["by_portfolio"])

    return 0


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
