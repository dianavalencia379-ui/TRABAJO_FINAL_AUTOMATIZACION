# Fase 11 · Validación de pruebas

## Alcance de la batería principal

- `tests/test_portfolio_engine.py`
- `tests/test_hrp_engine.py`
- `tests/test_pdf_generator.py`
- `tests/test_api_report_endpoint.py`

## Cobertura prioritaria

- pesos del portfolio y sumas al 100%
- pesos HRP y suma total igual a 1
- generación de payload y binario PDF
- persistencia del PDF generado
- endpoint `POST /api/report/{user_id}` con casos happy path, usuario inexistente y falta de ReportLab

## Entrypoints

```bash
python -m pytest
python scripts/run_main_test_battery.py
```

## Dependencias de testing

- `pytest`
- `fastapi` / `starlette.testclient`
- `httpx` como soporte requerido por `starlette.testclient`
- `reportlab` para validación real de PDFs

## Hallazgos del entorno revisado

- `.venv` contiene `pytest-9.1.1`, `fastapi-0.137.2`, `reportlab-5.0.0`, `scipy-1.18.0` y `yfinance-1.4.1`.
- En la inspección del `site-packages` no aparece `httpx`, así que la ejecución real de tests API depende de instalarlo primero.
- Hay drift entre algunos pins declarados y el entorno (`pytest<9.0`, `reportlab<5.0`, `yfinance<1.0`).

## Notas

- `pytest.ini` fija `tests/` como raíz de descubrimiento.
- La batería principal queda concentrada en el runner `scripts/run_main_test_battery.py`.
