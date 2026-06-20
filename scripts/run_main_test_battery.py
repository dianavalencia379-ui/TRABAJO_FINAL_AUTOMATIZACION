from __future__ import annotations

from pathlib import Path

import pytest


MAIN_TEST_BATTERY = [
    "tests/test_portfolio_engine.py",
    "tests/test_hrp_engine.py",
    "tests/test_pdf_generator.py",
    "tests/test_api_report_endpoint.py",
]


def main() -> int:
    """Ejecuta la batería principal de tests de regresión del proyecto."""
    project_root = Path(__file__).resolve().parents[1]
    test_targets = [str(project_root / relative_path) for relative_path in MAIN_TEST_BATTERY]
    print("Ejecutando batería principal de validación (Fase 11):")
    for target in MAIN_TEST_BATTERY:
        print(f" - {target}")
    return pytest.main(["-ra", *test_targets])


if __name__ == "__main__":
    raise SystemExit(main())
