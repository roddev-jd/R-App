# Instrucciones de Uso - Listador de Carpetas

## 🚀 Inicio Rápido

### 1. Instalación
```bash
# Instalar dependencias
python3 install.py

# O manualmente:
python3 -m pip install -r requirements.txt
```

### 2. Ejecutar la Aplicación
```bash
# Opción 1: Ejecutar directamente
python3 folder_listing_app.py

# Opción 2: Usar script de inicio
python3 run_app.py
```

### 3. Demostración
```bash
# Crear carpetas de ejemplo
python3 demo_folders.py

# Luego ejecutar la aplicación y seleccionar la carpeta "demo_folders"
```

## 📋 Uso de la Aplicación

### Paso 1: Seleccionar Directorio
1. Hacer clic en el botón **"Examinar"**
2. Navegar hasta el directorio que contiene las carpetas a listar
3. Seleccionar el directorio y hacer clic en **"Abrir"**

### Paso 2: Configurar Nombre del Archivo (Opcional)
- El nombre por defecto es `carpetas_listadas.xlsx`
- Puedes cambiarlo antes de procesar

### Paso 3: Generar Excel
1. Hacer clic en **"Generar Lista de Carpetas"**
2. Esperar a que se complete el proceso
3. El archivo Excel se guardará en el mismo directorio seleccionado

## 📊 Estructura del Excel Generado

| SKU |
|-----|
| 1   |
| 2   |
| 123 |
| 456 |

### Características de la Columna SKU:
- **Extrae números** del nombre de la carpeta (ej: "Producto123" → 123)
- **Números secuenciales** si no hay números en el nombre
- **Formato numérico** en Excel (no texto)

## ⚙️ Configuración

Puedes personalizar la aplicación editando `config.py`:

### Interfaz
```python
UI_CONFIG = {
    "theme": "dark",  # "dark" o "light"
    "color_theme": "blue",  # "blue", "green", "dark-blue"
    "window_size": "600x400"
}
```

### Procesamiento
```python
PROCESSING_CONFIG = {
    "extract_numbers_from_names": True,  # Extraer números de nombres
    "use_sequential_numbers": True,      # Usar números secuenciales
    "sort_folders": True,               # Ordenar alfabéticamente
    "case_sensitive": False             # No distinguir mayúsculas
}
```

### Excel
```python
EXCEL_CONFIG = {
    "default_filename": "carpetas_listadas.xlsx",
    "sheet_name": "Carpetas",
    "sku_column_name": "SKU",
    "folder_column_name": "Nombre_Carpeta"
}
```

## 🧪 Pruebas

### Ejecutar Pruebas Automáticas
```bash
python3 test_app.py
```

### Crear Carpetas de Prueba
```bash
python3 demo_folders.py
```

## 📁 Estructura del Proyecto

```
index/
├── folder_listing_app.py    # Aplicación principal
├── config.py               # Configuración
├── requirements.txt        # Dependencias
├── install.py             # Script de instalación
├── run_app.py             # Script de inicio
├── test_app.py            # Pruebas automáticas
├── demo_folders.py        # Generador de carpetas de ejemplo
├── demo_folders/          # Carpetas de demostración
├── README.md              # Documentación
└── INSTRUCCIONES.md       # Este archivo
```

## 🔧 Solución de Problemas

### Error: "No se encontró pip"
```bash
# En macOS/Linux
python3 -m pip install -r requirements.txt

# En Windows
py -m pip install -r requirements.txt
```

### Error: "No tienes permisos"
- Verifica que tienes permisos de lectura en el directorio
- En macOS, puede necesitar permisos de Terminal

### Error: "No se encontraron carpetas"
- Asegúrate de que el directorio contiene carpetas (no solo archivos)
- Verifica que no estás seleccionando un archivo

### Error al guardar Excel
- Verifica permisos de escritura en el directorio
- Cierra el archivo Excel si está abierto en otra aplicación

## 🎯 Ejemplos de Uso

### Ejemplo 1: Listar Productos
```
Directorio: /Productos/
Carpetas: Producto001, Producto002, Producto123
Resultado: SKU 1, 2, 123
```

### Ejemplo 2: Listar Categorías
```
Directorio: /Categorías/
Carpetas: Ropa, Zapatos, Accesorios
Resultado: SKU 1, 2, 3 (secuencial)
```

### Ejemplo 3: Listar Inventario
```
Directorio: /Inventario/
Carpetas: Item100, Item200, ItemABC
Resultado: SKU 100, 200, 3 (secuencial para ABC)
```

## 📞 Soporte

Si encuentras problemas:
1. Ejecuta `python3 test_app.py` para verificar la instalación
2. Revisa los mensajes de error en la interfaz
3. Verifica que todas las dependencias estén instaladas
4. Asegúrate de tener permisos en el directorio seleccionado 