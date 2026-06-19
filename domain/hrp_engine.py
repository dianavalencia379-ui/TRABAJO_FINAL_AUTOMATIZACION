"""Motor HRP para obtener pesos recomendados del advisor."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd

try:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
except ImportError:  # pragma: no cover - depende del entorno
    leaves_list = None
    linkage = None
    squareform = None

from data_layer.db import get_connection, get_portfolio_positions
from data_layer.yahoo_client import fetch_price_history


def _round_amount(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _normalize_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        raise ValueError("La serie de precios está vacía.")

    frame = prices.copy()
    frame.columns = [str(column).strip().upper() for column in frame.columns]
    frame = frame.sort_index().ffill().dropna(how="all")
    frame = frame.dropna(axis=1, how="all")
    if len(frame.columns) < 2:
        raise ValueError("HRP requiere al menos dos activos con precios válidos.")
    return frame


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_price_frame(prices)
    returns = frame.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="all")
    returns = returns.dropna(axis=1, how="all")
    zero_variance = [column for column in returns.columns if np.isclose(returns[column].std(ddof=0), 0.0)]
    if zero_variance:
        returns = returns.drop(columns=zero_variance)
    if len(returns.columns) < 2 or returns.empty:
        raise ValueError("No hay suficientes rentabilidades útiles para ejecutar HRP.")
    return returns.dropna(how="any")


def correlation_to_distance(correlation: pd.DataFrame) -> pd.DataFrame:
    clipped = correlation.clip(lower=-1.0, upper=1.0)
    distance_values = np.sqrt((1.0 - clipped) / 2.0)
    return pd.DataFrame(distance_values, index=correlation.index, columns=correlation.columns)


def _inverse_variance_weights(covariance: pd.DataFrame) -> pd.Series:
    diagonal = np.diag(covariance.values)
    clipped = np.clip(diagonal, 1e-12, None)
    inverse = 1.0 / clipped
    weights = inverse / inverse.sum()
    return pd.Series(weights, index=covariance.index)


def _cluster_variance(covariance: pd.DataFrame, cluster_items: list[str]) -> float:
    cluster_cov = covariance.loc[cluster_items, cluster_items]
    cluster_weights = _inverse_variance_weights(cluster_cov)
    variance = float(cluster_weights.T @ cluster_cov.values @ cluster_weights)
    return max(variance, 1e-12)


def _fallback_cluster_order(distance: pd.DataFrame) -> list[str]:
    clusters: list[list[str]] = [[label] for label in distance.index]

    def average_distance(left: list[str], right: list[str]) -> float:
        values = distance.loc[left, right].to_numpy(dtype=float)
        return float(values.mean())

    while len(clusters) > 1:
        best_pair: tuple[int, int] | None = None
        best_distance = float("inf")
        for left_index in range(len(clusters) - 1):
            for right_index in range(left_index + 1, len(clusters)):
                candidate = average_distance(clusters[left_index], clusters[right_index])
                if candidate < best_distance:
                    best_distance = candidate
                    best_pair = (left_index, right_index)

        assert best_pair is not None
        left_index, right_index = best_pair
        merged = clusters[left_index] + clusters[right_index]
        clusters = [
            cluster
            for index, cluster in enumerate(clusters)
            if index not in {left_index, right_index}
        ]
        clusters.append(merged)

    return clusters[0]


def build_cluster_order(distance: pd.DataFrame) -> tuple[list[str], str]:
    if linkage is None or leaves_list is None or squareform is None:
        return _fallback_cluster_order(distance), "average-fallback"

    condensed = squareform(distance.values, checks=False)
    linkage_matrix = linkage(condensed, method="single")
    ordered_indices = leaves_list(linkage_matrix)
    order = distance.index[ordered_indices].tolist()
    return order, "single"


def recursive_bisection(covariance: pd.DataFrame, sorted_assets: list[str]) -> pd.Series:
    weights = pd.Series(1.0, index=sorted_assets)
    clusters: list[list[str]] = [sorted_assets]

    while clusters:
        cluster = clusters.pop(0)
        if len(cluster) <= 1:
            continue

        split_index = len(cluster) // 2
        left_cluster = cluster[:split_index]
        right_cluster = cluster[split_index:]
        left_variance = _cluster_variance(covariance, left_cluster)
        right_variance = _cluster_variance(covariance, right_cluster)
        alpha = 1.0 - (left_variance / (left_variance + right_variance))

        weights[left_cluster] *= alpha
        weights[right_cluster] *= 1.0 - alpha
        clusters.extend([left_cluster, right_cluster])

    return weights / weights.sum()


def calculate_hrp_weights(prices: pd.DataFrame) -> dict[str, Any]:
    normalized_prices = _normalize_price_frame(prices)
    returns = calculate_returns(normalized_prices)
    covariance = returns.cov()
    correlation = returns.corr().fillna(0.0)
    distance = correlation_to_distance(correlation)
    cluster_order, clustering_method = build_cluster_order(distance)
    recommended_weights = recursive_bisection(covariance, cluster_order).sort_values(ascending=False)

    return {
        "recommended_weights": {
            ticker: _round_amount(weight)
            for ticker, weight in recommended_weights.to_dict().items()
        },
        "cluster_order": cluster_order,
        "clustering_method": clustering_method,
        "returns": returns,
        "covariance": covariance,
        "correlation": correlation,
        "distance": distance,
    }


def _build_current_weights(rows: list[sqlite3.Row]) -> tuple[dict[str, dict[str, Any]], float]:
    positions: dict[str, dict[str, Any]] = {}
    total_value = 0.0

    for row in rows:
        ticker = str(row["ticker"]).upper()
        quantity = float(row["quantity"])
        avg_price = float(row["avg_price"])
        current_value = quantity * avg_price
        position = positions.setdefault(
            ticker,
            {
                "ticker": ticker,
                "asset_name": row["asset_name"],
                "quantity": 0.0,
                "avg_price": 0.0,
                "current_value": 0.0,
            },
        )
        position["quantity"] += quantity
        position["current_value"] += current_value
        total_value += current_value

    for position in positions.values():
        if position["quantity"] > 0:
            position["avg_price"] = _round_amount(position["current_value"] / position["quantity"], 2)
        position["quantity"] = _round_amount(position["quantity"], 4)
        position["current_value"] = _round_amount(position["current_value"], 2)
        position["current_weight"] = _round_amount(position["current_value"] / total_value)

    return positions, total_value


def build_hrp_portfolio_snapshot(
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
    lookback_days: int = 252,
    interval: str = "1d",
    prefer_live_data: bool = True,
) -> dict[str, Any]:
    """Construye un snapshot HRP listo para advisor y rebalanceo."""

    owns_connection = connection is None
    active_connection = connection or get_connection(database_path)

    try:
        rows = get_portfolio_positions(
            active_connection,
            portfolio_id=portfolio_id,
            user_email=user_email,
        )
        if not rows:
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "filters": {"portfolio_id": portfolio_id, "user_email": user_email},
                "tickers": [],
                "weights_table": [],
                "current_weights": {},
                "recommended_weights": {},
                "diagnostics": {"price_source": "unavailable", "warnings": ["No hay posiciones para calcular HRP."]},
            }

        current_positions, total_current_value = _build_current_weights(rows)
        tickers = list(current_positions.keys())

        history = fetch_price_history(
            tickers,
            lookback_days=lookback_days,
            interval=interval,
            prefer_live_data=prefer_live_data,
        )
        hrp_result = calculate_hrp_weights(history.prices)

        weights_table: list[dict[str, Any]] = []
        for ticker in tickers:
            position = current_positions[ticker]
            recommended_weight = float(hrp_result["recommended_weights"].get(ticker, 0.0))
            current_weight = float(position["current_weight"])
            weights_table.append(
                {
                    **position,
                    "current_weight": _round_amount(current_weight),
                    "recommended_weight": _round_amount(recommended_weight),
                    "difference": _round_amount(recommended_weight - current_weight),
                }
            )

        weights_table.sort(key=lambda item: item["recommended_weight"], reverse=True)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "filters": {"portfolio_id": portfolio_id, "user_email": user_email},
            "tickers": tickers,
            "weights_table": weights_table,
            "current_weights": {
                ticker: _round_amount(data["current_weight"])
                for ticker, data in current_positions.items()
            },
            "recommended_weights": hrp_result["recommended_weights"],
            "diagnostics": {
                "price_source": history.source,
                "used_fallback": history.source != "yahoo",
                "warnings": history.warnings,
                "history_rows": int(len(history.prices.index)),
                "history_start": str(history.prices.index.min().date()),
                "history_end": str(history.prices.index.max().date()),
                "returns_rows": int(len(hrp_result["returns"].index)),
                "clustering_method": hrp_result["clustering_method"],
                "cluster_order": hrp_result["cluster_order"],
                "portfolio_current_value": _round_amount(total_current_value, 2),
                "weights_sum": {
                    "current": _round_amount(sum(item["current_weight"] for item in current_positions.values())),
                    "recommended": _round_amount(sum(hrp_result["recommended_weights"].values())),
                },
                "metadata": history.metadata,
            },
            "matrices": {
                "correlation": hrp_result["correlation"].round(6).to_dict(),
                "distance": hrp_result["distance"].round(6).to_dict(),
                "covariance": hrp_result["covariance"].round(8).to_dict(),
            },
        }
    finally:
        if owns_connection:
            active_connection.close()
