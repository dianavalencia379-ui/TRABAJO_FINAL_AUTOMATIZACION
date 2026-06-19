from __future__ import annotations

from fastapi import FastAPI

from config import settings

app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    description="API base del proyecto Dashboard_Financiero.",
)


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "project": settings.app_name, "phase": "fase-1"}
