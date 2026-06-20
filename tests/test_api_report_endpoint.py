from __future__ import annotations

from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError) as exc:  # pragma: no cover - depende del entorno
    TestClient = None
    TESTCLIENT_IMPORT_ERROR = str(exc)
else:
    TESTCLIENT_IMPORT_ERROR = None

import api
from reports.pdf_generator import GeneratedPdfReport


pytestmark = pytest.mark.skipif(
    TestClient is None,
    reason=TESTCLIENT_IMPORT_ERROR or "fastapi.testclient no está disponible en este entorno.",
)


def test_generate_report_endpoint_returns_pdf_reference(tmp_path: Path, monkeypatch) -> None:
    """Verifica que el endpoint devuelva la referencia del PDF generado."""
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))
    monkeypatch.setattr(
        api,
        "generate_user_report_pdf",
        lambda **_: GeneratedPdfReport(
            file_name="informe_test.pdf",
            content=b"%PDF-1.4\nmock",
            generated_at="2026-06-19T10:00:00+00:00",
            warnings=["mock-warning"],
            sections=["Datos del usuario", "Portfolio"],
        ),
    )

    client = TestClient(api.app)

    response = client.post("/api/report/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["user"]["email"] == "diana@example.com"
    assert payload["portfolio"]["portfolio_count"] >= 1
    assert payload["pdf"]["file_name"].endswith(".pdf")
    assert payload["pdf"]["download_url"].startswith("/report-files/")
    assert payload["pdf"]["size_bytes"] > 0
    assert Path(payload["pdf"]["absolute_path"]).exists()


def test_generate_report_endpoint_returns_404_for_unknown_user() -> None:
    """Comprueba la respuesta 404 cuando el usuario solicitado no existe."""
    client = TestClient(api.app)

    response = client.post("/api/report/9999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "user_not_found"


def test_generate_report_endpoint_handles_missing_reportlab(monkeypatch) -> None:
    """Valida el error controlado cuando ReportLab no está disponible."""
    client = TestClient(api.app)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (False, "ReportLab no está disponible."))

    response = client.post("/api/report/1")

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "pdf_generation_unavailable"
    assert payload["pdf"]["available"] is False


def test_generate_report_endpoint_generates_real_pdf_when_available(tmp_path: Path, monkeypatch) -> None:
    """Comprueba la generación real del PDF cuando el entorno lo permite."""
    available, message = api.is_pdf_generation_available()
    if not available:
        pytest.skip(message or "La generación PDF no está disponible en este entorno.")

    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    client = TestClient(api.app)

    response = client.post("/api/report/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["pdf"]["file_name"].endswith(".pdf")
    assert payload["pdf"]["size_bytes"] > 0
    assert payload["sections"]
    assert Path(payload["pdf"]["absolute_path"]).exists()
