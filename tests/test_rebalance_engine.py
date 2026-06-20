from __future__ import annotations

import sqlite3

from data_layer.db import create_schema, seed_database
from domain.rebalance_engine import build_rebalance_advisor_snapshot, classify_rebalance_action


def _build_seeded_connection() -> sqlite3.Connection:
    """Crea una base en memoria con datos seed para pruebas de rebalanceo."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def test_classify_rebalance_action_uses_configurable_threshold() -> None:
    """Valida la clasificación de acciones según distintos umbrales."""
    assert classify_rebalance_action(difference=0.031, threshold=0.03) == "increase"
    assert classify_rebalance_action(difference=-0.031, threshold=3) == "reduce"
    assert classify_rebalance_action(difference=0.02, threshold=0.03) == "hold"


def test_build_rebalance_advisor_snapshot_returns_table_ready_output() -> None:
    """Asegura que el advisor produzca una tabla lista para UI y reportes."""
    connection = _build_seeded_connection()

    snapshot = build_rebalance_advisor_snapshot(
        connection=connection,
        user_email="diana@example.com",
        prefer_live_data=False,
        lookback_days=150,
        rebalance_threshold=3,
    )

    assert snapshot["filters"]["user_email"] == "diana@example.com"
    assert snapshot["rebalance_threshold"] == 0.03
    assert snapshot["rebalance_threshold_pct"] == 3.0
    assert snapshot["summary"]["asset_count"] == 5
    assert len(snapshot["advisor_table"]) == 5
    assert snapshot["summary"]["increase_count"] + snapshot["summary"]["reduce_count"] + snapshot["summary"]["hold_count"] == 5
    assert snapshot["summary"]["weights_sum_pct"]["current"] == 100.0
    assert snapshot["summary"]["weights_sum_pct"]["target"] == 100.0
    assert snapshot["advisor_table"][0]["abs_difference_pct"] >= snapshot["advisor_table"][-1]["abs_difference_pct"]
    assert {row["action"] for row in snapshot["advisor_table"]}.issubset({"increase", "reduce", "hold"})
    assert all(
        {
            "ticker",
            "asset_name",
            "current_value",
            "target_value",
            "value_delta",
            "current_weight_pct",
            "target_weight_pct",
            "difference_pct",
            "action",
            "action_label",
        }.issubset(row.keys())
        for row in snapshot["advisor_table"]
    )


def test_build_rebalance_advisor_snapshot_returns_empty_structure_when_no_matches() -> None:
    """Verifica la salida vacía del advisor cuando no existen posiciones."""
    connection = _build_seeded_connection()

    snapshot = build_rebalance_advisor_snapshot(
        connection=connection,
        user_email="missing@example.com",
        prefer_live_data=False,
    )

    assert snapshot["advisor_table"] == []
    assert snapshot["summary"]["asset_count"] == 0
    assert snapshot["summary"]["total_current_value"] == 0.0
    assert snapshot["diagnostics"]["warnings"]
