# App_SUITE Launcher

Launcher profesional para App_SUITE con interfaz moderna, gestión automática de puertos y sistema de actualizaciones.

## Características

✨ **Puerto Rotativo Automático** (8005-8050)
- Selección automática de puerto disponible en cada ejecución
- Evita conflictos cuando múltiples instancias intentan usar el mismo puerto
- Persistencia del último puerto usado

🖥️ **Monitor de Sistema en Tiempo Real**
- Uso de CPU del servidor
- Uso de memoria (porcentaje y GB)
- Tiempo de actividad (uptime)
- PID del proceso

🔄 **Sistema de Actualizaciones Automáticas**
- Detección de nuevas versiones desde GitHub releases
- Notificaciones cuando hay actualizaciones disponibles
- Descarga e instalación con barra de progreso
- Backup automático antes de actualizar

↩️ **Rollback Simple**
- Mantiene respaldo de la versión anterior
- Permite volver atrás si hay problemas
- Restauración con un solo clic

🎨 **Interfaz Moderna**
- Diseño con customtkinter
- Colores coherentes con el frontend de App_SUITE
- Compatible con macOS y Windows
- Modo claro/oscuro automático

## Instalación

### 1. Verificar Python

Requiere Python 3.10 o superior:

```bash
python3 --version
```

### 2. Instalar Dependencias

```bash
pip install -r requirements_server.txt
```

O instalar manualmente:

```bash
pip install customtkinter psutil packaging Pillow requests fastapi uvicorn
```

## Uso

### Iniciar el Launcher

```bash
python3 launcher.py
```

O si es ejecutable:

```bash
./launcher.py
```

### Primera Ejecución

1. El launcher se abrirá en una ventana de 700x600px
2. Click en **"Start Server"** para iniciar FastAPI
3. El navegador se abrirá automáticamente en `http://127.0.0.1:{puerto}`
4. El puerto será seleccionado automáticamente (rotación)

### Operaciones Comunes

**Iniciar Servidor:**
- Click en botón "Start Server" (rosa)
- Puerto se selecciona automáticamente
- Navegador se abre automáticamente

**Detener Servidor:**
- Click en botón "Stop Server" (rojo)
- Detención graceful con fallback a force kill

**Reabrir Navegador:**
- Click en botón "Reopen Browser" (cyan)
- Solo disponible cuando servidor está corriendo

**Chequear Actualizaciones:**
- Click en "Check for Updates"
- Se verifica contra GitHub releases
- Notificación si hay actualización disponible

**Actualizar Aplicación:**
- Click en "Update to v{version}" cuando esté disponible
- Se crea backup automáticamente
- Instalación con barra de progreso
- Servidor se reinicia automáticamente

**Rollback a Versión Anterior:**
- Click en botón "Rollback" (borde rojo)
- Solo disponible si hay backup
- Restaura versión anterior completa

## Arquitectura

### Componentes Principales

```
launcher.py                     # Entry point
launcher_lib/
├── app.py                     # SuiteLauncher (integrador principal)
├── config_manager.py          # Gestión de launcher_config.ini
├── port_manager.py            # Rotación de puertos 8005-8050
├── server_manager.py          # Ciclo de vida del servidor FastAPI
├── update_manager.py          # Actualizaciones desde GitHub
├── system_monitor.py          # Monitor CPU/memoria con psutil
└── ui/
    ├── main_window.py         # Ventana principal
    ├── update_dialog.py       # Diálogo de actualización
    ├── progress_dialog.py     # Barra de progreso
    └── styles.py              # Colores y estilos
```

### Archivos de Configuración

**launcher_config.ini** (`FlexStart/backend/launcher_config.ini`):
- Versión actual
- Último puerto usado
- Configuración de actualizaciones
- Metadata de backups

**Creado automáticamente en primer uso**

### Directorios

**`.backups/`** (raíz del proyecto):
- Backups automáticos antes de actualizar
- Se mantiene solo el último backup
- No se versiona en git

**`launcher.log`** (raíz del proyecto):
- Logs detallados del launcher
- Rotación automática
- No se versiona en git

## Configuración Avanzada

### Modificar Rango de Puertos

Editar `launcher_config.ini`:

```ini
[Launcher]
port_range_min = 8005
port_range_max = 8050
```

### Desactivar Auto-Abrir Navegador

```ini
[Launcher]
auto_open_browser = false
```

### Cambiar Intervalo de Chequeo de Actualizaciones

```ini
[UpdateSettings]
update_check_interval_hours = 4
```

### Desactivar Chequeo Automático

```ini
[UpdateSettings]
auto_check_updates = false
```

## Solución de Problemas

### Todos los Puertos Ocupados

**Síntoma:** Error "No available ports in range 8005-8050"

**Solución:**
1. Cerrar otras instancias del servidor
2. Verificar procesos que usen esos puertos: `lsof -i :8005-8050` (macOS/Linux)
3. Ampliar rango en configuración

### Fallo al Iniciar Servidor

**Síntoma:** Servidor no inicia, botón vuelve a "Start Server"

**Solución:**
1. Revisar `launcher.log` para detalles
2. Verificar que `FlexStart/backend/app.py` existe
3. Verificar dependencias de FastAPI instaladas
4. Intentar puerto específico manualmente

### Actualizaci
ón Falla

**Síntoma:** Error durante actualización

**Solución:**
1. El rollback se ejecuta automáticamente
2. Verificar conexión a internet
3. Verificar acceso a GitHub
4. Revisar `launcher.log` para detalles

### Interfaz No Responde

**Síntoma:** Ventana se congela

**Solución:**
1. Esperar (operaciones largas pueden bloquear UI momentáneamente)
2. Si persiste, cerrar y reiniciar launcher
3. Revisar logs para excepciones

## Logs y Debugging

### Ver Logs en Tiempo Real

```bash
tail -f launcher.log
```

### Logs Detallados

Todos los componentes logean con formato:
```
[2025-12-04 10:30:45] [INFO] launcher_lib.server_manager: Server started successfully on port 8015
```

### Niveles de Log

- **INFO**: Operaciones normales
- **WARNING**: Problemas recuperables
- **ERROR**: Fallos que impiden operación
- **DEBUG**: Información detallada (no habilitado por defecto)

## Desarrollo

### Estructura de Código

- **ConfigManager**: Persistencia de configuración
- **PortManager**: Algoritmo round-robin para puertos
- **ServerManager**: Subprocess management de uvicorn
- **UpdateManager**: GitHub API + instalación de actualizaciones
- **SystemMonitor**: psutil para métricas de sistema
- **MainWindow**: customtkinter UI

### Agregar Nueva Funcionalidad

1. Implementar en manager correspondiente
2. Agregar callback en `MainWindow`
3. Conectar en `SuiteLauncher.connect_callbacks()`
4. Probar con logs habilitados

## Compatibilidad

### Sistemas Operativos

- ✅ macOS (Darwin) - Desarrollo principal
- ✅ Windows 10/11
- ✅ Linux (Ubuntu, Debian, etc.)

### Versiones de Python

- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13

### Navegadores

Auto-apertura funciona con navegador por defecto del sistema.

## FAQ

**P: ¿Puedo ejecutar múltiples instancias?**
R: Sí, cada instancia usará un puerto diferente automáticamente.

**P: ¿Qué pasa si cierro el launcher con el servidor corriendo?**
R: El servidor seguirá corriendo. Debes detenerlo manualmente o reiniciar la máquina.

**P: ¿Puedo cambiar el puerto manualmente?**
R: Actualmente no desde la UI, pero puedes editar `last_used_port` en el config.

**P: ¿Las actualizaciones son automáticas?**
R: El chequeo es automático, pero la instalación requiere confirmación del usuario.

**P: ¿Qué pasa con mis configuraciones al actualizar?**
R: Los archivos `config.ini` y `data/` se preservan automáticamente.

## Recursos

- **Logs**: `launcher.log`
- **Configuración**: `FlexStart/backend/launcher_config.ini`
- **Backups**: `.backups/`
- **GitHub**: https://github.com/roddev-jd/R-App

## Licencia

Parte de App_SUITE v2.0.2 - Ripley Corporation

---

**Última actualización:** Diciembre 2025
**Versión del Launcher:** 2.0.2
