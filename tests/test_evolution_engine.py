from __future__ import annotations

from math import isclose
import sqlite3

from data_layer.db import create_schema, seed_database
from data_layer.seed_data import build_seed_payload
from domain.evolution_engine import (
    build_evolution_snapshot,
    build_evolution_snapshot_from_db,
    generate_fictional_history,
)


def _build_seeded_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def test_generate_fictional_history_is_deterministic_and_monthly() -> None:
    history = generate_fictional_history(
        start_value=100.0,
        monthly_return=0.01,
        seasonality=0.0,
        periods=3,
        shock_periods=(),
    )

    assert history == [
        {"date": "2023-01-31", "total_value": 101.0},
        {"date": "2023-02-28", "total_value": 102.01},
        {"date": "2023-03-31", "total_value": 103.03},
    ]


def test_build_evolution_snapshot_calculates_returns_and_drawdown() -> None:
    history = [
        {"date": "2024-01-31", "total_value": 100.0},
        {"date": "2024-02-29", "total_value": 110.0},
        {"date": "2024-03-31", "total_value": 105.0},
        {"date": "2024-04-30", "total_value": 120.0},
    ]

    snapshot = build_evolution_snapshot(history, label="demo")
    metrics = snapshot["metrics"]

    expected_annualized = ((120.0 / 100.0) ** (1 / (90 / 365.25)) - 1) * 100

    assert snapshot["label"] == "demo"
    assert len(snapshot["series"]) == 4
    assert metrics["start_value"] == 100.0
    assert metrics["end_value"] == 120.0
    assert metrics["cumulative_return_pct"] == 20.0
    assert metrics["max_drawdown_pct"] == -4.5455
    assert metrics["latest_drawdown_pct"] == 0.0
    assert metrics["best_period_return_pct"] == 14.2857
    assert metrics["worst_period_return_pct"] == -4.5455
    assert isclose(metrics["annualized_return_pct"], round(expected_annualized, 4), rel_tol=0.0, abs_tol=0.0001)


def test_build_evolution_snapshot_from_db_aggregates_seeded_history() -> None:
    connection = _build_seeded_connection()
    seed_payload = build_seed_payload()

    expected_start = round(
        sum(portfolio["portfolio"]["history_records"][0]["total_value"] for portfolio in seed_payload),
        2,
    )
    expected_end = round(
        sum(portfolio["portfolio"]["history_records"][-1]["total_value"] for portfolio in seed_payload),
        2,
    )

    snapshot = build_evolution_snapshot_from_db(connection=connection)

    assert snapshot["filters"] == {"portfolio_id": None, "user_email": None}
    assert snapshot["metrics"]["points"] == 36
    assert snapshot["metrics"]["start_date"] == "2023-01-31"
    assert snapshot["metrics"]["end_date"] == "2025-12-31"
    assert snapshot["metrics"]["start_value"] == expected_start
    assert snapshot["metrics"]["end_value"] == expected_end
    assert snapshot["metrics"]["cumulative_return_pct"] > 0
    assert len(snapshot["series"]) == 36


def test_build_evolution_snapshot_from_db_filters_single_user() -> None:
    connection = _build_seeded_connection()

    snapshot = build_evolution_snapshot_from_db(
        connection=connection,
        user_email="jose@example.com",
    )

    assert snapshot["filters"] == {
        "portfolio_id": None,
        "user_email": "jose@example.com",
    }
    assert snapshot["label"] == "user:jose@example.com"
    assert snapshot["metrics"]["points"] == 36
    assert snapshot["metrics"]["start_value"] > 0
    assert snapshot["metrics"]["max_drawdown_pct"] <= 0
