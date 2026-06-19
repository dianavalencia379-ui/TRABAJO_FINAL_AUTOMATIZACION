from __future__ import annotations

import sqlite3

from data_layer.db import create_schema, get_user_portfolios, seed_database
from domain.evolution_engine import build_evolution_snapshot_from_db
from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot
from domain.rebalance_engine import build_rebalance_advisor_snapshot
from reports.pdf_generator import (
    build_report_payload,
    generate_user_report_pdf,
    is_pdf_generation_available,
    persist_generated_report,
)


def _build_seeded_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    seed_database(connection)
    return connection


def _build_dashboard_data(connection: sqlite3.Connection, *, user_email: str) -> dict[str, object]:
    portfolio_snapshot = build_portfolio_snapshot(
        connection=connection,
        user_email=user_email,
    )
    evolution_snapshot = build_evolution_snapshot_from_db(
        connection=connection,
        user_email=user_email,
    )
    hrp_snapshot = build_hrp_portfolio_snapshot(
        connection=connection,
        user_email=user_email,
        prefer_live_data=False,
        lookback_days=120,
    )
    advisor_snapshot = build_rebalance_advisor_snapshot(
        connection=connection,
        user_email=user_email,
        prefer_live_data=False,
        rebalance_threshold=3,
        portfolio_snapshot=portfolio_snapshot,
        hrp_snapshot=hrp_snapshot,
    )
    user_portfolios = [dict(row) for row in get_user_portfolios(connection, user_email=user_email)]
    return {
        "portfolio_snapshot": portfolio_snapshot,
        "evolution_snapshot": evolution_snapshot,
        "hrp_snapshot": hrp_snapshot,
        "advisor_snapshot": advisor_snapshot,
        "user_portfolios": user_portfolios,
    }


def test_build_report_payload_contains_required_sections() -> None:
    connection = _build_seeded_connection()
    selected_user = {
        "user_name": "Diana Valencia",
        "user_email": "diana@example.com",
    }
    dashboard_data = _build_dashboard_data(connection, user_email="diana@example.com")

    payload = build_report_payload(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )

    assert payload["file_name"].endswith(".pdf")
    assert payload["user"]["email"] == "diana@example.com"
    assert payload["summary"]["portfolio_summary"]["total_current_value"] > 0
    assert payload["tables"]["composition_rows"]
    assert payload["tables"]["evolution_rows"]
    assert payload["tables"]["current_weight_rows"]
    assert payload["tables"]["hrp_weight_rows"]
    assert payload["tables"]["rebalance_rows"]
    assert len(payload["tables"]["current_weight_rows"]) == len(dashboard_data["hrp_snapshot"]["weights_table"])
    assert len(payload["tables"]["hrp_weight_rows"]) == len(dashboard_data["hrp_snapshot"]["weights_table"])
    assert "Aviso académico" in payload["sections"]


def test_generate_user_report_pdf_returns_pdf_or_clear_unavailable_message() -> None:
    connection = _build_seeded_connection()
    selected_user = {
        "user_name": "Diana Valencia",
        "user_email": "diana@example.com",
    }
    dashboard_data = _build_dashboard_data(connection, user_email="diana@example.com")

    available, message = is_pdf_generation_available()
    if not available:
        assert message is not None
        assert "ReportLab" in message
        return

    report = generate_user_report_pdf(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )

    assert report.file_name.endswith(".pdf")
    assert report.content.startswith(b"%PDF")
    assert len(report.sections) >= 10


def test_generate_user_report_pdf_can_be_persisted_to_disk(tmp_path) -> None:
    connection = _build_seeded_connection()
    selected_user = {
        "user_name": "Diana Valencia",
        "user_email": "diana@example.com",
    }
    dashboard_data = _build_dashboard_data(connection, user_email="diana@example.com")

    available, message = is_pdf_generation_available()
    if not available:
        assert message is not None
        return

    report = generate_user_report_pdf(
        selected_user=selected_user,
        dashboard_data=dashboard_data,
    )
    stored_path = persist_generated_report(report, output_dir=tmp_path)

    assert stored_path.exists()
    assert stored_path.name == report.file_name
    assert stored_path.read_bytes().startswith(b"%PDF")
