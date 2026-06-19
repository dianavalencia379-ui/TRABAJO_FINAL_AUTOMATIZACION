from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Dashboard_Financiero"
    environment: str = "development"
    database_name: str = "dashboard_financiero.db"
    data_dirname: str = "data"
    reports_dirname: str = "reports"
    generated_reports_dirname: str = "generated_reports"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def database_path(self) -> Path:
        return self.base_dir / self.data_dirname / self.database_name

    @property
    def data_dir(self) -> Path:
        return self.base_dir / self.data_dirname

    @property
    def reports_dir(self) -> Path:
        return self.base_dir / self.reports_dirname

    @property
    def generated_reports_dir(self) -> Path:
        return self.data_dir / self.generated_reports_dirname


settings = Settings()
