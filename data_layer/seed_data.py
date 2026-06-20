"""Datos ficticios iniciales para la base SQLite del dashboard."""

from __future__ import annotations

from typing import Any

from domain.evolution_engine import generate_fictional_history


SEED_USERS: list[dict[str, Any]] = [
    {
        "name": "Diana Valencia",
        "email": "diana@example.com",
        "portfolio": {
            "name": "Growth USA",
            "positions": [
                {"ticker": "AAPL", "asset_name": "Apple Inc.", "quantity": 28.0, "avg_price": 178.50},
                {"ticker": "MSFT", "asset_name": "Microsoft Corp.", "quantity": 16.0, "avg_price": 372.40},
                {"ticker": "NVDA", "asset_name": "NVIDIA Corp.", "quantity": 18.0, "avg_price": 842.30},
                {"ticker": "GOOGL", "asset_name": "Alphabet Inc.", "quantity": 20.0, "avg_price": 151.25},
                {"ticker": "AMZN", "asset_name": "Amazon.com Inc.", "quantity": 12.0, "avg_price": 182.90},
            ],
            "history": {
                "start_value": 52000.0,
                "monthly_return": 0.0125,
                "seasonality": 0.020,
            },
        },
    },
    {
        "name": "Antonio Ruiz",
        "email": "antonio@example.com",
        "portfolio": {
            "name": "Defensive Global",
            "positions": [
                {"ticker": "JNJ", "asset_name": "Johnson & Johnson", "quantity": 32.0, "avg_price": 152.80},
                {"ticker": "PG", "asset_name": "Procter & Gamble", "quantity": 24.0, "avg_price": 158.60},
                {"ticker": "KO", "asset_name": "Coca-Cola Co.", "quantity": 48.0, "avg_price": 61.15},
                {"ticker": "PEP", "asset_name": "PepsiCo Inc.", "quantity": 22.0, "avg_price": 171.75},
                {"ticker": "V", "asset_name": "Visa Inc.", "quantity": 18.0, "avg_price": 274.30},
            ],
            "history": {
                "start_value": 43000.0,
                "monthly_return": 0.0078,
                "seasonality": 0.012,
            },
        },
    },
    {
        "name": "José Martínez",
        "email": "jose@example.com",
        "portfolio": {
            "name": "Tech Balanced",
            "positions": [
                {"ticker": "AAPL", "asset_name": "Apple Inc.", "quantity": 18.0, "avg_price": 176.40},
                {"ticker": "AMD", "asset_name": "Advanced Micro Devices", "quantity": 30.0, "avg_price": 164.20},
                {"ticker": "MSFT", "asset_name": "Microsoft Corp.", "quantity": 14.0, "avg_price": 369.90},
                {"ticker": "META", "asset_name": "Meta Platforms Inc.", "quantity": 11.0, "avg_price": 468.55},
                {"ticker": "QQQ", "asset_name": "Invesco QQQ Trust", "quantity": 26.0, "avg_price": 438.10},
            ],
            "history": {
                "start_value": 47000.0,
                "monthly_return": 0.0101,
                "seasonality": 0.016,
            },
        },
    },
]
def build_seed_payload() -> list[dict[str, Any]]:
    """Expande usuarios con su histórico mensual precalculado."""
    payload: list[dict[str, Any]] = []

    for user in SEED_USERS:
        portfolio = dict(user["portfolio"])
        history_config = portfolio.pop("history")
        portfolio["history_records"] = generate_fictional_history(**history_config)
        payload.append(
            {
                "name": user["name"],
                "email": user["email"],
                "portfolio": portfolio,
            }
        )

    return payload
