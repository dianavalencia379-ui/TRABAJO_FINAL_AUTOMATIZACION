from __future__ import annotations

import sqlite3

from data_layer.db import create_schema, get_user_portfolios, get_users, seed_database


def _build_seeded_connection() -> sqlite3.Connection:
    """Crea una base en memoria con datos seed para probar helpers SQL."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def test_get_users_returns_seeded_users_with_aggregates() -> None:
    """Valida que la consulta de usuarios entregue agregados poblados."""
    connection = _build_seeded_connection()

    rows = get_users(connection)

    assert len(rows) == 3
    assert rows[0]["portfolio_count"] >= 1
    assert rows[0]["position_count"] >= 5
    assert rows[0]["invested_amount"] > 0


def test_get_user_portfolios_filters_by_user_email() -> None:
    """Comprueba el filtrado de portfolios por email de usuario."""
    connection = _build_seeded_connection()

    rows = get_user_portfolios(connection, user_email="dianavalencia379@gmail.com")

    assert len(rows) == 1
    assert rows[0]["portfolio_name"] == "Growth USA"
    assert rows[0]["user_email"] == "dianavalencia379@gmail.com"
