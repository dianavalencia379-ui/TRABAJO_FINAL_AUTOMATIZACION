# Calendario de Trabajo - Dashboard Financiero (Sprint Intensivo)

Este documento detalla la planificación temporal, el reparto de responsabilidades y la estrategia de colaboración para un equipo de **8 personas**, adaptada para comenzar **hoy (20 de junio de 2026)**. Consiste en un **sprint intensivo de 4 días** estructurado para que las 12 fases del proyecto se completen antes de la fecha límite oficial: **23 de junio de 2026 a las 23:59**.

---

## 1. Distribución del Equipo y Roles

Para garantizar un desarrollo progresivo y una participación individual clara y justificable (15% de la nota), se han distribuido los roles del proyecto entre los 8 integrantes:

| Integrante | Rol Principal | Enfoque en el Sprint |
| :--- | :--- | :--- |
| **Diana Marcela Valencia Garcia** | **Coordinadora, Release Manager & Editora** | Gestión del plan de trabajo, orquestación de ramas en GitHub, revisión de Pull Requests para merge a `develop`/`main` y compilación de la memoria grupal. |
| **Antonio Jose Ruiz Jimenez** | **Quant Developer & Lógica Financiera** | Desarrollo y calibración del algoritmo HRP (clustering, bisección de varianza), cálculo de rentabilidades y motor del reequilibrio. |
| **Darío Ruiz Abrante** | **Backend & Database Developer** | Estructuración del esquema SQLite, diseño de consultas e índices optimizados, y carga de datos iniciales estables (seed data). |
| **Jimy Alexander Arias Vasco** | **UI Lead Developer (Streamlit)** | Estructura base de `app.py`, pestañas principales de Resumen y Portfolio, y diseño UX general de la aplicación. |
| **Joaquin Gonzalez Garcia** | **Interactive UI Developer** | Integración de gráficos dinámicos con Plotly para la visualización de la composición y la evolución histórica del portfolio. |
| **Johanna Valencia Rozo** | **PDF Report Specialist (ReportLab)** | Implementación de `pdf_generator.py` mediante ReportLab, maquetación del informe financiero apaisado y su sistema de tablas. |
| **Jhuliana Tuesta Pintado** | **API & Automation Engineer** | Desarrollo del servidor FastAPI (`api.py`), integración de endpoints de descarga e informes, y documentación del flujo con Zapier/Make. |
| **José Luis Martínez Pardo** | **QA & Testing Engineer** | Diseño y codificación de la suite de pruebas automatizadas con Pytest (cobertura matemática de HRP y APIs), alineación del entorno local y QA. |

---

## 2. Cronograma del Sprint (Fases 1 a 12)

El sprint de 4 días distribuye los entregables de manera paralela para maximizar la productividad:

```mermaid
gantt
    title Plan de Trabajo (8 personas) - Dashboard Financiero
    dateFormat  YYYY-MM-DD
    axisFormat %d-%b
    
    section Día 1 (20 Jun)
    Fase 1: Prep. Entorno        :active, des1, 2026-06-20, 2026-06-20
    Fase 2: SQLite & Semillero   :active, des2, 2026-06-20, 2026-06-21
    Fase 3: Motor de Cartera     :des3, 2026-06-20, 2026-06-21
    
    section Día 2 (21 Jun)
    Fase 4: Evolución Histórica  :des4, 2026-06-21, 2026-06-21
    Fase 5: Algoritmo HRP        :des5, 2026-06-21, 2026-06-22
    Fase 6: Advisor Rebalanceo   :des6, 2026-06-21, 2026-06-22
    
    section Día 3 (22 Jun)
    Fase 7: Interfaz Streamlit   :des7, 2026-06-22, 2026-06-22
    Fase 8: Generador PDF        :des8, 2026-06-22, 2026-06-23
    Fase 9: API FastAPI          :des9, 2026-06-22, 2026-06-23
    
    section Día 4 (23 Jun)
    Fase 10: Automatización      :des10, 2026-06-23, 2026-06-23
    Fase 11: Batería de Pruebas  :des11, 2026-06-23, 2026-06-23
    Fase 12: Memoria & Cierre    :des12, 2026-06-23, 2026-06-24
```

### Día 1: Sábado 20 de junio - Cimientos y Persistencia
*   **Fase 1: Preparación del proyecto**
    *   *Tareas:* Creación de la estructura del repositorio local, alineación del entorno virtual (`.venv` en Python 3.12) y sincronización del manifiesto de `requirements.txt`.
    *   *Responsables:* Diana Marcela Valencia Garcia (Coordinación) y José Luis Martínez Pardo (Alineación técnica).
*   **Fase 2: Base de datos**
    *   *Tareas:* Diseño físico del esquema SQLite en `data_layer/db.py` (creación de tablas, constraints e índices) y script de inicialización `scripts/init_db.py`.
    *   *Responsables:* Darío Ruiz Abrante.
*   **Fase 3: Motor de cartera**
    *   *Tareas:* Codificación de `domain/portfolio_engine.py` para consolidar cantidades de activos, costes, valores actuales y cálculo de pesos en el portfolio.
    *   *Responsables:* Darío Ruiz Abrante (Estructura de datos) y Antonio Jose Ruiz Jimenez (Validación financiera).

### Día 2: Domingo 21 de junio - Algoritmos Financieros y Rebalanceo
*   **Fase 4: Evolución histórica**
    *   *Tareas:* Desarrollo de `domain/evolution_engine.py` para construir series históricas deterministas estables e interpretar métricas clave (Max Drawdown, rentabilidad acumulada/anualizada).
    *   *Responsables:* Antonio Jose Ruiz Jimenez y Darío Ruiz Abrante.
*   **Fase 5: Motor HRP**
    *   *Tareas:* Codificación matemática en `domain/hrp_engine.py` del algoritmo *Hierarchical Risk Parity* (cálculo de retornos, distancias, clustering jerárquico y bisección recursiva de pesos). Conexión externa y fallback local en `data_layer/yahoo_client.py`.
    *   *Responsables:* Antonio Jose Ruiz Jimenez.
*   **Fase 6: Advisor de rebalanceo**
    *   *Tareas:* Desarrollo de `domain/rebalance_engine.py` para clasificar las acciones requeridas sobre la cartera (Aumentar, Reducir, Mantener) según la desviación porcentual tolerada.
    *   *Responsables:* Antonio Jose Ruiz Jimenez.

### Día 3: Lunes 22 de junio - Interfaz de Usuario, Gráficos y PDF/API
*   **Fase 7: Interfaz Streamlit**
    *   *Tareas:* Desarrollo de la UI interactiva en `app.py` y archivos de soporte bajo `ui/`. Integración de gráficos dinámicos de Plotly para composición de activos e histórico.
    *   *Responsables:* Jimy Alexander Arias Vasco (Diseño general y tabs) y Joaquin Gonzalez Garcia (Integración de Plotly y gráficos interactivos).
*   **Fase 8: Informes PDF**
    *   *Tareas:* Creación de `reports/pdf_generator.py` para estructurar el reporte apaisado en A4 mediante ReportLab, incluyendo tablas estilizadas y sumario dinámico del advisor.
    *   *Responsables:* Johanna Valencia Rozo y Joaquin Gonzalez Garcia (Apoyo en diseño).
*   **Fase 9: API**
    *   *Tareas:* Desarrollo de la API FastAPI en `api.py` para exponer el endpoint `POST /api/report/{user_id}` y montar la carpeta estática para la descarga de PDFs.
    *   *Responsables:* Jhuliana Tuesta Pintado.

### Día 4: Martes 23 de junio (Entrega) - Integraciones, Tests y Documentación
*   **Fase 10: Automatización trimestral**
    *   *Tareas:* Diseño documental del flujo en Make / Zapier para disparar la API, descargar el PDF y enviar por email. Redacción de `docs/Fase_10_Automatizacion_Trimestral.md`.
    *   *Responsables:* Jhuliana Tuesta Pintado y Diana Marcela Valencia Garcia.
*   **Fase 11: Batería de pruebas**
    *   *Tareas:* Redacción de test suite con Pytest en `tests/` para validar la lógica del motor de cartera, HRP y rebalanceo, logrando paso limpio del runtime.
    *   *Responsables:* José Luis Martínez Pardo.
*   **Fase 12: Memoria final**
    *   *Tareas:* Redacción de la memoria académica global (introducción, arquitectura, diagramas e HRP). Recopilación de los registros individuales de commits de cada participante (Anexo).
    *   *Responsables:* Diana Marcela Valencia Garcia (Redacción jefe & compilación) y todos los integrantes (Anexo individual).
*   **Hito Cierre (20:00 - 23:59):** Integración de `develop` en `main`, tag de versión final `v1.0.0` y subida definitiva del repositorio de GitHub junto con el documento PDF de la memoria.

---

## 3. Matriz RACI del Proyecto (8 Personas)

*   **R** (Responsible): Quien ejecuta la tarea.
*   **A** (Accountable): Quien valida, responde del entregable y autoriza el PR.
*   **C** (Consulted): Quienes asesoran o aportan código de soporte.
*   **I** (Informed): Quienes reciben actualizaciones sobre la funcionalidad finalizada.

| Fase / Entregable | Diana V. (Coordinadora) | Antonio R. (Quant) | Darío R. (Backend) | Jimy A. (UI Lead) | Joaquin G. (Plots) | Johanna V. (PDF) | Jhuliana T. (API) | José M. (QA) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fase 1: Prep. Entorno** | **A / R** | I | I | I | I | I | I | **R** |
| **Fase 2: Base de Datos** | A | C | **R** | I | I | I | C | I |
| **Fase 3: Motor Cartera** | A | C | **R** | I | I | I | I | C |
| **Fase 4: Evolución** | A | **R** | C | I | I | I | I | I |
| **Fase 5: Motor HRP** | I | **A / R** | I | I | I | I | I | C |
| **Fase 6: Rebalanceo** | I | **A / R** | I | I | I | I | I | I |
| **Fase 7: Interfaz Web** | A | C | I | **R** | **R** | I | I | I |
| **Fase 8: Informes PDF** | A | I | I | I | C | **R** | I | I |
| **Fase 9: API FastAPI** | A | I | I | I | I | C | **R** | I |
| **Fase 10: Automatización** | **C** | I | I | I | I | I | **R** | I |
| **Fase 11: Pruebas (Pytest)** | I | C | C | I | I | I | C | **A / R** |
| **Fase 12: Memoria Final** | **A / R** | C | C | C | C | C | C | C |

---

## 4. Política de GitHub y Ramas

Para cumplir con las buenas prácticas de Git evaluadas con un 15%:

1.  **Rama develop:** Todos los integrantes realizarán *Pull Requests (PR)* a `develop`. Queda bloqueada la escritura directa en `main`.
2.  **Ramas de características:**
    *   `feature/db-setup` (Darío Ruiz)
    *   `feature/hrp-engine` (Antonio Ruiz)
    *   `feature/streamlit-ui` (Jimy Arias & Joaquin Gonzalez)
    *   `feature/pdf-api` (Johanna Valencia & Jhuliana Tuesta)
    *   `feature/test-suite` (José Martínez)
    *   `feature/docs-memory` (Diana Valencia)
3.  **Aprobaciones:** Diana Marcela Valencia Garcia (Release Manager) revisará y aprobará formalmente las integraciones en `develop` tras recibir la confirmación de tests exitosos por parte de José Luis Martínez Pardo.
4.  **Tag Final:** El 23 de junio a las 20:00 se unirá `develop` a `main`, marcando la versión definitiva con el tag `v1.0.0` para entrega formal.
