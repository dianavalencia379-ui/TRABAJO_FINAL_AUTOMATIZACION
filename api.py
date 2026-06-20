from __future__ import annotations

from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from data_layer.db import (
    ensure_generated_reports_directory,
    get_connection,
    get_user_by_id,
    get_user_portfolios,
    initialize_database,
)
from domain.evolution_engine import build_evolution_snapshot_from_db
from domain.hrp_engine import build_hrp_portfolio_snapshot
from domain.portfolio_engine import build_portfolio_snapshot
from domain.rebalance_engine import build_rebalance_advisor_snapshot
from reports.pdf_generator import (
    ReportGenerationError,
    generate_user_report_pdf,
    is_pdf_generation_available,
    persist_generated_report,
)


class ReportUserResponse(BaseModel):
    id: int
    name: str
    email: str


class ReportPortfolioResponse(BaseModel):
    portfolio_count: int
    position_count: int
    total_current_value: float
    total_cost_basis: float
    primary_portfolio: str | None


class ReportPdfResponse(BaseModel):
    file_name: str
    relative_path: str
    absolute_path: str
    download_url: str
    generated_at: str
    size_bytes: int
    available: bool = True


class ReportGenerationResponse(BaseModel):
    status: str
    message: str
    user: ReportUserResponse
    portfolio: ReportPortfolioResponse
    pdf: ReportPdfResponse
    warnings: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)

app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    description="API del proyecto Dashboard_Financiero con generación de informes PDF.",
)

reports_output_dir = ensure_generated_reports_directory()
app.mount("/report-files", StaticFiles(directory=reports_output_dir), name="report-files")


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
        payload["user_id"] = user_id
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=http_status, content=payload)


def _build_dashboard_data(*, user_email: str) -> dict[str, Any]:
    """Construye los datos consolidados que necesita el endpoint de reportes."""
    with get_connection() as connection:
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
            prefer_live_data=True,
        )
        advisor_snapshot = build_rebalance_advisor_snapshot(
            connection=connection,
            user_email=user_email,
            rebalance_threshold=3,
            prefer_live_data=True,
            portfolio_snapshot=portfolio_snapshot,
            hrp_snapshot=hrp_snapshot,
        )
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
    """Calcula una ruta relativa al proyecto cuando es posible."""
    from pathlib import Path

    target_path = Path(file_path)
    try:
        return target_path.relative_to(settings.base_dir).as_posix()
    except ValueError:
        return target_path.as_posix()


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    """Expone un chequeo básico de disponibilidad del servicio."""
    return {"status": "ok", "project": settings.app_name, "phase": "fase-9"}


@app.post(
    "/api/report/{user_id}",
    tags=["reports"],
    response_model=ReportGenerationResponse,
)
def generate_report(user_id: int) -> ReportGenerationResponse | JSONResponse:
    """Genera y persiste un informe PDF para el usuario solicitado."""
    try:
        initialize_database(reset=False)
    except Exception as exc:
        return _error_response(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_unavailable",
            message=f"No fue posible inicializar o abrir la base de datos: {exc}",
            user_id=user_id,
            extra={
                "database_path": str(settings.database_path),
            },
        )

    with get_connection() as connection:
        selected_user = get_user_by_id(connection, user_id=user_id)

    if selected_user is None:
        return _error_response(
            http_status=status.HTTP_404_NOT_FOUND,
            code="user_not_found",
            message="No existe un usuario con el ID solicitado.",
            user_id=user_id,
        )

    pdf_available, pdf_message = is_pdf_generation_available()
    if not pdf_available:
        return _error_response(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="pdf_generation_unavailable",
            message=pdf_message or "La generación PDF no está disponible en este entorno.",
            user_id=user_id,
            extra={
                "pdf": {"available": False},
                "email": selected_user["user_email"],
            },
        )

    selected_user_data = dict(selected_user)

    try:
        dashboard_data = _build_dashboard_data(user_email=selected_user_data["user_email"])
        report = generate_user_report_pdf(
            selected_user=selected_user_data,
            dashboard_data=dashboard_data,
        )
        stored_path = persist_generated_report(
            report,
            output_dir=ensure_generated_reports_directory(),
        )
    except ReportGenerationError as exc:
        return _error_response(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="report_generation_failed",
            message=str(exc),
            user_id=user_id,
            extra={"email": selected_user_data["user_email"]},
        )
    except Exception as exc:
        return _error_response(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="unexpected_report_error",
            message=f"Ocurrió un error al preparar el informe: {exc}",
            user_id=user_id,
            extra={"email": selected_user_data["user_email"]},
        )

    portfolio_summary = dashboard_data["portfolio_snapshot"].get("portfolio_summary", {})
    user_portfolios = dashboard_data.get("user_portfolios", [])
    relative_path = _build_relative_report_path(str(stored_path))

    return ReportGenerationResponse(
        status="generated",
        message="Informe PDF generado correctamente.",
        user=ReportUserResponse(
            id=int(selected_user_data["user_id"]),
            name=str(selected_user_data["user_name"]),
            email=str(selected_user_data["user_email"]),
        ),
        portfolio=ReportPortfolioResponse(
            portfolio_count=int(portfolio_summary.get("portfolio_count", 0) or 0),
            position_count=int(portfolio_summary.get("position_count", 0) or 0),
            total_current_value=float(portfolio_summary.get("total_current_value", 0.0) or 0.0),
            total_cost_basis=float(portfolio_summary.get("total_cost_basis", 0.0) or 0.0),
            primary_portfolio=(
                str(user_portfolios[0].get("portfolio_name"))
                if user_portfolios
                else None
            ),
        ),
        pdf=ReportPdfResponse(
            file_name=report.file_name,
            relative_path=relative_path,
            absolute_path=str(stored_path),
            download_url=f"/report-files/{report.file_name}",
            generated_at=report.generated_at,
            size_bytes=len(report.content),
        ),
        warnings=list(report.warnings),
        sections=list(report.sections),
    )
