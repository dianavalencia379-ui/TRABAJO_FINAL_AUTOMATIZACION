from __future__ import annotations

from pprint import pprint

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_layer.db import initialize_database
from domain.portfolio_engine import build_portfolio_snapshot


def main() -> int:
    """Ejecuta una validación manual del snapshot consolidado de portfolio."""
    db_result = initialize_database(reset=False)
    snapshot = build_portfolio_snapshot()

    print("Base lista:", db_result["is_functional"])
    print("Resumen portfolio:")
    pprint(snapshot["portfolio_summary"])
    print("Top 5 posiciones:")
    pprint(snapshot["positions_table"][:5])
    print("Composición por portfolio:")
    pprint(snapshot["composition"]["by_portfolio"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
