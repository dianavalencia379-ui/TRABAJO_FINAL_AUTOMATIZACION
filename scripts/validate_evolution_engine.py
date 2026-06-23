# ============================================================
# scripts/validate_evolution_engine.py — Validación del motor
# de evolución histórica. Ejecuta el motor y muestra métricas
# y serie histórica en consola para verificación manual.
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
from domain.evolution_engine import build_evolution_snapshot_from_db


def main() -> int:
    """
    Valida por consola la salida agregada del motor de evolución histórica.

    Pasos:
      1. Inicializar la base de datos
      2. Construir el snapshot de evolución agregado (todos los portfolios)
      3. Mostrar métricas, primeros puntos de la serie y resumen por portfolio
    """
    # Paso 1: Inicializar base de datos sin resetear datos existentes
    db_result = initialize_database(reset=False)

    # Paso 2: Construir snapshot de evolución agregado (sin filtro = todos)
    snapshot = build_evolution_snapshot_from_db()

    # Paso 3: Mostrar resultados en consola para verificación manual
    print("Base lista:", db_result["is_functional"])

    # Métricas globales: rentabilidad, drawdown, fechas, etc.
    print("Métricas globales de evolución:")
    pprint(snapshot["metrics"])

    # Primeros 5 puntos de la serie histórica agregada
    print("Primeros 5 puntos de la serie agregada:")
    pprint(snapshot["series"][:5])

    # Resumen de evolución desglosado por portfolio
    print("Resumen por portfolio:")
    pprint(db_result["portfolio_evolution_summaries"])

    # Retornar 0 si la base pasó la verificación funcional, 1 si no
    return 0 if db_result["is_functional"] else 1


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
