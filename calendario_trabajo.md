# Calendario de Trabajo - Dashboard Financiero (Sprint Intensivo)

Este documento detalla la planificación temporal, el reparto de responsabilidades y la estrategia de colaboración para un equipo de **7 personas**, adaptada para comenzar **hoy (20 de junio de 2026)**. Consiste en un **sprint intensivo de 4 días** estructurado para que las 12 fases del proyecto se completen antes de la fecha límite oficial: **23 de junio de 2026 a las 23:59**.

---

## 1. Distribución del Equipo y Roles

Tras la salida de José Luis Martínez Pardo, los roles y responsabilidades individuales del proyecto se han redistribuido entre los 7 integrantes restantes del equipo:

| Integrante | Rol Principal | Enfoque en el Sprint |
| :--- | :--- | :--- |
| **Diana Marcela Valencia Garcia** | **Coordinadora, Release Manager & Editora** | Gestión del plan de trabajo, orquestación de ramas en GitHub, revisión y aprobación de Pull Requests, y compilación final de la memoria. |
| **Antonio Jose Ruiz Jimenez** | **Quant Developer & Lógica Financiera** | Desarrollo y calibración del algoritmo HRP (clustering, bisección de varianza), cálculo de rentabilidades, motor del reequilibrio y alineación del entorno técnico. |
| **Darío Ruiz Abrante** | **Backend & Testing Developer** | Estructuración del esquema SQLite (seed data), diseño del motor de cartera básico, y desarrollo del suite de pruebas automatizadas en Pytest. |
| **Jimy Alexander Arias Vasco** | **UI Lead Developer (Streamlit)** | Estructura base de `app.py`, pestañas principales de Resumen y Portfolio, y diseño UX general de la aplicación. |
| **Joaquin Gonzalez Garcia** | **Interactive UI Developer** | Integración de gráficos dinámicos con Plotly para la visualización de la composición y la evolución histórica del portfolio. |
| **Johanna Valencia Rozo** | **PDF Report Specialist (ReportLab)** | Implementación de `pdf_generator.py` mediante ReportLab, maquetación del informe financiero apaisado y su sistema de tablas. |
| **Jhuliana Tuesta Pintado** | **API & Automation Engineer** | Desarrollo del servidor FastAPI (`api.py`), integración de endpoints de descarga e informes, y documentación del flujo con Zapier/Make. |

---

## 2. Cronograma del Sprint (Fases 1 a 12)

El sprint de 4 días distribuye los entregables de manera paralela para maximizar la productividad:

| Día | Fecha | Fases de Desarrollo | Hito Clave |
| :--- | :--- | :--- | :--- |
| **Día 1** | Sábado 20 de junio | **Fase 1:** Preparación del Entorno<br>**Fase 2:** SQLite & Semillero de datos<br>**Fase 3:** Motor de Cartera básico | Base de datos creada con seed de demostración y cálculos de pesos actuales operativos. |
| **Día 2** | Domingo 21 de junio | **Fase 4:** Evolución Histórica Ficticia<br>**Fase 5:** Motor de Optimización HRP<br>**Fase 6:** Advisor de Rebalanceo | Motores financieros HRP y rebalanceo 100% calibrados con fallback a simulación. |
| **Día 3** | Lunes 22 de junio | **Fase 7:** Interfaz Streamlit (Pestañas)<br>**Fase 8:** Generador de PDF (ReportLab)<br>**Fase 9:** API FastAPI (Endpoints) | Interfaz web Streamlit operativa y API local lista para generar reportes en PDF. |
| **Día 4** | Martes 23 de junio *(Entrega)* | **Fase 10:** Automatización (Zapier/Make)<br>**Fase 11:** Cobertura de Pruebas (Pytest)<br>**Fase 12:** Memoria Académica & Cierre | Integración estable en `main`, tag de versión `v1.0.0` y subida del repositorio final. |

### Día 1: Sábado 20 de junio - Cimientos y Persistencia
*   **Fase 1: Preparación del proyecto**
    *   *Tareas:* Creación de la estructura del repositorio local, alineación del entorno virtual (`.venv` en Python 3.12) y sincronización del manifiesto de `requirements.txt`.
    *   *Responsables:* Diana Marcela Valencia Garcia (Coordinación) y Antonio Jose Ruiz Jimenez (Alineación técnica).
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
    *   *Responsables:* Antonio Jose Ruiz Jimenez y Johanna Valencia Rozo (Soporte y revisión).
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
    *   *Responsables:* Darío Ruiz Abrante (Desarrollo de pruebas) y Diana Marcela Valencia Garcia (Aprobación y aseguramiento).
*   **Fase 12: Memoria final**
    *   *Tareas:* Redacción de la memoria académica global (introducción, arquitectura, diagramas e HRP). Recopilación de los registros individuales de commits de cada participante (Anexo).
    *   *Responsables:* Todos los integrantes (Colaboración en redacción y anexos individuales).
*   **Hito Cierre (20:00 - 23:59):** Integración de `develop` en `main`, tag de versión final `v1.0.0` y subida definitiva del repositorio de GitHub junto con el documento PDF de la memoria.

---

## 3. Matriz RACI del Proyecto (7 Personas)

*   **R** (Responsible): Quien ejecuta la tarea.
*   **A** (Accountable): Quien valida, responde del entregable y autoriza el PR.
*   **C** (Consulted): Quienes asesoran o aportan código de soporte.
*   **I** (Informed): Quienes reciben actualizaciones sobre la funcionalidad finalizada.

| Fase / Entregable | Diana V. (Coordinadora) | Antonio R. (Quant) | Darío R. (Backend/QA) | Jimy A. (UI Lead) | Joaquin G. (Plots) | Johanna V. (PDF) | Jhuliana T. (API) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fase 1: Prep. Entorno** | **A** | **R** | I | I | I | I | I |
| **Fase 2: Base de Datos** | A | C | **R** | I | I | I | C |
| **Fase 3: Motor Cartera** | A | C | **R** | **C** | I | I | I |
| **Fase 4: Evolución** | A | **R** | C | I | I | I | I | I |
| **Fase 5: Motor HRP** | I | **A / R** | I | I | I | **C** | I |
| **Fase 6: Rebalanceo** | I | **A / R** | I | I | I | I | I | I |
| **Fase 7: Interfaz Web** | A | C | I | **R** | **R** | I | I | I |
| **Fase 8: Informes PDF** | A | I | I | I | C | **R** | I |
| **Fase 9: API FastAPI** | A | I | I | I | I | C | **R** |
| **Fase 10: Automatización** | **C** | I | I | I | I | I | **R** |
| **Fase 11: Pruebas (Pytest)** | **A** | C | **R** | I | I | I | C |
| **Fase 12: Memoria Final** | **C** | **C** | **C** | **C** | **C** | **C** | **C** |

---

## 4. Política de GitHub y Ramas

Para cumplir con las buenas prácticas de Git evaluadas con un 15%:

1.  **Rama develop:** Todos los integrantes realizarán *Pull Requests (PR)* a `develop`. Queda bloqueada la escritura directa en `main`.
2.  **Ramas de características:**
    *   `feature/db-setup` (Darío Ruiz)
    *   `feature/hrp-engine` (Antonio Ruiz)
    *   `feature/streamlit-ui` (Jimy Arias & Joaquin Gonzalez)
    *   `feature/pdf-api` (Johanna Valencia & Jhuliana Tuesta)
    *   `feature/test-suite` (Darío Ruiz)
    *   `feature/docs-memory` (Diana Valencia)
3.  **Aprobaciones:** Diana Marcela Valencia Garcia (Release Manager) revisará y aprobará formalmente las integraciones en `develop` tras recibir la confirmación de tests exitosos por parte de Darío Ruiz Abrante.
4.  **Tag Final:** El 23 de junio a las 20:00 se unirá `develop` a `main`, marcando la versión definitiva con el tag `v1.0.0` para entrega formal.
