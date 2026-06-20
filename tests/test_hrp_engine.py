from __future__ import annotations

import sqlite3

from data_layer.db import create_schema, seed_database
from data_layer.yahoo_client import fetch_price_history, generate_simulated_price_history
from domain.hrp_engine import build_hrp_portfolio_snapshot, calculate_hrp_weights


def _build_seeded_connection() -> sqlite3.Connection:
    """Crea una base en memoria con datos seed para pruebas HRP."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def test_generate_simulated_price_history_returns_complete_frame() -> None:
    """Valida que el histórico simulado cubra todos los tickers solicitados."""
    prices = generate_simulated_price_history(["AAPL", "MSFT", "NVDA"], lookback_days=120)

    assert list(prices.columns) == ["AAPL", "MSFT", "NVDA"]
    assert len(prices.index) == 120
    assert prices.isna().sum().sum() == 0
    assert (prices > 0).all().all()


def test_fetch_price_history_uses_simulated_fallback_when_live_disabled() -> None:
    """Comprueba el uso del fallback simulado cuando se desactiva Yahoo."""
    result = fetch_price_history(["AAPL", "MSFT", "NVDA"], lookback_days=90, prefer_live_data=False)

    assert result.source == "simulated"
    assert result.metadata["fallback"] is True
    assert list(result.prices.columns) == ["AAPL", "MSFT", "NVDA"]
    assert len(result.prices.index) == 90


def test_calculate_hrp_weights_sums_to_one() -> None:
    """Verifica que los pesos HRP calculados formen una asignación válida."""
    prices = generate_simulated_price_history(["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"], lookback_days=180)

    result = calculate_hrp_weights(prices)

    assert len(result["recommended_weights"]) == 5
    assert round(sum(result["recommended_weights"].values()), 6) == 1.0
    assert all(0.0 < weight < 1.0 for weight in result["recommended_weights"].values())
    assert len(result["cluster_order"]) == 5
    assert set(result["cluster_order"]) == {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"}


def test_build_hrp_portfolio_snapshot_returns_interpretable_weights() -> None:
    """Asegura que el snapshot HRP devuelva pesos y diagnósticos interpretables."""
    connection = _build_seeded_connection()

    snapshot = build_hrp_portfolio_snapshot(
        connection=connection,
        user_email="diana@example.com",
        prefer_live_data=False,
        lookback_days=150,
    )

    assert snapshot["tickers"] == ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"]
    assert snapshot["diagnostics"]["price_source"] == "simulated"
    assert snapshot["diagnostics"]["used_fallback"] is True
    assert round(sum(snapshot["current_weights"].values()), 6) == 1.0
    assert round(sum(snapshot["recommended_weights"].values()), 6) == 1.0
    assert snapshot["diagnostics"]["weights_sum"]["current"] == 1.0
    assert snapshot["diagnostics"]["weights_sum"]["recommended"] == 1.0
    assert len(snapshot["weights_table"]) == 5
    assert snapshot["weights_table"][0]["ticker"] in snapshot["tickers"]
    assert set(snapshot["matrices"]["correlation"].keys()) == set(snapshot["tickers"])
