"""
Archivo de configuración para el Listador de Carpetas
"""

# Configuración de la interfaz
UI_CONFIG = {
    "window_title": "Listador de Carpetas - Generador Excel",
    "window_size": "600x500",
    "theme": "dark",  # "dark" o "light"
    "color_theme": "blue",  # "blue", "green", "dark-blue"
    "font_size_title": 24,
    "font_size_normal": 14,
    "font_size_small": 12
}

# Configuración del Excel
EXCEL_CONFIG = {
    "default_filename": "carpetas_listadas.xlsx",
    "sheet_name": "Carpetas",
    "sku_column_name": "SKU",
    "number_format": "0"  # Formato de número entero
}

# Configuración de procesamiento
PROCESSING_CONFIG = {
    "extract_numbers_from_names": True,  # Extraer números de nombres de carpetas
    "use_sequential_numbers": True,  # Usar números secuenciales si no hay números
    "sort_folders": True,  # Ordenar carpetas alfabéticamente
    "case_sensitive": False  # No distinguir mayúsculas/minúsculas
}

# Mensajes de la interfaz
MESSAGES = {
    "select_directory": "Seleccionar directorio para listar carpetas",
    "no_directory_selected": "Por favor selecciona un directorio",
    "directory_not_exists": "El directorio seleccionado no existe",
    "no_folders_found": "No se encontraron carpetas en el directorio seleccionado",
    "permission_error": "No tienes permisos para acceder al directorio seleccionado",
    "read_error": "Error al leer el directorio",
    "process_error": "Error durante el procesamiento",
    "success_title": "Éxito",
    "success_message": "Archivo Excel generado exitosamente!",
    "error_title": "Error",
    "warning_title": "Advertencia"
} 