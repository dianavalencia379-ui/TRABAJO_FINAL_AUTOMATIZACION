# ============================================================
# data_layer/yahoo_client.py — Cliente de precios históricos
# Descarga precios reales desde Yahoo Finance o genera datos
# simulados como fallback para el advisor HRP.
# ============================================================

"""Cliente de precios históricos con fallback simulado para el advisor HRP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any

import numpy as np
import pandas as pd

# Importación opcional de yfinance (puede no estar instalado)
try:
    import yfinance as yf
except ImportError:  # pragma: no cover - depende del entorno
    yf = None


# ------------------------------------------------------------
# Constantes de configuración
# ------------------------------------------------------------

DEFAULT_LOOKBACK_DAYS = 252   # Días de historial por defecto (1 año bursátil)
DEFAULT_MIN_POINTS = 60       # Mínimo de puntos válidos para considerar el historial útil

# Precios base de referencia por ticker (usados en simulación)
_BASE_PRICE_BY_TICKER: dict[str, float] = {
    "AAPL": 178.50,
    "MSFT": 372.40,
    "NVDA": 842.30,
    "GOOGL": 151.25,
    "AMZN": 182.90,
    "JNJ": 152.80,
    "PG": 158.60,
    "KO": 61.15,
    "PEP": 171.75,
    "V": 274.30,
    "AMD": 164.20,
    "META": 468.55,
    "QQQ": 438.10,
}

# Agrupación sectorial de tickers (usada para generar correlaciones realistas)
_GROUP_BY_TICKER: dict[str, str] = {
    "AAPL": "mega_tech",
    "MSFT": "mega_tech",
    "NVDA": "semis",
    "AMD": "semis",
    "GOOGL": "platforms",
    "META": "platforms",
    "AMZN": "platforms",
    "QQQ": "growth_etf",
    "JNJ": "defensive",
    "PG": "defensive",
    "KO": "defensive",
    "PEP": "defensive",
    "V": "payments",
}


# ------------------------------------------------------------
# Modelo de resultado de precios
# ------------------------------------------------------------

@dataclass(frozen=True)
class PriceHistoryResult:
    """Resultado inmutable de una consulta de precios históricos."""
    prices: pd.DataFrame          # DataFrame con precios de cierre por ticker
    source: str                   # Fuente: 'yahoo' o 'simulated'
    warnings: list[str]           # Advertencias generadas durante la obtención
    metadata: dict[str, Any]      # Metadatos adicionales (intervalo, filas, columnas)


# ------------------------------------------------------------
# Funciones auxiliares internas
# ------------------------------------------------------------

def _normalized_tickers(tickers: list[str] | tuple[str, ...]) -> list[str]:
    """
    Normaliza tickers a mayúsculas, elimina duplicados y espacios.
    Lanza ValueError si la lista resultante está vacía.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        clean = str(ticker).strip().upper()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    if not normalized:
        raise ValueError("Se requiere al menos un ticker para obtener precios históricos.")
    return normalized


def _stable_seed(*parts: str) -> int:
    """
    Construye una semilla determinista a partir de varios textos.
    Garantiza que la simulación produzca siempre los mismos resultados
    para los mismos tickers.
    """
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _resolve_close_frame(raw_data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """
    Extrae y ordena la serie de precios de cierre desde la respuesta de Yahoo.
    Maneja tanto DataFrames con MultiIndex como con índice simple.
    """
    if raw_data.empty:
        return pd.DataFrame()

    # Manejar respuesta con MultiIndex de columnas (múltiples tickers)
    if isinstance(raw_data.columns, pd.MultiIndex):
        if "Close" in raw_data.columns.get_level_values(0):
            close_frame = raw_data["Close"].copy()
        else:
            close_frame = raw_data.droplevel(0, axis=1).copy()
    else:
        # Respuesta con índice simple (un solo ticker)
        if "Close" in raw_data.columns and len(tickers) == 1:
            close_frame = raw_data[["Close"]].rename(columns={"Close": tickers[0]})
        else:
            close_frame = raw_data.copy()

    # Reordenar columnas, ordenar por fecha, rellenar huecos y limpiar nulos
    close_frame = close_frame.reindex(columns=tickers)
    close_frame = close_frame.sort_index().ffill().dropna(how="all")
    return close_frame.dropna(axis=1, how="all")


# ------------------------------------------------------------
# Descarga de precios reales desde Yahoo Finance
# ------------------------------------------------------------

def _download_yahoo_prices(
    tickers: list[str],
    *,
    lookback_days: int,
    interval: str,
) -> PriceHistoryResult:
    """
    Descarga precios reales desde Yahoo Finance y valida su cobertura.
    Lanza RuntimeError si yfinance no está disponible o los datos son insuficientes.
    """
    if yf is None:
        raise RuntimeError("yfinance no está instalado en el entorno actual.")

    # Descargar datos con margen extra de días para cubrir fines de semana y festivos
    raw_data = yf.download(
        tickers=tickers,
        period=f"{max(lookback_days + 30, 90)}d",
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
        group_by="column",
    )

    close_frame = _resolve_close_frame(raw_data, tickers)
    if close_frame.empty:
        raise RuntimeError("Yahoo Finance devolvió una serie vacía.")

    # Registrar advertencias por tickers sin datos
    warnings: list[str] = []
    missing_tickers = [ticker for ticker in tickers if ticker not in close_frame.columns]
    if missing_tickers:
        warnings.append(f"Sin datos para algunos tickers: {', '.join(missing_tickers)}")

    # Validar que hay suficientes puntos históricos
    if len(close_frame.index) < DEFAULT_MIN_POINTS:
        raise RuntimeError(
            f"Histórico insuficiente desde Yahoo Finance: {len(close_frame.index)} filas útiles."
        )

    return PriceHistoryResult(
        prices=close_frame.tail(lookback_days),
        source="yahoo",
        warnings=warnings,
        metadata={
            "interval": interval,
            "rows": int(len(close_frame.index)),
            "columns": list(close_frame.columns),
        },
    )


# ------------------------------------------------------------
# Generación de precios simulados (fallback)
# ------------------------------------------------------------

def generate_simulated_price_history(
    tickers: list[str] | tuple[str, ...],
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    end_date: datetime | None = None,
) -> pd.DataFrame:
    """
    Genera precios ficticios deterministas con factores comunes y sectoriales.
    Simula correlaciones realistas entre tickers del mismo sector.
    """
    normalized = _normalized_tickers(tickers)

    # Generar índice de fechas hábiles hacia atrás desde end_date
    index = pd.bdate_range(
        end=(end_date or datetime.now(UTC)).date(),
        periods=max(lookback_days, DEFAULT_MIN_POINTS),
    )

    # Factor de mercado global (afecta a todos los tickers)
    global_rng = np.random.default_rng(_stable_seed(*normalized, str(len(index))))
    market_factor = global_rng.normal(0.00035, 0.0105, size=len(index))

    # Factores sectoriales (afectan a tickers del mismo grupo)
    group_names = sorted({_GROUP_BY_TICKER.get(ticker, "general") for ticker in normalized})
    group_factors = {
        group_name: global_rng.normal(0.0001, 0.0065, size=len(index))
        for group_name in group_names
    }

    price_frame = pd.DataFrame(index=index)
    for ticker in normalized:
        rng = np.random.default_rng(_stable_seed("ticker", ticker))
        group_name = _GROUP_BY_TICKER.get(ticker, "general")
        group_factor = group_factors[group_name]

        # Precio base del ticker (conocido o generado aleatoriamente)
        base_price = _BASE_PRICE_BY_TICKER.get(ticker, 75.0 + (rng.integers(0, 220) / 3.0))

        # Parámetros individuales del ticker
        market_beta = 0.55 + (rng.random() * 0.55)       # Sensibilidad al mercado
        group_beta = 0.18 + (rng.random() * 0.35)         # Sensibilidad al sector
        drift = 0.00008 + (rng.random() * 0.00055)        # Tendencia alcista leve
        idiosyncratic = rng.normal(0.0, 0.009 + (rng.random() * 0.012), size=len(index))

        # Calcular retornos combinando todos los factores
        returns = drift + (market_beta * market_factor) + (group_beta * group_factor) + idiosyncratic
        returns = np.clip(returns, -0.18, 0.18)  # Limitar movimientos extremos

        # Construir serie de precios desde el precio base
        prices = base_price * np.cumprod(1.0 + returns)
        price_frame[ticker] = np.round(prices, 4)

    return price_frame


# ------------------------------------------------------------
# Función principal de obtención de precios
# ------------------------------------------------------------

def fetch_price_history(
    tickers: list[str] | tuple[str, ...],
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    interval: str = "1d",
    prefer_live_data: bool = True,
) -> PriceHistoryResult:
    """
    Obtiene precios históricos para los tickers indicados.
    Si prefer_live_data=True intenta Yahoo Finance primero.
    Si prefer_live_data=False devuelve datos simulados directamente.
    """
    normalized = _normalized_tickers(tickers)
    warnings: list[str] = []

    if prefer_live_data:
        # Intentar descarga real desde Yahoo Finance
        try:
            live_result = _download_yahoo_prices(
                normalized,
                lookback_days=lookback_days,
                interval=interval,
            )
            live_prices = live_result.prices.reindex(columns=normalized).dropna(axis=1, how="all")

            # Verificar que se obtuvieron datos para todos los tickers
            if len(live_prices.columns) == len(normalized):
                return PriceHistoryResult(
                    prices=live_prices,
                    source=live_result.source,
                    warnings=live_result.warnings,
                    metadata=live_result.metadata,
                )
            raise RuntimeError(
                f"Descarga parcial de Yahoo Finance para los tickers {normalized}. "
                f"Columnas recibidas: {list(live_prices.columns)}"
            )
        except Exception as exc:
            raise RuntimeError(f"Fallo al descargar precios reales de Yahoo Finance: {exc}") from exc

    # Fallback: usar precios simulados deterministas
    simulated_prices = generate_simulated_price_history(normalized, lookback_days=lookback_days)
    return PriceHistoryResult(
        prices=simulated_prices,
        source="simulated",
        warnings=warnings,
        metadata={
            "interval": interval,
            "rows": int(len(simulated_prices.index)),
            "columns": list(simulated_prices.columns),
            "fallback": True,
        },
    )
