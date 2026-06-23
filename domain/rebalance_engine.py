# ============================================================
# domain/rebalance_engine.py — Advisor de rebalanceo
# Compara pesos actuales del portfolio contra los pesos
# recomendados por HRP y genera recomendaciones de acción.
# ============================================================

"""Advisor de rebalanceo para comparar pesos actuales vs. HRP."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any

from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot


# Umbral por defecto: diferencia del 3% para activar rebalanceo
DEFAULT_REBALANCE_THRESHOLD = 0.03


# ------------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------------

def _round_amount(value: float, digits: int = 6) -> float:
    """Redondea valores del advisor con la precisión indicada."""
    return round(float(value), digits)


def _normalize_threshold(threshold: float) -> float:
    """
    Normaliza el umbral aceptando valores fraccionales o porcentuales.
    Valores > 1 se interpretan como porcentaje y se dividen entre 100.
    Lanza ValueError si el umbral es negativo.
    """
    normalized = float(threshold)
    if normalized < 0:
        raise ValueError("El umbral de rebalanceo no puede ser negativo.")
    if normalized > 1:
        normalized /= 100.0  # Convertir porcentaje a fracción decimal
    return normalized


def classify_rebalance_action(
    *, difference: float,
    threshold: float = DEFAULT_REBALANCE_THRESHOLD
) -> str:
    """
    Clasifica la acción de rebalanceo según la desviación del peso objetivo.

    Retorna:
      'increase' — el peso actual está por debajo del objetivo
      'reduce'   — el peso actual está por encima del objetivo
      'hold'     — la diferencia está dentro del umbral aceptable
    """
    normalized_threshold = _normalize_threshold(threshold)
    if difference > normalized_threshold:
        return "increase"
    if difference < -normalized_threshold:
        return "reduce"
    return "hold"


def _empty_advisor_snapshot(
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
    threshold: float = DEFAULT_REBALANCE_THRESHOLD,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """
    Devuelve la salida vacía estándar del advisor de rebalanceo.
    Se usa cuando no hay datos suficientes para generar recomendaciones.
    """
    normalized_threshold = _normalize_threshold(threshold)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {"portfolio_id": portfolio_id, "user_email": user_email},
        "rebalance_threshold": normalized_threshold,
        "rebalance_threshold_pct": _round_amount(normalized_threshold * 100, 2),
        "advisor_table": [],
        # Columnas disponibles en la tabla del advisor
        "table_columns": [
            "ticker",
            "asset_name",
            "current_quantity",
            "avg_price",
            "current_value",
            "target_value",
            "value_delta",
            "current_weight_pct",
            "target_weight_pct",
            "difference_pct",
            "action_label",
        ],
        "summary": {
            "asset_count": 0,
            "increase_count": 0,
            "reduce_count": 0,
            "hold_count": 0,
            "total_current_value": 0.0,
            "total_target_value": 0.0,
            "net_value_delta": 0.0,
            "weights_sum_pct": {"current": 0.0, "target": 0.0},
        },
        "diagnostics": {
            "warnings": warnings or [],
            "source": {"portfolio_engine": "n/a", "hrp_engine": "n/a"},
        },
    }


# ------------------------------------------------------------
# Función principal del advisor de rebalanceo
# ------------------------------------------------------------

def build_rebalance_advisor_snapshot(
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
    rebalance_threshold: float = DEFAULT_REBALANCE_THRESHOLD,
    lookback_days: int = 252,
    interval: str = "1d",
    prefer_live_data: bool = True,
    portfolio_snapshot: dict[str, Any] | None = None,
    hrp_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye una salida interpretable para advisor, UI y PDF.

    Pasos:
      1. Obtener snapshots de portfolio y HRP (o usar los provistos)
      2. Cruzar activos de ambas fuentes
      3. Calcular diferencias entre pesos actuales y objetivos
      4. Clasificar acciones: aumentar, reducir o mantener
      5. Retornar tabla del advisor con resumen y diagnósticos
    """
    normalized_threshold = _normalize_threshold(rebalance_threshold)

    # Paso 1: Obtener snapshot del portfolio actual
    portfolio_data = portfolio_snapshot or build_portfolio_snapshot(
        portfolio_id=portfolio_id,
        user_email=user_email,
        connection=connection,
        database_path=database_path,
    )

    # Obtener snapshot HRP con pesos recomendados
    hrp_data = hrp_snapshot or build_hrp_portfolio_snapshot(
        portfolio_id=portfolio_id,
        user_email=user_email,
        connection=connection,
        database_path=database_path,
        lookback_days=lookback_days,
        interval=interval,
        prefer_live_data=prefer_live_data,
    )

    # Paso 2: Indexar filas por ticker para cruce eficiente
    asset_rows = {
        str(item["ticker"]).upper(): item
        for item in portfolio_data.get("composition", {}).get("by_asset", [])
    }
    hrp_rows = {
        str(item["ticker"]).upper(): item
        for item in hrp_data.get("weights_table", [])
    }

    # Unión de tickers de ambas fuentes
    tickers = sorted(set(asset_rows) | set(hrp_rows))

    # Recoger advertencias del motor HRP
    warnings = list(hrp_data.get("diagnostics", {}).get("warnings", []))

    # Retornar snapshot vacío si no hay tickers
    if not tickers:
        if not warnings:
            warnings.append("No hay datos suficientes para generar el advisor de rebalanceo.")
        return _empty_advisor_snapshot(
            portfolio_id=portfolio_id,
            user_email=user_email,
            threshold=normalized_threshold,
            warnings=warnings,
        )

    # Valor total actual del portfolio
    total_current_value = float(
        portfolio_data.get("portfolio_summary", {}).get("total_current_value")
        or hrp_data.get("diagnostics", {}).get("portfolio_current_value")
        or 0.0
    )

    # Paso 3 y 4: Construir tabla del advisor con diferencias y acciones
    advisor_table: list[dict[str, Any]] = []
    for ticker in tickers:
        asset_row = asset_rows.get(ticker, {})
        hrp_row = hrp_rows.get(ticker, {})

        # Peso y valor actual del activo
        current_value = float(asset_row.get("value", hrp_row.get("current_value", 0.0)))
        current_weight = float(
            asset_row.get("weight_pct", hrp_row.get("current_weight", 0.0) * 100.0)
        ) / 100.0

        # Peso objetivo recomendado por HRP
        target_weight = float(
            hrp_row.get(
                "recommended_weight",
                hrp_data.get("recommended_weights", {}).get(ticker, 0.0),
            )
        )

        # Calcular diferencia, valor objetivo y delta de valor
        difference = target_weight - current_weight
        target_value = total_current_value * target_weight
        value_delta = target_value - current_value  # Cuánto hay que comprar/vender

        # Clasificar acción de rebalanceo
        action = classify_rebalance_action(
            difference=difference,
            threshold=normalized_threshold
        )

        advisor_table.append(
            {
                "ticker": ticker,
                "asset_name": asset_row.get("asset_name") or hrp_row.get("asset_name") or ticker,
                "current_quantity": _round_amount(hrp_row.get("quantity", 0.0), 4),
                "avg_price": _round_amount(hrp_row.get("avg_price", 0.0), 2),
                "current_value": _round_amount(current_value, 2),
                "target_value": _round_amount(target_value, 2),
                "value_delta": _round_amount(value_delta, 2),         # Diferencia en dinero
                "current_weight": _round_amount(current_weight),
                "target_weight": _round_amount(target_weight),
                "difference": _round_amount(difference),
                "current_weight_pct": _round_amount(current_weight * 100, 2),
                "target_weight_pct": _round_amount(target_weight * 100, 2),
                "difference_pct": _round_amount(difference * 100, 2),
                "abs_difference_pct": _round_amount(abs(difference) * 100, 2),  # Para ordenar
                "action": action,
                # Etiqueta legible de la acción en español
                "action_label": {
                    "increase": "Aumentar",
                    "reduce": "Reducir",
                    "hold": "Mantener",
                }[action],
                "threshold_pct": _round_amount(normalized_threshold * 100, 2),
            }
        )

    # Ordenar por mayor desviación absoluta primero
    advisor_table.sort(
        key=lambda item: (item["abs_difference_pct"], item["ticker"]),
        reverse=True,
    )

    # Paso 5: Calcular totales del resumen
    current_weights_sum = sum(item["current_weight"] for item in advisor_table)
    target_weights_sum = sum(item["target_weight"] for item in advisor_table)
    total_target_value = sum(item["target_value"] for item in advisor_table)
    net_value_delta = sum(item["value_delta"] for item in advisor_table)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {"portfolio_id": portfolio_id, "user_email": user_email},
        "rebalance_threshold": normalized_threshold,
        "rebalance_threshold_pct": _round_amount(normalized_threshold * 100, 2),
        "advisor_table": advisor_table,
        "table_columns": [
            "ticker",
            "asset_name",
            "current_quantity",
            "avg_price",
            "current_value",
            "target_value",
            "value_delta",
            "current_weight_pct",
            "target_weight_pct",
            "difference_pct",
            "action_label",
        ],
        # Resumen con conteos por acción y totales financieros
        "summary": {
            "asset_count": len(advisor_table),
            "increase_count": sum(1 for item in advisor_table if item["action"] == "increase"),
            "reduce_count": sum(1 for item in advisor_table if item["action"] == "reduce"),
            "hold_count": sum(1 for item in advisor_table if item["action"] == "hold"),
            "total_current_value": _round_amount(total_current_value, 2),
            "total_target_value": _round_amount(total_target_value, 2),
            "net_value_delta": _round_amount(net_value_delta, 2),
            "weights_sum_pct": {
                "current": _round_amount(current_weights_sum * 100, 2),
                "target": _round_amount(target_weights_sum * 100, 2),
            },
        },
        "diagnostics": {
            "warnings": warnings,
            # Timestamps de los snapshots usados como fuente
            "source": {
                "portfolio_engine": portfolio_data.get("generated_at", "unknown"),
                "hrp_engine": hrp_data.get("generated_at", "unknown"),
            },
            "hrp": hrp_data.get("diagnostics", {}),
        },
    }
