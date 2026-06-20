from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Mapping


def _strip_optional_quotes(value: str) -> str:
    """Elimina comillas envolventes opcionales de un valor de configuración."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_dotenv(env_file: Path) -> dict[str, str]:
    """Carga pares clave-valor simples desde un archivo .env."""
    if not env_file.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

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
    """Obtiene una variable priorizando el entorno sobre el archivo .env."""
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
    """Devuelve el primer secreto disponible junto con el nombre de su variable."""
    for name in names:
        value = environ.get(name)
        if value:
            return value, name

    for name in names:
        value = dotenv_values.get(name)
        if value:
            return value, name

    return None, None


@dataclass(frozen=True)
class Settings:
    app_name: str = "Dashboard_Financiero"
    environment: str = "development"
    database_name: str = "dashboard_financiero.db"
    data_dirname: str = "data"
    reports_dirname: str = "reports"
    generated_reports_dirname: str = "generated_reports"
    api_key: str | None = field(default=None, repr=False)
    api_key_env_name: str | None = None

    @property
    def base_dir(self) -> Path:
        """Devuelve la carpeta base del proyecto."""
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
        """Entrega la API key obligatoria o lanza un error descriptivo."""
        if self.api_key:
            return self.api_key

        env_name = self.api_key_env_name or "DASHBOARD_API_KEY"
        raise RuntimeError(
            f"Falta configurar la API key en el entorno o en .env ({env_name})."
        )


def build_settings(
    *,
    base_dir: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Construye la configuración efectiva a partir del entorno y .env."""
    resolved_base_dir = base_dir or Path(__file__).resolve().parent
    resolved_environ = os.environ if environ is None else environ
    dotenv_values = _load_dotenv(resolved_base_dir / ".env")

    configured_api_key_name = _get_env_value(
        "API_KEY_ENV_VAR",
        environ=resolved_environ,
        dotenv_values=dotenv_values,
        default="DASHBOARD_API_KEY",
    ).strip() or "DASHBOARD_API_KEY"

    api_key, api_key_env_name = _get_first_secret(
        (
            configured_api_key_name,
            "DASHBOARD_API_KEY",
            "API_KEY",
            "APP_API_KEY",
            "SERVICE_API_KEY",
        ),
        environ=resolved_environ,
        dotenv_values=dotenv_values,
    )

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
        api_key=api_key,
        api_key_env_name=api_key_env_name or configured_api_key_name,
    )


settings = build_settings()
