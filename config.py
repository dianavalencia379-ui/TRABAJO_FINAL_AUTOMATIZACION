# ============================================================
# config.py — Configuración global del proyecto
# Dashboard Financiero. Carga variables de entorno y del
# archivo .env para construir un objeto Settings inmutable.
# ============================================================

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


DEFAULT_ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/27964672/42twvzz/"
DEFAULT_ZAPIER_REPORT_INTERVAL_SECONDS = 90 * 24 * 60 * 60


# ------------------------------------------------------------
# Funciones auxiliares para carga de configuración
# ------------------------------------------------------------

def _strip_optional_quotes(value: str) -> str:
    """Elimina comillas envolventes opcionales de un valor de configuración."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_dotenv(env_file: Path) -> dict[str, str]:
    """
    Carga pares clave-valor simples desde un archivo .env.
    Ignora líneas vacías, comentarios y líneas sin signo '='.
    """
    if not env_file.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        # Ignorar líneas vacías, comentarios y líneas sin '='
        if not line or line.startswith("#") or "=" not in line:
            continue

        # Separar clave y valor en el primer '=' encontrado
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if not key:
            continue

        loaded[key] = _strip_optional_quotes(value.strip())

    return loaded


def _get_env_value(
    name: str,
    *,
    environ: Mapping[str, str],
    dotenv_values: Mapping[str, str],
    default: str,
) -> str:
    """
    Obtiene una variable de configuración priorizando:
    1. Variables de entorno del sistema (environ)
    2. Archivo .env (dotenv_values)
    3. Valor por defecto (default)
    """
    value = environ.get(name)
    if value is not None:
        return value
    return dotenv_values.get(name, default)


def _get_first_secret(
    names: tuple[str, ...],
    *,
    environ: Mapping[str, str],
    dotenv_values: Mapping[str, str],
) -> tuple[str | None, str | None]:
    """
    Busca el primer secreto disponible entre los nombres indicados.
    Primero busca en variables de entorno, luego en el archivo .env.
    Devuelve el valor encontrado y el nombre de su variable.
    """
    # Buscar primero en variables de entorno del sistema
    for name in names:
        value = environ.get(name)
        if value:
            return value, name

    # Buscar luego en el archivo .env
    for name in names:
        value = dotenv_values.get(name)
        if value:
            return value, name

    # No se encontró ningún secreto
    return None, None


def _get_int_env_value(
    name: str,
    *,
    environ: Mapping[str, str],
    dotenv_values: Mapping[str, str],
    default: int,
) -> int:
    """Carga un entero desde configuración y valida que no sea negativo."""
    raw_value = _get_env_value(
        name,
        environ=environ,
        dotenv_values=dotenv_values,
        default=str(default),
    ).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"La variable {name} debe ser un entero válido.") from exc

    if value < 0:
        raise ValueError(f"La variable {name} no puede ser negativa.")

    return value


# ------------------------------------------------------------
# Clase principal de configuración (inmutable)
# ------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """
    Objeto de configuración inmutable del proyecto.
    Todos los valores se cargan al inicio y no pueden modificarse
    en tiempo de ejecución (frozen=True).
    """
    app_name: str = "Dashboard_Financiero"          # Nombre de la aplicación
    environment: str = "development"                 # Entorno: development / production
    database_name: str = "dashboard_financiero.db"  # Nombre del archivo SQLite
    data_dirname: str = "data"                       # Carpeta de datos
    reports_dirname: str = "reports"                 # Carpeta de reportes
    generated_reports_dirname: str = "generated_reports"  # Subcarpeta de PDFs generados
    api_key: str | None = field(default=None, repr=False)  # API key (oculta en repr)
    api_key_env_name: str | None = None              # Nombre de la variable de la API key
    zapier_webhook_url: str | None = None            # Webhook opcional para enviar payloads a Zapier
    public_api_base_url: str | None = None           # Base pública para construir URLs absolutas
    zapier_report_interval_seconds: int = DEFAULT_ZAPIER_REPORT_INTERVAL_SECONDS

    @property
    def base_dir(self) -> Path:
        """Devuelve la carpeta base del proyecto (donde está config.py)."""
        return Path(__file__).resolve().parent

    @property
    def database_path(self) -> Path:
        """Compone la ruta completa del archivo SQLite."""
        return self.base_dir / self.data_dirname / self.database_name

    @property
    def data_dir(self) -> Path:
        """Expone la carpeta configurada para datos persistentes."""
        return self.base_dir / self.data_dirname

    @property
    def reports_dir(self) -> Path:
        """Expone la carpeta lógica asociada a reportes del proyecto."""
        return self.base_dir / self.reports_dirname

    @property
    def generated_reports_dir(self) -> Path:
        """Expone la carpeta donde se guardan los PDFs generados."""
        return self.data_dir / self.generated_reports_dirname

    @property
    def has_api_key(self) -> bool:
        """Indica si existe una API key cargada en la configuración."""
        return bool(self.api_key)

    def require_api_key(self) -> str:
        """
        Entrega la API key obligatoria.
        Lanza RuntimeError si no está configurada.
        """
        if self.api_key:
            return self.api_key

        env_name = self.api_key_env_name or "DASHBOARD_API_KEY"
        raise RuntimeError(
            f"Falta configurar la API key en el entorno o en .env ({env_name})."
        )


# ------------------------------------------------------------
# Constructor de Settings
# ------------------------------------------------------------

def build_settings(
    *,
    base_dir: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """
    Construye la configuración efectiva a partir del entorno y .env.
    Permite inyectar base_dir y environ para facilitar pruebas unitarias.
    """
    resolved_base_dir = base_dir or Path(__file__).resolve().parent
    resolved_environ = os.environ if environ is None else environ

    # Cargar variables del archivo .env si existe
    dotenv_values = _load_dotenv(resolved_base_dir / ".env")

    # Determinar el nombre de la variable de entorno que contiene la API key
    configured_api_key_name = _get_env_value(
        "API_KEY_ENV_VAR",
        environ=resolved_environ,
        dotenv_values=dotenv_values,
        default="DASHBOARD_API_KEY",
    ).strip() or "DASHBOARD_API_KEY"

    # Buscar la API key entre los nombres conocidos de variables de secretos
    api_key, api_key_env_name = _get_first_secret(
        (
            configured_api_key_name,
            "DASHBOARD_API_KEY",
            "GEMINI_API_KEY",
            "API_KEY",
            "APP_API_KEY",
            "SERVICE_API_KEY",
        ),
        environ=resolved_environ,
        dotenv_values=dotenv_values,
    )

    # Construir y retornar el objeto Settings con todos los valores resueltos
    return Settings(
        app_name=_get_env_value(
            "APP_NAME",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="Dashboard_Financiero",
        ),
        environment=_get_env_value(
            "ENVIRONMENT",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="development",
        ),
        database_name=_get_env_value(
            "DATABASE_NAME",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="dashboard_financiero.db",
        ),
        data_dirname=_get_env_value(
            "DATA_DIRNAME",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="data",
        ),
        reports_dirname=_get_env_value(
            "REPORTS_DIRNAME",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="reports",
        ),
        generated_reports_dirname=_get_env_value(
            "GENERATED_REPORTS_DIRNAME",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default="generated_reports",
        ),
        zapier_webhook_url=(
            _get_env_value(
                "ZAPIER_WEBHOOK_URL",
                environ=resolved_environ,
                dotenv_values=dotenv_values,
                default=DEFAULT_ZAPIER_WEBHOOK_URL,
            ).strip()
            or None
        ),
        public_api_base_url=(
            _get_env_value(
                "PUBLIC_API_BASE_URL",
                environ=resolved_environ,
                dotenv_values=dotenv_values,
                default="",
            ).strip().rstrip("/")
            or None
        ),
        zapier_report_interval_seconds=_get_int_env_value(
            "ZAPIER_REPORT_INTERVAL_SECONDS",
            environ=resolved_environ,
            dotenv_values=dotenv_values,
            default=DEFAULT_ZAPIER_REPORT_INTERVAL_SECONDS,
        ),
        api_key=api_key,
        api_key_env_name=api_key_env_name or configured_api_key_name,
    )


# ------------------------------------------------------------
# Instancia global de configuración
# Se importa desde otros módulos con: from config import settings
# ------------------------------------------------------------
settings = build_settings()
