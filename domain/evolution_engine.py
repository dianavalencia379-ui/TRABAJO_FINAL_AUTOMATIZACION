"""Motor reusable para evolución histórica y métricas de rentabilidad."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping


def _round_amount(value: float) -> float:
    return round(float(value), 2)


def _round_pct(value: float) -> float:
    return round(float(value) * 100, 4)


def _parse_date(raw_value: Any) -> date:
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise TypeError(f"Fecha no soportada: {type(raw_value)!r}")
    return date.fromisoformat(raw_value)


def _normalize_history_records(
    history_records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in history_records:
        record_date = _parse_date(record["date"])
        total_value = float(record["total_value"])
        normalized.append(
            {
                "date": record_date,
                "total_value": total_value,
            }
        )
    normalized.sort(key=lambda item: item["date"])
    return normalized


def _empty_metrics() -> dict[str, Any]:
    return {
        "start_date": None,
        "end_date": None,
        "start_value": 0.0,
        "end_value": 0.0,
        "points": 0,
        "elapsed_days": 0,
        "cumulative_return_pct": 0.0,
        "annualized_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "latest_drawdown_pct": 0.0,
        "best_period_return_pct": 0.0,
        "worst_period_return_pct": 0.0,
    }


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def generate_fictional_history(
    start_value: float,
    monthly_return: float,
    seasonality: float,
    start_date: date = date(2023, 1, 31),
    periods: int = 36,
    shock_periods: tuple[int, ...] = (8, 19, 31),
    shock_return: float = -0.018,
) -> list[dict[str, float | str]]:
    """Genera una serie mensual determinista con pequeñas variaciones y caídas."""

    history: list[dict[str, float | str]] = []
    current_value = float(start_value)
    current_year = start_date.year
    current_month = start_date.month

    for period in range(periods):
        month_index = (period % 12) - 6
        seasonal_adjustment = month_index * seasonality / 12
        shock = shock_return if period in shock_periods else 0.0
        current_value *= 1 + monthly_return + seasonal_adjustment + shock

        record_date = _month_end(current_year, current_month)
        history.append(
            {
                "date": record_date.isoformat(),
                "total_value": _round_amount(current_value),
            }
        )

        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return history


def build_evolution_snapshot(
    history_records: Iterable[Mapping[str, Any]],
    *,
    label: str | None = None,
) -> dict[str, Any]:
    """Construye serie histórica enriquecida y métricas principales."""

    normalized = _normalize_history_records(history_records)
    if not normalized:
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "label": label,
            "series": [],
            "metrics": _empty_metrics(),
        }

    first_point = normalized[0]
    start_date = first_point["date"]
    start_value = float(first_point["total_value"])
    running_peak = start_value
    previous_value: float | None = None
    period_returns: list[float] = []
    max_drawdown = 0.0
    series: list[dict[str, Any]] = []

    for point in normalized:
        record_date = point["date"]
        total_value = float(point["total_value"])
        previous_peak = running_peak

        if total_value > running_peak:
            running_peak = total_value

        period_return = 0.0
        if previous_value and previous_value > 0:
            period_return = (total_value / previous_value) - 1
            period_returns.append(period_return)

        cumulative_return = 0.0
        if start_value > 0:
            cumulative_return = (total_value / start_value) - 1

        drawdown = 0.0
        if running_peak > 0:
            drawdown = (total_value / running_peak) - 1
        max_drawdown = min(max_drawdown, drawdown)

        series.append(
            {
                "date": record_date.isoformat(),
                "total_value": _round_amount(total_value),
                "period_return_pct": _round_pct(period_return),
                "cumulative_return_pct": _round_pct(cumulative_return),
                "drawdown_pct": _round_pct(drawdown),
                "is_new_peak": total_value >= previous_peak,
            }
        )
        previous_value = total_value

    end_point = normalized[-1]
    end_date = end_point["date"]
    end_value = float(end_point["total_value"])
    elapsed_days = max((end_date - start_date).days, 0)

    cumulative_return = 0.0
    annualized_return = 0.0
    if start_value > 0:
        cumulative_return = (end_value / start_value) - 1
        if elapsed_days > 0 and end_value > 0:
            years = elapsed_days / 365.25
            if years > 0:
                annualized_return = (end_value / start_value) ** (1 / years) - 1

    metrics = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "start_value": _round_amount(start_value),
        "end_value": _round_amount(end_value),
        "points": len(series),
        "elapsed_days": elapsed_days,
        "cumulative_return_pct": _round_pct(cumulative_return),
        "annualized_return_pct": _round_pct(annualized_return),
        "max_drawdown_pct": _round_pct(max_drawdown),
        "latest_drawdown_pct": series[-1]["drawdown_pct"],
        "best_period_return_pct": _round_pct(max(period_returns, default=0.0)),
        "worst_period_return_pct": _round_pct(min(period_returns, default=0.0)),
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "label": label,
        "series": series,
        "metrics": metrics,
    }


def build_evolution_snapshot_from_db(
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
    connection: sqlite3.Connection | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    """Adaptador opcional para leer ``portfolio_history`` desde SQLite."""

    from data_layer.db import get_connection, get_portfolio_history_series

    owns_connection = connection is None
    active_connection = connection or get_connection(database_path)

    try:
        history_records = get_portfolio_history_series(
            active_connection,
            portfolio_id=portfolio_id,
            user_email=user_email,
        )
        label = (
            f"portfolio:{portfolio_id}"
            if portfolio_id is not None
            else f"user:{user_email}"
            if user_email is not None
            else "all-portfolios"
        )
        snapshot = build_evolution_snapshot(history_records, label=label)
        snapshot["filters"] = {
            "portfolio_id": portfolio_id,
            "user_email": user_email,
        }
        return snapshot
    finally:
        if owns_connection:
            active_connection.close()
