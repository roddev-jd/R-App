import asyncio
import json
import logging
import os
import queue
import subprocess
import sys
import threading
import ctypes
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import main_logic
from main_logic import log_queue, new_log_event
from core.sse_channel import search_progress_queue, data_load_progress_queue
from core.error_handlers import api_error_handler, validate_config, OperationType, log_operation_start, log_operation_end

# Nuevos imports para servicios
from services.data_service import create_data_service
from services.filter_service import create_filter_service
from services.export_service import create_export_service

# Sistema de capabilities con fallback
try:
    # Agregar path para shared si no está disponible
    shared_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared')
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)
    from capabilities import get_system_capabilities
except ImportError:
    def get_system_capabilities():
        return {
            "duckdb_available": True,
            "opencv_available": False,
            "reportes_available": True,
            "ahead_tool": False,
        }

# Modelos de datos
class FilterRequest(BaseModel):
    blob_filename: Optional[str] = None
    value_filters: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Filtros SKU
    use_sku_hijo_file: bool = False
    extend_sku_hijo: bool = False
    sku_hijo_manual_list: Optional[List[str]] = None
    use_sku_padre_file: bool = False
    sku_padre_manual_list: Optional[List[str]] = None
    
    # Filtros Ticket
    use_ticket_file: bool = False
    ticket_manual_list: Optional[List[str]] = None
    
    # Otros filtros
    lineamiento_manual_list: Optional[List[str]] = None
    selected_display_columns: Optional[List[str]] = None

    # Filtros personalizados de texto (búsqueda por coincidencias)
    custom_text_filters: Optional[Dict[str, List[str]]] = Field(default_factory=dict)

    # Característica de coloreado por prioridad
    enable_priority_coloring: bool = False
    
    # Paginación
    page: int = 1
    page_size: int = 100

class SaveStateRequest(BaseModel):
    value_filters: Dict[str, List[str]] = Field(default_factory=dict)
    selected_columns: List[str] = Field(default_factory=list)
    extend_sku_search: bool = False

class DataLoadRequest(BaseModel):
    """Modelo para solicitudes de carga de datos con columnas específicas."""
    selected_columns: Optional[List[str]] = None

class ScriptRequest(BaseModel):
    script_id: str

class DeclarationRequest(BaseModel):
    team_member: str
    declaration_text: str

class TeamMemberResponse(BaseModel):
    member_id: str
    display_name: str
    excel_url: str

class RejectionRequest(BaseModel):
    team_member: str
    rejection_text: str
    rejection_obs: str

class TeamMemberRejectResponse(BaseModel):
    member_id: str
    display_name: str
    excel_url: str

# Middleware de validación
class ConfigValidationMiddleware(BaseHTTPMiddleware):
    """Middleware para validar configuración antes de procesar requests."""
    
    EXCLUDED_PATHS = {
        "/", "/docs", "/redoc", "/openapi.json", "/health", 
        "/reportes", "/buscador-integral"
    }
    
    async def dispatch(self, request: Request, call_next):
        if (request.url.path in self.EXCLUDED_PATHS or 
            request.url.path.startswith(("/assets", "/static", "/css"))):
            return await call_next(request)
        
        if request.url.path.startswith("/api/"):
            if not main_logic.config_data.get("config_parser"):
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Configuration not available",
                        "message": "La configuración del sistema no está disponible. Verifique config.ini.",
                        "path": request.url.path
                    }
                )
        
        return await call_next(request)

# Configuración de aplicación
app = FastAPI(title="Reportes Chile API", version="1.2.0")
app.add_middleware(ConfigValidationMiddleware)

# Pool de threads para scripts
script_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="script_worker")

# Lista para rastrear tareas en background
background_tasks = []

# Inicialización de servicios
data_service = None  # Se inicializará en startup o lazy
filter_service = None  # Se inicializará en startup o lazy
export_service = None  # Se inicializará en startup o lazy

def get_data_service():
    """Factory function para obtener DataService con lazy initialization."""
    global data_service
    if data_service is None:
        data_service = create_data_service(
            config_data=main_logic.config_data,
            io_executor=main_logic.io_executor
        )
        logging.info("DataService inicializado via lazy loading.")
    return data_service

def get_filter_service():
    """Factory function para obtener FilterService con lazy initialization."""
    global filter_service
    if filter_service is None:
        filter_service = create_filter_service(
            config_data=main_logic.config_data,
            io_executor=main_logic.io_executor
        )
        logging.info("FilterService inicializado via lazy loading.")
    return filter_service

def get_export_service():
    """Factory function para obtener ExportService con lazy initialization."""
    global export_service
    if export_service is None:
        export_service = create_export_service(
            config_data=main_logic.config_data,
            io_executor=main_logic.io_executor
        )
        logging.info("ExportService inicializado via lazy loading.")
    return export_service

# Registrar routers modulares
from endpoints.sharepoint import router as sharepoint_router
app.include_router(sharepoint_router)

# NOTA: Las pestañas "códigos" y "columnas" están implementadas directamente en el frontend

# Configuración de directorios
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_REPORTES_FRONTEND_DIR = os.path.join(BACKEND_DIR, "..", "frontend")
FLEXSTART_DIR = os.path.join(BACKEND_DIR, "..", "..", "..")
HERRAMIENTAS_DIR = os.path.join(FLEXSTART_DIR, "herramientas")

# Scripts permitidos para seguridad
def get_allowed_scripts():
    """Genera diccionario de scripts permitidos."""
    diseno_dir = os.path.join(FLEXSTART_DIR, "apps", "diseno")
    return {
        "procesador_cargas": os.path.join(diseno_dir, "APP_CARGAS/app_cargas.py"),
        "buscador_diseno": os.path.join(diseno_dir, "Buscador.py"),
        "miniaturas_diseno": os.path.join(diseno_dir, "Miniaturas.py"),
        "RipleyDownloader": os.path.join(diseno_dir, "RipleyDownloader.py"),
        "Scrapper": os.path.join(diseno_dir, "Scrapper.py"),
        "Renamer-PH": os.path.join(diseno_dir, "Renamer-PH.py"),
        "Renamer-Rimage": os.path.join(diseno_dir, "Renamer-Rimage.py"),
        "SVC-OK": os.path.join(diseno_dir, "SVC-OK.py"),
        "Renamer-ImgFile": os.path.join(diseno_dir, "Renamer-ImgFile.py"),
        "Renamer-Muestras": os.path.join(diseno_dir, "Renamer-Muestras.py"),
        "lastImage": os.path.join(diseno_dir, "lastImage.py"),
        "Insert": os.path.join(diseno_dir, "Insert.py"),
        "Dept": os.path.join(diseno_dir, "Dept.py"),
        "Encarpetar": os.path.join(diseno_dir, "Encarpetar.py"),
        "Indexar": os.path.join(diseno_dir, "index", "run_app.py"),
        "Prod-Selector": os.path.join(diseno_dir, "Prod-Selector.py"),
        "TeamSearch": os.path.join(diseno_dir, "TeamSearch.py"),
        "Convertidor": os.path.join(diseno_dir, "Convertidor.py"),
        "Compresor": os.path.join(diseno_dir, "Compress", "Compresor.py"),
        "RotateImg": os.path.join(diseno_dir, "RotateImg.py"),
        "Multi-Tags-moda-producto": os.path.join(diseno_dir, "MultiTag", "main.py"),
        "image_validator": os.path.join(diseno_dir, "image_validator.py"),
    }

ALLOWED_SCRIPTS = get_allowed_scripts()

# Las rutas estáticas se manejan en el gateway principal cuando se monta como sub-app


# Función auxiliar para inicializar SharePoint
async def initialize_sharepoint_auth():
    """Inicializa la autenticación de SharePoint en background."""
    try:
        # Ejecutar la inicialización en un thread separado para no bloquear el startup
        def init_auth():
            try:
                auth = main_logic.get_sharepoint_authenticator()
                # Intentar obtener un token para verificar que funciona
                token = auth.get_token()
                logging.info("Autenticación SharePoint inicializada correctamente al startup")
                return True
            except Exception as e:
                logging.warning(f"No se pudo inicializar autenticación SharePoint: {e}")
                return False
        
        # Ejecutar en background
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(main_logic.sharepoint_executor, init_auth)
        
    except Exception as e:
        logging.warning(f"Error durante inicialización SharePoint: {e}")

# Eventos de aplicación
@app.on_event("startup")
async def startup_event():
    """Inicializa recursos de la aplicación."""
    global data_service

    if not main_logic.config_data.get("config_parser"):
        logging.critical("Configuración de main_logic NO cargada. API podría no funcionar.")
    else:
        logging.info("Aplicación FastAPI iniciada. Configuración de main_logic cargada.")

    # Inicializar DataService
    data_service = create_data_service(
        config_data=main_logic.config_data,
        io_executor=main_logic.io_executor
    )
    logging.info("DataService inicializado correctamente.")

    # Log de thread pools
    pools_info = [
        f"Scripts: {script_executor._max_workers} workers",
        f"I/O: {main_logic.io_executor._max_workers} workers",
        f"SharePoint: {main_logic.sharepoint_executor._max_workers} workers"
    ]
    logging.info(f"ThreadPoolExecutors iniciados - {', '.join(pools_info)}")

    # Inicializar SharePoint authentication en background y rastrear la tarea
    task = asyncio.create_task(initialize_sharepoint_auth())
    background_tasks.append(task)

@app.on_event("shutdown")
async def shutdown_event():
    """Limpia recursos al cerrar la aplicación."""

    # Watchdog NON-DAEMON con force kill de threads bloqueados
    def force_exit_watchdog(timeout: int = 10):
        """
        Watchdog que garantiza exit después de timeout.
        NON-DAEMON para que Python no lo ignore cuando hay threads bloqueados.
        """
        time.sleep(timeout)

        logging.critical(f"[WATCHDOG] Shutdown exceeded {timeout}s. Force killing application.")

        # Intento 1: Matar threads bloqueados de ThreadPoolExecutor con ctypes (CPython only)
        try:
            killed_any = False
            for thread in threading.enumerate():
                if "ThreadPoolExecutor" in thread.name or "ScriptExec" in thread.name:
                    logging.warning(f"[WATCHDOG] Force killing thread: {thread.name}")
                    try:
                        if hasattr(ctypes, 'pythonapi'):
                            result = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                                ctypes.c_long(thread.ident),
                                ctypes.py_object(SystemExit)
                            )
                            if result == 1:
                                killed_any = True
                            elif result > 1:
                                # Rollback si afectó múltiples threads
                                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                                    ctypes.c_long(thread.ident), None
                                )
                    except Exception as e:
                        logging.error(f"[WATCHDOG] Error killing thread {thread.name}: {e}")

            if killed_any:
                logging.info("[WATCHDOG] Waiting 1s for threads to die...")
                time.sleep(1.0)
        except Exception as e:
            logging.error(f"[WATCHDOG] Error in thread killing phase: {e}")

        # Intento 2: Force exit (último recurso)
        logging.critical("[WATCHDOG] Executing os._exit(1) - immediate termination")
        os._exit(1)

    watchdog = threading.Thread(
        target=force_exit_watchdog,
        args=(10,),
        daemon=False  # ← CRÍTICO: Non-daemon para que Python no lo ignore
    )
    watchdog.start()
    logging.info("[SHUTDOWN] Watchdog non-daemon iniciado (timeout: 10 segundos)")

    # Paso 1/5: Cancelar tareas en background
    logging.info("[SHUTDOWN] Paso 1/5: Cancelando tareas en background...")
    for task in background_tasks:
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
                logging.info("[SHUTDOWN] Tarea en background cancelada exitosamente")
            except asyncio.TimeoutError:
                logging.warning("[SHUTDOWN] Tarea en background no se canceló dentro del timeout")
            except asyncio.CancelledError:
                logging.info("[SHUTDOWN] Tarea en background fue cancelada")

    # Paso 2/5: Vaciar colas SSE
    logging.info("[SHUTDOWN] Paso 2/5: Vaciando colas SSE...")
    try:
        # Vaciar cola asyncio de progreso de búsqueda
        while not search_progress_queue.empty():
            try:
                search_progress_queue.get_nowait()
            except:
                break

        # Vaciar cola thread-safe de progreso de carga de datos
        while not data_load_progress_queue.empty():
            try:
                data_load_progress_queue.get_nowait()
            except:
                break

        # Enviar señal de terminación
        try:
            data_load_progress_queue.put_nowait({"type": "shutdown"})
        except:
            pass

        logging.info("[SHUTDOWN] Colas SSE vaciadas correctamente")
    except Exception as e:
        logging.warning(f"[SHUTDOWN] Error vaciando colas SSE: {e}")

    # Paso 3/5: Cerrar conexión DuckDB
    logging.info("[SHUTDOWN] Paso 3/5: Cerrando conexiones de base de datos...")
    if main_logic.duckdb_conn:
        try:
            main_logic.duckdb_conn.close()
            main_logic.duckdb_conn = None
            logging.info("[SHUTDOWN] Conexión DuckDB cerrada correctamente")
        except Exception as e:
            logging.warning(f"[SHUTDOWN] Error cerrando DuckDB: {e}")

    # Paso 4/5: Cerrar ThreadPoolExecutors con force kill si necesario
    logging.info("[SHUTDOWN] Paso 4/5: Cerrando ThreadPoolExecutors...")
    executors = [
        ("Scripts", script_executor),
        ("I/O", main_logic.io_executor),
        ("SharePoint", main_logic.sharepoint_executor)
    ]

    def force_shutdown_executor(name: str, executor: ThreadPoolExecutor, timeout: float):
        """
        Shutdown executor con force kill de threads bloqueados.
        1. Cancel pending futures
        2. Esperar timeout
        3. Force kill threads con ctypes si no terminan
        """
        logging.info(f"[SHUTDOWN] Shutting down executor: {name}")

        # Paso 1: Cancel pending futures
        executor.shutdown(wait=False, cancel_futures=True)

        # Paso 2: Esperar con timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check si hay threads activos del executor
            executor_threads = [
                t for t in threading.enumerate()
                if ("ThreadPoolExecutor" in t.name or "ScriptExec" in t.name) and t.is_alive()
            ]
            if not executor_threads:
                logging.info(f"[SHUTDOWN] {name} executor shutdown cleanly")
                return True
            time.sleep(0.1)

        # Paso 3: Force kill threads que no terminaron
        logging.warning(f"[SHUTDOWN] {name} executor did not shutdown in {timeout}s, force killing")
        executor_threads = [
            t for t in threading.enumerate()
            if ("ThreadPoolExecutor" in t.name or "ScriptExec" in t.name) and t.is_alive()
        ]

        for thread in executor_threads:
            logging.warning(f"[SHUTDOWN] Force killing thread: {thread.name}")
            try:
                if hasattr(ctypes, 'pythonapi'):
                    result = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(thread.ident),
                        ctypes.py_object(SystemExit)
                    )
                    if result == 0:
                        logging.error(f"[SHUTDOWN] Invalid thread ID: {thread.ident}")
                    elif result > 1:
                        # Rollback si afectó múltiples threads
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            ctypes.c_long(thread.ident), None
                        )
                        logging.error(f"[SHUTDOWN] Failed to kill thread {thread.name}")
            except Exception as e:
                logging.error(f"[SHUTDOWN] Error killing thread {thread.name}: {e}")

        return False

    # Ejecutar shutdown en threads DAEMON (no bloquean watchdog)
    shutdown_threads = []
    for name, executor in executors:
        t = threading.Thread(
            target=force_shutdown_executor,
            args=(name, executor, 3.0),
            daemon=True  # ← CRÍTICO: Daemon para no bloquear watchdog
        )
        t.start()
        shutdown_threads.append(t)

    # Esperar máximo 4s total
    for t in shutdown_threads:
        t.join(timeout=4.0)

    # Log final status
    alive_threads = [t for t in shutdown_threads if t.is_alive()]
    if alive_threads:
        logging.error(f"[SHUTDOWN] {len(alive_threads)} executor shutdowns still running")
    else:
        logging.info("[SHUTDOWN] All executors shutdown successfully")

    # Paso 5/5: Limpieza completa
    logging.info("[SHUTDOWN] Paso 5/5: Limpieza completa")
    logging.info("[SHUTDOWN] Aplicación FastAPI cerrada correctamente")

# Rutas principales
@app.get("/", include_in_schema=False)
async def get_reportes_root():
    """Sirve la página principal de Reportes."""
    return _serve_html_file(
        os.path.join(APP_REPORTES_FRONTEND_DIR, "index.html"),
        "Reportes index.html no encontrado."
    )

@app.get("/reportes", include_in_schema=False)
async def get_reportes_index():
    """Sirve la página principal de Reportes."""
    return _serve_html_file(
        os.path.join(APP_REPORTES_FRONTEND_DIR, "index.html"),
        "Reportes index.html no encontrado."
    )

@app.get("/buscador-integral", include_in_schema=False)
async def get_buscador_integral():
    """Sirve la página del buscador integral de fotos estudio."""
    return _serve_html_file(
        os.path.join(os.path.dirname(__file__), "..", "..", "buscador-integral.html"),
        "Buscador integral HTML no encontrado."
    )

def _serve_html_file(file_path: str, error_message: str):
    """Función auxiliar para servir archivos HTML con manejo de errores."""
    if not os.path.exists(file_path):
        logging.error(f"{error_message} Ruta: {file_path}")
        raise HTTPException(status_code=404, detail=error_message)
    return FileResponse(file_path)


# Endpoints de configuración
@app.get("/api/config/blobs", summary="Obtener lista de blobs y default")
async def api_get_blob_options():
    """Obtiene lista de blobs disponibles."""
    return get_data_service().get_blob_options_for_api()

@app.get("/api/config/settings/{blob_display_name}", summary="Obtener configuración de filtros para un blob")
async def api_get_config_settings(blob_display_name: str):
    """Obtiene configuración de filtros para un blob específico."""
    raw_settings = get_data_service().get_config_settings_for_api(blob_display_name)
    if not raw_settings:
        raise HTTPException(
            status_code=404,
            detail=f"Configuración no encontrada para {blob_display_name}"
        )

    return {
        "filter_columns": raw_settings.get("filter_cols", []),
        "hide_columns": raw_settings.get("hide_cols", []),
        "not_empty_columns": raw_settings.get("not_empty_cols", []),
        "hide_values": raw_settings.get("hide_values", {}),
        "exclude_rows": raw_settings.get("exclude_rows", {})
    }

@app.get("/api/config/filter-visibility/{blob_display_name}", summary="Obtener configuración de visibilidad de filtros")
async def api_get_filter_visibility(blob_display_name: str):
    """
    Retorna configuración de visibilidad de filtros para una base de datos específica.

    Controla qué filtros mostrar/ocultar en el frontend y define filtros personalizados.

    Args:
        blob_display_name: Nombre de la base de datos (ej: "UNIVERSO PERU", "EQUIVALENCIAS CL -> PE")

    Returns:
        {
            "show_ticket_filter": bool,           # Mostrar filtro de Requerimiento (columna 'ticket')
            "show_lineamiento_filter": bool,      # Mostrar filtro de Ticket (columna 'asunto_lineamientos')
            "show_sku_hijo_filter": bool,         # Mostrar filtro de SKU Hijo
            "show_sku_padre_filter": bool,        # Mostrar filtro de SKU Padre
            "custom_text_filters": [              # Filtros personalizados de texto
                "columna1", "columna2"
            ]
        }
    """
    raw_settings = get_data_service().get_config_settings_for_api(blob_display_name)
    if not raw_settings:
        raise HTTPException(
            status_code=404,
            detail=f"Configuración no encontrada para {blob_display_name}"
        )

    return {
        "show_ticket_filter": raw_settings.get('show_ticket_filter', True),
        "show_lineamiento_filter": raw_settings.get('show_lineamiento_filter', True),
        "show_sku_hijo_filter": raw_settings.get('show_sku_hijo_filter', True),
        "show_sku_padre_filter": raw_settings.get('show_sku_padre_filter', True),
        "custom_text_filters": raw_settings.get('custom_text_filters', [])
    }

@app.get("/api/data/columns/{blob_display_name}", summary="Obtener columnas disponibles para selector")
async def api_get_available_columns(blob_display_name: str):
    """
    Obtiene las columnas disponibles para el selector de columnas.
    Retorna: available_columns, essential_columns, y selected_columns (del config o caché).
    """
    try:
        raw_settings = get_data_service().get_config_settings_for_api(blob_display_name)
        if not raw_settings:
            raise HTTPException(
                status_code=404,
                detail=f"Configuración no encontrada para {blob_display_name}"
            )

        # Obtener columnas disponibles (configuradas o desde metadata del caché)
        available_columns = raw_settings.get("availablecolumns", [])
        essential_columns = raw_settings.get("essentialcolumns", [])
        default_selected = raw_settings.get("selectcolumns", "")

        # Verificar si los 3 parámetros de configuración existen (para modal condicional)
        has_column_config = (
            "availablecolumns" in raw_settings and bool(available_columns) and
            "essentialcolumns" in raw_settings and bool(essential_columns) and
            "selectcolumns" in raw_settings
        )

        # Si no hay columnas disponibles configuradas, intentar desde caché Parquet
        if not available_columns:
            persistent_cache = main_logic.persistent_cache
            if persistent_cache and persistent_cache.has_cached_data(blob_display_name):
                metadata = persistent_cache.get_cached_metadata(blob_display_name)
                if metadata and metadata.get("format") == "parquet":
                    # Leer columnas del archivo Parquet
                    try:
                        import pyarrow.parquet as pq
                        from pathlib import Path
                        cache_dir = persistent_cache.cache_dir
                        parquet_file = cache_dir / persistent_cache._get_cache_filename(blob_display_name, format='parquet')
                        if parquet_file.exists():
                            parquet_metadata = pq.read_metadata(parquet_file)
                            available_columns = parquet_metadata.schema.names
                            logging.info(f"Columnas obtenidas desde metadata de Parquet: {len(available_columns)} columnas")
                    except Exception as e:
                        logging.warning(f"No se pudieron leer columnas desde Parquet: {e}")

        # Convertir default_selected de string a lista
        if default_selected and isinstance(default_selected, str):
            default_selected = [col.strip() for col in default_selected.split(',') if col.strip()]
        elif not default_selected:
            default_selected = essential_columns if essential_columns else []

        # Verificar si hay preferencia guardada en SavedState (tiene prioridad sobre config)
        saved_state = main_logic.config_data.get("saved_states", {}).get(blob_display_name.upper(), {})
        last_selected = saved_state.get("last_selected_columns")
        if last_selected:
            default_selected = [col.strip() for col in last_selected.split(',') if col.strip()]
            logging.info(f"Usando columnas desde SavedState para '{blob_display_name}': {len(default_selected)} columnas")

        return {
            "available_columns": available_columns,
            "essential_columns": essential_columns,
            "default_selected_columns": default_selected,
            "total_columns": len(available_columns) if available_columns else 0,
            "has_column_config": has_column_config
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo columnas disponibles para '{blob_display_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo columnas: {str(e)}")

@app.post("/api/data/load/{blob_display_name}", summary="Cargar datos con verificación inteligente de caché")
@api_error_handler
async def api_load_data(blob_display_name: str, request: Optional[DataLoadRequest] = None):
    """Carga datos con verificación automática de actualizaciones (caché inteligente).

    COMPORTAMIENTO:
    1. Verifica automáticamente si hay actualizaciones en SharePoint (si aplica)
    2. Usa caché si está actualizado (rápido)
    3. Descarga nueva versión si hay cambios (actualizado)

    Args:
        blob_display_name: Nombre de la fuente de datos
        request: Opcional - Request body con selected_columns para optimizar carga

    Returns:
        Incluye campo 'cache_decision': 'using_cache' | 'downloading_fresh' | 'no_cache'
    """
    # Extraer columnas seleccionadas si se proporcionaron
    selected_columns = None
    if request and request.selected_columns:
        selected_columns = request.selected_columns
        logging.info(f"Carga solicitada con {len(selected_columns)} columnas específicas para '{blob_display_name}'")

    operation_id = log_operation_start(OperationType.DATA_LOAD, {
        "blob": blob_display_name,
        "custom_columns": len(selected_columns) if selected_columns else 0
    })

    try:
        validate_config(main_logic.config_data)
        result = await get_data_service().load_blob_data_safe(blob_display_name, selected_columns=selected_columns)
        log_operation_end(operation_id, OperationType.DATA_LOAD, True, {"rows": result.get("row_count_original", 0)})
        return result
    except Exception as e:
        log_operation_end(operation_id, OperationType.DATA_LOAD, False, {"error": str(e)})
        raise

@app.get("/api/data/check-updates/{blob_display_name}", summary="Verificar actualizaciones disponibles para una base")
async def api_check_updates(blob_display_name: str):
    """Verifica si hay actualizaciones disponibles para una base con cache persistente."""
    try:
        from services.cache_service import persistent_cache
        
        # Verificar si la base es cacheable
        if not persistent_cache.is_cacheable(blob_display_name):
            return {
                "cacheable": False,
                "has_cache": False,
                "update_available": False,
                "message": f"La base '{blob_display_name}' no utiliza cache persistente"
            }
        
        # Verificar si tiene cache local
        has_cache = persistent_cache.has_cached_data(blob_display_name)
        if not has_cache:
            return {
                "cacheable": True,
                "has_cache": False,
                "update_available": True,
                "message": "No hay cache local disponible"
            }
        
        # Obtener configuración de la base
        blob_attrs = main_logic.config_data.get("blob_options", {}).get(blob_display_name.upper())
        if not blob_attrs:
            raise HTTPException(
                status_code=404,
                detail=f"Configuración no encontrada para {blob_display_name}"
            )
        
        source_url = blob_attrs.get("value")
        source_type = blob_attrs.get("source_type")
        
        if source_type != "sharepoint":
            return {
                "cacheable": True,
                "has_cache": has_cache,
                "update_available": False,
                "message": "Solo se verifica actualizaciones para fuentes SharePoint"
            }
        
        # Obtener headers de autenticación usando el mismo método que las cargas
        auth_headers = None
        try:
            auth = main_logic.get_sharepoint_authenticator()
            access_token = auth.get_token()
            auth_headers = {"Authorization": f"Bearer {access_token}"}
        except Exception as e:
            logging.warning(f"No se pudo obtener token de autenticación: {e}")
        
        # Verificar actualizaciones remotas
        update_info = persistent_cache.check_remote_update(
            blob_display_name, 
            source_url, 
            auth_headers
        )
        
        return {
            "cacheable": True,
            "has_cache": True,
            "update_available": update_info.get("update_available", False),
            "cache_timestamp": update_info.get("cache_timestamp"),
            "remote_last_modified": update_info.get("remote_last_modified"),
            "comparison_details": update_info.get("comparison_details", ""),
            "check_error": update_info.get("error"),
            "message": "Verificación de actualizaciones completada",
            "recommendation": "Se recomienda realizar una Carga Completa" if update_info.get("update_available") else "Cache actualizado"
        }
        
    except Exception as e:
        logging.error(f"Error verificando actualizaciones para {blob_display_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar actualizaciones: {str(e)}"
        )


# (upload/clear SKU Hijo y SKU Padre no cambian)
@app.post("/api/files/upload/sku-hijo", summary="Subir archivo SKU Hijo")
async def api_upload_sku_hijo(file: UploadFile = File(...)):
    # ... código sin cambios ...
    try:
        contents = await file.read()
        sku_list = main_logic.process_sku_file_upload(contents, file.filename)
        # Actualizar tanto main_logic (para compatibilidad) como FilterService
        main_logic.sku_hijo_filter_list = sku_list
        get_filter_service().set_sku_hijo_filter_list(sku_list)
        count = len(sku_list) if sku_list else 0
        return {"message": f"Archivo SKU Hijo procesado con {count} SKUs.", "sku_count": count}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error subiendo SKU Hijo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar archivo SKU Hijo.")
    finally:
        if file: 
            await file.close()

@app.delete("/api/files/sku-hijo", summary="Limpiar filtro SKU Hijo")
async def api_clear_sku_hijo():
    # ... código sin cambios ...
    main_logic.sku_hijo_filter_list = None
    get_filter_service().set_sku_hijo_filter_list(None)
    # --- AÑADIR ESTA LÍNEA ---
    logging.info("DEBUG: La variable global 'sku_hijo_filter_list' ha sido establecida a None.")
    return {"message": "Filtro SKU Hijo limpiado."}

@app.post("/api/files/upload/sku-padre", summary="Subir archivo SKU Padre")
async def api_upload_sku_padre(file: UploadFile = File(...)):
    # ... código sin cambios ...
    try:
        contents = await file.read()
        sku_list = main_logic.process_sku_file_upload(contents, file.filename)
        # Actualizar tanto main_logic (para compatibilidad) como FilterService
        main_logic.sku_padre_filter_list = sku_list
        get_filter_service().set_sku_padre_filter_list(sku_list)
        count = len(sku_list) if sku_list else 0
        return {"message": f"Archivo SKU Padre procesado con {count} SKUs.", "sku_count": count}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error subiendo SKU Padre: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar archivo SKU Padre.")
    finally:
        if file: 
            await file.close()

@app.delete("/api/files/sku-padre", summary="Limpiar filtro SKU Padre")
async def api_clear_sku_padre():
    # ... código sin cambios ...
    main_logic.sku_padre_filter_list = None
    get_filter_service().set_sku_padre_filter_list(None)
    # --- AÑADIR ESTA LÍNEA ---
    logging.info("DEBUG: La variable global 'sku_padre_filter_list' ha sido establecida a None.")
    return {"message": "Filtro SKU Padre limpiado."}

# --- NUEVOS ENDPOINTS PARA ARCHIVO DE TICKETS ---
@app.post("/api/files/upload/ticket-file", summary="Subir archivo de Tickets")
async def api_upload_ticket_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # Reutilizamos la misma función de procesamiento, ya que la lógica es idéntica
        ticket_list = main_logic.process_sku_file_upload(contents, file.filename)
        # Actualizar tanto main_logic (para compatibilidad) como FilterService
        main_logic.ticket_filter_list = ticket_list
        get_filter_service().set_ticket_filter_list(ticket_list)
        count = len(ticket_list) if ticket_list else 0
        return {"message": f"Archivo de Tickets procesado con {count} Tickets.", "ticket_count": count}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error subiendo archivo de Tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar archivo de Tickets.")
    finally:
        if file:
            await file.close()

@app.delete("/api/files/ticket-file", summary="Limpiar filtro de Tickets desde archivo")
async def api_clear_ticket_file():
    main_logic.ticket_filter_list = None
    get_filter_service().set_ticket_filter_list(None)
    return {"message": "Filtro de Tickets por archivo limpiado."}


@app.post("/api/data/filter", summary="Aplicar filtros y obtener datos resultantes")
async def api_filter_data(request: FilterRequest):
    """Aplica filtros y retorna datos resultantes con auto-corrección de sincronización."""
    logging.debug(f"Filter request: blob={request.blob_filename}, filters={len(request.value_filters)}")
    
    if main_logic.df_original.empty:
        logging.warning("Intento de filtrar sin datos originales cargados.")
        return _empty_filter_response("No hay datos originales cargados. Por favor, carga datos primero.")

    # 🔥 NUEVO COMPORTAMIENTO: Solo detectar desajuste, NO auto-corregir automáticamente
    if request.blob_filename and request.blob_filename != main_logic.current_blob_display_name:
        logging.info(f"Desajuste detectado: Frontend solicita '{request.blob_filename}' "
                       f"pero backend tiene '{main_logic.current_blob_display_name}'. "
                       f"Usuario debe presionar 'Carga Rápida' para sincronizar.")
        
        # Verificar si la base solicitada está en caché
        cache_key = request.blob_filename.upper()
        cache_available = cache_key in main_logic.loaded_dataframes_cache
        cache_status = "disponible en caché" if cache_available else "requiere descarga"
        
        # 🚨 NO ejecutar auto-corrección - devolver respuesta informativa
        return JSONResponse(
            status_code=409,  # 409 Conflict - estado desincronizado 
            content={
                "message": f"Base desincronizada: Frontend solicita '{request.blob_filename}' pero backend tiene '{main_logic.current_blob_display_name}'",
                "frontend_request": request.blob_filename,
                "backend_loaded": main_logic.current_blob_display_name,
                "cache_status": cache_status,
                "cache_available": cache_available,
                "action_required": "Presiona 'Carga Rápida' para cargar la base solicitada",
                "auto_correction": False
            }
        )

    try:
        result = await get_filter_service().apply_all_filters_safe(
            df_original=main_logic.df_original,
            duckdb_conn=main_logic.duckdb_conn,
            current_blob_display_name=main_logic.current_blob_display_name,
            value_filters=request.value_filters,
            use_sku_hijo_file=request.use_sku_hijo_file,
            extend_sku_hijo=request.extend_sku_hijo,
            sku_hijo_manual_list=request.sku_hijo_manual_list,
            use_sku_padre_file=request.use_sku_padre_file,
            sku_padre_manual_list=request.sku_padre_manual_list,
            use_ticket_file=request.use_ticket_file,
            ticket_manual_list=request.ticket_manual_list,
            lineamiento_manual_list=request.lineamiento_manual_list,
            selected_display_columns=request.selected_display_columns,
            enable_priority_coloring=request.enable_priority_coloring,
            page=request.page,
            page_size=request.page_size,
            custom_text_filters=request.custom_text_filters
        )
        return result
    except Exception as e:
        logging.error(f"Error aplicando filtros: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al aplicar filtros: {str(e)}")

def _empty_filter_response(message: str):
    """Genera respuesta estándar para filtros sin datos."""
    return JSONResponse(
        status_code=400, 
        content={"message": message, **_get_empty_response_data()}
    )

def _get_empty_response_data():
    """Datos estándar para respuestas vacías."""
    return {
        "row_count_filtered": 0,
        "data": [],
        "columns_in_data": []
    }

@app.post("/api/data/export", summary="Exportar datos filtrados a Excel")
@api_error_handler
async def api_export_data(request: FilterRequest):
    """Exporta datos filtrados a Excel con manejo de errores centralizado."""
    operation_id = log_operation_start(OperationType.DATA_EXPORT, {"blob": request.blob_filename})
    
    if main_logic.df_original.empty:
        raise ValueError("No hay datos originales cargados para exportar")

    try:
        excel_path = await get_export_service().get_excel_export_safe(
            df_original=main_logic.df_original,
            duckdb_conn=main_logic.duckdb_conn,
            current_blob_display_name=main_logic.current_blob_display_name,
            filter_service=get_filter_service(),
            value_filters=request.value_filters,
            use_sku_hijo_file=request.use_sku_hijo_file,
            extend_sku_hijo=request.extend_sku_hijo,
            sku_hijo_manual_list=request.sku_hijo_manual_list,
            use_sku_padre_file=request.use_sku_padre_file,
            sku_padre_manual_list=request.sku_padre_manual_list,
            use_ticket_file=request.use_ticket_file,
            ticket_manual_list=request.ticket_manual_list,
            lineamiento_manual_list=request.lineamiento_manual_list,
            selected_display_columns=request.selected_display_columns,
            enable_priority_coloring=request.enable_priority_coloring,
            custom_text_filters=request.custom_text_filters
        )
        
        current_display_name = main_logic.current_blob_display_name or "datos"
        filename = f"{current_display_name}_filtrado_{main_logic.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        def iterfile(path: str):
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
            os.remove(path)

        log_operation_end(operation_id, OperationType.DATA_EXPORT, True, {"filename": filename})
        
        return StreamingResponse(
            iterfile(excel_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        log_operation_end(operation_id, OperationType.DATA_EXPORT, False, {"error": str(e)})
        raise


@app.post("/api/data/export-cancel", summary="Cancelar exportación en curso")
async def api_cancel_export():
    """Cancela la exportación en curso si existe."""
    try:
        get_export_service().request_export_cancellation()
        return {"message": "Cancelación de exportación solicitada."}
    except Exception as e:
        logging.error(f"Error al cancelar exportación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al cancelar exportación: {str(e)}")


@app.post("/api/data/export-csv", summary="Exportar datos filtrados a CSV")
async def api_export_data_csv(request: FilterRequest):
    if main_logic.df_original.empty:
        raise HTTPException(status_code=400, detail="No hay datos originales cargados para exportar.")

    try:
        csv_generator = await get_export_service().get_csv_export_safe(
            df_original=main_logic.df_original,
            duckdb_conn=main_logic.duckdb_conn,
            current_blob_display_name=main_logic.current_blob_display_name,
            filter_service=get_filter_service(),
            value_filters=request.value_filters,
            use_sku_hijo_file=request.use_sku_hijo_file,
            extend_sku_hijo=request.extend_sku_hijo,
            sku_hijo_manual_list=request.sku_hijo_manual_list,
            use_sku_padre_file=request.use_sku_padre_file,
            sku_padre_manual_list=request.sku_padre_manual_list,
            use_ticket_file=request.use_ticket_file,
            ticket_manual_list=request.ticket_manual_list,
            lineamiento_manual_list=request.lineamiento_manual_list,
            selected_display_columns=request.selected_display_columns,
            enable_priority_coloring=request.enable_priority_coloring,
            custom_text_filters=request.custom_text_filters
        )

        current_display_name = main_logic.current_blob_display_name or "datos"
        filename = f"{current_display_name}_filtrado_{main_logic.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            csv_generator(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except InterruptedError:
        raise HTTPException(status_code=499, detail="Exportación cancelada por el usuario.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error exportando a CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al exportar datos: {str(e)}")

# (save/load state, log stream y refresh_data no cambian)
# ... resto de endpoints sin cambios ...
@app.post("/api/state/save/{blob_display_name}", summary="Guardar estado de filtros")
async def api_save_state(blob_display_name: str, state: SaveStateRequest):
    # ... código sin cambios ...
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible para guardar.")
    try:
        success = main_logic.save_current_filter_state_to_config(
            blob_display_name=blob_display_name,
            value_filters_state=state.value_filters,
            selected_columns_state=state.selected_columns,
            extend_sku_search_state=state.extend_sku_search
        )
        if success:
            return {"message": "Estado guardado exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="No se pudo guardar el estado en el archivo de configuración.")
    except Exception as e:
        logging.error(f"Error guardando estado para {blob_display_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al guardar estado: {str(e)}")


@app.get("/api/state/load/{blob_display_name}", summary="Cargar estado de filtros guardado")
async def api_load_state(blob_display_name: str):
    # ... código sin cambios ...
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible para cargar estado.")

    state = main_logic.load_filter_state_from_config(blob_display_name)
    if state:
        return state
    else:
        return {"message": f"No se encontró estado guardado para {blob_display_name}.",
                "value_filters": {}, "selected_columns": [], "extend_sku_search": False}


# ===== ENDPOINTS DE FAVORITOS (Sistema independiente de puerto) =====

@app.post("/api/favorites/save", summary="Guardar favorito para base de datos específica")
async def api_save_favorite(request: Request):
    """
    Guarda un favorito en config.ini del servidor para una base de datos específica.
    Cada base de datos tiene su propio favorito independiente.
    """
    try:
        data = await request.json()
        database_name = data.get('database_name')

        if not database_name:
            raise HTTPException(status_code=400, detail="database_name es requerido")

        state = {
            'value_filters': data.get('value_filters', {}),
            'selected_columns': data.get('selected_columns', []),
            'extend_sku_search': data.get('extend_sku_search', False)
        }

        success = main_logic.save_favorite_to_config(state, database_name)

        if success:
            return JSONResponse({
                'status': 'success',
                'message': f'Favorito guardado exitosamente para {database_name}'
            })
        else:
            raise HTTPException(status_code=500, detail="Error al guardar favorito en config.ini")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en api_save_favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/favorites/load/{database_name}", summary="Cargar favorito para base de datos específica")
async def api_load_favorite(database_name: str):
    """
    Carga el favorito guardado desde config.ini para una base de datos específica.
    Cada base de datos tiene su propio favorito independiente.
    """
    try:
        favorite = main_logic.load_favorite_from_config(database_name)

        if favorite:
            return JSONResponse({
                'status': 'success',
                'data': favorite
            })
        else:
            raise HTTPException(status_code=404, detail=f"No hay favorito guardado para {database_name}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en api_load_favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/favorites/delete/{database_name}", summary="Eliminar favorito de base de datos específica")
async def api_delete_favorite(database_name: str):
    """
    Elimina el favorito guardado de config.ini para una base de datos específica.
    """
    try:
        success = main_logic.delete_favorite_from_config(database_name)

        if success:
            return JSONResponse({
                'status': 'success',
                'message': f'Favorito eliminado exitosamente para {database_name}'
            })
        else:
            raise HTTPException(status_code=404, detail=f"No había favorito para eliminar en {database_name}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en api_delete_favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/favorites/has/{database_name}", summary="Verificar si existe favorito para base de datos")
async def api_has_favorite(database_name: str):
    """
    Verifica si existe un favorito guardado para una base de datos específica.
    Retorna metadata básica si existe.
    """
    try:
        metadata = main_logic.has_favorite_for_database(database_name)

        if metadata:
            return JSONResponse({
                'status': 'success',
                'data': metadata
            })
        else:
            return JSONResponse({
                'status': 'success',
                'data': {
                    'exists': False,
                    'database_name': database_name
                }
            })
    except Exception as e:
        logging.error(f"Error en api_has_favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def log_generator(request_param: Request):
    # ... código sin cambios ...
    initial_logs = list(log_queue) 
    for log_entry in initial_logs:
        if await request_param.is_disconnected():
            logging.info("Cliente SSE de logs desconectado (envió iniciales).")
            break
        yield f"data: {log_entry}\n\n"
        await asyncio.sleep(0.01) 

    while True:
        if await request_param.is_disconnected():
            logging.info("Cliente SSE de logs desconectado (esperando nuevos).")
            break
        try:
            await asyncio.wait_for(new_log_event.wait(), timeout=15) 
        except asyncio.TimeoutError:
            yield ": keep-alive\n\n" 
            continue 
        
        if log_queue: 
            try:
                latest_log = log_queue[-1] 
                yield f"data: {latest_log}\n\n"
            except IndexError: 
                pass 
        
        await asyncio.sleep(0.01)

@app.get("/api/logs/stream", summary="Flujo de logs del servidor (SSE)")
async def stream_logs(request: Request):
    # ... código sin cambios ...
    return StreamingResponse(log_generator(request), media_type="text/event-stream")


async def data_load_progress_generator(request_param: Request):
    """Generador async para transmitir progreso de carga de datos via SSE.

    Consume del queue.Queue síncrono (thread-safe) que se alimenta desde ThreadPoolExecutor.
    """
    logging.info("Cliente SSE de progreso de carga conectado")

    while True:
        if await request_param.is_disconnected():
            logging.info("Cliente SSE de progreso de carga desconectado")
            break

        try:
            # Consumir del queue síncrono con timeout
            # Usar run_in_executor para no bloquear el event loop
            loop = asyncio.get_running_loop()

            # Ejecutar get() del queue síncrono en executor
            message_data = await loop.run_in_executor(
                None,
                lambda: data_load_progress_queue.get(timeout=15)
            )

            # Enviar el mensaje de progreso al cliente
            yield f"data: {json.dumps(message_data)}\n\n"

        except queue.Empty:
            # Keep-alive cada 15 segundos si no hay mensajes
            yield ": keep-alive\n\n"
            continue
        except Exception as e:
            logging.error(f"Error en generador SSE de progreso de carga: {e}")
            break

        await asyncio.sleep(0.01)


@app.get("/api/progress/load/stream", summary="Flujo de progreso de carga de datos (SSE)")
async def stream_data_load_progress(request: Request):
    """
    Endpoint SSE para transmitir progreso en tiempo real de la carga de datos.

    Los clientes reciben eventos JSON con información sobre:
    - Porcentaje de progreso (0-100)
    - Etapa actual del procesamiento
    - Mensajes descriptivos
    - Estado de completitud

    Ejemplo de mensaje:
    {
        "type": "progress",
        "progress_percent": 45,
        "message": "Procesando datos...",
        "stage": "processing"
    }
    """
    return StreamingResponse(
        data_load_progress_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/data/refresh/{blob_display_name}", summary="Forzar recarga desde fuente y actualizar caché de datos")
async def api_refresh_data(blob_display_name: str, request: Optional[DataLoadRequest] = None):
    """Fuerza recarga de datos desde fuente original.

    Args:
        blob_display_name: Nombre de la fuente de datos
        request: Opcional - Request body con selected_columns para optimizar carga
    """
    # Extraer columnas seleccionadas si se proporcionaron
    selected_columns = None
    if request and request.selected_columns:
        selected_columns = request.selected_columns
        logging.info(f"Refresh solicitado con {len(selected_columns)} columnas específicas para '{blob_display_name}'")

    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible.")
    try:
        result = await get_data_service().refresh_blob_data_safe(blob_display_name, selected_columns=selected_columns)
        return result
    except ValueError as ve:
        logging.error(f"ValueError en api_refresh_data para {blob_display_name}: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error general en api_refresh_data para {blob_display_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar datos: {str(e)}")
    
@app.get("/api/debug/list-blobs", summary="[DEBUG] Listar todos los blobs en el contenedor")
async def api_debug_list_blobs():
    """
    Endpoint de diagnóstico para listar todos los archivos en el contenedor de Azure.
    Esto ayuda a verificar que las rutas en config.ini son correctas.
    """
    if not main_logic.config_data.get("connection_string") or not main_logic.config_data.get("container_name"):
        raise HTTPException(status_code=503, detail="Configuración de Azure no disponible.")
    try:
        from azure.storage.blob import BlobServiceClient
        
        blob_service_client = BlobServiceClient.from_connection_string(main_logic.config_data["connection_string"])
        container_client = blob_service_client.get_container_client(main_logic.config_data["container_name"])
        
        blob_list = [blob.name for blob in container_client.list_blobs(name_starts_with="paola/")]
        
        return {"blob_count_in_folder": len(blob_list), "blobs_in_paola_folder": blob_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando con Azure o listando blobs: {str(e)}")    
    


# --- FUNCIÓN AUXILIAR PARA EJECUTAR SCRIPTS ---
def _execute_script_sync(script_path: str, script_dir: str) -> dict:
    """
    Función síncrona para ejecutar un script en un proceso separado.
    Esta función se ejecuta en un thread separado para no bloquear el event loop.
    """
    try:
        # Ejecuta el script en un proceso separado para no bloquear la API.
        # El script abrirá su propia ventana si es una app de GUI.
        process = subprocess.Popen(
            [sys.executable, script_path], 
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # No esperamos a que termine el proceso para permitir scripts GUI de larga duración
        # Simplemente verificamos que se haya iniciado correctamente
        return {
            "success": True,
            "pid": process.pid,
            "message": f"Script iniciado correctamente con PID {process.pid}"
        }
    except Exception as e:
        logging.error(f"Error ejecutando script '{script_path}': {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error al iniciar el script: {str(e)}"
        }

# --- ENDPOINT PARA EJECUTAR SCRIPTS (ASYNC) ---
@app.post("/api/run-script", summary="Ejecutar un script de herramienta local de forma asíncrona")
async def run_script(request: ScriptRequest):
    script_path = ALLOWED_SCRIPTS.get(request.script_id)

    if not script_path:
        raise HTTPException(status_code=404, detail="Script no encontrado o no permitido.")

    if not os.path.exists(script_path):
        logging.error(f"El archivo de script no existe en la ruta: {script_path}")
        raise HTTPException(status_code=500, detail="El archivo de script no fue encontrado en el servidor.")

    try:
        script_dir = os.path.dirname(script_path)
        
        # Ejecutar el script de forma asíncrona usando ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            script_executor,
            _execute_script_sync,
            script_path,
            script_dir
        )
        
        if result["success"]:
            logging.info(f"Script '{request.script_id}' iniciado exitosamente. PID: {result.get('pid')}")
            return {
                "message": f"El script '{request.script_id}' se ha iniciado de forma asíncrona.",
                "script_id": request.script_id,
                "pid": result.get("pid"),
                "status": "started"
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint run_script para '{request.script_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al iniciar el script: {str(e)}")

@app.delete("/api/cache/clear", summary="Limpiar completamente el caché del servidor")
async def api_clear_cache():
    """
    Endpoint para limpiar completamente el caché del servidor.
    Elimina todos los datos cargados en memoria y limpia los caches.
    """
    try:
        # Limpiar variables globales del estado actual
        import pandas as pd
        main_logic.df_original = pd.DataFrame()
        main_logic.df_filtered = pd.DataFrame()
        main_logic.current_blob_display_name = None
        
        # Limpiar filtros de archivos
        main_logic.sku_hijo_filter_list = None
        main_logic.sku_padre_filter_list = None
        main_logic.ticket_filter_list = None
        
        # Limpiar cachés TTL
        main_logic.loaded_dataframes_cache.clear()
        main_logic.cached_filter_options.clear() 
        main_logic.cached_metadata.clear()
        
        # Cerrar conexión DuckDB si existe
        if main_logic.duckdb_conn:
            try:
                main_logic.duckdb_conn.close()
                main_logic.duckdb_conn = None
            except Exception as e:
                logging.warning(f"Error cerrando conexión DuckDB: {e}")
        
        logging.info("Caché del servidor limpiado completamente")
        return {
            "success": True,
            "message": "Caché del servidor limpiado exitosamente",
            "cleared_items": {
                "dataframes": True,
                "filter_options": True,
                "metadata": True,
                "current_state": True,
                "file_filters": True,
                "duckdb_connection": True
            }
        }
        
    except Exception as e:
        logging.error(f"Error limpiando caché del servidor: {e}")
        return {
            "success": False,
            "message": f"Error al limpiar caché: {str(e)}"
        }

@app.get("/api/cache/status", summary="Consultar estado actual del caché de datos")
async def api_get_cache_status():
    """
    Endpoint para consultar qué datos están actualmente cargados en caché.
    Útil para mostrar al usuario qué bases están disponibles sin necesidad de carga completa.
    """
    try:
        cache_status = {
            "has_data_loaded": not main_logic.df_original.empty,
            "current_blob_display_name": main_logic.current_blob_display_name,
            "row_count": len(main_logic.df_original) if not main_logic.df_original.empty else 0,
            "columns_count": len(main_logic.df_original.columns) if not main_logic.df_original.empty else 0,
            "available_columns": list(main_logic.df_original.columns) if not main_logic.df_original.empty else [],
            "sku_hijo_loaded": main_logic.sku_hijo_filter_list is not None,
            "sku_padre_loaded": main_logic.sku_padre_filter_list is not None,
            "ticket_loaded": main_logic.ticket_filter_list is not None
        }
        return cache_status
    except Exception as e:
        logging.error(f"Error consultando estado del caché: {e}")
        return {
            "has_data_loaded": False,
            "current_blob_display_name": None,
            "row_count": 0,
            "columns_count": 0,
            "available_columns": [],
            "sku_hijo_loaded": False,
            "sku_padre_loaded": False,
            "ticket_loaded": False,
            "error": str(e)
        }

@app.get("/api/health", summary="Verificar estado del servidor")
async def health_check():
    """
    Endpoint para verificar que el servidor esté funcionando correctamente.
    """
    try:
        # Verificar que la configuración esté cargada
        if not main_logic.config_data.get("config_parser"):
            return {"status": "error", "message": "Configuración no disponible"}
        
        # Verificar que las rutas básicas estén disponibles
        return {
            "status": "healthy",
            "message": "Servidor funcionando correctamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Error en health check: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/system/capabilities", summary="Obtener capabilities del sistema")
async def get_capabilities():
    """
    Endpoint para verificar las capabilities disponibles del sistema.
    Permite al frontend adaptar la interfaz según las dependencias disponibles.
    """
    try:
        capabilities = get_system_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities
        }
    except Exception as e:
        logging.error(f"Error obteniendo capabilities: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "capabilities": {
                "duckdb_available": False,
                "opencv_available": False,
                "reportes_full": False,
                "reportes_light": True,
                "ahead_tool": False,
            }
        }

@app.post("/api/diagnostics/network", summary="Recibir diagnósticos de red del cliente")
async def receive_network_diagnostics(diagnostics: dict):
    """
    Endpoint para recibir reportes de diagnóstico de red desde el frontend.
    Útil para analizar patrones de conectividad de usuarios con problemas.
    """
    try:
        # Log estructurado para análisis posterior
        logging.warning(
            f"NETWORK_DIAGNOSTIC: "
            f"Error={diagnostics.get('error', {}).get('message', 'Unknown')} "
            f"Endpoint={diagnostics.get('endpoint', 'Unknown')} "
            f"UserAgent={diagnostics.get('browser', {}).get('userAgent', 'Unknown')[:50]} "
            f"Connection={diagnostics.get('network', {}).get('connection', 'Unknown')} "
            f"Online={diagnostics.get('network', {}).get('online', 'Unknown')} "
            f"Timestamp={diagnostics.get('timestamp', 'Unknown')}"
        )
        
        # También log completo para debug detallado
        logging.debug(f"Network diagnostics full report: {json.dumps(diagnostics, indent=2)}")
        
        return {
            "status": "received",
            "message": "Diagnósticos de red recibidos correctamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Error procesando diagnósticos de red: {e}")
        return {
            "status": "error",
            "message": "Error al procesar diagnósticos"
        }

# --- ENDPOINTS PARA LA FUNCIONALIDAD DE DECLARACIONES ---
@app.get("/api/team-members", summary="Obtener lista de integrantes del equipo")
async def api_get_team_members():
    """Obtiene la lista de integrantes del equipo disponibles para declaraciones."""
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible.")
    
    try:
        team_members = main_logic.get_team_members()
        return {"team_members": team_members}
    except Exception as e:
        logging.error(f"Error al obtener integrantes del equipo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/api/declarations/load", summary="Cargar declaración al archivo Excel de SharePoint")
async def api_load_declaration(request: DeclarationRequest):
    """Carga una declaración al archivo Excel de SharePoint correspondiente al integrante del equipo."""
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible.")
    
    try:
        result = main_logic.load_declaration_to_sharepoint(
            team_member=request.team_member,
            declaration_text=request.declaration_text
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['message'])
            
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error al cargar declaración: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# --- ENDPOINTS PARA LA FUNCIONALIDAD DE RECHAZOS ---
@app.get("/api/team-members-reject", summary="Obtener lista de integrantes del equipo para rechazos")
async def api_get_team_members_reject():
    """Obtiene la lista de integrantes del equipo disponibles para rechazos."""
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible.")
    
    try:
        team_members = main_logic.get_team_members_reject()
        return {"team_members": team_members}
    except Exception as e:
        logging.error(f"Error al obtener integrantes del equipo para rechazos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/api/rejections/load", summary="Cargar rechazo al archivo Excel de SharePoint")
async def api_load_rejection(request: RejectionRequest):
    """Carga un rechazo al archivo Excel de SharePoint correspondiente al integrante del equipo."""
    if not main_logic.config_data.get("config_parser"):
        raise HTTPException(status_code=503, detail="Configuración no disponible.")
    
    try:
        result = main_logic.load_rejection_to_sharepoint(
            team_member=request.team_member,
            rejection_text=request.rejection_text,
            rejection_obs=request.rejection_obs
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['message'])
            
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error al cargar rechazo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# --- ENDPOINTS DE SHAREPOINT MOVIDOS A endpoints_sharepoint.py ---

# --- ENDPOINTS SSE MOVIDOS A endpoints_sharepoint.py ---
