# ============================================================
# data_layer/seed_data.py — Datos ficticios iniciales
# Define los usuarios y portfolios de ejemplo para poblar
# la base de datos SQLite del Dashboard Financiero.
# ============================================================

"""Datos ficticios iniciales para la base SQLite del dashboard."""

from __future__ import annotations

from typing import Any

# Motor que genera el historial de valores ficticios
from domain.evolution_engine import generate_fictional_history


# ------------------------------------------------------------
# Datos de usuarios de prueba con sus portfolios y posiciones
# ------------------------------------------------------------

SEED_USERS: list[dict[str, Any]] = [
    {
        # Usuario 1: Diana Valencia — Portfolio de crecimiento en USA
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
            # Parámetros para generar el historial ficticio de valores
            "history": {
                "start_value": 52000.0,      # Valor inicial del portfolio
                "monthly_return": 0.0125,    # Retorno mensual estimado
                "seasonality": 0.020,        # Factor de estacionalidad
            },
        },
    },
    {
        # Usuario 2: Antonio Ruiz — Portfolio defensivo global
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
                "start_value": 43000.0,      # Valor inicial del portfolio
                "monthly_return": 0.0078,    # Retorno mensual conservador
                "seasonality": 0.012,        # Baja estacionalidad (portfolio defensivo)
            },
        },
    },
    {
        # Usuario 3: José Martínez — Portfolio tecnológico balanceado
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
                "start_value": 47000.0,      # Valor inicial del portfolio
                "monthly_return": 0.0101,    # Retorno mensual moderado
                "seasonality": 0.016,        # Estacionalidad media
            },
        },
    },
]


# ------------------------------------------------------------
# Constructor del payload de seed
# ------------------------------------------------------------

def build_seed_payload() -> list[dict[str, Any]]:
    """
    Expande usuarios con su histórico mensual precalculado.

    El histórico generado por generate_fictional_history() se reescala
    proporcionalmente para que su ÚLTIMO punto coincida exactamente con el
    valor real de las posiciones (cantidad x precio medio). Antes,
    'start_value' era un número elegido a mano sin relación con las
    posiciones reales del usuario, lo que producía una desviación de
    decenas de miles de dólares entre el histórico y el valor actual del
    portfolio (ej. Diana: el histórico terminaba en $74,778 mientras sus
    posiciones reales sumaban $31,337). El reescalado conserva la forma
    relativa de la serie (estacionalidad, caídas programadas) y solo
    ajusta la magnitud para que el dashboard sea internamente consistente.
    """
    payload: list[dict[str, Any]] = []

    for user in SEED_USERS:
        portfolio = dict(user["portfolio"])

        # Extraer configuración del historial (no se guarda en DB directamente)
        history_config = portfolio.pop("history")
        positions = portfolio["positions"]

        # Calcular el costo base real sumando cantidad × precio promedio
        real_cost_basis = sum(
            position["quantity"] * position["avg_price"]
            for position in positions
        )

        # Generar el historial ficticio con los parámetros configurados
        history_records = generate_fictional_history(**history_config)

        # Calcular factor de escala para alinear el historial con el valor real
        generated_end_value = history_records[-1]["total_value"]
        scale_factor = (real_cost_basis / generated_end_value) if generated_end_value else 1.0

        # Reescalar todos los registros del historial proporcionalmente
        for record in history_records:
            record["total_value"] = round(record["total_value"] * scale_factor, 2)

        # Agregar el historial reescalado al portfolio
        portfolio["history_records"] = history_records

        payload.append(
            {
                "name": user["name"],
                "email": user["email"],
                "portfolio": portfolio,
            }
        )

    return payload
