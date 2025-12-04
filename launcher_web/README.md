# Lanzador Web para App_SUITE

Lanzador web moderno con interfaz de navegador para gestionar el servidor principal de App_SUITE.

## Características

✅ **Interfaz web moderna** heredada del diseño FlexStart
✅ **Control completo del servidor** (iniciar/detener/reiniciar)
✅ **Monitoreo en tiempo real** (CPU, memoria, logs)
✅ **Sistema de actualizaciones** integrado con GitHub
✅ **Rollback** a versiones anteriores
✅ **Sin dependencias GUI** (customtkinter, tkinter, PyQt)
✅ **Compatible con equipos antiguos y nuevos**

## Requisitos

- Python 3.10+
- Navegador web moderno (Chrome, Firefox, Safari, Edge)
- Conexión a Internet (solo para verificar actualizaciones)

## Instalación

1. Instalar dependencias:

```bash
pip install -r launcher_web/requirements.txt
```

2. Verificar que las dependencias de `launcher_lib` estén instaladas:

```bash
pip install -r requirements_server.txt
```

## Uso

### Inicio Rápido

Desde el directorio raíz del proyecto:

```bash
python start_launcher.py
```

o

```bash
python3 start_launcher.py
```

El lanzador se iniciará en el puerto **9999** y abrirá automáticamente el navegador en `http://127.0.0.1:9999`.

### Inicio Manual

Si prefieres iniciar manualmente:

```bash
cd launcher_web
python launcher_web_server.py
```

Luego abre tu navegador en: `http://127.0.0.1:9999`

## Funcionalidades

### 1. Control del Servidor

- **Iniciar Servidor**: Inicia el servidor principal FastAPI en un puerto disponible (8005-8050)
- **Detener Servidor**: Detiene el servidor principal de forma segura
- **Abrir Aplicación**: Abre el servidor principal en una nueva pestaña del navegador

### 2. Monitor del Sistema

- **CPU**: Muestra el uso de CPU del servidor en porcentaje
- **Memoria**: Muestra el uso de memoria del servidor
- **Uptime**: Tiempo de actividad del servidor

Los datos se actualizan en tiempo real cada 2 segundos.

### 3. Logs del Servidor

- Ver logs del servidor en tiempo real
- Auto-scroll opcional
- Función de limpieza de logs
- Sección colapsable para ahorrar espacio

### 4. Centro de Actualizaciones

- **Verificar Actualizaciones**: Consulta GitHub para nuevas versiones
- **Instalar Actualización**: Descarga e instala nuevas versiones automáticamente
- **Rollback**: Restaura la versión anterior si algo sale mal
- Progreso en tiempo real durante la instalación

## Comportamiento al Cerrar Pestaña

⚠️ **IMPORTANTE**: Cerrar la pestaña del navegador NO detiene los servicios.

Cuando cierras la pestaña del lanzador web:
- ✅ `launcher_web_server.py` sigue corriendo (puerto 9999)
- ✅ El servidor principal sigue corriendo (puerto 8005-8050, si estaba activo)
- ✅ Puedes volver a abrir el lanzador en `http://127.0.0.1:9999`

### Advertencia de Cierre

Si intentas cerrar la pestaña mientras el servidor está corriendo:
- Recibirás una advertencia del navegador para confirmar la acción
- Un banner informativo visible te recordará que cerrar la pestaña NO detiene el servidor
- Esto te ayuda a evitar cierres accidentales mientras los servicios están activos

### Para Detener Completamente

**Opción 1**: Usa el botón "Detener Servidor" en el lanzador web antes de cerrar la pestaña

**Opción 2**: Presiona `Ctrl+C` en la terminal donde ejecutaste `start_launcher.py`

**Opción 3**: Cierra la terminal completamente

## Arquitectura

```
start_launcher.py (puerto 9999)
    ↓
launcher_web_server.py (Backend FastAPI)
    ↓
launcher.html (Frontend Web)
    ↓
Reutiliza managers de launcher_lib:
    - ConfigManager
    - PortManager
    - ServerManager
    - UpdateManager
    - SystemMonitor
```

## Configuración

La configuración se guarda en:
```
FlexStart/backend/launcher_config.ini
```

Opciones configurables:
- `auto_start_server`: Iniciar servidor automáticamente
- `auto_open_browser`: Abrir navegador automáticamente
- `auto_check_updates`: Verificar actualizaciones al iniciar
- `port_range_min/max`: Rango de puertos (8005-8050)

## Diseño Visual

El lanzador web hereda la estética de FlexStart:

- **Colores**: Rosa primario (#ea338c), Cian secundario (#0dcaf0)
- **Tipografía**: Roboto (texto), Montserrat (encabezados)
- **Componentes**: Cards con sombras suaves, botones animados
- **Responsive**: Funciona en móvil, tablet y desktop

## Estructura de Archivos

```
launcher_web/
├── __init__.py
├── launcher_web_server.py      # Backend API (FastAPI)
├── requirements.txt             # Dependencias
├── README.md                    # Este archivo
├── templates/
│   └── launcher.html           # UI principal
└── static/
    ├── css/
    │   └── launcher.css        # Estilos heredados de FlexStart
    └── js/
        ├── api-client.js       # Cliente API REST
        ├── sse-handler.js      # Manejo de SSE
        ├── ui-components.js    # Gestión de UI
        └── launcher.js         # Lógica principal
```

## API Endpoints

### Server Control
- `POST /api/server/start` - Iniciar servidor
- `POST /api/server/stop` - Detener servidor
- `GET /api/server/status` - Estado del servidor

### Configuration
- `GET /api/config` - Obtener configuración
- `PATCH /api/config` - Actualizar configuración

### Updates
- `GET /api/updates/check` - Verificar actualizaciones
- `POST /api/updates/install` - Instalar actualización
- `POST /api/updates/rollback` - Rollback
- `GET /api/updates/backup-status` - Estado del backup

### Monitoring
- `GET /api/monitor/metrics` - Métricas del sistema

### SSE Streams
- `GET /api/sse/logs` - Stream de logs
- `GET /api/sse/metrics` - Stream de métricas
- `GET /api/sse/update-progress` - Progreso de actualización

## Troubleshooting

### El puerto 9999 está ocupado

Si el puerto 9999 está en uso, puedes especificar otro:

```bash
python launcher_web/launcher_web_server.py --port 9998
```

### El navegador no se abre automáticamente

Abre manualmente: `http://127.0.0.1:9999`

### Error al iniciar el servidor

Verifica que:
1. Las dependencias estén instaladas
2. El puerto 9999 esté disponible
3. Los archivos de `launcher_lib` existan

### Logs no aparecen

1. Verifica que el servidor principal esté corriendo
2. Revisa la consola del navegador (F12) para errores
3. Verifica la conexión SSE en la pestaña Network

## Ventajas sobre el Lanzador Desktop

| Característica | Desktop (customtkinter) | Web |
|----------------|------------------------|-----|
| **Dependencias** | Requiere customtkinter | Solo navegador |
| **Compatibilidad** | Python 3.10+ + GUI libs | Python 3.10+ |
| **Actualizar UI** | Reinstalar | Editar CSS |
| **Debugging** | Difícil | DevTools |
| **Responsive** | No | Sí |
| **Memoria** | ~50-80 MB | ~30-50 MB |
| **Equipos antiguos** | ❌ Puede fallar | ✅ Funciona |

## Soporte

Para reportar problemas o sugerir mejoras, contacta al equipo de desarrollo de Ripley Product & Category.

---

**Version**: 1.0.0
**Last Updated**: Diciembre 2025
**Maintainer**: Ripley Product & Category Team
