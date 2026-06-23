# ============================================================
# tests/test_api_report_endpoint.py — Tests del endpoint API
# Verifica el comportamiento del endpoint POST /api/report/{id}
# para generación de informes PDF del Dashboard Financiero.
# ============================================================

from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

# Importación opcional de TestClient (requiere httpx instalado)
try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError) as exc:  # pragma: no cover
    TestClient = None
    TESTCLIENT_IMPORT_ERROR = str(exc)
else:
    TESTCLIENT_IMPORT_ERROR = None

import api
from reports.pdf_generator import GeneratedPdfReport


# Saltar todos los tests si TestClient no está disponible en el entorno
pytestmark = pytest.mark.skipif(
    TestClient is None,
    reason=TESTCLIENT_IMPORT_ERROR or "fastapi.testclient no está disponible en este entorno.",
)


def _build_test_client():
    """Crea un cliente de prueba tipado cuando FastAPI TestClient está disponible."""
    assert TestClient is not None
    client_class = TestClient
    return client_class(api.app)


def test_generate_report_endpoint_returns_pdf_reference(tmp_path: Path, monkeypatch) -> None:
    """
    Verifica que el endpoint devuelva la referencia completa del PDF generado.
    Usa monkeypatch para simular la generación del PDF sin ReportLab real.
    """
    # Redirigir el directorio de salida a una carpeta temporal del test
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)

    # Simular que la generación PDF está disponible
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))

    # Reemplazar la generación real del PDF con un mock
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

    client = _build_test_client()
    response = client.post("/api/report/1")

    # Verificar respuesta exitosa
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["user"]["email"] == "dvalenciag@student.universidadviu.com"
    assert payload["portfolio"]["portfolio_count"] >= 1
    assert payload["pdf"]["file_name"].endswith(".pdf")
    assert payload["pdf"]["download_url"].startswith("/report-files/")
    assert payload["pdf"]["public_download_url"] is None
    assert payload["pdf"]["size_bytes"] > 0
    assert Path(payload["pdf"]["absolute_path"]).exists()


def test_generate_report_endpoint_exposes_public_pdf_url_without_replacing_download_url(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Expone public_download_url cuando existe base pública y conserva download_url relativo."""
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))
    monkeypatch.setattr(
        api,
        "generate_user_report_pdf",
        lambda **_: GeneratedPdfReport(
            file_name="informe_test.pdf",
            content=b"%PDF-1.4\nmock",
            generated_at="2026-06-23T10:00:00+00:00",
            warnings=[],
            sections=["Datos del usuario"],
        ),
    )
    monkeypatch.setattr(
        api,
        "settings",
        SimpleNamespace(
            app_name=api.settings.app_name,
            base_dir=api.settings.base_dir,
            database_path=api.settings.database_path,
            public_api_base_url="https://api.example.com",
            zapier_webhook_url=api.settings.zapier_webhook_url,
        ),
    )

    client = _build_test_client()
    response = client.post("/api/report/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pdf"]["download_url"] == "/report-files/informe_test.pdf"
    assert payload["pdf"]["public_download_url"] == "https://api.example.com/report-files/informe_test.pdf"


def test_generate_report_endpoint_returns_404_for_unknown_user() -> None:
    """
    Comprueba que el endpoint retorne 404 cuando el usuario no existe.
    Usa un ID inexistente (9999) para provocar el error controlado.
    """
    client = _build_test_client()
    response = client.post("/api/report/9999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "user_not_found"


def test_generate_report_endpoint_handles_missing_reportlab(monkeypatch) -> None:
    """
    Valida el error controlado (503) cuando ReportLab no está disponible.
    Simula que la generación PDF no está disponible en el entorno.
    """
    client = _build_test_client()

    # Simular que ReportLab no está instalado
    monkeypatch.setattr(
        api, "is_pdf_generation_available",
        lambda: (False, "ReportLab no está disponible.")
    )

    response = client.post("/api/report/1")

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "pdf_generation_unavailable"
    assert payload["pdf"]["available"] is False  # PDF no disponible en la respuesta


def test_generate_report_endpoint_generates_real_pdf_when_available(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Comprueba la generación real del PDF cuando el entorno lo permite.
    Reemplaza las llamadas a Yahoo Finance con datos simulados para
    evitar dependencias de red en los tests.
    """
    # Saltar el test si la generación PDF no está disponible
    available, message = api.is_pdf_generation_available()
    if not available:
        pytest.skip(message or "La generación PDF no está disponible en este entorno.")

    # Reemplazar fetch_price_history con datos simulados para evitar llamadas reales
    import data_layer.yahoo_client
    from data_layer.yahoo_client import PriceHistoryResult, generate_simulated_price_history

    def mock_fetch_price_history(tickers, **kwargs):
        """Mock que devuelve precios simulados en lugar de datos reales de Yahoo."""
        prices = generate_simulated_price_history(
            tickers,
            lookback_days=kwargs.get("lookback_days", 252)
        )
        return PriceHistoryResult(
            prices=prices,
            source="simulated",
            warnings=[],
            metadata={"mocked": True},
        )

    monkeypatch.setattr(data_layer.yahoo_client, "fetch_price_history", mock_fetch_price_history)

    # Redirigir el directorio de salida a una carpeta temporal del test
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)

    client = _build_test_client()
    response = client.post("/api/report/1")

    # Verificar generación exitosa con PDF real
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["pdf"]["file_name"].endswith(".pdf")
    assert payload["pdf"]["size_bytes"] > 0
    assert payload["sections"]  # Debe incluir al menos una sección
    assert Path(payload["pdf"]["absolute_path"]).exists()


def test_zapier_debug_report_posts_to_default_webhook_when_missing_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Usa el webhook por defecto en código cuando no existe configuración explícita."""
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))
    monkeypatch.setattr(
        api,
        "generate_user_report_pdf",
        lambda **_: GeneratedPdfReport(
            file_name="informe_test.pdf",
            content=b"%PDF-1.4\nmock",
            generated_at="2026-06-23T10:00:00+00:00",
            warnings=["mock-warning"],
            sections=["Datos del usuario", "Portfolio"],
        ),
    )
    monkeypatch.setattr(
        api,
        "settings",
        SimpleNamespace(
            app_name=api.settings.app_name,
            base_dir=api.settings.base_dir,
            database_path=api.settings.database_path,
            public_api_base_url="https://api.example.com",
            zapier_webhook_url="https://hooks.zapier.com/hooks/catch/27964672/42twvzz/",
        ),
    )

    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok":true}'

        def getcode(self):
            return self.status

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        captured["url"] = req.full_url
        captured["body"] = req.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(api.request, "urlopen", fake_urlopen)

    client = _build_test_client()
    response = client.post("/api/zapier/debug/report?user_id=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["user"]["name"] == "Diana Valencia"
    assert payload["delivery"]["mode"] == "webhook_sent"
    assert payload["delivery"]["webhook_configured"] is True
    assert payload["delivery"]["http_status"] == 200
    assert payload["pdf"]["download_url"] == "/report-files/informe_test.pdf"
    assert payload["pdf"]["public_download_url"] == "https://api.example.com/report-files/informe_test.pdf"
    assert payload["zapier_payload"]["pdf"]["public_download_url"] == payload["pdf"]["public_download_url"]
    assert payload["zapier_payload"]["pdf"]["file_name"] == "informe_test.pdf"
    assert payload["zapier_payload"]["pdf"]["mime_type"] == "application/pdf"
    assert payload["zapier_payload"]["pdf"]["size_bytes"] == len(b"%PDF-1.4\nmock")
    assert payload["zapier_payload"]["pdf"]["encoding"] == "base64"
    assert payload["zapier_payload"]["pdf"]["content_base64"] == base64.b64encode(b"%PDF-1.4\nmock").decode("ascii")
    assert captured["timeout"] == 10
    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/27964672/42twvzz/"
    assert '"requested_user_id": 1' in str(captured["body"])


def test_zapier_debug_report_posts_to_configured_webhook(tmp_path: Path, monkeypatch) -> None:
    """Envía el payload a Zapier cuando existe webhook configurado."""
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))
    monkeypatch.setattr(
        api,
        "generate_user_report_pdf",
        lambda **_: GeneratedPdfReport(
            file_name="informe_test.pdf",
            content=b"%PDF-1.4\nmock",
            generated_at="2026-06-23T10:00:00+00:00",
            warnings=[],
            sections=["Datos del usuario"],
        ),
    )
    monkeypatch.setattr(
        api,
        "settings",
        SimpleNamespace(
            app_name=api.settings.app_name,
            base_dir=api.settings.base_dir,
            database_path=api.settings.database_path,
            public_api_base_url="https://api.example.com",
            zapier_webhook_url="https://hooks.zapier.com/hooks/catch/123/abc",
        ),
    )

    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok":true}'

        def getcode(self):
            return self.status

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        captured["url"] = req.full_url
        captured["body"] = req.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(api.request, "urlopen", fake_urlopen)

    client = _build_test_client()
    response = client.post("/api/zapier/debug/report?user_id=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["delivery"]["mode"] == "webhook_sent"
    assert payload["delivery"]["http_status"] == 200
    assert payload["pdf"]["download_url"] == "/report-files/informe_test.pdf"
    assert payload["pdf"]["public_download_url"] == "https://api.example.com/report-files/informe_test.pdf"
    assert payload["zapier_payload"]["pdf"]["mime_type"] == "application/pdf"
    assert payload["zapier_payload"]["pdf"]["encoding"] == "base64"
    assert payload["zapier_payload"]["pdf"]["public_download_url"] == payload["pdf"]["public_download_url"]
    assert payload["zapier_payload"]["pdf"]["content_base64"] == base64.b64encode(b"%PDF-1.4\nmock").decode("ascii")
    assert captured["timeout"] == 10
    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/123/abc"
    assert '"requested_user_id": 1' in str(captured["body"])


def test_zapier_debug_report_returns_preview_when_webhook_is_explicitly_empty(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Conserva el modo preview si el webhook se vacía explícitamente."""
    monkeypatch.setattr(api, "ensure_generated_reports_directory", lambda: tmp_path)
    monkeypatch.setattr(api, "is_pdf_generation_available", lambda: (True, None))
    monkeypatch.setattr(
        api,
        "generate_user_report_pdf",
        lambda **_: GeneratedPdfReport(
            file_name="informe_test.pdf",
            content=b"%PDF-1.4\nmock",
            generated_at="2026-06-23T10:00:00+00:00",
            warnings=["mock-warning"],
            sections=["Datos del usuario", "Portfolio"],
        ),
    )
    monkeypatch.setattr(
        api,
        "settings",
        SimpleNamespace(
            app_name=api.settings.app_name,
            base_dir=api.settings.base_dir,
            database_path=api.settings.database_path,
            public_api_base_url="https://api.example.com",
            zapier_webhook_url="",
        ),
    )

    client = _build_test_client()
    response = client.post("/api/zapier/debug/report?user_id=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "preview"
    assert payload["delivery"]["mode"] == "preview"
    assert payload["delivery"]["webhook_configured"] is False
    assert payload["pdf"]["download_url"] == "/report-files/informe_test.pdf"
    assert payload["pdf"]["public_download_url"] == "https://api.example.com/report-files/informe_test.pdf"
