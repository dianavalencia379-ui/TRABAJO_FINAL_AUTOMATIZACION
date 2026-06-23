# ============================================================
# data_layer/db.py — Utilidades SQLite para el dashboard
# Gestiona conexiones, esquema, seed y consultas principales
# del proyecto Dashboard Financiero.
# ============================================================

"""Utilidades SQLite para el dashboard financiero."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from config import settings
from data_layer.seed_data import build_seed_payload


# ------------------------------------------------------------
# Esquema de la base de datos
# Define las tablas e índices necesarios para la aplicación
# ------------------------------------------------------------

SCHEMA_STATEMENTS: tuple[str, ...] = (
    # Tabla de usuarios del sistema
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """,
    # Tabla de portfolios asociados a cada usuario
    """
    CREATE TABLE IF NOT EXISTS portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """,
    # Tabla de posiciones (activos) dentro de cada portfolio
    """
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        asset_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        avg_price REAL NOT NULL,
        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE,
        UNIQUE (portfolio_id, ticker)
    )
    """,
    # Tabla de historial de valor total por portfolio y fecha
    """
    CREATE TABLE IF NOT EXISTS portfolio_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        total_value REAL NOT NULL,
        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE,
        UNIQUE (portfolio_id, date)
    )
    """,
    # Índices para optimizar las consultas más frecuentes
    "CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_positions_portfolio_id ON positions (portfolio_id)",
    "CREATE INDEX IF NOT EXISTS idx_history_portfolio_id_date ON portfolio_history (portfolio_id, date)",
)


# ------------------------------------------------------------
# Funciones auxiliares de configuración de rutas
# ------------------------------------------------------------

def _timestamp() -> str:
    """Devuelve la marca temporal fija usada al sembrar datos demo."""
    return "2026-06-19T09:00:00"


def get_database_path() -> Path:
    """Obtiene la ruta configurada para la base SQLite principal."""
    return settings.database_path


def ensure_database_directory() -> Path:
    """Garantiza que exista la carpeta de datos de la base."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir


def ensure_generated_reports_directory() -> Path:
    """Garantiza que exista la carpeta de PDFs generados."""
    settings.generated_reports_dir.mkdir(parents=True, exist_ok=True)
    return settings.generated_reports_dir


# ------------------------------------------------------------
# Funciones de conexión y esquema
# ------------------------------------------------------------

def get_connection(database_path: Path | None = None) -> sqlite3.Connection:
    """Abre una conexión SQLite con filas accesibles por nombre."""
    ensure_database_directory()
    connection = sqlite3.connect(database_path or get_database_path())
    connection.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    connection.execute("PRAGMA foreign_keys = ON")  # Activar integridad referencial
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Crea el esquema base de tablas e índices si aún no existe."""
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.commit()


def reset_database(database_path: Path | None = None) -> Path:
    """Elimina la base existente para forzar una recreación limpia."""
    target = database_path or get_database_path()
    ensure_database_directory()
    if target.exists():
        target.unlink()  # Eliminar archivo SQLite del disco
    return target


# ------------------------------------------------------------
# Funciones de seed (datos iniciales)
# ------------------------------------------------------------

def is_seeded(connection: sqlite3.Connection) -> bool:
    """Comprueba si la base ya contiene usuarios cargados."""
    row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return bool(row and row["total"] > 0)


def seed_database(connection: sqlite3.Connection) -> bool:
    """
    Inserta los datos ficticios iniciales cuando la base está vacía.
    Retorna True si se insertaron datos, False si ya estaban cargados.
    """
    if is_seeded(connection):
        return False

    created_at = _timestamp()
    for user in build_seed_payload():
        # Insertar usuario
        cursor = connection.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            (user["name"], user["email"], created_at),
        )
        user_id = cursor.lastrowid

        # Insertar portfolio del usuario
        portfolio = user["portfolio"]
        portfolio_cursor = connection.execute(
            "INSERT INTO portfolios (user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, portfolio["name"], created_at),
        )
        portfolio_id = portfolio_cursor.lastrowid

        # Insertar posiciones del portfolio
        connection.executemany(
            """
            INSERT INTO positions (portfolio_id, ticker, asset_name, quantity, avg_price)
            VALUES (:portfolio_id, :ticker, :asset_name, :quantity, :avg_price)
            """,
            [
                {"portfolio_id": portfolio_id, **position}
                for position in portfolio["positions"]
            ],
        )

        # Insertar historial de valores del portfolio
        connection.executemany(
            """
            INSERT INTO portfolio_history (portfolio_id, date, total_value)
            VALUES (:portfolio_id, :date, :total_value)
            """,
            [
                {"portfolio_id": portfolio_id, **record}
                for record in portfolio["history_records"]
            ],
        )

    connection.commit()
    return True


# ------------------------------------------------------------
# Inicialización completa de la base de datos
# ------------------------------------------------------------

def initialize_database(reset: bool = False) -> dict[str, Any]:
    """Inicializa esquema, seed y validaciones básicas de la base."""
    if reset:
        reset_database()  # Borrar base si se solicita reset completo

    with get_connection() as connection:
        create_schema(connection)
        seeded = seed_database(connection)
        verification = verify_database(connection)

    return {
        "database_path": str(get_database_path()),
        "seeded": seeded,
        **verification,
    }


# ------------------------------------------------------------
# Consultas principales
# ------------------------------------------------------------

def get_table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Cuenta los registros de cada tabla principal del modelo."""
    table_names = ("users", "portfolios", "positions", "portfolio_history")
    return {
        table_name: connection.execute(
            f"SELECT COUNT(*) AS total FROM {table_name}"
        ).fetchone()["total"]
        for table_name in table_names
    }


def get_portfolio_summaries(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Recupera un resumen agregado por portfolio para validación y UI."""
    return connection.execute(
        """
        SELECT
            p.id AS portfolio_id,
            u.name AS user_name,
            u.email AS email,
            p.name AS portfolio_name,
            COALESCE(pos.positions_count, 0) AS positions_count,
            COALESCE(hist.history_points, 0) AS history_points,
            ROUND(COALESCE(pos.invested_amount, 0), 2) AS invested_amount
        FROM users u
        JOIN portfolios p ON p.user_id = u.id
        LEFT JOIN (
            SELECT
                portfolio_id,
                COUNT(*) AS positions_count,
                SUM(quantity * avg_price) AS invested_amount
            FROM positions
            GROUP BY portfolio_id
        ) pos ON pos.portfolio_id = p.id
        LEFT JOIN (
            SELECT
                portfolio_id,
                COUNT(*) AS history_points
            FROM portfolio_history
            GROUP BY portfolio_id
        ) hist ON hist.portfolio_id = p.id
        ORDER BY u.id
        """
    ).fetchall()


def get_users(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Lista usuarios con conteos y capital estimado consolidado."""
    return connection.execute(
        """
        SELECT
            u.id AS user_id,
            u.name AS user_name,
            u.email AS user_email,
            u.created_at AS created_at,
            COUNT(DISTINCT p.id) AS portfolio_count,
            COUNT(DISTINCT pos.id) AS position_count,
            ROUND(COALESCE(SUM(pos.quantity * pos.avg_price), 0), 2) AS invested_amount
        FROM users u
        LEFT JOIN portfolios p ON p.user_id = u.id
        LEFT JOIN positions pos ON pos.portfolio_id = p.id
        GROUP BY u.id, u.name, u.email, u.created_at
        ORDER BY u.name, u.id
        """
    ).fetchall()


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    """Busca un usuario por ID junto con sus agregados principales."""
    return connection.execute(
        """
        SELECT
            u.id AS user_id,
            u.name AS user_name,
            u.email AS user_email,
            u.created_at AS created_at,
            COUNT(DISTINCT p.id) AS portfolio_count,
            COUNT(DISTINCT pos.id) AS position_count,
            ROUND(COALESCE(SUM(pos.quantity * pos.avg_price), 0), 2) AS invested_amount
        FROM users u
        LEFT JOIN portfolios p ON p.user_id = u.id
        LEFT JOIN positions pos ON pos.portfolio_id = p.id
        WHERE u.id = ?
        GROUP BY u.id, u.name, u.email, u.created_at
        """,
        (user_id,),
    ).fetchone()


def get_user_portfolios(
    connection: sqlite3.Connection,
    *,
    user_email: str | None = None,
    user_id: int | None = None,
) -> list[sqlite3.Row]:
    """Devuelve los portfolios filtrados por usuario o email."""
    query = """
        SELECT
            p.id AS portfolio_id,
            p.name AS portfolio_name,
            p.created_at AS created_at,
            u.id AS user_id,
            u.name AS user_name,
            u.email AS user_email,
            COUNT(pos.id) AS position_count,
            ROUND(COALESCE(SUM(pos.quantity * pos.avg_price), 0), 2) AS invested_amount
        FROM portfolios p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN positions pos ON pos.portfolio_id = p.id
    """
    filters: list[str] = []
    parameters: list[Any] = []

    # Filtrar por email si se proporcionó
    if user_email is not None:
        filters.append("u.email = ?")
        parameters.append(user_email)

    # Filtrar por ID si se proporcionó
    if user_id is not None:
        filters.append("u.id = ?")
        parameters.append(user_id)

    if filters:
        query = f"{query} WHERE {' AND '.join(filters)}"

    query = f"""
        {query}
        GROUP BY p.id, p.name, p.created_at, u.id, u.name, u.email
        ORDER BY p.id
    """
    return connection.execute(query, parameters).fetchall()


def get_portfolio_history_series(
    connection: sqlite3.Connection,
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
) -> list[sqlite3.Row]:
    """Obtiene la serie histórica agregada filtrada por portfolio o usuario."""
    query = """
        SELECT
            ph.date AS date,
            ROUND(SUM(ph.total_value), 2) AS total_value
        FROM portfolio_history ph
        JOIN portfolios p ON p.id = ph.portfolio_id
        JOIN users u ON u.id = p.user_id
    """

    filters: list[str] = []
    parameters: list[Any] = []

    if portfolio_id is not None:
        filters.append("ph.portfolio_id = ?")
        parameters.append(portfolio_id)

    if user_email is not None:
        filters.append("u.email = ?")
        parameters.append(user_email)

    if filters:
        query = f"{query} WHERE {' AND '.join(filters)}"

    query = f"{query} GROUP BY ph.date ORDER BY ph.date"
    return connection.execute(query, parameters).fetchall()


def get_portfolio_evolution_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Construye métricas de evolución para cada portfolio persistido."""
    from domain.evolution_engine import build_evolution_snapshot_from_db

    evolution_summaries: list[dict[str, Any]] = []
    for summary in get_portfolio_summaries(connection):
        snapshot = build_evolution_snapshot_from_db(
            connection=connection,
            portfolio_id=summary["portfolio_id"],
        )
        evolution_summaries.append(
            {
                "portfolio_id": summary["portfolio_id"],
                "portfolio_name": summary["portfolio_name"],
                "user_name": summary["user_name"],
                "email": summary["email"],
                **snapshot["metrics"],
            }
        )
    return evolution_summaries


def get_portfolio_positions(
    connection: sqlite3.Connection,
    *,
    portfolio_id: int | None = None,
    user_email: str | None = None,
) -> list[sqlite3.Row]:
    """Recupera posiciones enriquecidas con datos de portfolio y usuario."""
    query = """
        SELECT
            pos.id AS position_id,
            pos.portfolio_id AS portfolio_id,
            p.name AS portfolio_name,
            p.user_id AS user_id,
            u.name AS user_name,
            u.email AS user_email,
            pos.ticker AS ticker,
            pos.asset_name AS asset_name,
            pos.quantity AS quantity,
            pos.avg_price AS avg_price
        FROM positions pos
        JOIN portfolios p ON p.id = pos.portfolio_id
        JOIN users u ON u.id = p.user_id
    """

    filters: list[str] = []
    parameters: list[Any] = []

    if portfolio_id is not None:
        filters.append("pos.portfolio_id = ?")
        parameters.append(portfolio_id)

    if user_email is not None:
        filters.append("u.email = ?")
        parameters.append(user_email)

    if filters:
        query = f"{query} WHERE {' AND '.join(filters)}"

    query = f"{query} ORDER BY p.id, pos.ticker"
    return connection.execute(query, parameters).fetchall()


# ------------------------------------------------------------
# Verificación de integridad de la base de datos
# ------------------------------------------------------------

def verify_database(connection: sqlite3.Connection) -> dict[str, Any]:
    """
    Valida que la base sembrada tenga cobertura suficiente para la app.
    Verifica mínimos de usuarios, portfolios, posiciones e historial.
    """
    counts = get_table_counts(connection)
    summaries = get_portfolio_summaries(connection)
    evolution_summaries = get_portfolio_evolution_summaries(connection)

    # Verificar que se cumplen los mínimos requeridos por la aplicación
    is_functional = (
        counts["users"] >= 3
        and counts["portfolios"] >= 3
        and counts["positions"] >= 15
        and counts["portfolio_history"] >= 90
        and all(summary["positions_count"] >= 5 for summary in summaries)
        and all(summary["history_points"] >= 30 for summary in summaries)
        and all(summary["points"] >= 30 for summary in evolution_summaries)
    )
    return {
        "counts": counts,
        "portfolio_summaries": [dict(summary) for summary in summaries],
        "portfolio_evolution_summaries": evolution_summaries,
        "is_functional": is_functional,
    }
