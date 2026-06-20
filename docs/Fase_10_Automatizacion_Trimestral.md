# Fase 10 · Entregable documental de automatización trimestral

## 1. Objetivo del entregable

Documentar el flujo completo para automatizar, cada trimestre, la generación y el envío por email del informe PDF de un usuario usando la API ya implementada en `POST /api/report/{user_id}`.

Este documento toma como base el código actual del proyecto y no redefine la API existente.

---

## 2. Contrato actual revisado de la API

### Endpoint principal

- **Método:** `POST`
- **Ruta:** `/api/report/{user_id}`
- **Archivo fuente:** `api.py`
- **Función:** `generate_report(user_id: int)`

### Comportamiento actual

1. Inicializa o valida la base de datos SQLite.
2. Busca el usuario por `user_id`.
3. Verifica que la generación PDF esté disponible.
4. Construye los datos del dashboard para ese usuario.
5. Genera el informe PDF.
6. Persiste el archivo en `data/generated_reports/`.
7. Devuelve metadatos del informe y la URL relativa de descarga.

### Entrada

- **Path param requerido:** `user_id` (integer)
- **Body:** no requiere body JSON.
- **Headers recomendados:**
  - `Accept: application/json`

### Respuesta exitosa esperada (`200 OK`)

```json
{
  "status": "generated",
  "message": "Informe PDF generado correctamente.",
  "user": {
    "id": 1,
    "name": "Diana Valencia",
    "email": "diana@example.com"
  },
  "portfolio": {
    "portfolio_count": 1,
    "position_count": 5,
    "total_current_value": 48231.75,
    "total_cost_basis": 47012.40,
    "primary_portfolio": "Growth USA"
  },
  "pdf": {
    "file_name": "informe_diana_example_com_2026-06-19.pdf",
    "relative_path": "data/generated_reports/informe_diana_example_com_2026-06-19.pdf",
    "absolute_path": "C:/Users/Diana/Desktop/Dashboard_Financiero/data/generated_reports/informe_diana_example_com_2026-06-19.pdf",
    "download_url": "/report-files/informe_diana_example_com_2026-06-19.pdf",
    "generated_at": "2026-06-19T10:00:00+00:00",
    "size_bytes": 245612,
    "available": true
  },
  "warnings": [],
  "sections": [
    "Datos del usuario",
    "Portfolio",
    "Composición",
    "Valor total",
    "Evolución histórica",
    "Pesos actuales",
    "Pesos HRP",
    "Tabla de rebalanceo",
    "Comentario final",
    "Aviso académico"
  ]
}
```

### Respuestas de error identificadas en el código

#### `404 Not Found`

```json
{
  "status": "error",
  "code": "user_not_found",
  "message": "No existe un usuario con el ID solicitado.",
  "user_id": 9999
}
```

#### `503 Service Unavailable` por PDF no disponible

```json
{
  "status": "error",
  "code": "pdf_generation_unavailable",
  "message": "ReportLab no está disponible.",
  "user_id": 1,
  "pdf": {
    "available": false
  },
  "email": "diana@example.com"
}
```

#### Otros errores contemplados

- `503` `database_unavailable`
- `503` `report_generation_failed`
- `500` `unexpected_report_error`

---

## 3. Consideraciones relevantes para automatización

### Descarga del PDF

La API **no adjunta el binario PDF en la respuesta**. Devuelve metadatos y la ruta relativa de descarga en `pdf.download_url`.

Por tanto, la automatización debe hacer:

1. `POST /api/report/{user_id}` para generar el informe.
2. `GET {BASE_URL}{pdf.download_url}` para recuperar el PDF.
3. Enviar ese PDF como adjunto por email.

### URL pública necesaria

El backend expone los archivos generados mediante:

- `app.mount("/report-files", StaticFiles(...))`

Eso significa que, si la API está publicada en:

- `https://mi-dominio.com`

entonces el archivo debe descargarse desde una URL como:

- `https://mi-dominio.com/report-files/informe_xxx.pdf`

### Alcance actual de la API

- El endpoint se dispara por `user_id`.
- Genera **un informe por usuario y por ejecución**.
- No implementa envío de email interno; ese paso queda en Zapier o Make.
- No se observa autenticación en el endpoint actual, por lo que conviene documentar esta limitación si se publica fuera de un entorno controlado.

---

## 4. Flujo trimestral propuesto (principal: Make)

Se prioriza **Make** como flujo principal porque resuelve de forma clara el encadenado `Scheduler -> HTTP -> Parse JSON -> Download file -> Email`.

### Objetivo del escenario

Cada trimestre, ejecutar la generación del informe PDF de un usuario y enviarlo por correo electrónico al destinatario correspondiente.

### Frecuencia sugerida

- **Periodicidad:** cada 3 meses.
- Ejemplo práctico: primer día hábil de enero, abril, julio y octubre a las 08:00.

### Módulos / pasos en Make

#### Paso 1. Scheduler

- Módulo: **Scheduler**
- Configuración: ejecución trimestral.
- Ejemplo: `Every 3 months`.

#### Paso 2. HTTP - Generar informe

- Módulo: **HTTP > Make a request**
- Método: `POST`
- URL:

```text
https://TU_BASE_URL/api/report/1
```

- Headers:

```text
Accept: application/json
```

- Body: vacío.

#### Paso 3. Validación de respuesta

Comprobar al menos:

- `status = generated`
- `pdf.download_url` informado
- `user.email` informado

Si falla:

- registrar el error en Make
- opcionalmente enviar email interno de alerta al administrador

#### Paso 4. HTTP - Descargar PDF

- Módulo: **HTTP > Get a file**
- URL construida con la respuesta del paso 2:

```text
https://TU_BASE_URL{{2.pdf.download_url}}
```

Ejemplo resuelto:

```text
https://mi-dominio.com/report-files/informe_diana_example_com_2026-06-19.pdf
```

#### Paso 5. Email - Envío al usuario

- Módulo: **Email / Gmail / Microsoft 365**
- Para: `{{2.user.email}}`
- Asunto sugerido:

```text
Informe financiero trimestral - {{formatDate(now; "YYYY-[Q]Q")}}
```

- Cuerpo sugerido:

```text
Hola {{2.user.name}},

Adjuntamos tu informe financiero trimestral generado automáticamente desde Dashboard_Financiero.

Resumen:
- Portfolio principal: {{2.portfolio.primary_portfolio}}
- Posiciones: {{2.portfolio.position_count}}
- Valor actual estimado: {{2.portfolio.total_current_value}}

Este informe tiene fines académicos y demostrativos.

Saludos.
```

- Adjunto:
  - archivo devuelto por el paso 4
  - nombre sugerido: `{{2.pdf.file_name}}`

#### Paso 6. Registro opcional

Guardar en Google Sheets, Airtable o Data Store:

- fecha de ejecución
- user_id
- email destino
- nombre del PDF
- resultado del envío

---

## 5. Esquema end-to-end del proceso

```text
[Scheduler trimestral en Make]
        |
        v
[POST /api/report/{user_id}]
        |
        v
[FastAPI valida DB y usuario]
        |
        v
[Construcción de snapshots financieros]
        |
        v
[Generación del PDF]
        |
        v
[Persistencia en data/generated_reports]
        |
        v
[Respuesta JSON con pdf.download_url]
        |
        v
[GET /report-files/{file_name} desde Make]
        |
        v
[Email con PDF adjunto al usuario]
        |
        v
[Registro / alerta opcional]
```

---

## 6. Llamada HTTP documentada

### Ejemplo con cURL

```bash
curl -X POST "https://TU_BASE_URL/api/report/1" \
  -H "Accept: application/json"
```

### Ejemplo de interpretación de respuesta

Campos especialmente relevantes para la automatización:

- `status`: debe ser `generated`
- `message`: confirmación funcional
- `user.id`: id del usuario procesado
- `user.name`: nombre para personalizar el email
- `user.email`: destinatario natural del envío
- `portfolio.primary_portfolio`: dato útil para el cuerpo del correo
- `portfolio.position_count`: resumen rápido
- `portfolio.total_current_value`: resumen rápido
- `pdf.file_name`: nombre del adjunto
- `pdf.download_url`: ruta para descargar el binario PDF
- `pdf.generated_at`: trazabilidad
- `pdf.size_bytes`: validación simple
- `warnings`: avisos generados durante el proceso
- `sections`: secciones incluidas en el informe

### Descarga posterior del archivo

```bash
curl -L "https://TU_BASE_URL/report-files/informe_diana_example_com_2026-06-19.pdf" \
  --output informe_trimestral.pdf
```

---

## 7. Envío por email documentado

### Datos mínimos para el email

- **Destinatario:** `user.email`
- **Asunto:** informe financiero trimestral
- **Mensaje:** breve explicación + aviso académico
- **Adjunto:** archivo descargado desde `pdf.download_url`

### Secuencia recomendada del envío

1. Ejecutar `POST /api/report/{user_id}`.
2. Leer `user.email`, `user.name`, `portfolio.*` y `pdf.*`.
3. Descargar el PDF con `GET {BASE_URL}{pdf.download_url}`.
4. Crear email al usuario.
5. Adjuntar el PDF con el nombre `pdf.file_name`.
6. Enviar.
7. Registrar éxito o error.

### Plantilla breve sugerida

**Asunto**

```text
Informe financiero trimestral - Dashboard_Financiero
```

**Cuerpo**

```text
Hola {user.name},

Te enviamos tu informe financiero trimestral generado automáticamente.

Portfolio principal: {portfolio.primary_portfolio}
Posiciones: {portfolio.position_count}
Valor actual estimado: {portfolio.total_current_value}

Adjunto encontrarás el PDF correspondiente.

Aviso: este material tiene fines académicos y demostrativos.
```

---

## 8. Equivalencia breve en Zapier

El flujo equivalente en Zapier sería:

1. **Schedule by Zapier** cada 3 meses.
2. **Webhooks by Zapier - Custom Request** para `POST /api/report/{user_id}`.
3. **Webhooks by Zapier - GET** para descargar `pdf.download_url`.
4. **Gmail / Email by Zapier** para enviar el adjunto.

La lógica es la misma; cambia únicamente la interfaz de configuración.

---

## 9. Notas y límites detectados

1. El endpoint actual genera el informe correctamente, pero **no envía emails por sí mismo**.
2. La automatización depende de que la API esté accesible mediante una **base URL pública o alcanzable** desde Make/Zapier.
3. `pdf.absolute_path` sirve para diagnóstico local, pero para automatización externa debe priorizarse `pdf.download_url`.
4. No se observa autenticación en `POST /api/report/{user_id}`; si se expone a internet, conviene añadir protección en una fase posterior.
5. El endpoint actual no recibe rango temporal ni trimestre como parámetro; la periodicidad la controla exclusivamente la herramienta de automatización.

---

## 10. Resultado esperado de la Fase 10

Queda definido un flujo documentalmente completo para:

- disparar trimestralmente la generación del informe,
- consumir la API existente sin rediseñarla,
- descargar el PDF generado,
- enviarlo por correo al usuario,
- y dejar trazado el proceso de punta a punta.
