from __future__ import annotations

from pprint import pprint

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_layer.db import initialize_database
from domain.evolution_engine import build_evolution_snapshot_from_db


def main() -> int:
    """Valida por consola la salida agregada del motor de evolución."""
    db_result = initialize_database(reset=False)
    snapshot = build_evolution_snapshot_from_db()

    print("Base lista:", db_result["is_functional"])
    print("Métricas globales de evolución:")
    pprint(snapshot["metrics"])
    print("Primeros 5 puntos de la serie agregada:")
    pprint(snapshot["series"][:5])
    print("Resumen por portfolio:")
    pprint(db_result["portfolio_evolution_summaries"])
    return 0 if db_result["is_functional"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
