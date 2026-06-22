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

*(Nota: Espacio reservado para los informes del resto de integrantes: Diana V., Darío R., Jimy A., José M., Johanna V. y Jhuliana T.)*
