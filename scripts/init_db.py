# ============================================================
# scripts/init_db.py — Inicializador de base de datos
# Script CLI para crear el esquema SQLite, insertar datos
# ficticios y validar la base del Dashboard Financiero.
# ============================================================

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_layer.db import get_database_path, initialize_database


# ------------------------------------------------------------
# Argumentos CLI
# ------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Define y parsea los argumentos CLI del inicializador de base.
    Uso: python init_db.py [--reset]
    """
    parser = argparse.ArgumentParser(
        description="Inicializa la base SQLite del dashboard."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina la base existente antes de recrear el esquema y recargar datos.",
    )
    return parser.parse_args()


# ------------------------------------------------------------
# Función principal
# ------------------------------------------------------------

def main() -> int:
    """
    Inicializa la base de datos y muestra un resumen de validación en consola.

    Retorna 0 si la base pasó la verificación funcional, 1 si no.
    """
    args = parse_args()

    # Inicializar base de datos (con o sin reset según el argumento)
    result = initialize_database(reset=args.reset)

    # Mostrar ruta de la base de datos
    print(f"Base de datos objetivo: {get_database_path()}")

    # Indicar si se insertaron datos ficticios en esta ejecución
    print(f"Datos ficticios insertados en esta ejecución: {result['seeded']}")

    # Conteo de registros por tabla
    print("Conteo por tabla:")
    for table_name, total in result["counts"].items():
        print(f"- {table_name}: {total}")

    # Resumen por portfolio con posiciones e historial
    print("Resumen por portfolio:")
    for summary in result["portfolio_summaries"]:
        print(
            "- #{portfolio_id} {user_name} ({email}) · {portfolio_name} · "
            "{positions_count} posiciones · {history_points} puntos históricos · "
            "importe estimado ${invested_amount}".format(**summary)
        )

    # Métricas de evolución histórica por portfolio
    print("Evolución histórica por portfolio:")
    for summary in result["portfolio_evolution_summaries"]:
        print(
            "- #{portfolio_id} {portfolio_name} · acumulada {cumulative_return_pct}% · "
            "anualizada {annualized_return_pct}% · max drawdown {max_drawdown_pct}% · "
            "desde {start_date} hasta {end_date}".format(**summary)
        )

    # Resultado de la verificación funcional de la base
    print(f"Verificación funcional: {result['is_functional']}")

    # Retornar 0 si todo está correcto, 1 si hay problemas
    return 0 if result["is_functional"] else 1


# Punto de entrada al ejecutar el script directamente
if __name__ == "__main__":
    raise SystemExit(main())
