# Explorador Interactivo del DENUE

Un dashboard geoespacial de alto rendimiento construido con Python y Dash para la visualización y el análisis interactivo de las unidades económicas de México, utilizando los datos del Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI.

Esta aplicación transforma los masivos archivos de datos del DENUE en una herramienta visual rápida y responsiva, permitiendo a los usuarios explorar la distribución y características de millones de negocios en un mapa interactivo.

[Aquí puedes añadir una captura de pantalla o un GIF animado de la aplicación en funcionamiento.]


## 🚀 Características Principales

* **Visualización en Mapa Interactivo:** Utiliza `Dash Leaflet` para representar hasta 10,000 puntos de datos de manera fluida, coloreados según la categoría de personal ocupado.
* **Filtros Dinámicos en Cascada:** Permite filtrar las unidades económicas por Estado, Municipio y por la clasificación industrial SCIAN (Sector, Subsector, Rama, etc.).
* **Rendimiento Optimizado:**
    * **Backend Eficiente:** Usa **DuckDB** para realizar consultas increíblemente rápidas sobre el conjunto de datos completo.
    * **Muestreo Inteligente:** Aunque los cálculos y la gráfica de resumen se basan en el 100% de los datos filtrados, solo se envía una muestra aleatoria de 10,000 puntos al mapa para garantizar una experiencia de usuario fluida y sin bloqueos.
* **Interactividad Total:**
    * **Información al Instante:** Haz clic en cualquier punto del mapa para ver los detalles específicos de esa unidad económica (nombre, actividad, personal, código SCIAN).
    * **Tooltips Informativos:** Pasa el cursor sobre cualquier punto para ver su nombre y actividad económica.
    * **Ajuste de Vista Automático:** El mapa se centra y se ajusta automáticamente para mostrar todos los datos cargados.

## 🛠️ Tecnologías Utilizadas

* **Backend y Lógica:** Python, Dash (`DashProxy` de `dash-extensions`)
* **Base de Datos:** DuckDB
* **Análisis de Datos:** Pandas, GeoPandas
* **Visualización:**
    * **Mapa:** Dash Leaflet
    * **Gráficas:** Plotly Express
* **Entorno de Desarrollo:** Conda (Miniforge)

## ⚙️ Instalación y Ejecución Local

Para ejecutar esta aplicación en tu propia máquina, sigue estos pasos:

**Requisitos:**
* Tener **Miniforge** o **Anaconda** instalado.
* Tener todos los archivos del proyecto (`app.py`, `requirements.txt`, etc.) en una carpeta.

1.  **Abrir la Terminal**
    * En Windows, abre el "Miniforge Prompt".
    * En macOS o Linux, abre tu terminal.

2.  **Navegar al Directorio del Proyecto**
    ```bash
    cd ruta/a/tu/carpeta/denue_dashboard
    ```

3.  **Crear y Activar el Ambiente de Conda**
    ```bash
    # Crear el ambiente con Python 3.12
    conda create --name denue_env python=3.12 -y

    # Activar el ambiente
    conda activate denue_env
    ```

4.  **Instalar las Dependencias**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Ejecutar la Aplicación**
    ```bash
    python app.py
    ```

6.  **Abrir en el Navegador**
    * Abre tu navegador web y ve a la dirección que aparece en la terminal (normalmente `http://127.0.0.1:8050/`).
