# Bloque 0.1 · Saneamiento del entorno

## Objetivo

Dejar coherentes `requirements.txt`, `.venv` y la estrategia local de `.env` para poder repetir una validación runtime sin rehacer el análisis manual.

## Estado revisado

- La `.venv` actual fue creada con `Python 3.14.4`.
- Había drift entre versiones instaladas y rangos declarados en `requirements.txt`.
- `httpx` seguía siendo una dependencia necesaria para `fastapi.testclient`/`starlette.testclient`, pero no aparece en la inspección actual de `site-packages`.
- El `.env` local existente usa una clave de proveedor (`GEMINI_API_KEY`), mientras que la configuración base priorizaba `DASHBOARD_API_KEY` salvo mapeo explícito.

## Alineación aplicada

### 1. Dependencias

Se ajustó `requirements.txt` para reflejar el baseline observado en `.venv` y mantener márgenes razonables dentro de las majors activas:

- `streamlit>=1.58,<2.0`
- `fastapi>=0.137,<1.0`
- `uvicorn>=0.49,<1.0`
- `numpy>=2.4,<3.0`
- `pandas>=3.0,<4.0`
- `scipy>=1.18,<2.0`
- `yfinance>=1.4,<2.0`
- `reportlab>=5.0,<6.0`
- `pytest>=9.1,<10.0`
- `httpx>=0.28,<1.0`
- `pydantic>=2.13,<3.0`

### 2. Estrategia `.env`

- `config.py` ahora acepta `GEMINI_API_KEY` como fallback local además de `DASHBOARD_API_KEY` y otras variantes ya soportadas.
- `.env.example` documenta el caso local mínimo con `API_KEY_ENV_VAR=GEMINI_API_KEY`.

### 3. Cobertura mínima

Se añadió un test para asegurar que `build_settings()` carga correctamente `GEMINI_API_KEY` sin requerir una variable intermedia adicional.

## Cómo repetir el baseline runtime

1. Activar o recrear la virtualenv.
2. Reinstalar dependencias desde `requirements.txt`.
3. Copiar `.env.example` a `.env` si hace falta y completar la clave solo en local.
4. Ejecutar la batería base:

```bash
python -m pytest
```

## Nota importante

Este bloque deja alineado el manifiesto y la estrategia de configuración, pero la `.venv` actual solo quedará totalmente convergida cuando se reinstalen los paquetes desde `requirements.txt` para incorporar `httpx` y sincronizar versiones instaladas con el manifiesto actualizado.
