# Bloque 0.2 · Baseline runtime post-saneamiento

## Objetivo

Dejar registrado el estado observable del entorno tras el saneamiento y compararlo con el baseline previo de `Bloque_0_1_Saneamiento_Entorno.md`.

## Evidencia observable del entorno

- `.venv/pyvenv.cfg` sigue apuntando a `Python 3.12.13`.
- `.venv/Scripts/` contiene `python.exe`, `streamlit.exe`, `uvicorn.exe`, `pytest.exe` y `fastapi.exe`.
- `requirements.txt` mantiene declaradas las dependencias base del proyecto, incluyendo `httpx>=0.28,<1.0`.
- `.venv/Lib/site-packages/` contiene, entre otras, `streamlit-1.58.0`, `fastapi-0.137.2`, `uvicorn-0.49.0`, `numpy-2.4.6`, `pandas-3.0.3`, `scipy-1.18.0`, `reportlab-5.0.0`, `pytest-9.1.1`, `pydantic-2.13.4` y `yfinance-1.4.1`.
- En la misma inspección de `site-packages` no aparece `httpx`.
- La carpeta `data/` todavía no muestra una base SQLite persistida ni `generated_reports/` antes de ejecutar el runtime.

## Comparación con el baseline anterior

### Se mantiene

- La virtualenv observada sigue siendo Python `3.12.13`.
- Se conserva la alineación documental de `requirements.txt` con las majors esperadas.
- `config.py` y `.env.example` siguen preparados para usar `GEMINI_API_KEY` como caso local.
- El bloqueo principal detectado en el baseline anterior sigue siendo el mismo: falta `httpx` en la virtualenv inspeccionada.

### Cambios observables respecto al baseline anterior

- Ahora queda confirmado por inspección que la virtualenv expone los ejecutables esperados para `Streamlit`, `Uvicorn/FastAPI` y `Pytest`.
- No hay evidencia persistida previa en `data/` de una ejecución nueva posterior al saneamiento.

## Lectura operativa actual

- **Streamlit:** binario presente en `.venv/Scripts/streamlit.exe`.
- **API:** binario presente en `.venv/Scripts/uvicorn.exe` y paquete `fastapi` presente.
- **PDF:** `reportlab-5.0.0` está instalado, por lo que la capacidad de generación PDF sigue estando disponible a nivel de dependencias.
- **Tests:** `pytest` está instalado, pero la validación real del endpoint vía `fastapi.testclient` sigue condicionada por la ausencia de `httpx` en la virtualenv inspeccionada.

## Conclusión del baseline

El saneamiento dejó consistente el manifiesto y la configuración local, pero la virtualenv todavía no muestra convergencia completa con `requirements.txt` porque falta `httpx`. Mientras no se reinstale o sincronice el entorno, la validación runtime completa de API/tests seguirá teniendo riesgo de bloqueo aunque Streamlit, FastAPI/Uvicorn, ReportLab y Pytest estén presentes.
