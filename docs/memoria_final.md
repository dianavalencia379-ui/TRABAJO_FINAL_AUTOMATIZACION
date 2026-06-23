# Memoria de Proyecto: Dashboard Financiero Colectivo

**Asignatura:** Automatización de Procesos Financieros  
**Máster en IA para Finanzas**  
**Fecha de Entrega:** 23 de junio de 2026  

---

## Portada e Integrantes del Equipo

*   **Coordinadora, Release Manager & Editora:** Diana Marcela Valencia Garcia
*   **Quant Developer & Lógica Financiera:** Antonio Jose Ruiz Jimenez
*   **Backend & Testing Developer:** Darío Ruiz Abrante
*   **UI Lead Developer (Streamlit):** Jimy Alexander Arias Vasco
*   **Interactive UI Developer (Plotly):** José Luis Martínez Pardo
*   **PDF Report Specialist (ReportLab):** Johanna Valencia Rozo
*   **API & Automation Engineer (FastAPI):** Jhuliana Tuesta Pintado

---

## 1. Descripción General del Proyecto

`Dashboard_Financiero` es una aplicación web multiusuario orientada a la gestión, visualización y análisis de carteras de inversión. Permite a los usuarios consultar la composición actual de su cartera, analizar su evolución histórica, optimizar los pesos de sus activos mediante el algoritmo **Hierarchical Risk Parity (HRP)** y generar informes detallados en formato PDF de forma automatizada.

El sistema se conecta en tiempo real con proveedores de datos financieros (Yahoo Finance) y expone una API estructurada pensada para integrarse con herramientas de automatización externa (como Make o Zapier) para la generación y envío periódico de informes de cartera.

---

## 2. Objetivos del Proyecto

### Objetivo General
Desarrollar una solución tecnológica integrada y multiusuario para la gestión, optimización y reporte automatizado de carteras de inversión, aplicando metodologías cuantitativas y herramientas de automatización de procesos financieros.

### Objetivos Específicos
1.  **Persistencia:** Diseñar una base de datos local SQLite para registrar usuarios, portafolios, posiciones históricas y la evolución consolidada.
2.  **Optimización Cuantitativa:** Implementar el algoritmo HRP (*Hierarchical Risk Parity*) para proponer asignaciones de activos eficientes basadas en la correlación jerárquica y el riesgo implícito.
3.  **Visualización Interactiva:** Construir una interfaz gráfica responsiva en Streamlit con visualizaciones dinámicas de la composición de activos e históricos de evolución.
4.  **Generación de Reportes:** Desarrollar un motor de maquetación en PDF mediante ReportLab que consolide el estado financiero del usuario y las recomendaciones del asesor.
5.  **API y Automatización:** Exponer endpoints REST con FastAPI que permitan disparar la creación de informes y su envío automático desde plataformas externas.
6.  **Calidad de Software:** Conseguir un entorno de pruebas robusto con Pytest para validar el 100% de la lógica de negocio cuantitativa.

---

## 3. Metodología de Trabajo y Planificación

El equipo ha utilizado una metodología ágil tipo **Sprint Intensivo de 4 días** (del 20 de junio al 23 de junio de 2026), distribuyendo las tareas de desarrollo en paralelo de la siguiente forma:

### Matriz RACI del Proyecto
*   **R** (Responsible): Quien ejecuta la tarea.
*   **A** (Accountable): Quien valida, responde del entregable y autoriza el PR.
*   **C** (Consulted): Quienes asesoran o aportan código.
*   **I** (Informed): Quienes reciben actualizaciones.

| Fase / Entregable | Diana V. | Antonio R. | Darío R. | Jimy A. | José M. | Johanna V. | Jhuliana T. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fase 1: Prep. Entorno** | **A** | **R** | I | I | I | I | I |
| **Fase 2: Base de Datos** | A | C | **R** | I | I | I | C |
| **Fase 3: Motor Cartera** | A | C | **R** | **C** | I | I | I |
| **Fase 4: Evolución** | A | **R** | C | I | I | I | I |
| **Fase 5: Motor HRP** | I | **A / R** | I | I | I | **C** | I |
| **Fase 6: Rebalanceo** | I | **A / R** | I | I | I | I | I |
| **Fase 7: Interfaz Web** | A | C | I | **R** | **R** | I | I |
| **Fase 8: Informes PDF** | A | I | I | I | C | **R** | I |
| **Fase 9: API FastAPI** | A | I | I | I | I | C | **R** |
| **Fase 10: Automatización** | **C** | I | I | I | I | I | **R** |
| **Fase 11: Pruebas (Pytest)** | **A** | C | **R** | I | I | I | C |
| **Fase 12: Memoria Final** | **C** | **C** | **C** | **C** | **C** | **C** | **C** |

### Flujo de Git y GitHub
Se ha implementado una política estricta de protección de ramas:
1.  **`main`**: Solo código estable de producción. Bloqueada para subida directa.
2.  **`develop`**: Rama de integración diaria.
3.  **`feature/*`**: Ramas de desarrollo temporal donde trabaja cada programador. Las fusiones se realizan mediante Pull Request (PR) validados por la Release Manager tras superar la suite de tests.

---

## 4. Arquitectura y Organización del Sistema

El proyecto sigue una arquitectura limpia estructurada por capas funcionales:

```text
Dashboard_Financiero/
├── Proyecto.code-workspace   # Configuración de entorno y extensiones de Antigravity
├── .python-version           # Anclaje de la versión de Python (3.12.13)
├── app.py                    # Interfaz gráfica Streamlit
├── api.py                    # Servidor API FastAPI
├── config.py                 # Carga de entornos y gestión de API keys (.env)
├── requirements.txt          # Manifiesto de dependencias bloqueadas
├── data_layer/               # PERSISTENCIA Y CONEXIONES DE DATOS
│   ├── db.py                 # Conexión SQLite y esquema de tablas
│   ├── yahoo_client.py       # Descarga real de Yahoo Finance con fallback para tests
│   └── seed_data.py          # Script de inserción de datos de prueba
├── domain/                   # LÓGICA DE NEGOCIO CUANTITATIVA
│   ├── portfolio_engine.py   # Consolidación de cartera y pesos actuales
│   ├── evolution_engine.py   # Cálculo de rentabilidad y drawdowns
│   ├── hrp_engine.py         # Algoritmo matemático Hierarchical Risk Parity
│   └── rebalance_engine.py   # Advisor de reequilibrio de activos
├── ui/                       # COMPONENTES VISUALES DE STREAMLIT
├── reports/                  # GENERACIÓN DE REPORTES PDF
│   └── pdf_generator.py      # Estructura del PDF en ReportLab
├── scripts/                  # SCRIPTS DE VALIDACIÓN Y CONTROL
└── tests/                    # PRUEBAS AUTOMATIZADAS (28 TESTS)
```

---

## 5. Explicación Funcional y Técnica de los Módulos

### 5.1. Persistencia (SQLite)
El sistema gestiona la información a través de 4 tablas principales:
*   `users`: Datos identificativos del usuario.
*   `portfolios`: Carteras asociadas a cada cuenta.
*   `positions`: Cantidad y coste medio de los activos.
*   `portfolio_history`: Registro mensual de evolución histórica del valor total.

### 5.2. Módulo Asesor HRP (Hierarchical Risk Parity)
Diseñado e implementado para evitar la inestabilidad de la optimización media-varianza clásica de Markowitz. El proceso matemático consta de:
1.  **Retornos e Históricos**: Descarga de precios reales de Yahoo Finance y conversión a series de rentabilidades diarias.
2.  **Matriz de Distancia**: Conversión de la matriz de correlación en distancias métricas ($d_{i,j} = \sqrt{\frac{1-\rho_{i,j}}{2}}$).
3.  **Clustering Jerárquico**: Agrupamiento de activos utilizando el método de enlace simple (*single linkage*).
4.  **Bisección Recursiva**: Reparto de pesos inversamente proporcionales a la varianza a lo largo de las ramas del árbol jerárquico obtenido.

### 5.3. Advisor de Rebalanceo
Compara la distribución de pesos del portfolio actual del usuario frente a los pesos recomendados por HRP. Aplica una señal de decisión según un umbral porcentual configurable:
*   Diferencia $> \text{Umbral}$: **Aumentar** posición.
*   Diferencia $< -\text{Umbral}$: **Reducir** posición.
*   En otro caso: **Mantener** posición.

---

## 6. Mejoras e Innovaciones Implementadas

1.  **Garantía de Datos Reales en Producción**: Se eliminó la simulación por defecto en entornos productivos. El sistema requiere e intenta siempre la conexión real con Yahoo Finance, lanzando excepciones explícitas y controladas en caso de fallos de red.
2.  **Entorno Hermético para Tests**: Se mockeó la descarga de precios de Yahoo Finance en el entorno de pruebas, garantizando que el suite de Pytest sea rápido, seguro y funcione al 100% de manera offline.
3.  **Anclaje de Entorno**: Configuración unificada de `.python-version` y `Proyecto.code-workspace` para garantizar que todo el equipo utilice exactamente la misma versión de Python (3.12.13) en Antigravity IDE.

---

## 7. Conclusiones y Aprendizajes

*   *El uso del algoritmo HRP demuestra cómo los métodos de agrupamiento jerárquico aplicados a finanzas mejoran la estabilidad en la asignación de carteras sin depender de optimizadores cuadráticos propensos a errores.*
*   *La estructuración modular y las políticas estrictas de Git Flow en GitHub han sido críticas para evitar conflictos entre los desarrolladores del backend, del frontend y del motor financiero.*

---

## Anexo: Informes de Participación Individual

### Anexo A: Informe de Antonio Jose Ruiz Jimenez (Quant Lead)
*   **Participación Específica:** Lógica financiera y optimización cuantitativa.
*   **Funcionalidades Desarrolladas:** 
    *   Calibración del motor matemático HRP (`hrp_engine.py`).
    *   Diseño del motor de rebalanceo (`rebalance_engine.py`) y del gestor de evolución histórica (`evolution_engine.py`).
    *   Ajuste del cliente de Yahoo Finance (`yahoo_client.py`) para obligar el uso de datos de mercado reales offline y online.
    *   Co-creación del archivo `.python-version` y el espacio de trabajo relativo de Antigravity.
*   **Evidencias de Commits:** Commits firmados bajo el usuario `antonio` con prefijos `feat` y `chore` vinculados a la lógica financiera.
*   **Problemas y Soluciones:** Solución del fallo de importación `ModuleNotFoundError` al ejecutar scripts de inicialización, documentando el uso de `python -m scripts.init_db` en la guía oficial.
*   **Reflexión Personal:** *El desarrollo colaborativo me ha permitido comprender cómo integrar cálculos numéricos complejos de SciPy/NumPy en flujos visuales (Streamlit) y APIs (FastAPI) de forma estable y testeada.*

### Anexo B: Informe de Diana Marcela Valencia Garcia (Coordinadora, Release Manager & Editora)

* **Participación Específica:** Coordinación técnica del proyecto, revisión del repositorio, gestión documental y apoyo en la validación del código, entorno y pruebas antes de la entrega final.

* **Funcionalidades Desarrolladas:**

  * Creación y mantenimiento de la documentación principal del proyecto en `README.md`, incluyendo descripción general, arquitectura, tecnologías, fases de trabajo y checklist de entrega.
  * Revisión de la coherencia entre la memoria, el calendario de trabajo y la estructura real del repositorio.
  * Participación en la configuración del entorno mediante ajustes en `.env.example`, `config.py` y documentación de dependencias.
  * Actualización de datos de prueba en `data_layer/seed_data.py`, especialmente los asociados al usuario de demostración.
  * Revisión de scripts de validación como `validate_hrp_engine.py` y `validate_rebalance_engine.py`.
  * Apoyo en la comprobación de tests automatizados en `tests/`, verificando que la aplicación funcionara de forma integrada.
  * Revisión de artefactos generados, como la base de datos local y los reportes PDF de demostración.

* **Evidencias de Commits:** Commits firmados bajo el usuario `dianavalencia379-ui`, vinculados principalmente a documentación, configuración del entorno, datos semilla, scripts de validación, pruebas y revisión general del proyecto.

* **Problemas y Soluciones:** Durante el desarrollo se detectaron desajustes entre documentación, entorno local, dependencias y pruebas. Diana participó en la revisión y corrección de estos puntos, ayudando a mantener la coherencia entre el código, los datos de prueba y la memoria final.

* **Reflexión Personal:** *Mi participación me ha permitido comprender la importancia de la coordinación técnica en un proyecto colaborativo. Además de organizar el trabajo y revisar la documentación final, he podido participar en la validación del entorno, los datos de prueba y los tests, asegurando que el proyecto entregado fuera coherente y funcional.*

### Anexo C: Informe de Darío Ruiz Abrante (Backend & Testing Developer)

* **Participación Específica:** Desarrollo backend, persistencia de datos, validación de motores principales y pruebas automatizadas del sistema.

* **Funcionalidades Desarrolladas:**

  * Diseño inicial de la base de datos SQLite y scripts de inicialización del proyecto.
  * Implementación y revisión del esquema de datos en `data_layer/db.py`.
  * Desarrollo de datos de prueba y validaciones asociadas a los motores de cartera y evolución.
  * Apoyo en el desarrollo del motor de cartera básico (`portfolio_engine.py`), calculando posiciones, valores y pesos actuales.
  * Incorporación y posterior ajuste de restricciones de integridad en SQLite.
  * Desarrollo y revisión de pruebas automatizadas con Pytest para validar la lógica principal del proyecto.
  * Participación en la comprobación de motores financieros, incluyendo validaciones del HRP y del rebalanceo.

* **Evidencias de Commits:** Commits firmados bajo el usuario `darioruiz1725-ai`, vinculados a la configuración inicial de base de datos, scripts de validación, restricciones SQLite, pruebas y mejoras de lógica financiera.

* **Problemas y Soluciones:** Durante el desarrollo se detectó que algunas restricciones de SQLite podían generar conflictos con la evolución del esquema. Darío participó en la incorporación, revisión y reversión de dichas restricciones, priorizando la estabilidad de la base de datos y la compatibilidad con los tests.

* **Reflexión Personal:** *Mi participación me ha permitido comprender la importancia de una base de datos bien estructurada y de una batería de pruebas fiable en un proyecto financiero. El uso de SQLite, scripts de validación y Pytest ha sido clave para asegurar que la aplicación funcionara de forma estable antes de la entrega.*

### Anexo D: Informe de Jimy Alexander Arias Vasco (UI Lead Developer - Streamlit)

* **Participación Específica:** Desarrollo de la interfaz principal en Streamlit, mejora de la experiencia de usuario y apoyo en la integración visual del dashboard.

* **Funcionalidades Desarrolladas:**

  * Desarrollo y mejora de la estructura visual de la aplicación en Streamlit.
  * Participación en la pestaña de resumen ejecutivo, incorporando métricas más claras para el usuario.
  * Rediseño de elementos visuales mediante tarjetas HTML, avisos y presentación más ordenada de resultados.
  * Mejora de la visualización de drawdown, mejor/peor periodo y métricas de rebalanceo.
  * Apoyo en la integración de información financiera dentro de la interfaz, evitando que los resultados aparecieran como tablas crudas.
  * Participación en ajustes de compatibilidad visual y correcciones de presentación en la aplicación.

* **Evidencias de Commits:** Participación visible bajo el usuario `jimyarias-gif` en la rama `feature/streamlit-ui`, con aportaciones relacionadas con rediseño visual, alertas de drawdown, tarjetas de resumen y mejoras de UX. También aparece participación posterior en una rama de automatización API para exponer una URL pública de descarga del PDF.

* **Problemas y Soluciones:** Uno de los principales retos fue transformar los resultados financieros en una interfaz entendible para un usuario no técnico. Para solucionarlo, se sustituyeron salidas demasiado tabulares por tarjetas, indicadores y mensajes visuales más claros.

* **Reflexión Personal:** *El desarrollo de la interfaz me ha permitido comprender cómo traducir cálculos financieros complejos en una experiencia visual clara y usable. La parte más importante ha sido conseguir que el usuario pudiera interpretar rápidamente el estado de su cartera, los riesgos y las recomendaciones de rebalanceo.*

### Anexo E: Informe de José Luis Martínez Pardo (Interactive UI Developer - Plotly)

* **Participación Específica:** Desarrollo de componentes interactivos de interfaz, apoyo en visualización de datos financieros y ajustes de dependencias necesarias para la representación gráfica.

* **Funcionalidades Desarrolladas:**

  * Modificación y mejora de la pestaña de portfolio (`tab_portfolio.py`).
  * Revisión de la pestaña de asesor financiero (`tab_advisor.py`), vinculada a la presentación de pesos actuales, pesos HRP y recomendaciones.
  * Actualización de `requirements.txt` para asegurar que las librerías necesarias para visualización estuvieran incluidas.
  * Apoyo en la integración de gráficos y elementos interactivos para representar la composición y evolución de la cartera.
  * Revisión de la coherencia visual entre los resultados del motor financiero y la presentación final en Streamlit.

* **Evidencias de Commits:** Commits firmados bajo el usuario `josemartinezpardo1-design`, asociados a cambios en `tab_portfolio.py`, `tab_advisor.py` y `requirements.txt`.

* **Problemas y Soluciones:** Durante el desarrollo fue necesario ajustar la presentación de los datos financieros para que los resultados del portfolio y del asesor HRP fueran comprensibles. José contribuyó a mejorar la estructura visual y a revisar las dependencias necesarias para que los gráficos y componentes interactivos funcionaran correctamente.

* **Reflexión Personal:** *Mi participación me ha permitido profundizar en la importancia de la visualización interactiva dentro de una aplicación financiera. No basta con calcular correctamente los datos: también es necesario presentarlos de forma clara, ordenada y útil para que el usuario pueda tomar decisiones.*

### Anexo F: Informe de Johanna Valencia Rozo (PDF Report Specialist - ReportLab)

* **Participación Específica:** Apoyo en la generación de informes PDF, revisión de salidas documentales y colaboración en la integración de resultados financieros dentro del reporte final.

* **Funcionalidades Desarrolladas:**

  * Participación en la fase de informes PDF mediante ReportLab.
  * Revisión del formato de salida del informe financiero generado automáticamente.
  * Apoyo en la inclusión de información de cartera, evolución histórica, pesos HRP y recomendaciones de rebalanceo dentro del reporte.
  * Colaboración en la comprobación de que los informes fueran útiles como entregable académico y como salida automatizable.
  * Apoyo puntual en la revisión del motor HRP y de la coherencia de los resultados mostrados en los informes.

* **Evidencias de Commits:** Commits firmados bajo el usuario `johannarozo`, con aportaciones visibles en el historial del repositorio. Aunque los mensajes de commit son poco descriptivos, su rol queda asociado en la memoria y el calendario a la fase de generación de informes PDF mediante ReportLab.

* **Problemas y Soluciones:** Uno de los retos principales fue convertir los resultados de la aplicación en un documento PDF claro y presentable. Johanna participó en la revisión de la estructura del informe, asegurando que la salida generada incluyera la información financiera relevante y pudiera integrarse en el flujo de automatización.

* **Reflexión Personal:** *Mi participación me ha permitido comprender la importancia de los informes automáticos dentro de un proyecto financiero. La generación del PDF permite que los resultados del dashboard no se queden solo en la aplicación, sino que puedan entregarse, almacenarse o enviarse automáticamente al usuario final.*

### Anexo G: Informe de Jhuliana Tuesta Pintado (API & Automation Engineer - FastAPI)

* **Participación Específica:** Desarrollo y documentación de la API del proyecto, integración con herramientas externas y diseño del flujo de automatización para la generación periódica de informes.

* **Funcionalidades Desarrolladas:**

  * Participación en el desarrollo del servidor FastAPI (`api.py`) para exponer endpoints de generación de informes.
  * Definición del endpoint principal de reporte, orientado a generar el PDF financiero de un usuario concreto.
  * Apoyo en la integración entre la API, la base de datos y el generador de informes PDF.
  * Diseño del flujo de automatización trimestral mediante herramientas externas como Zapier o Make.
  * Documentación del proceso: llamada HTTP a la API, generación del PDF y envío automático del informe por correo.
  * Revisión de la compatibilidad del flujo de automatización con la estructura final del proyecto.

* **Evidencias de Commits:** Su participación queda documentada en la memoria y en el calendario de trabajo como responsable de API y automatización. En el historial público revisado no aparece un usuario de GitHub claramente identificable con su nombre, por lo que su contribución se refleja como participación funcional dentro del módulo `api.py` y la documentación del flujo Zapier/Make.

* **Problemas y Soluciones:** El principal reto fue plantear una automatización externa realista para un proyecto ejecutado en local. Para resolverlo, se diseñó un flujo basado en una petición HTTP desde Zapier o Make hacia FastAPI, con generación del PDF y posterior envío del informe como adjunto.

* **Reflexión Personal:** *Mi participación me ha permitido comprender cómo una aplicación financiera puede conectarse con herramientas externas de automatización. La integración con FastAPI, Zapier o Make demuestra cómo los informes pueden generarse de forma periódica sin intervención manual, acercando el proyecto a un caso de uso real.*
