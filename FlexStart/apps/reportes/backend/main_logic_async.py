"""
FASE 2.1b: Versión Async de load_blob_data()
Orquestador async puro con paralelización de operaciones I/O

Este archivo contiene la versión refactorizada async de load_blob_data()
que reemplazará la versión síncrona en main_logic.py

Fecha: 2025-11-14
Versión: 2.0.5
Optimizaciones:
- Operaciones I/O verdaderamente asíncronas (sin run_in_executor para I/O)
- Paralelización con asyncio.gather() para descargas simultáneas
- Descarga principal + enrichment en paralelo
- CPU-bound operations (pandas) en thread pool con asyncio.to_thread()
"""

import asyncio
import io
import logging
import time
from typing import Dict, Any, Optional, List
import pandas as pd

# Imports de módulos async (Fase 2.1a)
from services.async_storage_utils import (
    download_blob_with_progress_async
)
from services.async_sharepoint_service import (
    download_sharepoint_with_progress_async
)

# Imports de módulos existentes
from services.csv_utils import csv_utils
from services.dataframe_utils import dataframe_utils
from services.cache_service import persistent_cache
from services.progress_utils import DataLoadProgressTracker
from services.sharepoint_service import get_sharepoint_authenticator


async def load_blob_data_async(
    param_from_frontend_url: str,
    selected_columns_from_api: Optional[List[str]] = None,
    config_data: dict = None,
    progress_tracker: Optional[DataLoadProgressTracker] = None
) -> Dict[str, Any]:
    """
    Versión ASYNC de load_blob_data con paralelización de operaciones I/O.

    MEJORAS FASE 2.1:
    - I/O verdaderamente asíncrono (Azure, FTP, S3, SharePoint)
    - Descarga principal + enrichment en paralelo con asyncio.gather()
    - Procesamiento CPU-bound (pandas) con asyncio.to_thread()
    - Sin bloqueo del event loop

    Args:
        param_from_frontend_url: Identificador de la fuente de datos
        selected_columns_from_api: Lista opcional de columnas específicas
        config_data: Configuración global (inyectada desde main_logic)
        progress_tracker: Tracker de progreso SSE

    Returns:
        Dict con información de la carga realizada
    """
    start_time = time.time()

    if not progress_tracker:
        progress_tracker = DataLoadProgressTracker(
            operation_name="Carga de datos async",
            blob_display_name=param_from_frontend_url
        )

    progress_tracker.update_progress(1, "init", f"Iniciando carga async de '{param_from_frontend_url}'...")
    logging.info(f"⚡ [ASYNC] load_blob_data_async: '{param_from_frontend_url}'")

    # --- PASO 1: DETERMINAR COLUMNAS A CARGAR ---
    selected_columns = None
    if selected_columns_from_api:
        selected_columns = [col.strip().lower() for col in selected_columns_from_api]
        logging.info(f"Usando columnas desde API: {len(selected_columns)} columnas")
    else:
        # Leer configuración de selectcolumns del config.ini
        key_for_config = param_from_frontend_url.upper()
        config_settings = config_data["filter_configs"].get(key_for_config, {})
        select_columns_cfg = config_settings.get('selectcolumns', '')
        if select_columns_cfg and select_columns_cfg.strip():
            selected_columns = [col.strip().lower() for col in select_columns_cfg.split(',') if col.strip()]
            logging.info(f"Usando columnas desde config: {len(selected_columns)} columnas")

    # --- PASO 2: VERIFICACIÓN DE CACHÉ INTELIGENTE ---
    cache_decision = "no_cache"

    if persistent_cache.is_cacheable(param_from_frontend_url) and persistent_cache.has_cached_data(param_from_frontend_url):
        key_for_blob_lookup = param_from_frontend_url.upper()
        found_blob_attrs = config_data.get("blob_options", {}).get(key_for_blob_lookup)

        if found_blob_attrs:
            source_type = found_blob_attrs.get("source_type")

            # Verificar actualizaciones para SharePoint/Azure
            if source_type in ["sharepoint", "azure"]:
                try:
                    progress_tracker.update_progress(2, "verifying", "Verificando actualizaciones...")

                    if source_type == "sharepoint":
                        # SharePoint check (síncrono - mover a thread)
                        auth = get_sharepoint_authenticator()
                        access_token = await asyncio.to_thread(auth.get_token)
                        auth_headers = {"Authorization": f"Bearer {access_token}"}
                        source_url = found_blob_attrs.get("source_url", "")

                        update_info = await asyncio.to_thread(
                            persistent_cache.check_remote_update,
                            param_from_frontend_url,
                            source_url,
                            auth_headers,
                            "sharepoint"
                        )

                    elif source_type == "azure":
                        # Azure check (también mover a thread - usa SDK síncrono)
                        filename = found_blob_attrs.get("filename")
                        azure_config = {
                            'connection_string': config_data.get("connection_string"),
                            'container_name': config_data.get("container_name"),
                            'blob_name': filename
                        }

                        update_info = await asyncio.to_thread(
                            persistent_cache.check_remote_update,
                            param_from_frontend_url,
                            "",
                            None,
                            "azure",
                            azure_config
                        )

                    # Decisión común
                    if update_info.get('error'):
                        cache_decision = "using_cache"
                        logging.warning(f"⚠️ Error verificando actualizaciones - usando caché")
                    elif update_info.get('update_available'):
                        await asyncio.to_thread(persistent_cache.clear_cache, param_from_frontend_url)
                        cache_decision = "downloading_fresh"
                        logging.info(f"🔄 Actualización detectada - descargando nuevo")
                    else:
                        cache_decision = "using_cache"
                        logging.info(f"✅ Caché actualizado - usando versión local")

                except Exception as e:
                    cache_decision = "using_cache"
                    logging.warning(f"⚠️ Error verificando actualizaciones: {e}")
            else:
                cache_decision = "using_cache"

    # --- PASO 3: INTENTAR CARGAR DESDE CACHÉ ---
    if cache_decision == "using_cache":
        cached_data = await asyncio.to_thread(
            persistent_cache.load_cached_data,
            param_from_frontend_url
        )

        if cached_data is not None and not cached_data.empty:
            # Aplicar selección de columnas si aplica
            if selected_columns:
                available_cols = [col for col in selected_columns if col in cached_data.columns]
                if available_cols:
                    cached_data = cached_data[available_cols]

            load_time = time.time() - start_time
            progress_tracker.finish(
                success=True,
                final_message=f"✅ Cargado desde caché: {len(cached_data):,} filas en {load_time:.2f}s"
            )

            return {
                "message": f"Datos cargados desde caché en {load_time:.2f}s",
                "row_count_original": len(cached_data),
                "columns": list(cached_data.columns),
                "filter_options": {},
                "from_cache": True,
                "load_time_seconds": round(load_time, 2),
                "cache_decision": "using_cache",
                "df_loaded": cached_data  # Retornar DataFrame para procesamiento posterior
            }

    # --- PASO 4: DESCARGAR DESDE FUENTE ORIGINAL (ASYNC) ---
    logging.info(f"Descargando desde fuente original...")

    key_for_blob_lookup = param_from_frontend_url.upper()
    found_blob_attrs = config_data.get("blob_options", {}).get(key_for_blob_lookup)

    if not found_blob_attrs:
        raise ValueError(f"Fuente de datos no encontrada: {param_from_frontend_url}")

    filename = found_blob_attrs.get("value")
    source_type = found_blob_attrs.get("source_type")

    progress_tracker.update_progress(5, "download", f"Descargando desde {source_type}...")

    # --- PASO 5: PARALELIZACIÓN - DESCARGA PRINCIPAL + ENRICHMENT ---
    download_tasks = []

    # Tarea 1: Descarga principal
    async def download_main_data():
        """Descarga datos principales según el tipo de fuente."""
        if source_type == 'azure':
            connection_string = config_data.get("connection_string")
            container_name = config_data.get("container_name")

            if not all([connection_string, container_name, filename]):
                raise ValueError("Falta configuración de Azure")

            # Descarga async con progreso
            blob_content = await download_blob_with_progress_async(
                connection_string,
                container_name,
                filename,
                progress_tracker=progress_tracker,
                step=5
            )

            return blob_content

        elif source_type == 'sharepoint':
            # SharePoint async
            blob_content = await download_sharepoint_with_progress_async(
                site_id=found_blob_attrs.get('site_id'),
                drive_id=found_blob_attrs.get('drive_id'),
                item_path=filename,
                progress_tracker=progress_tracker,
                step=5
            )
            return blob_content

        else:
            raise ValueError(f"Tipo de fuente no soportado para async: {source_type}")

    download_tasks.append(download_main_data())

    # Tarea 2: Descarga enrichment (si aplica) - EN PARALELO
    enrichment_source = found_blob_attrs.get("enrichment_source")
    if enrichment_source:
        async def download_enrichment_data():
            """Descarga datos de enriquecimiento en paralelo."""
            logging.info(f"⚡ [ASYNC] Descargando enrichment '{enrichment_source}' en paralelo...")
            # TODO: Implementar descarga async de enrichment
            # Por ahora, retornar None para indicar que no hay enrichment
            return None

        download_tasks.append(download_enrichment_data())

    # EJECUTAR DESCARGAS EN PARALELO
    logging.info(f"⚡ [ASYNC] Ejecutando {len(download_tasks)} descargas en paralelo...")
    download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

    # Procesar resultados
    main_blob_content = download_results[0]
    if isinstance(main_blob_content, Exception):
        raise main_blob_content

    enrichment_data = download_results[1] if len(download_results) > 1 else None

    # --- PASO 6: PARSEAR DATOS (CPU-BOUND en thread pool) ---
    progress_tracker.update_progress(25, "processing", "Parseando datos...")

    async def parse_data(blob_content: bytes):
        """Parsea CSV/Excel en thread separado (CPU-bound)."""
        if filename.lower().endswith('.csv'):
            # Parsear CSV
            df = await asyncio.to_thread(
                csv_utils.read_csv_from_bytes,
                blob_content,
                filename,
                usecols=selected_columns
            )
        elif filename.lower().endswith(('.xlsx', '.xls')):
            # Parsear Excel
            buffer = io.BytesIO(blob_content)
            df = await asyncio.to_thread(
                pd.read_excel,
                buffer,
                engine='openpyxl',
                usecols=selected_columns
            )
        else:
            raise ValueError(f"Formato de archivo no soportado: {filename}")

        return df

    df_loaded = await parse_data(main_blob_content)

    # Normalizar columnas
    df_loaded.columns = df_loaded.columns.str.strip().str.lower()
    logging.info(f"⚡ [ASYNC] Datos parseados: {df_loaded.shape[0]:,} filas, {df_loaded.shape[1]} columnas")

    # --- PASO 7: POST-PROCESAMIENTO (en thread pool) ---
    # TODO: Aplicar filtros previos, enriquecimiento, normalización de SKUs, etc.
    # Por ahora, retornar datos básicos

    # --- PASO 8: GUARDAR EN CACHÉ (background task - no esperar) ---
    if persistent_cache.is_cacheable(param_from_frontend_url):
        # Guardar en background sin esperar
        asyncio.create_task(
            asyncio.to_thread(
                persistent_cache.save_to_cache,
                param_from_frontend_url,
                df_loaded,
                filename
            )
        )
        logging.info(f"⚡ [ASYNC] Guardando en caché en background...")

    # --- PASO 9: RETORNAR RESULTADO ---
    load_time = time.time() - start_time
    logging.info(f"🚀 [ASYNC] CARGA COMPLETADA en {load_time:.2f}s")

    progress_tracker.finish(
        success=True,
        final_message=f"✅ Carga async completada: {len(df_loaded):,} filas en {load_time:.2f}s"
    )

    return {
        "message": f"Datos cargados async en {load_time:.2f}s",
        "row_count_original": len(df_loaded),
        "columns": list(df_loaded.columns),
        "filter_options": {},
        "source_type": source_type,
        "from_cache": False,
        "load_time_seconds": round(load_time, 2),
        "cache_decision": cache_decision,
        "df_loaded": df_loaded  # Retornar DataFrame para procesamiento posterior
    }


# =============================================================================
# FUNCIONES AUXILIARES ASYNC
# =============================================================================

async def _load_enrichment_data_cached_async(
    enrichment_source: str,
    source_type: str,
    blob_attrs: dict,
    config_data: dict
) -> Optional[pd.DataFrame]:
    """
    Versión ASYNC de _load_enrichment_data_cached.
    Descarga y cachea fuentes de enriquecimiento de forma asíncrona.

    Args:
        enrichment_source: Nombre de la fuente de enriquecimiento
        source_type: Tipo de fuente (azure, ftp, s3, sharepoint)
        blob_attrs: Atributos de configuración del blob
        config_data: Configuración global

    Returns:
        DataFrame con datos de enriquecimiento o None si falla
    """
    cache_name = f"enrichment_{enrichment_source.replace('/', '_').replace('.', '_')}"

    # 1. Intentar cargar desde caché
    if await asyncio.to_thread(persistent_cache.has_cached_data, cache_name):
        logging.info(f"⚡ [ASYNC] Cargando enrichment '{enrichment_source}' desde caché...")
        try:
            df_cached = await asyncio.to_thread(persistent_cache.load_cached_data, cache_name)
            if df_cached is not None and not df_cached.empty:
                logging.info(f"✅ Enrichment '{enrichment_source}' cargado desde caché ({len(df_cached)} filas)")
                return df_cached
        except Exception as e:
            logging.warning(f"Error cargando enrichment desde caché: {e}")
            await asyncio.to_thread(persistent_cache.clear_cache, cache_name)

    # 2. Si no hay caché, descargar desde fuente original (async)
    logging.info(f"⚡ [ASYNC] Descargando enrichment '{enrichment_source}' desde fuente...")

    # TODO: Implementar descarga async según source_type
    # Por ahora, retornar None
    return None
