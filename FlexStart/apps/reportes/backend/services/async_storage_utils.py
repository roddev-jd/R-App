"""
Async Storage Utilities - Fase 2.1
Operaciones I/O asíncronas para Azure Blob Storage y S3

Este módulo proporciona versiones async de las funciones de descarga para:
- Azure Blob Storage (usando azure.storage.blob.aio) - usado por Reportes
- S3 (usando aioboto3) - usado por prod_peru

Fecha: 2025-11-14
Versión: 2.0.5
Parte de: FASE 2 - Hito 2.1: Operaciones I/O Asíncronas
"""

import io
import logging
import asyncio
from typing import Optional, Callable, Any, Dict
from datetime import datetime

# Azure async imports
try:
    from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_ASYNC_AVAILABLE = True
except ImportError:
    AZURE_ASYNC_AVAILABLE = False
    logging.warning("azure-storage-blob[aio] no disponible. Instalar con: pip install azure-storage-blob[aio]")

# S3 async imports
try:
    import aioboto3
    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    logging.warning("aioboto3 no disponible. Instalar con: pip install aioboto3")

# HTTP async imports
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logging.warning("aiohttp no disponible. Instalar con: pip install aiohttp")

# File I/O async imports
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    logging.warning("aiofiles no disponible. Instalar con: pip install aiofiles")


# =============================================================================
# AZURE BLOB STORAGE - ASYNC
# =============================================================================

async def download_from_azure_blob_async(
    connection_string: str,
    container_name: str,
    blob_name: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bytes:
    """
    Descarga un blob desde Azure Blob Storage de forma asíncrona.

    Args:
        connection_string: Azure connection string
        container_name: Nombre del contenedor
        blob_name: Nombre del blob
        progress_callback: Función callback opcional para reportar progreso (downloaded, total)

    Returns:
        bytes: Contenido del blob descargado

    Raises:
        ResourceNotFoundError: Si el blob no existe
        Exception: Otros errores de Azure
    """
    if not AZURE_ASYNC_AVAILABLE:
        raise ImportError("azure-storage-blob[aio] no está instalado. Ejecutar: pip install azure-storage-blob[aio]")

    logging.info(f"⚡ [ASYNC] Descargando blob de Azure: {container_name}/{blob_name}")

    async with AsyncBlobServiceClient.from_connection_string(connection_string) as blob_service_client:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Obtener propiedades para conocer el tamaño total
        properties = await blob_client.get_blob_properties()
        total_size = properties.size

        logging.info(f"📊 Tamaño del blob: {total_size / 1024 / 1024:.2f} MB")

        # Descargar el blob
        download_stream = await blob_client.download_blob()

        # Leer en chunks para permitir tracking de progreso
        blob_content = bytearray()
        chunk_size = 1024 * 1024  # 1 MB chunks
        downloaded = 0

        async for chunk in download_stream.chunks():
            blob_content.extend(chunk)
            downloaded += len(chunk)

            # Reportar progreso si hay callback
            if progress_callback:
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(downloaded, total_size)
                    else:
                        progress_callback(downloaded, total_size)
                except Exception as e:
                    logging.warning(f"Error en progress_callback: {e}")

        logging.info(f"✅ [ASYNC] Blob descargado exitosamente: {len(blob_content) / 1024 / 1024:.2f} MB")
        return bytes(blob_content)


async def download_blob_with_progress_async(
    connection_string: str,
    container_name: str,
    blob_name: str,
    progress_tracker: Optional[Any] = None,
    step: int = 3
) -> bytes:
    """
    Descarga blob de Azure con tracking de progreso compatible con SSE.

    Args:
        connection_string: Azure connection string
        container_name: Nombre del contenedor
        blob_name: Nombre del blob
        progress_tracker: Objeto con método update_progress(step, status, message)
        step: Número de paso para progress tracking

    Returns:
        bytes: Contenido del blob descargado
    """
    if not AZURE_ASYNC_AVAILABLE:
        raise ImportError("azure-storage-blob[aio] no está instalado")

    start_time = datetime.now()

    # Progress callback que integra con progress_tracker
    async def update_progress(downloaded: int, total: int):
        if progress_tracker:
            percent = (downloaded / total * 100) if total > 0 else 0
            mb_downloaded = downloaded / 1024 / 1024
            mb_total = total / 1024 / 1024

            message = f"Descargando: {mb_downloaded:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)"

            try:
                progress_tracker.update_progress(step, "processing", message)
            except Exception as e:
                logging.warning(f"Error actualizando progress_tracker: {e}")

    if progress_tracker:
        progress_tracker.update_progress(step, "processing", f"Iniciando descarga de {blob_name}...")

    # Descargar usando la función async principal
    blob_content = await download_from_azure_blob_async(
        connection_string,
        container_name,
        blob_name,
        progress_callback=update_progress
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    speed_mbps = (len(blob_content) / 1024 / 1024) / elapsed if elapsed > 0 else 0

    if progress_tracker:
        progress_tracker.update_progress(
            step,
            "completed",
            f"Descarga completada: {len(blob_content) / 1024 / 1024:.2f} MB en {elapsed:.1f}s ({speed_mbps:.2f} MB/s)"
        )

    return blob_content


async def get_blob_properties_async(
    connection_string: str,
    container_name: str,
    blob_name: str
) -> Dict[str, Any]:
    """
    Obtiene las propiedades de un blob de Azure de forma asíncrona.
    Útil para verificar si hay actualizaciones sin descargar el archivo completo.

    Args:
        connection_string: Azure connection string
        container_name: Nombre del contenedor
        blob_name: Nombre del blob

    Returns:
        Dict con propiedades del blob (last_modified, size, etag, etc.)
    """
    if not AZURE_ASYNC_AVAILABLE:
        raise ImportError("azure-storage-blob[aio] no está instalado")

    async with AsyncBlobServiceClient.from_connection_string(connection_string) as blob_service_client:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        properties = await blob_client.get_blob_properties()

        return {
            'last_modified': properties.last_modified,
            'size': properties.size,
            'etag': properties.etag,
            'content_type': properties.content_settings.content_type if properties.content_settings else None,
        }


# =============================================================================
# S3 - ASYNC
# =============================================================================

async def download_from_s3_async(
    bucket_name: str,
    key: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = 'us-east-1',
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bytes:
    """
    Descarga un objeto desde S3 de forma asíncrona.

    Args:
        bucket_name: Nombre del bucket S3
        key: Key del objeto en S3
        aws_access_key_id: AWS access key (opcional, usa credenciales por defecto)
        aws_secret_access_key: AWS secret key (opcional)
        region_name: Región de AWS
        progress_callback: Función callback opcional para progreso

    Returns:
        bytes: Contenido del objeto descargado
    """
    if not AIOBOTO3_AVAILABLE:
        raise ImportError("aioboto3 no está instalado. Ejecutar: pip install aioboto3")

    logging.info(f"⚡ [ASYNC] Descargando de S3: s3://{bucket_name}/{key}")

    session = aioboto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

    async with session.client('s3') as s3_client:
        # Obtener metadata del objeto
        try:
            head_response = await s3_client.head_object(Bucket=bucket_name, Key=key)
            total_size = head_response.get('ContentLength', 0)
            logging.info(f"📊 Tamaño del objeto S3: {total_size / 1024 / 1024:.2f} MB")
        except:
            total_size = 0

        # Descargar el objeto
        response = await s3_client.get_object(Bucket=bucket_name, Key=key)

        # Leer el stream
        blob_content = bytearray()
        downloaded = 0

        async with response['Body'] as stream:
            chunk = await stream.read(1024 * 1024)  # 1 MB chunks
            while chunk:
                blob_content.extend(chunk)
                downloaded += len(chunk)

                # Reportar progreso
                if progress_callback and total_size > 0:
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(downloaded, total_size)
                        else:
                            progress_callback(downloaded, total_size)
                    except Exception as e:
                        logging.warning(f"Error en progress_callback: {e}")

                chunk = await stream.read(1024 * 1024)

        logging.info(f"✅ [ASYNC] Objeto S3 descargado: {len(blob_content) / 1024 / 1024:.2f} MB")
        return bytes(blob_content)


# =============================================================================
# FILE I/O - ASYNC
# =============================================================================

async def read_file_async(file_path: str) -> bytes:
    """
    Lee un archivo de forma asíncrona.

    Args:
        file_path: Ruta al archivo

    Returns:
        bytes: Contenido del archivo
    """
    if not AIOFILES_AVAILABLE:
        raise ImportError("aiofiles no está instalado. Ejecutar: pip install aiofiles")

    async with aiofiles.open(file_path, mode='rb') as f:
        content = await f.read()

    return content


async def write_file_async(file_path: str, content: bytes) -> None:
    """
    Escribe un archivo de forma asíncrona.

    Args:
        file_path: Ruta al archivo
        content: Contenido a escribir
    """
    if not AIOFILES_AVAILABLE:
        raise ImportError("aiofiles no está instalado. Ejecutar: pip install aiofiles")

    async with aiofiles.open(file_path, mode='wb') as f:
        await f.write(content)


# =============================================================================
# UTILITIES
# =============================================================================

def check_async_availability() -> Dict[str, bool]:
    """
    Verifica qué librerías async están disponibles.

    Returns:
        Dict con disponibilidad de cada librería
    """
    return {
        'azure_async': AZURE_ASYNC_AVAILABLE,
        'aioboto3': AIOBOTO3_AVAILABLE,
        'aiohttp': AIOHTTP_AVAILABLE,
        'aiofiles': AIOFILES_AVAILABLE,
    }


def log_async_availability():
    """
    Registra en el log la disponibilidad de librerías async.
    """
    availability = check_async_availability()

    logging.info("=== Disponibilidad de Librerías Async ===")
    for lib, available in availability.items():
        status = "✅" if available else "❌"
        logging.info(f"{status} {lib}: {'Disponible' if available else 'No instalado'}")

    all_available = all(availability.values())
    if all_available:
        logging.info("✅ Todas las librerías async están instaladas y listas")
    else:
        missing = [lib for lib, avail in availability.items() if not avail]
        logging.warning(f"⚠️ Librerías async faltantes: {', '.join(missing)}")


# Log availability al importar el módulo
log_async_availability()
