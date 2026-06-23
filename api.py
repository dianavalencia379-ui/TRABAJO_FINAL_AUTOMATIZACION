# ============================================================
# api.py — Punto de entrada de la API REST del proyecto
# Dashboard Financiero. Define los endpoints para generar
# informes PDF y verificar el estado del servicio.
# ============================================================

from __future__ import annotations

import base64
from datetime import UTC, datetime
import json
import logging
import threading
from typing import Any
from urllib import error, request

# Framework principal para construir la API REST
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Librería para validación y modelado de datos
from pydantic import BaseModel, Field

# Configuración global del proyecto
from config import settings

# Funciones de acceso a la base de datos
from data_layer.db import (
    ensure_generated_reports_directory,
    get_connection,
    get_user_by_id,
    get_users,
    get_user_portfolios,
    initialize_database,
)

# Motores de cálculo financiero
from domain.evolution_engine import build_evolution_snapshot_from_db
from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot
from domain.rebalance_engine import build_rebalance_advisor_snapshot

# Módulo de generación de reportes PDF
from reports.pdf_generator import (
    ReportGenerationError,
    generate_user_report_pdf,
    is_pdf_generation_available,
    persist_generated_report,
)


# ------------------------------------------------------------
# Modelos de respuesta (esquemas Pydantic)
# ------------------------------------------------------------

class ReportUserResponse(BaseModel):
    """Datos del usuario incluidos en la respuesta del reporte."""
    id: int
    name: str
    email: str


class ReportPortfolioResponse(BaseModel):
    """Resumen financiero del portafolio del usuario."""
    portfolio_count: int       # Número de portafolios del usuario
    position_count: int        # Total de posiciones abiertas
    total_current_value: float # Valor de mercado actual
    total_cost_basis: float    # Costo base total de las inversiones
    primary_portfolio: str | None  # Nombre del portafolio principal


class ReportPdfResponse(BaseModel):
    """Metadatos del archivo PDF generado."""
    file_name: str        # Nombre del archivo PDF
    relative_path: str    # Ruta relativa al proyecto
    absolute_path: str    # Ruta absoluta en el sistema
    download_url: str     # URL para descargar el PDF desde la API
    public_download_url: str | None = None  # URL pública opcional para integraciones externas
    generated_at: str     # Fecha y hora de generación
    size_bytes: int       # Tamaño del archivo en bytes
    available: bool = True  # Indica si el PDF está disponible


class ReportGenerationResponse(BaseModel):
    """Respuesta completa del endpoint de generación de reportes."""
    status: str                          # Estado de la operación
    message: str                         # Mensaje descriptivo
    user: ReportUserResponse             # Información del usuario
    portfolio: ReportPortfolioResponse   # Resumen del portafolio
    pdf: ReportPdfResponse               # Datos del PDF generado
    warnings: list[str] = Field(default_factory=list)  # Advertencias opcionales
    sections: list[str] = Field(default_factory=list)  # Secciones incluidas en el reporte


class ZapierDeliveryResponse(BaseModel):
    """Resultado del intento de entrega hacia Zapier."""
    mode: str
    webhook_configured: bool
    target_url: str | None = None
    attempted_at: str
    delivered_at: str | None = None
    http_status: int | None = None
    response_excerpt: str | None = None


class ZapierDebugResponse(BaseModel):
    """Respuesta del endpoint manual para previsualizar o enviar a Zapier."""
    status: str
    message: str
    user: ReportUserResponse
    portfolio: ReportPortfolioResponse
    pdf: ReportPdfResponse
    zapier_payload: dict[str, Any]
    delivery: ZapierDeliveryResponse
    warnings: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)


# ------------------------------------------------------------
# Inicialización de la aplicación FastAPI
# ------------------------------------------------------------

logger = logging.getLogger(__name__)

_ZAPIER_TIMER_MAX_CHUNK_SECONDS = 24 * 60 * 60
_zapier_timer_lock = threading.Lock()
_zapier_timer: threading.Timer | None = None
_zapier_timer_remaining_seconds = 0
_zapier_timer_running = False

app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    description="API del proyecto Dashboard_Financiero con generación de informes PDF.",
)

# Directorio donde se almacenan los reportes generados
reports_output_dir = ensure_generated_reports_directory()

# Montar carpeta de reportes como archivos estáticos descargables
app.mount("/report-files", StaticFiles(directory=reports_output_dir), name="report-files")


# ------------------------------------------------------------
# Funciones auxiliares internas
# ------------------------------------------------------------

def _error_response(
    *,
    http_status: int,
    message: str,
    code: str,
    user_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Genera una respuesta JSON uniforme para errores de la API."""
    payload: dict[str, Any] = {
        "status": "error",
        "code": code,
        "message": message,
    }
    if user_id is not None:
        payload["user_id"] = user_id  # Incluir ID de usuario si está disponible
    if extra:
        payload.update(extra)  # Agregar campos extra al payload
    return JSONResponse(status_code=http_status, content=payload)


def _build_dashboard_data(*, user_email: str) -> dict[str, Any]:
    """
    Construye los datos consolidados del dashboard para un usuario.
    Conecta con la base de datos y ejecuta los motores financieros.
    """
    with get_connection() as connection:
        # Snapshot del portafolio actual del usuario
        portfolio_snapshot = build_portfolio_snapshot(
            connection=connection,
            user_email=user_email,
        )
        # Historial de evolución del portafolio
        evolution_snapshot = build_evolution_snapshot_from_db(
            connection=connection,
            user_email=user_email,
        )
        # Snapshot de optimización HRP (Hierarchical Risk Parity)
        hrp_snapshot = build_hrp_portfolio_snapshot(
            connection=connection,
            user_email=user_email,
            prefer_live_data=True,
        )
        # Recomendaciones de rebalanceo del portafolio
        advisor_snapshot = build_rebalance_advisor_snapshot(
            connection=connection,
            user_email=user_email,
            rebalance_threshold=3,
            prefer_live_data=True,
            portfolio_snapshot=portfolio_snapshot,
            hrp_snapshot=hrp_snapshot,
        )
        # Lista de portafolios del usuario como diccionarios
        user_portfolios = [
            dict(row) for row in get_user_portfolios(connection, user_email=user_email)
        ]

    return {
        "portfolio_snapshot": portfolio_snapshot,
        "evolution_snapshot": evolution_snapshot,
        "hrp_snapshot": hrp_snapshot,
        "advisor_snapshot": advisor_snapshot,
        "user_portfolios": user_portfolios,
    }


def _build_relative_report_path(file_path: str) -> str:
    """
    Calcula la ruta relativa del reporte respecto al directorio base del proyecto.
    Si no es posible calcularla, retorna la ruta absoluta.
    """
    from pathlib import Path

    target_path = Path(file_path)
    try:
        return target_path.relative_to(settings.base_dir).as_posix()
    except ValueError:
        return target_path.as_posix()  # Fallback: retornar ruta absoluta


def _build_download_url(file_name: str) -> str:
    """Construye la URL relativa de descarga preservando el contrato principal."""
    return f"/report-files/{file_name}"


def _build_public_download_url(file_name: str) -> str | None:
    """Construye la URL pública absoluta si existe una base pública configurada."""
    if not settings.public_api_base_url:
        return None
    return f"{settings.public_api_base_url}{_build_download_url(file_name)}"


def _build_portfolio_response(
    *,
    dashboard_data: dict[str, Any],
    user_portfolios: list[dict[str, Any]],
) -> ReportPortfolioResponse:
    """Normaliza el resumen de portfolio usado por ambos endpoints."""
    portfolio_summary = dashboard_data["portfolio_snapshot"].get("portfolio_summary", {})
    return ReportPortfolioResponse(
        portfolio_count=int(portfolio_summary.get("portfolio_count", 0) or 0),
        position_count=int(portfolio_summary.get("position_count", 0) or 0),
        total_current_value=float(portfolio_summary.get("total_current_value", 0.0) or 0.0),
        total_cost_basis=float(portfolio_summary.get("total_cost_basis", 0.0) or 0.0),
        primary_portfolio=(
            str(user_portfolios[0].get("portfolio_name"))
            if user_portfolios
            else None
        ),
    )


def _prepare_report_artifacts(user_id: int) -> tuple[
    dict[str, Any],
    dict[str, Any],
    Any,
    Any,
    list[dict[str, Any]],
]:
    """Reutiliza el flujo actual de generación PDF y devuelve sus artefactos."""
    try:
        initialize_database(reset=False)
    except Exception as exc:
        raise RuntimeError(
            json.dumps(
                {
                    "http_status": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "code": "database_unavailable",
                    "message": f"No fue posible inicializar o abrir la base de datos: {exc}",
                    "extra": {"database_path": str(settings.database_path)},
                }
            )
        ) from exc

    with get_connection() as connection:
        selected_user = get_user_by_id(connection, user_id=user_id)

    if selected_user is None:
        raise LookupError(
            json.dumps(
                {
                    "http_status": status.HTTP_404_NOT_FOUND,
                    "code": "user_not_found",
                    "message": "No existe un usuario con el ID solicitado.",
                }
            )
        )

    pdf_available, pdf_message = is_pdf_generation_available()
    if not pdf_available:
        raise ReportGenerationError(
            json.dumps(
                {
                    "http_status": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "code": "pdf_generation_unavailable",
                    "message": pdf_message or "La generación PDF no está disponible en este entorno.",
                    "extra": {"pdf": {"available": False}, "email": selected_user["user_email"]},
                }
            )
        )

    selected_user_data = dict(selected_user)

    dashboard_data = _build_dashboard_data(user_email=selected_user_data["user_email"])
    report = generate_user_report_pdf(
        selected_user=selected_user_data,
        dashboard_data=dashboard_data,
    )
    stored_path = persist_generated_report(
        report,
        output_dir=ensure_generated_reports_directory(),
    )
    user_portfolios = dashboard_data.get("user_portfolios", [])
    return selected_user_data, dashboard_data, report, stored_path, user_portfolios


def _build_pdf_response(*, report: Any, stored_path: Any) -> ReportPdfResponse:
    """Construye los metadatos del PDF persistido."""
    relative_path = _build_relative_report_path(str(stored_path))
    return ReportPdfResponse(
        file_name=report.file_name,
        relative_path=relative_path,
        absolute_path=str(stored_path),
        download_url=_build_download_url(report.file_name),
        public_download_url=_build_public_download_url(report.file_name),
        generated_at=report.generated_at,
        size_bytes=len(report.content),
    )


def _build_zapier_payload(
    *,
    user_id: int,
    selected_user_data: dict[str, Any],
    portfolio: ReportPortfolioResponse,
    pdf: ReportPdfResponse,
    report: Any,
    trigger_source: str,
) -> dict[str, Any]:
    """Construye el payload que luego consumira Zapier."""
    pdf_payload = pdf.model_dump()
    pdf_payload.update(
        {
            "file_name": report.file_name,
            "mime_type": "application/pdf",
            "size_bytes": len(report.content),
            "encoding": "base64",
            "content_base64": base64.b64encode(report.content).decode("ascii"),
            "public_download_url": pdf.public_download_url,
        }
    )

    return {
        "event": "user_report_generated",
        "trigger_source": trigger_source,
        "requested_user_id": user_id,
        "generated_at": report.generated_at,
        "user": {
            "id": int(selected_user_data["user_id"]),
            "name": str(selected_user_data["user_name"]),
            "email": str(selected_user_data["user_email"]),
        },
        "portfolio": portfolio.model_dump(),
        "pdf": pdf_payload,
        "report": {
            "sections": list(report.sections),
            "warnings": list(report.warnings),
        },
        "integration": {
            "zapier_webhook_configured": bool(settings.zapier_webhook_url),
            "public_api_base_url": settings.public_api_base_url,
        },
    }


def _build_json_error_from_encoded(user_id: int, encoded_message: str) -> JSONResponse:
    """Reconstruye errores internos serializados para responder de forma uniforme."""
    try:
        payload = json.loads(encoded_message)
    except json.JSONDecodeError:
        return _error_response(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="unexpected_report_error",
            message=encoded_message,
            user_id=user_id,
        )

    return _error_response(
        http_status=int(payload.get("http_status", status.HTTP_500_INTERNAL_SERVER_ERROR)),
        code=str(payload.get("code", "unexpected_report_error")),
        message=str(payload.get("message", "Ocurrió un error inesperado.")),
        user_id=user_id,
        extra=payload.get("extra"),
    )


def _send_zapier_webhook(payload: dict[str, Any]) -> ZapierDeliveryResponse:
    """Envía el payload a Zapier cuando existe webhook configurado."""
    attempted_at = datetime.now(UTC).isoformat()
    webhook_url = settings.zapier_webhook_url
    if not webhook_url:
        return ZapierDeliveryResponse(
            mode="preview",
            webhook_configured=False,
            attempted_at=attempted_at,
        )

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return ZapierDeliveryResponse(
                mode="webhook_sent",
                webhook_configured=True,
                target_url=webhook_url,
                attempted_at=attempted_at,
                delivered_at=datetime.now(UTC).isoformat(),
                http_status=getattr(response, "status", response.getcode()),
                response_excerpt=response_body[:500] or None,
            )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Zapier respondió con HTTP {exc.code}: {detail[:500] or 'sin cuerpo de respuesta'}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"No fue posible contactar el webhook de Zapier: {exc.reason}") from exc


def _execute_zapier_report_flow(
    *,
    user_id: int,
    trigger_source: str,
) -> dict[str, Any]:
    """Ejecuta el flujo reutilizable de generación y entrega a Zapier para un usuario."""
    selected_user_data, dashboard_data, report, stored_path, user_portfolios = _prepare_report_artifacts(user_id)
    portfolio = _build_portfolio_response(
        dashboard_data=dashboard_data,
        user_portfolios=user_portfolios,
    )
    pdf = _build_pdf_response(report=report, stored_path=stored_path)
    zapier_payload = _build_zapier_payload(
        user_id=user_id,
        selected_user_data=selected_user_data,
        portfolio=portfolio,
        pdf=pdf,
        report=report,
        trigger_source=trigger_source,
    )
    delivery = _send_zapier_webhook(zapier_payload)

    return {
        "selected_user_data": selected_user_data,
        "portfolio": portfolio,
        "pdf": pdf,
        "zapier_payload": zapier_payload,
        "delivery": delivery,
        "warnings": list(report.warnings),
        "sections": list(report.sections),
    }


def _run_scheduled_zapier_reports() -> dict[str, list[int]]:
    """Dispara el flujo Zapier para todos los usuarios actuales cuando vence el temporizador."""
    initialize_database(reset=False)

    with get_connection() as connection:
        users = get_users(connection)

    summary: dict[str, list[int]] = {
        "attempted_user_ids": [],
        "sent_user_ids": [],
        "preview_user_ids": [],
        "failed_user_ids": [],
    }

    for user in users:
        user_id = int(user["user_id"])
        summary["attempted_user_ids"].append(user_id)
        try:
            result = _execute_zapier_report_flow(
                user_id=user_id,
                trigger_source="startup_interval_timer",
            )
        except Exception:
            summary["failed_user_ids"].append(user_id)
            logger.exception("Fallo el envio programado por Zapier para el usuario %s.", user_id)
            continue

        delivery = result["delivery"]
        if delivery.mode == "webhook_sent":
            summary["sent_user_ids"].append(user_id)
        else:
            summary["preview_user_ids"].append(user_id)

    return summary


def _schedule_next_zapier_report_run() -> None:
    """Programa la siguiente ejecución en memoria usando esperas troceadas seguras."""
    global _zapier_timer, _zapier_timer_remaining_seconds

    if settings.zapier_report_interval_seconds == 0:
        _zapier_timer = None
        _zapier_timer_remaining_seconds = 0
        logger.info("Temporizador Zapier deshabilitado con ZAPIER_REPORT_INTERVAL_SECONDS=0.")
        return

    if _zapier_timer_remaining_seconds <= 0:
        _zapier_timer_remaining_seconds = settings.zapier_report_interval_seconds

    timer = threading.Timer(
        min(_zapier_timer_remaining_seconds, _ZAPIER_TIMER_MAX_CHUNK_SECONDS),
        _scheduled_zapier_report_callback,
    )
    timer.daemon = True
    _zapier_timer = timer
    timer.start()


def _scheduled_zapier_report_callback() -> None:
    """Consume un tramo del temporizador y ejecuta el lote al completar el intervalo."""
    global _zapier_timer, _zapier_timer_remaining_seconds

    with _zapier_timer_lock:
        if not _zapier_timer_running:
            _zapier_timer = None
            return

        _zapier_timer = None
        if _zapier_timer_remaining_seconds > _ZAPIER_TIMER_MAX_CHUNK_SECONDS:
            _zapier_timer_remaining_seconds -= _ZAPIER_TIMER_MAX_CHUNK_SECONDS
            _schedule_next_zapier_report_run()
            return

        _zapier_timer_remaining_seconds = 0

    try:
        summary = _run_scheduled_zapier_reports()
        logger.info(
            "Flujo Zapier programado ejecutado. Intentados=%s, enviados=%s, preview=%s, fallidos=%s",
            len(summary["attempted_user_ids"]),
            len(summary["sent_user_ids"]),
            len(summary["preview_user_ids"]),
            len(summary["failed_user_ids"]),
        )
    finally:
        with _zapier_timer_lock:
            if _zapier_timer_running:
                _schedule_next_zapier_report_run()


@app.on_event("startup")
def start_zapier_report_timer() -> None:
    """Inicia el temporizador en memoria al arrancar la API."""
    global _zapier_timer_running

    with _zapier_timer_lock:
        if _zapier_timer_running:
            return
        _zapier_timer_running = True
        _schedule_next_zapier_report_run()


@app.on_event("shutdown")
def stop_zapier_report_timer() -> None:
    """Detiene el temporizador al cerrar el proceso de la API."""
    global _zapier_timer, _zapier_timer_remaining_seconds, _zapier_timer_running

    with _zapier_timer_lock:
        _zapier_timer_running = False
        _zapier_timer_remaining_seconds = 0
        if _zapier_timer is not None:
            _zapier_timer.cancel()
            _zapier_timer = None


# ------------------------------------------------------------
# Endpoints de la API
# ------------------------------------------------------------

@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    """Endpoint de salud: verifica que el servicio esté activo y respondiendo."""
    return {"status": "ok", "project": settings.app_name, "phase": "fase-9"}


@app.post(
    "/api/report/{user_id}",
    tags=["reports"],
    response_model=ReportGenerationResponse,
)
def generate_report(user_id: int) -> ReportGenerationResponse | JSONResponse:
    """
    Genera y persiste un informe PDF completo para el usuario indicado.
    
    Pasos:
      1. Inicializa la base de datos
      2. Valida que el usuario exista
      3. Verifica disponibilidad de generación PDF
      4. Construye los datos del dashboard
      5. Genera y guarda el PDF
      6. Retorna los metadatos del reporte generado
    """
    try:
        selected_user_data, dashboard_data, report, stored_path, user_portfolios = _prepare_report_artifacts(user_id)
    except LookupError as exc:
        return _build_json_error_from_encoded(user_id, str(exc))
    except ReportGenerationError as exc:
        message = str(exc)
        if message.startswith("{"):
            return _build_json_error_from_encoded(user_id, message)
        return _error_response(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="report_generation_failed",
            message=message,
            user_id=user_id,
        )
    except RuntimeError as exc:
        return _build_json_error_from_encoded(user_id, str(exc))
    except Exception as exc:
        return _error_response(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="unexpected_report_error",
            message=f"Ocurrió un error al preparar el informe: {exc}",
            user_id=user_id,
        )

    portfolio = _build_portfolio_response(
        dashboard_data=dashboard_data,
        user_portfolios=user_portfolios,
    )
    pdf = _build_pdf_response(report=report, stored_path=stored_path)

    return ReportGenerationResponse(
        status="generated",
        message="Informe PDF generado correctamente.",
        user=ReportUserResponse(
            id=int(selected_user_data["user_id"]),
            name=str(selected_user_data["user_name"]),
            email=str(selected_user_data["user_email"]),
        ),
        portfolio=portfolio,
        pdf=pdf,
        warnings=list(report.warnings),
        sections=list(report.sections),
    )


@app.post(
    "/api/zapier/debug/report",
    tags=["reports", "zapier"],
    response_model=ZapierDebugResponse,
)
def trigger_zapier_debug_report(user_id: int = 1) -> ZapierDebugResponse | JSONResponse:
    """Dispara manualmente el flujo base hacia Zapier o devuelve un preview util."""
    try:
        result = _execute_zapier_report_flow(
            user_id=user_id,
            trigger_source="manual_debug",
        )
    except LookupError as exc:
        return _build_json_error_from_encoded(user_id, str(exc))
    except ReportGenerationError as exc:
        message = str(exc)
        if message.startswith("{"):
            return _build_json_error_from_encoded(user_id, message)
        return _error_response(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="report_generation_failed",
            message=message,
            user_id=user_id,
        )
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("{"):
            return _build_json_error_from_encoded(user_id, message)
        return _error_response(
            http_status=status.HTTP_502_BAD_GATEWAY,
            code="zapier_delivery_failed",
            message=message,
            user_id=user_id,
        )
    except Exception as exc:
        return _error_response(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="unexpected_zapier_error",
            message=f"Ocurrió un error al preparar el flujo Zapier: {exc}",
            user_id=user_id,
        )

    selected_user_data = result["selected_user_data"]
    portfolio = result["portfolio"]
    pdf = result["pdf"]
    zapier_payload = result["zapier_payload"]
    delivery = result["delivery"]

    message = (
        "Preview listo para diseñar el Zap; define ZAPIER_WEBHOOK_URL con un webhook para enviar el payload real."
        if delivery.mode == "preview"
        else "Payload enviado correctamente al webhook configurado de Zapier."
    )

    return ZapierDebugResponse(
        status="preview" if delivery.mode == "preview" else "sent",
        message=message,
        user=ReportUserResponse(
            id=int(selected_user_data["user_id"]),
            name=str(selected_user_data["user_name"]),
            email=str(selected_user_data["user_email"]),
        ),
        portfolio=portfolio,
        pdf=pdf,
        zapier_payload=zapier_payload,
        delivery=delivery,
        warnings=result["warnings"],
        sections=result["sections"],
    )
