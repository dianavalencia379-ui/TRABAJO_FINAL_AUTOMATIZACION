<<<<<<< HEAD
# Dashboard_Financiero

## Resumen general del proyecto

Dashboard_Financiero es una aplicación desarrollada en Python para mostrar, analizar y documentar carteras de inversión de varios usuarios dentro de un entorno académico. El proyecto ya cuenta con una base funcional: tiene una estructura modular, utiliza SQLite como almacenamiento principal, ofrece una interfaz en Streamlit, calcula resúmenes de portfolio, genera una evolución histórica simulada, construye recomendaciones de rebalanceo con HRP, permite descargar informes en PDF y expone una API pensada para automatizaciones externas.

No está planteado como un producto financiero real ni como una herramienta de asesoramiento profesional. Los datos de usuarios, posiciones e históricos están preparados con fines demostrativos, y varias partes del análisis trabajan con datos ficticios o con mecanismos de fallback cuando el entorno no permite acceder a servicios externos.

## Cómo está organizado el sistema

La aplicación se apoya en una estructura bastante clara. En la capa de datos está `data_layer/`, donde se define la base SQLite, la carga inicial de datos y el acceso a históricos de precios. En la capa de dominio están los motores que hacen el trabajo importante: portfolio, evolución, HRP y rebalanceo. Encima de eso aparecen dos salidas principales: la interfaz web construida con Streamlit y la API construida con FastAPI. Además, el proyecto incluye un generador de informes PDF y una carpeta de pruebas automatizadas.

La idea general es sencilla: primero se inicializa la base de datos si hace falta, luego se recupera la información del usuario seleccionado, después se construyen varios snapshots con los datos del portfolio y, a partir de esos snapshots, se alimentan tanto la interfaz como el informe PDF y el endpoint de la API.

## Base de datos y datos iniciales

La persistencia del proyecto está implementada con SQLite. El esquema real trabaja con cuatro tablas principales:

- `users`: guarda los usuarios.
- `portfolios`: guarda los portfolios asociados a cada usuario.
- `positions`: almacena las posiciones de cada portfolio.
- `portfolio_history`: registra la evolución histórica del valor total.
=======
# **Dashboard_Financiero**

    Dashboard_Financiero es una aplicación web financiera desarrollada en Python cuyo objetivo es gestionar y analizar portfolios de inversión de múltiples usuarios.
    
    El proyecto permite demostrar el uso de una base de datos, visualización de datos financieros, cálculo de pesos de cartera, generación de recomendaciones de rebalanceo mediante el método Hierarchical Risk Parity (HRP), creación de informes PDF y automatización del envío trimestral de informes mediante una API.
    
    La aplicación está pensada como un proyecto académico, por lo que los datos utilizados pueden ser ficticios o simulados. Las recomendaciones generadas no constituyen asesoramiento financiero real.

**¿Qué va a hacer la aplicación?**

    La aplicación permitirá seleccionar distintos usuarios, cada uno con su propio portfolio de inversión guardado en base de datos. Al elegir un usuario, el dashboard mostrará la información correspondiente a su cartera.
    
    Las funcionalidades principales serán:
    
    Gestión de varios usuarios.
    Portfolio independiente para cada usuario.
    Almacenamiento de datos en SQLite.
    Visualización del valor total de la cartera.
    Cálculo del peso actual de cada activo.
    Gráficos de composición del portfolio.
    Evolución histórica ficticia de varios años.
    Advisor financiero basado en HRP.
    Tabla de rebalanceo con acciones recomendadas.
    Generación de informes financieros en PDF.
    API preparada para automatización externa con Zapier o Make.
    Arquitectura general
    flowchart TD
            A[Usuario] --> B[Dashboard Streamlit]
            B --> C[(Base de datos SQLite)]
            B --> D[Módulo Portfolio]
            B --> E[Módulo Advisor HRP]
            B --> F[Módulo Evolución Histórica]
            B --> G[Generador PDF]
        
            E --> H[Datos históricos o simulados]
            E --> I[Cálculo de pesos HRP]
            I --> J[Tabla de rebalanceo]
        
            K[Zapier / Make] --> L[API FastAPI]
            L --> C
            L --> G
        Flujo principal
        flowchart LR
            A[Seleccionar usuario] --> B[Consultar portfolio]
            B --> C[Calcular valor y pesos actuales]
            C --> D[Mostrar dashboard]
            D --> E[Ejecutar Advisor HRP]
            E --> F[Generar recomendación]
            F --> G[Crear informe PDF]
    Base de datos
>>>>>>> f530ab5b2edb1d6588171c902f0a0dbf5e100198

La inicialización está resuelta desde `data_layer/db.py` y también puede ejecutarse con `scripts/init_db.py`. Si la base todavía está vacía, el sistema inserta automáticamente datos seed para tres usuarios de ejemplo, cada uno con su portfolio, sus posiciones y un histórico mensual ya calculado.

Ese histórico no viene de mercado real: se genera de forma determinista desde `domain/evolution_engine.py`, lo que permite que la aplicación tenga datos consistentes para demostración y para pruebas.

## Qué hace el módulo de portfolio

El motor de portfolio toma las posiciones almacenadas en SQLite y construye una fotografía consolidada de la cartera. Calcula cantidades, coste total, valor actual estimado y peso porcentual de cada activo dentro del total.

En el estado actual, el valor actual se calcula con una lógica conservadora: `cantidad × precio medio`. Es decir, para esta parte base todavía no se usa un precio de mercado en tiempo real como valor oficial del portfolio. Eso simplifica la coherencia del dashboard y hace que los resultados dependan de datos internos reproducibles.

Además del detalle de posiciones, este módulo prepara resúmenes por portfolio y composiciones agregadas por activo. Esa salida es la que luego aparece en las tablas y gráficos de la app.

## Cómo funciona la evolución histórica

La evolución histórica parte de los registros de `portfolio_history` y genera una serie temporal lista para mostrar en la interfaz y reutilizar en informes. A partir de esa serie, el sistema calcula métricas como:

- rentabilidad acumulada,
- rentabilidad anualizada,
- drawdown máximo,
- drawdown actual,
- mejor y peor periodo.

<<<<<<< HEAD
Como el proyecto es académico, esta evolución está basada en históricos ficticios pero consistentes. Aun así, la implementación no se queda solo en dibujar una línea: realmente transforma la serie en métricas interpretables que luego se reutilizan en la pestaña de evolución, en el resumen general y en el PDF.

## Cómo funciona el advisor HRP

El módulo HRP es una de las piezas más interesantes del proyecto. Su objetivo es proponer pesos objetivo para la cartera usando Hierarchical Risk Parity. Para hacerlo, reúne primero los tickers del usuario, intenta descargar series históricas de precios y, con esos datos, calcula retornos, covarianzas, correlaciones, distancias y el orden jerárquico de clustering.

Después aplica la bisección recursiva propia del enfoque HRP para obtener los pesos recomendados.

Aquí hay un detalle importante: el sistema intenta usar Yahoo Finance cuando se activa esa preferencia, pero si la descarga falla, es parcial o el entorno no dispone de esa dependencia, el proyecto no se rompe. En su lugar utiliza un fallback simulado y deja constancia de ello en los diagnósticos. Esa decisión está bien resuelta para un entorno de entrega, porque mantiene el flujo operativo incluso sin conexión o sin acceso fiable a datos externos.

## Cómo funciona el rebalanceo

Una vez calculados los pesos actuales y los pesos objetivo HRP, entra en juego el motor de rebalanceo. Su función es traducir esa comparación en una recomendación clara para cada activo.

El sistema calcula para cada ticker:

- peso actual,
- peso objetivo,
- diferencia entre ambos,
- valor objetivo,
- delta monetario aproximado,
- acción sugerida.

La acción se clasifica como **Aumentar**, **Reducir** o **Mantener** según un umbral configurable desde la interfaz. Eso hace que la recomendación no se limite a mostrar números, sino que se convierta en una tabla realmente útil para interpretar qué cambios harían falta en la cartera.

## Interfaz web en Streamlit

La aplicación principal vive en `app.py` y está montada con Streamlit. La interfaz ya está separada en pestañas funcionales, lo que da una navegación bastante clara.

### Resumen

La pestaña de resumen muestra la vista ejecutiva del usuario seleccionado: valor estimado, número de posiciones, rentabilidad acumulada, drawdown, señales generales del advisor y una vista rápida de la evolución y de las posiciones principales.

### Portfolio

La pestaña de portfolio enseña la composición de la cartera del usuario, el valor agregado por activo, el valor por portfolio y el detalle completo de posiciones. Aquí se concentra la lectura más operativa de la cartera tal y como está cargada en la base de datos.

### Advisor

La pestaña advisor compara los pesos actuales con los pesos objetivo HRP. Presenta métricas resumidas, un gráfico comparativo y la tabla de rebalanceo. También incluye un bloque de diagnóstico para dejar visible la fuente de precios usada y algunos datos del cálculo.

### Evolución

La pestaña evolución presenta la serie histórica del portfolio junto con la rentabilidad acumulada, la rentabilidad anualizada y el drawdown. También expone el detalle mensual completo para poder revisar la trayectoria del valor de la cartera.

### Informes

La pestaña informes reúne las exportaciones disponibles. Desde ahí se puede descargar el detalle de posiciones en CSV, el advisor en CSV, un resumen en JSON y, si el entorno tiene disponible ReportLab, preparar y descargar el informe PDF.

## Generación de informes PDF

La generación del PDF está implementada en `reports/pdf_generator.py`. No es un simple archivo adjunto improvisado: reutiliza los snapshots ya calculados por el sistema y construye un informe con secciones concretas sobre usuario, portfolio, composición, evolución, pesos actuales, pesos HRP, tabla de rebalanceo, comentario final y aviso académico.

Esto es importante porque asegura coherencia entre lo que se ve en pantalla, lo que devuelve la API y lo que se entrega en el documento final.

También conviene dejar una nota honesta: la generación real del PDF depende de que ReportLab esté instalado y operativo en el entorno. El proyecto contempla esa posibilidad y, si la librería no está disponible, responde con un mensaje claro en vez de fallar de forma silenciosa.

## API y automatización documentada

El proyecto incluye `api.py`, una API en FastAPI con al menos dos piezas principales ya implementadas:

- `GET /health`, para comprobar disponibilidad.
- `POST /api/report/{user_id}`, para generar un informe PDF por usuario.

Ese endpoint inicializa la base si hace falta, valida el usuario, construye los datos necesarios, genera el PDF, lo guarda en `data/generated_reports/` y devuelve metadatos del archivo junto con una URL de descarga.

La automatización trimestral no está implementada dentro del backend como un scheduler interno. Lo que sí está preparado y documentado es el flujo para conectarlo con herramientas externas como Make o Zapier. De hecho, en `docs/Fase_10_Automatizacion_Trimestral.md` ya queda explicado cómo encadenar la llamada al endpoint, la descarga del PDF y el envío por correo.

Dicho de forma práctica: la automatización está resuelta a nivel documental y de contrato técnico de la API, no como un proceso autónomo que ya esté corriendo por sí solo dentro del proyecto.

## Pruebas y validación

El repositorio incluye una batería de pruebas con Pytest para validar varias piezas importantes:

- helpers de configuración y base de datos,
- motor de portfolio,
- motor de evolución,
- motor HRP,
- motor de rebalanceo,
- generador PDF,
- endpoint de la API.

Además, existe un runner principal en `scripts/run_main_test_battery.py` y una documentación específica en `docs/Fase_11_Validacion_Pruebas.md`.

Aquí también conviene ser precisos: el proyecto sí tiene pruebas implementadas y el alcance está bien definido, pero la ejecución real depende del entorno disponible. En la propia documentación ya se reconoce que puede haber diferencias entre versiones instaladas y versiones declaradas, y que ciertas pruebas de API o PDF dependen de disponer de librerías concretas como `httpx` o `reportlab`.

## Calidad del código y mantenibilidad

El código está organizado por responsabilidades y, en general, cada módulo explica bastante bien lo que hace. Hay docstrings en funciones clave, separación entre capa de datos, dominio, interfaz y reportes, y nombres suficientemente descriptivos para entender el flujo sin demasiada fricción.

Eso ayuda mucho en una entrega académica, porque no solo se ve que la aplicación funciona por partes, sino también que el proyecto se puede leer, mantener y ampliar con relativa facilidad.

## Estado real del proyecto

Viendo el código y la documentación actual, el proyecto ya tiene implementadas las piezas centrales que se esperaban para la entrega:

- estructura base modular,
- persistencia con SQLite,
- gestión de usuarios y portfolios,
- cálculo de composición y pesos,
- evolución histórica,
- advisor HRP,
- tabla de rebalanceo,
- interfaz en Streamlit,
- generación de PDF,
- API para informes,
- automatización externa documentada,
- batería de pruebas,
- código comentado con docstrings y separación por módulos.

Lo que queda condicionado no es tanto el diseño del proyecto como algunos aspectos de ejecución real del entorno: uso de Yahoo Finance, disponibilidad de ReportLab y consistencia exacta de dependencias para correr toda la batería de pruebas sin ajustes adicionales.

## Cierre

En conjunto, Dashboard_Financiero ya no es solo una idea de fases futuras, sino una base funcional bastante completa para demostrar un flujo financiero end to end: datos persistidos, análisis de cartera, evolución temporal, recomendación de rebalanceo, visualización web, exportación documental y exposición por API.

Para una entrega académica, el resultado es sólido porque conecta varias piezas reales de ingeniería de software sin ocultar sus límites: trabaja con datos demostrativos, reconoce dependencias del entorno y deja documentado qué partes son plenamente operativas y cuáles dependen de librerías o servicios externos.
=======
Este proyecto se desarrolla con fines educativos.
Los datos pueden ser ficticios o simulados.
Las recomendaciones del Advisor HRP no deben interpretarse como asesoramiento financiero profesional.
>>>>>>> f530ab5b2edb1d6588171c902f0a0dbf5e100198
