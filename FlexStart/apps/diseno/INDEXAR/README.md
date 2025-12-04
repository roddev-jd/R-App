# Listador de Carpetas - Generador Excel

Una aplicación Python con interfaz gráfica que lista todas las carpetas de un directorio seleccionado y las guarda en un archivo Excel con formato de números SKU.

## Características

- **Interfaz gráfica moderna** usando CustomTkinter
- **Selección de directorio** mediante diálogo de archivos
- **Generación automática de Excel** con formato de números
- **Columna SKU** con valores numéricos
- **Interfaz en español** completamente localizada
- **Manejo de errores** robusto
- **Información en tiempo real** del proceso

## Instalación

1. **Clonar o descargar** el proyecto
2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

1. **Ejecutar la aplicación**:
   ```bash
   python folder_listing_app.py
   ```

2. **Seleccionar directorio**:
   - Hacer clic en "Examinar"
   - Navegar y seleccionar el directorio que contiene las carpetas a listar

3. **Configurar nombre del archivo** (opcional):
   - El nombre por defecto es "carpetas_listadas.xlsx"
   - Puedes cambiarlo antes de procesar

4. **Generar Excel**:
   - Hacer clic en "Generar Lista de Carpetas"
   - El archivo se guardará en el mismo directorio seleccionado

## Estructura del Excel

El archivo Excel generado contiene solo la columna SKU:

| SKU |
|-----|
| 1   |
| 2   |
| 123 |

### Formato de la columna SKU:
- **Números extraídos** del nombre de la carpeta (si contiene dígitos)
- **Números secuenciales** si no hay dígitos en el nombre
- **Formato numérico** en Excel (no texto)

## Dependencias

- `customtkinter==5.2.0` - Interfaz gráfica moderna
- `openpyxl==3.1.2` - Manipulación de archivos Excel
- `pandas==2.1.4` - Procesamiento de datos

## Características técnicas

- **Compatibilidad**: Windows, macOS, Linux
- **Python**: 3.7+
- **Interfaz**: Tema oscuro por defecto
- **Manejo de errores**: Permisos, directorios inexistentes, etc.
- **Información en tiempo real**: Log de operaciones en la interfaz

## Ejemplo de uso

1. Tienes un directorio con carpetas de productos:
   ```
   /Productos/
   ├── Producto001
   ├── Producto002
   ├── ProductoABC
   └── Producto123
   ```

2. Al procesar, obtienes un Excel con:
   ```
   SKU | Nombre_Carpeta
   1    | Producto001
   2    | Producto002
   3    | ProductoABC
   123  | Producto123
   ```

## Solución de problemas

### Error de permisos
- Verifica que tienes permisos de lectura en el directorio seleccionado

### No se encuentran carpetas
- Asegúrate de que el directorio contiene carpetas (no solo archivos)

### Error al guardar Excel
- Verifica que tienes permisos de escritura en el directorio
- Asegúrate de que el archivo Excel no esté abierto en otra aplicación

## Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT. 