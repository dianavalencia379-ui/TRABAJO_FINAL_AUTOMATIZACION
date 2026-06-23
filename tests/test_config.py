# ============================================================
# tests/test_config.py — Tests de configuración
# Verifica la carga correcta de variables de entorno y
# secretos desde .env y el sistema en config.py.
# ============================================================

from __future__ import annotations

from pathlib import Path

import pytest

from config import build_settings


def test_build_settings_reads_api_key_from_dotenv(tmp_path: Path) -> None:
    """
    Verifica que la API key se cargue correctamente desde un archivo .env.
    Usa una variable personalizada apuntada por API_KEY_ENV_VAR.
    """
    # Crear .env con variable personalizada y su valor
    (tmp_path / ".env").write_text(
        "API_KEY_ENV_VAR=EXTERNAL_SERVICE_KEY\nEXTERNAL_SERVICE_KEY=super-secret-value\n",
        encoding="utf-8",
    )

    settings = build_settings(base_dir=tmp_path, environ={})

    # Verificar que la API key fue encontrada y es correcta
    assert settings.has_api_key is True
    assert settings.require_api_key() == "super-secret-value"
    assert settings.api_key_env_name == "EXTERNAL_SERVICE_KEY"


def test_build_settings_prefers_os_environment_over_dotenv(tmp_path: Path) -> None:
    """
    Comprueba que las variables de entorno del sistema tengan prioridad sobre .env.
    El valor del entorno debe sobreescribir el del archivo .env.
    """
    # .env con un valor que debe ser sobreescrito
    (tmp_path / ".env").write_text(
        "DASHBOARD_API_KEY=dotenv-value\n",
        encoding="utf-8",
    )

    # El entorno del sistema tiene el valor correcto
    settings = build_settings(
        base_dir=tmp_path,
        environ={"DASHBOARD_API_KEY": "environment-value"},
    )

    # El entorno debe ganar sobre el .env
    assert settings.require_api_key() == "environment-value"


def test_build_settings_reads_gemini_api_key_without_explicit_mapping(tmp_path: Path) -> None:
    """
    Verifica que GEMINI_API_KEY se detecte automáticamente sin configuración extra.
    Permite reutilizar un .env local con la clave de Gemini sin mapeo explícito.
    """
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=gemini-local-value\n",
        encoding="utf-8",
    )

    settings = build_settings(base_dir=tmp_path, environ={})

    # GEMINI_API_KEY debe ser reconocida como API key válida
    assert settings.has_api_key is True
    assert settings.require_api_key() == "gemini-local-value"
    assert settings.api_key_env_name == "GEMINI_API_KEY"


def test_settings_repr_does_not_expose_api_key(tmp_path: Path) -> None:
    """
    Asegura que la representación de Settings no exponga el valor del secreto.
    El campo api_key tiene repr=False en el dataclass para proteger el valor.
    """
    (tmp_path / ".env").write_text(
        "DASHBOARD_API_KEY=super-secret-value\n",
        encoding="utf-8",
    )

    settings = build_settings(base_dir=tmp_path, environ={})

    # El valor secreto no debe aparecer en el repr del objeto
    assert "super-secret-value" not in repr(settings)


def test_require_api_key_raises_when_missing(tmp_path: Path) -> None:
    """
    Comprueba que require_api_key() lance RuntimeError cuando falta la clave.
    El mensaje de error debe indicar cómo configurar la variable.
    """
    # Sin .env ni variables de entorno: no hay API key
    settings = build_settings(base_dir=tmp_path, environ={})

    # Debe lanzar RuntimeError con mensaje descriptivo
    with pytest.raises(RuntimeError, match="Falta configurar la API key"):
        settings.require_api_key()
