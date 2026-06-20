# Guía de Configuración Local en Antigravity IDE

Esta guía detalla el proceso paso a paso para que cada uno de los 7 componentes del equipo configure su entorno de desarrollo local dentro de **Antigravity IDE** y pueda trabajar en sus tareas individuales de forma alineada.

---

## Paso 1: Apertura del Espacio de Trabajo
1. Abre **Antigravity IDE**.
2. Ve a `File` -> `Open Workspace from File...` y selecciona el archivo de espacio de trabajo raíz:
   ```text
   Proyecto.code-workspace
   ```
3. Esto cargará la estructura del proyecto y configurará los directorios de trabajo correctos.

---

## Paso 2: Creación del Entorno Virtual y Dependencias
El proyecto utiliza **`uv`** como gestor rápido de paquetes y entornos virtuales de Python. Sigue estos comandos en la terminal integrada de Antigravity (PowerShell/Bash):

1. **Crear el entorno virtual** `.venv` con Python 3.12 (versión estable recomendada para asegurar compatibilidad con NumPy 2.4, Pandas 3.0 y SciPy 1.18):
   ```bash
   uv venv --python 3.12
   .venv\Scripts\activate (linux) o bien .venv\Scripts\activate.ps1 (windows)
   ```
2. **Instalar y sincronizar dependencias** desde el manifiesto `requirements.txt`:
   ```bash
   uv pip install -r requirements.txt
   ```
   *Nota: Esto instalará automáticamente `streamlit`, `fastapi`, `reportlab`, `pytest`, `httpx` y el resto de librerías del proyecto.*

---

## Paso 3: Configuración del Archivo de Entorno (`.env`)
El proyecto requiere variables de entorno mínimas para su ejecución y para simular llamadas HRP:

1. Copia el archivo de ejemplo `.env.example` y nómbralo `.env`:
   ```bash
   cp .env.example .env
   ```
2. Abre el archivo `.env` recién creado y asegúrate de que tiene la variable de mapeo correspondiente:
   ```env
   API_KEY_ENV_VAR=GEMINI_API_KEY
   GEMINI_API_KEY=tu_clave_api_aqui
   ```
   *(La clave se puede dejar vacía para las pruebas locales con datos simulados de fallback).*

---

## Paso 4: Inicialización de la Base de Datos SQLite
Para precargar los 3 usuarios de demostración (`Diana Valencia`, `Antonio Ruiz` y `Jose Martinez`) junto con sus portafolios, posiciones y el histórico ficticio:

1. Ejecuta el script de inicialización en la terminal:
   ```bash
   uv run python -m scripts.init_db
   ```
2. Esto creará el archivo de base de datos en `data/dashboard_financiero.db` y las carpetas requeridas.

---

## Paso 5: Verificación del Entorno (Batería de Tests)
Para asegurar que toda la lógica de negocio y las dependencias están correctamente configuradas, ejecuta la batería de pruebas:

```bash
uv run pytest
```
*Deberían pasar los **28 tests unitarios y de integración** sin fallos ni advertencias de importación.*

---

## Paso 6: Ejecución de las Aplicaciones

### A. Dashboard Streamlit (Interfaz de Usuario)
Para interactuar con el panel financiero de forma visual:
```bash
uv run streamlit run app.py
```
*La aplicación se abrirá por defecto en `http://localhost:8501`.*

### B. Servidor API FastAPI (Automatización)
Para interactuar con los endpoints de la API (para llamadas desde Make/Zapier):
```bash
uv run uvicorn api:app --reload
```
*El servidor de desarrollo se levantará en `http://localhost:8000`. Puedes consultar la documentación interactiva en `http://localhost:8000/docs`.*

---

## Paso 7: Flujo de Trabajo y Política de GitHub
De acuerdo con el plan del proyecto, se prohíbe subir cambios directamente a la rama `main`. Sigue esta secuencia para añadir tus contribuciones:

1. **Crear tu rama de característica** desde `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/tu-caracteristica
   ```
2. **Realizar cambios y commits descriptivos:**
   ```bash
   git add .
   git commit -m "Explicación breve y clara de los cambios realizados"
   ```
3. **Subir tu rama al repositorio remoto:**
   ```bash
   git push origin feature/tu-caracteristica
   ```
4. **Abrir Pull Request (PR):** Crea un Pull Request de tu rama apuntando a la rama `develop`. El PR será revisado por la Release Manager (**Diana Valencia**) y aprobado tras verificar el paso exitoso de los tests locales.
