from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_layer.db import get_database_path, initialize_database


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos CLI del inicializador de base."""
    parser = argparse.ArgumentParser(description="Inicializa la base SQLite del dashboard.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina la base existente antes de recrear el esquema y recargar datos.",
    )
    return parser.parse_args()


def main() -> int:
    """Inicializa la base y muestra un resumen de validación en consola."""
    args = parse_args()
    result = initialize_database(reset=args.reset)

    print(f"Base de datos objetivo: {get_database_path()}")
    print(f"Datos ficticios insertados en esta ejecución: {result['seeded']}")
    print("Conteo por tabla:")
    for table_name, total in result["counts"].items():
        print(f"- {table_name}: {total}")

    print("Resumen por portfolio:")
    for summary in result["portfolio_summaries"]:
        print(
            "- #{portfolio_id} {user_name} ({email}) · {portfolio_name} · "
            "{positions_count} posiciones · {history_points} puntos históricos · "
            "importe estimado ${invested_amount}".format(**summary)
        )

    print("Evolución histórica por portfolio:")
    for summary in result["portfolio_evolution_summaries"]:
        print(
            "- #{portfolio_id} {portfolio_name} · acumulada {cumulative_return_pct}% · "
            "anualizada {annualized_return_pct}% · max drawdown {max_drawdown_pct}% · "
            "desde {start_date} hasta {end_date}".format(**summary)
        )

    print(f"Verificación funcional: {result['is_functional']}")
    return 0 if result["is_functional"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
