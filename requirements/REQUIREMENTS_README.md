# Guía de Dependencias - App_SUITE v2.0.3

Esta guía explica los diferentes archivos de requirements del proyecto y cómo utilizarlos.

## 📋 Archivos de Requirements

### 1. `requirements.txt` (Principal)
**Uso recomendado para:** Instalación estándar del proyecto

Incluye todas las dependencias necesarias para ejecutar:
- ✅ Backend central (FastAPI Gateway)
- ✅ Aplicación Reportes
- ✅ Aplicación Prod Peru
- ✅ Launcher Web
- ✅ Módulos compartidos (shared)
- ✅ Sistema de métricas

**NO incluye:** Herramientas de diseño específicas

```bash
pip install -r requirements.txt
```

### 2. `requirements-minimal.txt` (Producción)
**Uso recomendado para:** Despliegue en servidores de producción

Versión mínima sin dependencias de desarrollo o UI del launcher.
Ideal para:
- Servidores web/cloud
- Contenedores Docker
- Entornos serverless

```bash
pip install -r requirements-minimal.txt
```

### 3. `requirements-dev.txt` (Desarrollo)
**Uso recomendado para:** Desarrollo activo del proyecto

Incluye todas las dependencias de `requirements.txt` más:
- Herramientas de testing (pytest, coverage)
- Linters y formatters (black, flake8, pylint)
- Debugging tools (ipython, ipdb)
- Dependencias opcionales completas

```bash
pip install -r requirements-dev.txt
```

### 4. `FlexStart/requirements_server.txt` (Legacy)
Archivo legacy mantenido por compatibilidad.
**Recomendación:** Usar `requirements.txt` en su lugar.

### 5. `launcher_web/requirements.txt` (Launcher)
Dependencias específicas del launcher web.
Ya incluidas en `requirements.txt`.

---

## 🎨 Herramientas de Diseño

Las herramientas de diseño tienen **requirements independientes** y NO están incluidos en los archivos principales:

```
FlexStart/apps/diseno/
├── INDEXAR/requirements.txt
├── MULTITAG/requirements.txt
├── APP_CARGAS_CHILE/requirements.txt
└── APP_CARGAS_PERU/requirements.txt
```

Para instalar dependencias de una herramienta específica:

```bash
# Ejemplo: INDEXAR
pip install -r FlexStart/apps/diseno/INDEXAR/requirements.txt

# Ejemplo: MULTITAG
pip install -r FlexStart/apps/diseno/MULTITAG/requirements.txt
```

**Razón de la separación:**
- Las herramientas de diseño tienen dependencias pesadas (PyQt6, PySide6, OpenCV)
- No son necesarias para ejecutar el servidor principal
- Se ejecutan como procesos separados

---

## 🚀 Guía de Instalación Rápida

### Instalación para Usuario Final
```bash
# 1. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias principales
pip install -r requirements.txt

# 3. Verificar instalación
python verify_dependencies.py
```

### Instalación para Desarrollo
```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate

# 2. Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# 3. Instalar herramientas de diseño específicas (si las necesitas)
pip install -r FlexStart/apps/diseno/INDEXAR/requirements.txt

# 4. Verificar instalación
python verify_dependencies.py
```

### Instalación para Producción (Servidor)
```bash
# 1. Usar requirements mínimos
pip install -r requirements-minimal.txt

# 2. Ejecutar servidor
uvicorn FlexStart.backend.app:app --host 0.0.0.0 --port 8005 --workers 4
```

---

## 🔍 Verificación de Dependencias

Ejecuta el script de verificación para confirmar que todo está instalado:

```bash
python verify_dependencies.py
```

Este script muestra:
- ✓ Dependencias críticas instaladas
- ✓ Versiones de cada paquete
- ⚠ Advertencias sobre dependencias opcionales faltantes
- ✗ Errores si faltan dependencias requeridas

---

## 📦 Dependencias Principales por Categoría

### Framework Web
- `fastapi` - Framework web moderno
- `uvicorn` - Servidor ASGI
- `pydantic` - Validación de datos
- `starlette` - Toolkit ASGI
- `jinja2` - Motor de plantillas

### Procesamiento de Datos
- `pandas` - Análisis de datos
- `duckdb` - Base de datos columnar rápida
- `pyarrow` - Serialización de datos
- `openpyxl` - Lectura/escritura Excel
- `xlsxwriter` - Escritura Excel optimizada

### Cloud & Storage
- `azure-storage-blob` - Azure Blob Storage (Reportes - Chile)
- `boto3` - AWS S3 (Prod Peru)
- `msal` - Microsoft Authentication (SharePoint)

### Utilidades
- `requests` - Cliente HTTP
- `aiohttp` - Cliente HTTP asíncrono
- `keyring` - Gestión segura de credenciales
- `psutil` - Información de procesos
- `packaging` - Manejo de versiones

### UI Desktop (Launcher)
- `customtkinter` - UI moderna para launcher
- `Pillow` - Procesamiento de imágenes

---

## 🔧 Comandos de Desarrollo Comunes

### Actualizar todas las dependencias
```bash
pip install --upgrade -r requirements.txt
```

### Generar requirements desde el entorno actual
```bash
pip freeze > requirements-freeze.txt
```

### Comparar versiones instaladas
```bash
pip list --outdated
```

### Instalar una dependencia específica
```bash
pip install nombre-paquete==version
```

---

## ⚠️ Notas Importantes

1. **Entorno Virtual Recomendado**
   - Siempre usa un entorno virtual (venv, virtualenv, conda)
   - Evita conflictos con otros proyectos

2. **Versiones Mínimas**
   - Los archivos usan `>=` para permitir actualizaciones compatibles
   - Prueba antes de actualizar a versiones mayores (breaking changes)

3. **Compatibilidad Python**
   - Versión mínima recomendada: Python 3.8+
   - Versión recomendada: Python 3.10+

4. **Dependencias del Sistema**
   - Algunas librerías requieren dependencias del sistema operativo
   - Ejemplo: `Pillow` puede requerir libjpeg, libpng en Linux

5. **Herramientas de Diseño**
   - Solo instala dependencias de herramientas que vayas a usar
   - PyQt6/PySide6 son paquetes grandes (~100MB+)

---

## 🆘 Solución de Problemas

### Error: "No module named 'fastapi'"
```bash
# Verifica que estés en el entorno virtual correcto
which python
pip install -r requirements.txt
```

### Error: "Could not find a version that satisfies the requirement"
```bash
# Actualiza pip
pip install --upgrade pip
# Reintenta instalación
pip install -r requirements.txt
```

### Error: "Microsoft Visual C++ required" (Windows)
- Instala Visual C++ Build Tools
- O usa versiones pre-compiladas: `pip install --only-binary :all: nombre-paquete`

### Error: Conflictos de versiones
```bash
# Limpia caché de pip
pip cache purge
# Reinstala en entorno limpio
pip install --force-reinstall -r requirements.txt
```

---

## 📝 Mantenimiento

### Actualizar requirements.txt
Cuando agregues nuevas dependencias:

1. Agrégalas a `requirements.txt` en la categoría apropiada
2. Si es opcional, agrégala a `requirements-dev.txt`
3. Actualiza `verify_dependencies.py` con la nueva dependencia
4. Documenta en este README si es necesario

### Política de Versiones
- **Dependencias críticas:** Versionado explícito (`package==1.2.3`)
- **Dependencias estables:** Versión mínima (`package>=1.2.0`)
- **Desarrollo:** Sin restricciones de versión (latest)

---

## 📞 Soporte

Si encuentras problemas con dependencias:
1. Verifica con `python verify_dependencies.py`
2. Revisa los logs de instalación
3. Consulta la documentación del paquete específico
4. Crea un issue con detalles del error

---

**Última actualización:** 2025-12-05
**Versión del proyecto:** 2.0.3
**Mantenedor:** Ripley Product & Category Team
