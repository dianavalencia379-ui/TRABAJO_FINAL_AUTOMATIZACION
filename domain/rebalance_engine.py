"""Advisor de rebalanceo para comparar pesos actuales vs. HRP."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any

from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot


DEFAULT_REBALANCE_THRESHOLD = 0.03


def _round_amount(value: float, digits: int = 6) -> float:
    """Redondea valores del advisor con la precisión indicada."""
    return round(float(value), digits)


def _normalize_threshold(threshold: float) -> float:
    """Normaliza el umbral aceptando valores fraccionales o porcentuales."""
    normalized = float(threshold)
    if normalized < 0:
        raise ValueError("El umbral de rebalanceo no puede ser negativo.")
    if normalized > 1:
        normalized /= 100.0
    return normalized


def classify_rebalance_action(*, difference: float, threshold: float = DEFAULT_REBALANCE_THRESHOLD) -> str:
    """Clasifica la acción de rebalanceo según la desviación del peso objetivo."""
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
    """Devuelve la salida vacía estándar del advisor de rebalanceo."""
    normalized_threshold = _normalize_threshold(threshold)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {"portfolio_id": portfolio_id, "user_email": user_email},
        "rebalance_threshold": normalized_threshold,
        "rebalance_threshold_pct": _round_amount(normalized_threshold * 100, 2),
        "advisor_table": [],
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
    """Construye una salida interpretable para advisor, UI y PDF."""

    normalized_threshold = _normalize_threshold(rebalance_threshold)
    portfolio_data = portfolio_snapshot or build_portfolio_snapshot(
        portfolio_id=portfolio_id,
        user_email=user_email,
        connection=connection,
        database_path=database_path,
    )
    hrp_data = hrp_snapshot or build_hrp_portfolio_snapshot(
        portfolio_id=portfolio_id,
        user_email=user_email,
        connection=connection,
        database_path=database_path,
        lookback_days=lookback_days,
        interval=interval,
        prefer_live_data=prefer_live_data,
    )

    asset_rows = {
        str(item["ticker"]).upper(): item for item in portfolio_data.get("composition", {}).get("by_asset", [])
    }
    hrp_rows = {str(item["ticker"]).upper(): item for item in hrp_data.get("weights_table", [])}
    tickers = sorted(set(asset_rows) | set(hrp_rows))

    warnings = list(hrp_data.get("diagnostics", {}).get("warnings", []))
    if not tickers:
        if not warnings:
            warnings.append("No hay datos suficientes para generar el advisor de rebalanceo.")
        return _empty_advisor_snapshot(
            portfolio_id=portfolio_id,
            user_email=user_email,
            threshold=normalized_threshold,
            warnings=warnings,
        )

    total_current_value = float(
        portfolio_data.get("portfolio_summary", {}).get("total_current_value")
        or hrp_data.get("diagnostics", {}).get("portfolio_current_value")
        or 0.0
    )

    advisor_table: list[dict[str, Any]] = []
    for ticker in tickers:
        asset_row = asset_rows.get(ticker, {})
        hrp_row = hrp_rows.get(ticker, {})

        current_value = float(asset_row.get("value", hrp_row.get("current_value", 0.0)))
        current_weight = float(asset_row.get("weight_pct", hrp_row.get("current_weight", 0.0) * 100.0)) / 100.0
        target_weight = float(
            hrp_row.get(
                "recommended_weight",
                hrp_data.get("recommended_weights", {}).get(ticker, 0.0),
            )
        )
        difference = target_weight - current_weight
        target_value = total_current_value * target_weight
        value_delta = target_value - current_value
        action = classify_rebalance_action(difference=difference, threshold=normalized_threshold)

        advisor_table.append(
            {
                "ticker": ticker,
                "asset_name": asset_row.get("asset_name") or hrp_row.get("asset_name") or ticker,
                "current_quantity": _round_amount(hrp_row.get("quantity", 0.0), 4),
                "avg_price": _round_amount(hrp_row.get("avg_price", 0.0), 2),
                "current_value": _round_amount(current_value, 2),
                "target_value": _round_amount(target_value, 2),
                "value_delta": _round_amount(value_delta, 2),
                "current_weight": _round_amount(current_weight),
                "target_weight": _round_amount(target_weight),
                "difference": _round_amount(difference),
                "current_weight_pct": _round_amount(current_weight * 100, 2),
                "target_weight_pct": _round_amount(target_weight * 100, 2),
                "difference_pct": _round_amount(difference * 100, 2),
                "abs_difference_pct": _round_amount(abs(difference) * 100, 2),
                "action": action,
                "action_label": {
                    "increase": "Aumentar",
                    "reduce": "Reducir",
                    "hold": "Mantener",
                }[action],
                "threshold_pct": _round_amount(normalized_threshold * 100, 2),
            }
        )

    advisor_table.sort(key=lambda item: (item["abs_difference_pct"], item["ticker"]), reverse=True)

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
            "source": {
                "portfolio_engine": portfolio_data.get("generated_at", "unknown"),
                "hrp_engine": hrp_data.get("generated_at", "unknown"),
            },
            "hrp": hrp_data.get("diagnostics", {}),
        },
    }
