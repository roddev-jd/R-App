"""
Async SharePoint Service - Fase 2.1
Operaciones SharePoint asíncronas usando aiohttp + Microsoft Graph API

Este módulo proporciona funciones async para:
- Descarga de archivos desde SharePoint
- Obtención de metadata de archivos
- Verificación de actualizaciones (last_modified)

Reutiliza la autenticación MSAL existente del módulo sharepoint_service.py

Fecha: 2025-11-14
Versión: 2.0.5
Parte de: FASE 2 - Hito 2.1: Operaciones I/O Asíncronas
"""

import io
import logging
import asyncio
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from urllib.parse import quote

# Importar autenticación MSAL existente
from .sharepoint_service import get_sharepoint_authenticator, SharePointAuth

# HTTP async imports
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logging.warning("aiohttp no disponible. Instalar con: pip install aiohttp")

# Pandas para lectura de Excel/CSV
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# =============================================================================
# CONSTANTES
# =============================================================================

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=300, connect=60, sock_read=120)  # 5 min total


# =============================================================================
# SHAREPOINT - ASYNC DOWNLOAD
# =============================================================================

async def download_from_sharepoint_async(
    file_url: str,
    access_token: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    timeout: Optional[aiohttp.ClientTimeout] = None
) -> bytes:
    """
    Descarga un archivo desde SharePoint usando Microsoft Graph API de forma asíncrona.

    Args:
        file_url: URL del archivo en SharePoint (formato Graph API)
        access_token: Token de acceso de MSAL
        progress_callback: Función callback opcional para reportar progreso (downloaded, total)
        timeout: Timeout personalizado (usa DEFAULT_TIMEOUT si no se proporciona)

    Returns:
        bytes: Contenido del archivo descargado

    Raises:
        aiohttp.ClientError: Errores de conexión HTTP
        Exception: Otros errores
    """
    if not AIOHTTP_AVAILABLE:
        raise ImportError("aiohttp no está instalado. Ejecutar: pip install aiohttp")

    logging.info(f"⚡ [ASYNC] Descargando desde SharePoint: {file_url}")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    timeout_config = timeout or DEFAULT_TIMEOUT

    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        # Primer request: obtener metadata del archivo
        async with session.get(file_url, headers=headers) as metadata_response:
            metadata_response.raise_for_status()
            file_metadata = await metadata_response.json()

            # Obtener URL de descarga
            download_url = file_metadata.get('@microsoft.graph.downloadUrl')
            if not download_url:
                raise ValueError("No se encontró URL de descarga en la respuesta de Graph API")

            file_size = file_metadata.get('size', 0)
            file_name = file_metadata.get('name', 'unknown')

            logging.info(f"📊 Archivo: {file_name}, Tamaño: {file_size / 1024 / 1024:.2f} MB")

        # Segundo request: descargar el archivo usando la URL directa
        async with session.get(download_url) as download_response:
            download_response.raise_for_status()

            # Leer en chunks para permitir progress tracking
            blob_content = bytearray()
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB chunks

            async for chunk in download_response.content.iter_chunked(chunk_size):
                blob_content.extend(chunk)
                downloaded += len(chunk)

                # Reportar progreso
                if progress_callback and file_size > 0:
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(downloaded, file_size)
                        else:
                            progress_callback(downloaded, file_size)
                    except Exception as e:
                        logging.warning(f"Error en progress_callback: {e}")

    logging.info(f"✅ [ASYNC] Archivo SharePoint descargado: {len(blob_content) / 1024 / 1024:.2f} MB")
    return bytes(blob_content)


async def download_sharepoint_file_with_auth_async(
    site_id: str,
    drive_id: str,
    item_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bytes:
    """
    Descarga un archivo de SharePoint usando autenticación MSAL existente.
    Función wrapper de alto nivel que maneja la autenticación automáticamente.

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo (ej: "/carpeta/archivo.xlsx")
        progress_callback: Función callback opcional para progreso

    Returns:
        bytes: Contenido del archivo
    """
    # Obtener token usando el autenticador existente (síncrono)
    auth = get_sharepoint_authenticator()
    access_token = await asyncio.to_thread(auth.get_token)

    # Construir URL de Graph API
    # Formato: /sites/{site-id}/drives/{drive-id}/root:/{item-path}
    encoded_path = quote(item_path)
    file_url = f"{GRAPH_API_BASE}/sites/{site_id}/drives/{drive_id}/root:{encoded_path}"

    # Descargar usando la función async
    return await download_from_sharepoint_async(file_url, access_token, progress_callback)


async def read_excel_from_sharepoint_async(
    site_id: str,
    drive_id: str,
    item_path: str,
    sheet_name: Optional[str] = None,
    usecols: Optional[list] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> pd.DataFrame:
    """
    Lee un archivo Excel desde SharePoint de forma asíncrona.

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo Excel
        sheet_name: Nombre de la hoja (None = primera hoja)
        usecols: Lista de columnas a leer (None = todas)
        progress_callback: Función callback para progreso

    Returns:
        pd.DataFrame: Datos del Excel
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas no está instalado")

    # Descargar el archivo
    file_content = await download_sharepoint_file_with_auth_async(
        site_id,
        drive_id,
        item_path,
        progress_callback
    )

    # Parsear Excel en thread separado (CPU-bound)
    logging.info("📊 Parseando archivo Excel...")
    df = await asyncio.to_thread(
        pd.read_excel,
        io.BytesIO(file_content),
        sheet_name=sheet_name,
        usecols=usecols,
        engine='openpyxl'
    )

    logging.info(f"✅ Excel parseado: {len(df)} filas, {len(df.columns)} columnas")
    return df


async def read_csv_from_sharepoint_async(
    site_id: str,
    drive_id: str,
    item_path: str,
    encoding: str = 'utf-8',
    usecols: Optional[list] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> pd.DataFrame:
    """
    Lee un archivo CSV desde SharePoint de forma asíncrona.

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo CSV
        encoding: Codificación del archivo (default: utf-8)
        usecols: Lista de columnas a leer (None = todas)
        progress_callback: Función callback para progreso

    Returns:
        pd.DataFrame: Datos del CSV
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas no está instalado")

    # Descargar el archivo
    file_content = await download_sharepoint_file_with_auth_async(
        site_id,
        drive_id,
        item_path,
        progress_callback
    )

    # Parsear CSV en thread separado (CPU-bound)
    logging.info("📊 Parseando archivo CSV...")
    df = await asyncio.to_thread(
        pd.read_csv,
        io.BytesIO(file_content),
        encoding=encoding,
        usecols=usecols
    )

    logging.info(f"✅ CSV parseado: {len(df)} filas, {len(df.columns)} columnas")
    return df


# =============================================================================
# SHAREPOINT - METADATA & PROPERTIES
# =============================================================================

async def get_sharepoint_file_metadata_async(
    site_id: str,
    drive_id: str,
    item_path: str
) -> Dict[str, Any]:
    """
    Obtiene metadata de un archivo de SharePoint sin descargarlo.
    Útil para verificar actualizaciones (lastModifiedDateTime).

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo

    Returns:
        Dict con metadata del archivo (name, size, lastModifiedDateTime, etc.)
    """
    if not AIOHTTP_AVAILABLE:
        raise ImportError("aiohttp no está instalado")

    # Obtener token
    auth = get_sharepoint_authenticator()
    access_token = await asyncio.to_thread(auth.get_token)

    # Construir URL
    encoded_path = quote(item_path)
    file_url = f"{GRAPH_API_BASE}/sites/{site_id}/drives/{drive_id}/root:{encoded_path}"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        async with session.get(file_url, headers=headers) as response:
            response.raise_for_status()
            metadata = await response.json()

            return {
                'name': metadata.get('name'),
                'size': metadata.get('size'),
                'last_modified': metadata.get('lastModifiedDateTime'),
                'created': metadata.get('createdDateTime'),
                'etag': metadata.get('eTag'),
                'web_url': metadata.get('webUrl'),
                '@microsoft.graph.downloadUrl': metadata.get('@microsoft.graph.downloadUrl'),
            }


async def check_sharepoint_file_updated_async(
    site_id: str,
    drive_id: str,
    item_path: str,
    cache_timestamp: datetime
) -> bool:
    """
    Verifica si un archivo de SharePoint ha sido actualizado desde un timestamp dado.

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo
        cache_timestamp: Timestamp del caché local para comparar

    Returns:
        bool: True si el archivo remoto es más nuevo que el caché
    """
    metadata = await get_sharepoint_file_metadata_async(site_id, drive_id, item_path)

    last_modified_str = metadata.get('last_modified')
    if not last_modified_str:
        logging.warning(f"No se pudo obtener lastModifiedDateTime para {item_path}")
        return True  # Asumir que hay actualización si no podemos verificar

    # Parsear timestamp de SharePoint (formato ISO 8601)
    remote_time = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))

    # Comparar
    is_updated = remote_time > cache_timestamp

    if is_updated:
        logging.info(f"🔄 Archivo SharePoint actualizado: {remote_time} > {cache_timestamp}")
    else:
        logging.info(f"✅ Archivo SharePoint sin cambios: {remote_time} <= {cache_timestamp}")

    return is_updated


# =============================================================================
# WRAPPER CON PROGRESS TRACKING COMPATIBLE
# =============================================================================

async def download_sharepoint_with_progress_async(
    site_id: str,
    drive_id: str,
    item_path: str,
    progress_tracker: Optional[Any] = None,
    step: int = 3
) -> bytes:
    """
    Descarga archivo de SharePoint con tracking de progreso compatible con SSE.

    Args:
        site_id: ID del sitio de SharePoint
        drive_id: ID del drive
        item_path: Ruta del archivo
        progress_tracker: Objeto con método update_progress(step, status, message)
        step: Número de paso para progress tracking

    Returns:
        bytes: Contenido del archivo descargado
    """
    start_time = datetime.now()

    # Progress callback que integra con progress_tracker
    async def update_progress(downloaded: int, total: int):
        if progress_tracker:
            percent = (downloaded / total * 100) if total > 0 else 0
            mb_downloaded = downloaded / 1024 / 1024
            mb_total = total / 1024 / 1024

            message = f"Descargando SharePoint: {mb_downloaded:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)"

            try:
                progress_tracker.update_progress(step, "processing", message)
            except Exception as e:
                logging.warning(f"Error actualizando progress_tracker: {e}")

    if progress_tracker:
        progress_tracker.update_progress(step, "processing", f"Iniciando descarga de {item_path}...")

    # Descargar
    file_content = await download_sharepoint_file_with_auth_async(
        site_id,
        drive_id,
        item_path,
        progress_callback=update_progress
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    speed_mbps = (len(file_content) / 1024 / 1024) / elapsed if elapsed > 0 else 0

    if progress_tracker:
        progress_tracker.update_progress(
            step,
            "completed",
            f"Descarga SharePoint completada: {len(file_content) / 1024 / 1024:.2f} MB en {elapsed:.1f}s ({speed_mbps:.2f} MB/s)"
        )

    return file_content


# =============================================================================
# UTILITIES
# =============================================================================

def check_async_sharepoint_availability() -> Dict[str, bool]:
    """
    Verifica disponibilidad de dependencias para SharePoint async.

    Returns:
        Dict con disponibilidad de cada librería
    """
    return {
        'aiohttp': AIOHTTP_AVAILABLE,
        'pandas': PANDAS_AVAILABLE,
    }


def log_async_sharepoint_availability():
    """
    Registra en el log la disponibilidad de librerías para SharePoint async.
    """
    availability = check_async_sharepoint_availability()

    logging.info("=== Disponibilidad SharePoint Async ===")
    for lib, available in availability.items():
        status = "✅" if available else "❌"
        logging.info(f"{status} {lib}: {'Disponible' if available else 'No instalado'}")


# Log availability al importar el módulo
log_async_sharepoint_availability()
