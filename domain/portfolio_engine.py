"""Motor de portfolio para enriquecer posiciones y preparar salidas de UI."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, UTC
from pathlib import Path
import sqlite3
from typing import Any

from data_layer.db import get_connection, get_portfolio_positions


def _round_amount(value: float) -> float:
    return round(float(value), 2)


def _safe_weight(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100, 4)


def _empty_snapshot(*, portfolio_id: int | None = None, user_email: str | None = None) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {
            "portfolio_id": portfolio_id,
            "user_email": user_email,
        },
        "positions_table": [],
        "portfolio_summary": {
            "portfolio_count": 0,
            "position_count": 0,
            "total_quantity": 0.0,
            "total_cost_basis": 0.0,
            "total_current_value": 0.0,
            "pricing_method": "avg_price",
        },
        "portfolio_breakdown": [],
        "composition": {
            "by_asset": [],
            "by_portfolio": [],
        },
    }


def build_portfolio_snapshot(
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    """Construye un snapshot listo para tablas y gráficos.

    En esta fase, el valor actual base se calcula como ``quantity * avg_price``.
    """

    owns_connection = connection is None
    active_connection = connection or get_connection(database_path)

    try:
        rows = get_portfolio_positions(
            active_connection,
            portfolio_id=portfolio_id,
            user_email=user_email,
        )
        if not rows:
            return _empty_snapshot(portfolio_id=portfolio_id, user_email=user_email)

        positions_table: list[dict[str, Any]] = []
        portfolio_totals: dict[int, dict[str, Any]] = {}
        asset_totals: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "ticker": "",
                "asset_name": "",
                "total_quantity": 0.0,
                "total_current_value": 0.0,
                "portfolio_count": 0,
            }
        )
        seen_asset_portfolios: set[tuple[str, int]] = set()

        total_quantity = 0.0
        total_cost_basis = 0.0
        total_current_value = 0.0

        for row in rows:
            quantity = float(row["quantity"])
            avg_price = float(row["avg_price"])
            current_price = avg_price
            cost_basis = quantity * avg_price
            current_value = quantity * current_price

            position = {
                "position_id": row["position_id"],
                "portfolio_id": row["portfolio_id"],
                "portfolio_name": row["portfolio_name"],
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "user_email": row["user_email"],
                "ticker": row["ticker"],
                "asset_name": row["asset_name"],
                "quantity": quantity,
                "avg_price": _round_amount(avg_price),
                "current_price": _round_amount(current_price),
                "cost_basis": _round_amount(cost_basis),
                "current_value": _round_amount(current_value),
                "pricing_method": "avg_price",
            }
            positions_table.append(position)

            portfolio_data = portfolio_totals.setdefault(
                row["portfolio_id"],
                {
                    "portfolio_id": row["portfolio_id"],
                    "portfolio_name": row["portfolio_name"],
                    "user_id": row["user_id"],
                    "user_name": row["user_name"],
                    "user_email": row["user_email"],
                    "positions_count": 0,
                    "total_quantity": 0.0,
                    "total_cost_basis": 0.0,
                    "total_current_value": 0.0,
                },
            )
            portfolio_data["positions_count"] += 1
            portfolio_data["total_quantity"] += quantity
            portfolio_data["total_cost_basis"] += cost_basis
            portfolio_data["total_current_value"] += current_value

            asset_data = asset_totals[row["ticker"]]
            asset_data["ticker"] = row["ticker"]
            asset_data["asset_name"] = row["asset_name"]
            asset_data["total_quantity"] += quantity
            asset_data["total_current_value"] += current_value
            portfolio_key = (row["ticker"], row["portfolio_id"])
            if portfolio_key not in seen_asset_portfolios:
                asset_data["portfolio_count"] += 1
                seen_asset_portfolios.add(portfolio_key)

            total_quantity += quantity
            total_cost_basis += cost_basis
            total_current_value += current_value

        for position in positions_table:
            position["weight_pct"] = _safe_weight(position["current_value"], total_current_value)

        portfolio_breakdown = []
        for portfolio_data in portfolio_totals.values():
            portfolio_data["total_quantity"] = _round_amount(portfolio_data["total_quantity"])
            portfolio_data["total_cost_basis"] = _round_amount(portfolio_data["total_cost_basis"])
            portfolio_data["total_current_value"] = _round_amount(portfolio_data["total_current_value"])
            portfolio_data["weight_pct"] = _safe_weight(
                portfolio_data["total_current_value"],
                total_current_value,
            )
            portfolio_breakdown.append(portfolio_data)

        portfolio_breakdown.sort(
            key=lambda item: item["total_current_value"],
            reverse=True,
        )

        composition_by_asset = []
        for asset_data in asset_totals.values():
            asset_value = _round_amount(asset_data["total_current_value"])
            composition_by_asset.append(
                {
                    "label": asset_data["ticker"],
                    "ticker": asset_data["ticker"],
                    "asset_name": asset_data["asset_name"],
                    "value": asset_value,
                    "weight_pct": _safe_weight(asset_value, total_current_value),
                    "quantity": _round_amount(asset_data["total_quantity"]),
                    "portfolio_count": asset_data["portfolio_count"],
                }
            )

        composition_by_asset.sort(key=lambda item: item["value"], reverse=True)
        composition_by_portfolio = [
            {
                "label": item["portfolio_name"],
                "portfolio_id": item["portfolio_id"],
                "portfolio_name": item["portfolio_name"],
                "user_name": item["user_name"],
                "user_email": item["user_email"],
                "value": item["total_current_value"],
                "weight_pct": item["weight_pct"],
                "positions_count": item["positions_count"],
            }
            for item in portfolio_breakdown
        ]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "filters": {
                "portfolio_id": portfolio_id,
                "user_email": user_email,
            },
            "positions_table": sorted(
                positions_table,
                key=lambda item: item["current_value"],
                reverse=True,
            ),
            "portfolio_summary": {
                "portfolio_count": len(portfolio_breakdown),
                "position_count": len(positions_table),
                "total_quantity": _round_amount(total_quantity),
                "total_cost_basis": _round_amount(total_cost_basis),
                "total_current_value": _round_amount(total_current_value),
                "pricing_method": "avg_price",
            },
            "portfolio_breakdown": portfolio_breakdown,
            "composition": {
                "by_asset": composition_by_asset,
                "by_portfolio": composition_by_portfolio,
            },
        }
    finally:
        if owns_connection:
            active_connection.close()
