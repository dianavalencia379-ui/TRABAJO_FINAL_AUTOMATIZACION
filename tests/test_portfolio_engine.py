from __future__ import annotations

import sqlite3

from data_layer.db import create_schema, seed_database
from domain.portfolio_engine import build_portfolio_snapshot


def _build_seeded_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def test_build_portfolio_snapshot_aggregates_seeded_data() -> None:
    connection = _build_seeded_connection()

    snapshot = build_portfolio_snapshot(connection=connection)

    assert snapshot["portfolio_summary"] == {
        "portfolio_count": 3,
        "position_count": 15,
        "total_quantity": 337.0,
        "total_cost_basis": 81509.15,
        "total_current_value": 81509.15,
        "pricing_method": "avg_price",
    }
    assert len(snapshot["positions_table"]) == 15
    assert snapshot["positions_table"][0]["ticker"] == "NVDA"
    assert snapshot["positions_table"][0]["current_value"] == 15161.4
    assert round(sum(item["weight_pct"] for item in snapshot["positions_table"]), 4) == 100.0
    assert snapshot["composition"]["by_asset"][0]["ticker"] == "NVDA"
    assert snapshot["composition"]["by_portfolio"][0]["portfolio_name"] == "Growth USA"


def test_build_portfolio_snapshot_filters_single_user() -> None:
    connection = _build_seeded_connection()

    snapshot = build_portfolio_snapshot(
        connection=connection,
        user_email="jose@example.com",
    )

    assert snapshot["portfolio_summary"] == {
        "portfolio_count": 1,
        "position_count": 5,
        "total_quantity": 99.0,
        "total_cost_basis": 29824.45,
        "total_current_value": 29824.45,
        "pricing_method": "avg_price",
    }
    assert [item["portfolio_name"] for item in snapshot["portfolio_breakdown"]] == ["Tech Balanced"]
    assert all(row["user_email"] == "jose@example.com" for row in snapshot["positions_table"])
    assert round(sum(item["weight_pct"] for item in snapshot["composition"]["by_asset"]), 4) == 100.0


def test_build_portfolio_snapshot_returns_empty_structure_when_no_matches() -> None:
    connection = _build_seeded_connection()

    snapshot = build_portfolio_snapshot(
        connection=connection,
        user_email="missing@example.com",
    )

    assert snapshot["positions_table"] == []
    assert snapshot["portfolio_breakdown"] == []
    assert snapshot["composition"] == {"by_asset": [], "by_portfolio": []}
    assert snapshot["portfolio_summary"]["total_current_value"] == 0.0
