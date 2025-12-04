# APP CARGAS

Aplicación Python para comparar nombres de carpetas con datos en Azure Blob Storage y generar reportes Excel.

## Funcionalidad

La aplicación:
1. Permite seleccionar una ubicación que contiene carpetas
2. Se conecta a Azure Blob Storage para descargar el archivo `tabla_wop_completa.csv`
3. Compara los nombres de las carpetas con los valores en la columna `sku_hijo_largo`
4. Genera un archivo Excel con dos hojas:
   - **Hoja 1 (Coincidencias Relacionadas)**: Incluye las coincidencias exactas más todos los registros que comparten el mismo `sku_padre_largo` y `color`
   - **Hoja 2 (Coincidencias Exactas)**: Solo las coincidencias exactas entre nombres de carpetas y `sku_hijo_largo`

## Características Mejoradas

✅ **Interfaz No Bloqueante**: La aplicación utiliza threading para evitar que la interfaz se congele durante el procesamiento

✅ **Visor de Eventos en Tiempo Real**: Muestra todos los eventos del procesamiento con timestamps para seguimiento detallado

✅ **Barra de Progreso**: Indica el progreso del procesamiento con porcentajes y estados descriptivos

✅ **Feedback Visual**: El botón se deshabilita durante el procesamiento y se muestra el estado actual

✅ **Logging Detallado**: Información completa sobre cada paso del proceso:
- Conexión a Azure Blob Storage
- Descarga del CSV
- Escaneo de carpetas
- Búsqueda de coincidencias
- Generación del archivo Excel

## Instalación

1. Asegúrate de tener Python 3.7+ instalado
2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración de Azure

La aplicación buscará las credenciales de Azure en el siguiente orden:
1. Llavero del sistema (keyring)
2. Variable de entorno `AZURE_STORAGE_CONNECTION_STRING`
3. Credenciales hardcodeadas (como respaldo)

Para configurar las credenciales en el llavero del sistema:
```python
import keyring
keyring.set_password("azure_storage", "blobaac", "tu_connection_string_aqui")
```

## Uso

1. Ejecuta la aplicación:
```bash
python app_cargas.py
```

2. En la interfaz:
   - Haz clic en "Seleccionar" para elegir la ubicación de las carpetas
   - Haz clic en "Procesar y Generar Reporte"
   - El archivo Excel se generará en el mismo directorio de la aplicación

## Estructura del Proyecto

```
APP_CARGAS/
├── app_cargas.py          # Aplicación principal
├── requirements.txt       # Dependencias
└── README.md             # Este archivo
```

## Datos de Azure Blob

- **Container URL**: https://blobaac.blob.core.windows.net/datascience
- **Archivo CSV**: tabla_wop_completa.csv
- **Columna de comparación**: sku_hijo_largo
- **Columnas relacionadas**: sku_padre_largo, color