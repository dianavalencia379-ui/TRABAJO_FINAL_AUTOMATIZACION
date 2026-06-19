from __future__ import annotations

from pathlib import Path

import pytest

from config import build_settings


def test_build_settings_reads_api_key_from_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "API_KEY_ENV_VAR=EXTERNAL_SERVICE_KEY\nEXTERNAL_SERVICE_KEY=super-secret-value\n",
        encoding="utf-8",
    )

    settings = build_settings(base_dir=tmp_path, environ={})

    assert settings.has_api_key is True
    assert settings.require_api_key() == "super-secret-value"
    assert settings.api_key_env_name == "EXTERNAL_SERVICE_KEY"


def test_build_settings_prefers_os_environment_over_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DASHBOARD_API_KEY=dotenv-value\n",
        encoding="utf-8",
    )

    settings = build_settings(
        base_dir=tmp_path,
        environ={"DASHBOARD_API_KEY": "environment-value"},
    )

    assert settings.require_api_key() == "environment-value"


def test_settings_repr_does_not_expose_api_key(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DASHBOARD_API_KEY=super-secret-value\n",
        encoding="utf-8",
    )

    settings = build_settings(base_dir=tmp_path, environ={})

    assert "super-secret-value" not in repr(settings)


def test_require_api_key_raises_when_missing(tmp_path: Path) -> None:
    settings = build_settings(base_dir=tmp_path, environ={})

    with pytest.raises(RuntimeError, match="Falta configurar la API key"):
        settings.require_api_key()
