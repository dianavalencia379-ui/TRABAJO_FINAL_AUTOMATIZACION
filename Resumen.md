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

La base de datos se organizará en cuatro tablas principales:

erDiagram
    USERS ||--o{ PORTFOLIOS : tiene
    PORTFOLIOS ||--o{ POSITIONS : contiene
    PORTFOLIOS ||--o{ PORTFOLIO_HISTORY : registra

    USERS {
        int id
        string name
        string email
        datetime created_at
    }

    PORTFOLIOS {
        int id
        int user_id
        string name
        datetime created_at
    }

    POSITIONS {
        int id
        int portfolio_id
        string ticker
        string asset_name
        float quantity
        float avg_price
    }

    PORTFOLIO_HISTORY {
        int id
        int portfolio_id
        date date
        float total_value
    }
Tecnologías utilizadas
Tecnología	Uso
Python	Lenguaje principal
Streamlit	Interfaz web
SQLite	Base de datos
Pandas	Tratamiento de datos
NumPy	Cálculos numéricos
SciPy	Cálculo HRP y clustering
Plotly	Gráficos interactivos
yfinance	Datos históricos de mercado
ReportLab	Generación de PDF
FastAPI	API para automatización
Pytest	Pruebas unitarias
Resultado esperado

Al finalizar el proyecto se tendrá una aplicación web funcional capaz de gestionar varios usuarios y portfolios desde una base de datos. Cada usuario podrá consultar su cartera, ver su evolución histórica, recibir una recomendación de rebalanceo mediante HRP y generar un informe financiero en PDF.

Además, el proyecto incluirá una API preparada para que una herramienta externa como Zapier o Make pueda solicitar el informe de forma automática cada tres meses y enviarlo al correo del usuario.

Aviso académico

Este proyecto se desarrolla con fines educativos.
Los datos pueden ser ficticios o simulados.
Las recomendaciones del Advisor HRP no deben interpretarse como asesoramiento financiero profesional.
