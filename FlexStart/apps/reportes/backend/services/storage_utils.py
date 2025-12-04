"""
Storage Utils - Utilidades para acceso a sistemas de almacenamiento.

Este módulo contiene funciones auxiliares para:
- Operaciones con Azure Blob Storage (usado por Reportes - Chile)
- Acceso a Amazon S3 (usado por prod_peru)
- Integración con SharePoint (usado por Reportes - Perú)
- Descarga y validación de archivos remotos

Extraído de main_logic.py para mejorar reutilización y mantenibilidad.
"""

import io
import logging
import os
import tempfile
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple, List, Union
from urllib.parse import urlparse

import keyring

# Constantes
S3_KEYRING_SERVICE = "ReportesRodrobusS3"

# Imports condicionales para librerías de storage
try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logging.warning("Azure Blob Storage no disponible - funcionalidad limitada")

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logging.warning("Amazon S3 no disponible - funcionalidad limitada")

try:
    from office365.sharepoint.client_context import ClientContext
    from office365.runtime.auth.authentication_context import AuthenticationContext
    SHAREPOINT_AVAILABLE = True
except ImportError:
    SHAREPOINT_AVAILABLE = False
    logging.warning("SharePoint no disponible - funcionalidad limitada")

# Import de utilidades relacionadas
try:
    from .progress_utils import DownloadProgressTracker
except ImportError:
    # Fallback si progress_utils no está disponible
    class DownloadProgressTracker:
        def __init__(self, *args, **kwargs):
            pass
        def update(self, *args, **kwargs):
            pass


def validate_storage_config(storage_type: str, config: Dict[str, Any]) -> bool:
    """
    Valida la configuración para un tipo de almacenamiento específico.

    Args:
        storage_type: Tipo de almacenamiento (azure, s3, sharepoint)
        config: Configuración del almacenamiento

    Returns:
        True si la configuración es válida
    """
    if storage_type == "azure":
        required_keys = ["connection_string", "container_name"]
        return all(key in config for key in required_keys)

    elif storage_type == "s3":
        required_keys = ["aws_access_key", "aws_secret_key", "bucket_name"]
        return all(key in config for key in required_keys)

    elif storage_type == "sharepoint":
        required_keys = ["site_url", "username", "password"]
        return all(key in config for key in required_keys)

    return False


def detect_storage_type_from_url(url: str) -> str:
    """
    Detecta el tipo de almacenamiento basándose en la URL.

    Args:
        url: URL del recurso

    Returns:
        Tipo de almacenamiento detectado
    """
    parsed_url = urlparse(url)

    if "blob.core.windows.net" in parsed_url.netloc:
        return "azure"
    elif "amazonaws.com" in parsed_url.netloc or "s3" in parsed_url.netloc:
        return "s3"
    elif "sharepoint.com" in parsed_url.netloc:
        return "sharepoint"
    elif parsed_url.scheme in ["http", "https"]:
        return "http"
    elif parsed_url.scheme == "file" or not parsed_url.scheme:
        return "local"

    return "unknown"


@lru_cache(maxsize=4)
def get_blob_service_client(connection_string: str):
    """Obtiene un cliente de Azure Blob Storage reutilizable con connection pooling."""
    return BlobServiceClient.from_connection_string(
        connection_string,
        max_single_get_size=32 * 1024 * 1024,  # 32MB chunks
        max_chunk_get_size=4 * 1024 * 1024,    # 4MB sub-chunks
    )


def download_from_azure_blob(connection_string: str, container_name: str,
                           blob_name: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
    """
    Descarga un archivo desde Azure Blob Storage.

    Args:
        connection_string: Cadena de conexión a Azure
        container_name: Nombre del contenedor
        blob_name: Nombre del blob a descargar
        progress_tracker: Tracker de progreso opcional

    Returns:
        Contenido del blob en bytes
    """
    if not AZURE_AVAILABLE:
        raise ImportError("Azure Blob Storage no está disponible. Instalar azure-storage-blob")

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )

        if progress_tracker:
            progress_tracker.update_bytes(0, f"Conectando a Azure Blob Storage...")

        # Obtener propiedades del blob para el tamaño
        blob_properties = blob_client.get_blob_properties()
        blob_size = blob_properties.size

        if progress_tracker and blob_size:
            progress_tracker.total_bytes = blob_size

        # Descargar el blob
        blob_data = blob_client.download_blob()
        content = blob_data.readall()

        if progress_tracker:
            progress_tracker.update_bytes(len(content), f"Descarga completada desde Azure")

        logging.info(f"Blob '{blob_name}' descargado exitosamente desde Azure ({len(content)} bytes)")
        return content

    except ResourceNotFoundError:
        logging.error(f"Blob '{blob_name}' no encontrado en contenedor '{container_name}'")
        raise FileNotFoundError(f"Blob '{blob_name}' no encontrado")
    except Exception as e:
        logging.error(f"Error al descargar desde Azure Blob Storage: {e}")
        raise


def _download_blob_with_progress(connection_string: str, container_name: str, filename: str) -> bytes:
    """Descarga un blob de Azure con progreso en tiempo real."""
    import time
    from .progress_utils import progress_utils

    try:
        blob_service_client = get_blob_service_client(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)

        properties = blob_client.get_blob_properties()
        total_size = properties.size

        logging.info(f"Iniciando descarga de {filename} - Tamaño: {total_size:,} bytes")

        # Progreso inicial
        progress_utils.emit_progress_message({
            "type": "download_progress",
            "filename": filename,
            "progress": 0,
            "total_size": total_size,
            "status": "starting",
            "message": f"Iniciando descarga de {filename}..."
        })

        # Configuración de descarga
        downloaded_bytes = 0
        blob_content = bytearray()
        start_time = time.time()
        last_progress_report = 0
        progress_report_threshold = max(1 * 1024 * 1024, total_size // 100)

        # Descarga por chunks
        for chunk in blob_client.download_blob(max_concurrency=8).chunks():
            blob_content.extend(chunk)
            downloaded_bytes += len(chunk)

            # Reportar progreso cuando sea necesario
            bytes_since_last_report = downloaded_bytes - last_progress_report
            if bytes_since_last_report >= progress_report_threshold:
                progress_percent = (downloaded_bytes / total_size) * 100
                elapsed_time = time.time() - start_time
                speed_mbps = progress_utils.calculate_download_speed(downloaded_bytes, elapsed_time)

                last_progress_report = downloaded_bytes
                progress_utils.emit_progress_message({
                    "type": "download_progress",
                    "filename": filename,
                    "progress": round(progress_percent, 1),
                    "downloaded_bytes": downloaded_bytes,
                    "total_size": total_size,
                    "speed_mbps": round(speed_mbps, 2),
                    "status": "downloading",
                    "message": f"Descargando {filename}: {progress_percent:.1f}% ({speed_mbps:.1f} MB/s)"
                })

        # Progreso final
        elapsed_time = time.time() - start_time
        avg_speed = progress_utils.calculate_download_speed(total_size, elapsed_time)

        progress_utils.emit_progress_message({
            "type": "download_progress",
            "filename": filename,
            "progress": 100,
            "downloaded_bytes": total_size,
            "total_size": total_size,
            "speed_mbps": round(avg_speed, 2),
            "elapsed_time": round(elapsed_time, 2),
            "status": "completed",
            "message": f"Descarga de {filename} completada en {elapsed_time:.1f}s ({avg_speed:.1f} MB/s promedio)"
        })

        logging.info(f"Descarga de {filename} completada - {total_size:,} bytes en {elapsed_time:.2f}s")
        return bytes(blob_content)

    except Exception as e:
        progress_utils.emit_progress_message({
            "type": "download_error",
            "filename": filename,
            "error": str(e),
            "status": "error",
            "message": f"Error descargando {filename}: {str(e)}"
        })

        logging.error(f"Error en descarga chunked de {filename}: {e}", exc_info=True)
        raise


def _read_xlsx_from_s3(s3_path: str) -> 'pd.DataFrame':
    """Lee un XLSX desde S3; para archivos grandes usa caché Parquet local."""
    import hashlib
    import io
    import pandas as pd
    from pathlib import Path

    # Obtener cache directory desde constantes del módulo principal
    CACHE_DIR = Path.home() / ".cache" / "ReportesRodrobus"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    bucket, key = _split_bucket_key(s3_path)
    client = _get_s3_client()

    # Intentamos obtener metadatos primero (tamaño y ETag). Algunos roles de IAM no permiten HeadObject.
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        size_bytes = head.get('ContentLength', 0)
        etag_raw = head.get('ETag', '').strip('"')
        etag_short = etag_raw[:10] if etag_raw else hashlib.md5(key.encode()).hexdigest()[:10]
    except client.exceptions.ClientError as e:
        logging.warning(f"No se pudo ejecutar head_object sobre s3://{bucket}/{key}: {e}. Continuaré sin caché Parquet.")
        size_bytes = 0
        etag_short = hashlib.md5(key.encode()).hexdigest()[:10]

    sanitized_key = _sanitize_key_for_filename(key)
    parquet_path = CACHE_DIR / f"{sanitized_key}__{etag_short}.parquet"

    if parquet_path.exists():
        logging.info(f"Cargando Parquet desde caché: {parquet_path}")
        return pd.read_parquet(parquet_path)

    # Si el archivo es menor a 10 MB, leerlo directamente para no sobrecargar.
    THRESHOLD_BYTES = 10 * 1024 * 1024
    logging.info(f"Descargando XLSX desde S3 (tamaño {size_bytes/1e6:.1f} MB): s3://{bucket}/{key}")
    obj = client.get_object(Bucket=bucket, Key=key)
    data = obj['Body'].read()

    df = pd.read_excel(io.BytesIO(data), engine='openpyxl')

    # Guardar en Parquet si el tamaño supera el umbral (mejora cargas futuras)
    try:
        if size_bytes > THRESHOLD_BYTES:
            logging.info(f"Guardando caché Parquet ({parquet_path})…")
            df.to_parquet(parquet_path, index=False)
            # Limpiar versiones antiguas de este archivo
            prefix = CACHE_DIR / f"{sanitized_key}__"
            for old_file in CACHE_DIR.glob(f"{sanitized_key}__*.parquet"):
                if old_file != parquet_path:
                    old_file.unlink(missing_ok=True)
    except Exception as cache_err:
        logging.warning(f"No se pudo cachear Parquet: {cache_err}")

    return df


def _read_csv_from_s3(s3_path: str) -> 'pd.DataFrame':
    """Lee un CSV desde S3; para archivos grandes usa caché Parquet local."""
    import hashlib
    import pandas as pd
    from pathlib import Path
    from .csv_utils import csv_utils

    # Obtener cache directory desde constantes del módulo principal
    CACHE_DIR = Path.home() / ".cache" / "ReportesRodrobus"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    bucket, key = _split_bucket_key(s3_path)
    client = _get_s3_client()

    # Intentar obtener metadatos (tamaño / ETag) para caché
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        size_bytes = head.get('ContentLength', 0)
        etag_raw = head.get('ETag', '').strip('"')
        etag_short = etag_raw[:10] if etag_raw else hashlib.md5(key.encode()).hexdigest()[:10]
    except client.exceptions.ClientError as e:
        logging.warning(f"No se pudo obtener metadatos de s3://{bucket}/{key}: {e}. Continuaré sin caché.")
        size_bytes = 0
        etag_short = hashlib.md5(key.encode()).hexdigest()[:10]

    sanitized_key = _sanitize_key_for_filename(key)
    parquet_path = CACHE_DIR / f"{sanitized_key}__{etag_short}.parquet"

    if parquet_path.exists():
        logging.info(f"Cargando CSV desde caché Parquet: {parquet_path}")
        return pd.read_parquet(parquet_path)

    logging.info(f"Descargando CSV desde S3 (tamaño {size_bytes/1e6:.1f} MB): s3://{bucket}/{key}")
    obj = client.get_object(Bucket=bucket, Key=key)
    raw_data = obj['Body'].read()

    df = csv_utils.read_csv_from_bytes(raw_data, key)

    # Si el archivo es grande, guardar caché Parquet
    THRESHOLD_BYTES = 5 * 1024 * 1024  # 5MB para CSV
    try:
        if size_bytes > THRESHOLD_BYTES:
            logging.info(f"Guardando caché Parquet para CSV: {parquet_path}")
            df.to_parquet(parquet_path, index=False)
            # Limpiar archivos de caché antiguos
            for old_file in CACHE_DIR.glob(f"{sanitized_key}__*.parquet"):
                if old_file != parquet_path:
                    old_file.unlink(missing_ok=True)
    except Exception as cache_err:
        logging.warning(f"Error guardando caché Parquet: {cache_err}")

    return df


# Funciones auxiliares S3
def _get_s3_client():
    """Devuelve un cliente boto3 usando credenciales almacenadas en keyring."""
    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")
        if not all([access_key, secret_key]):
            raise ValueError("Credenciales AWS no encontradas en keyring.")
        return boto3.client(
            "s3",
            aws_access_key_id=access_key.strip(),
            aws_secret_access_key=secret_key.strip()
        )
    except Exception as e:
        logging.error(f"Error obteniendo cliente S3: {e}")
        raise


def _split_bucket_key(path: str) -> tuple[str, str]:
    """Separa la cadena 'bucket/path/to/file' en bucket y key."""
    parts = path.split('/', 1)
    if len(parts) != 2:
        raise ValueError("El nombre de archivo para S3 debe ser 'bucket/ruta/al/archivo.ext'")
    return parts[0], parts[1]


def _extract_container_name_from_url(container_url: str) -> Optional[str]:
    """Extrae el nombre del contenedor de URL complejas de Azure."""
    endpoint_suffixes = ['.blob.core.windows.net', '.dfs.core.windows.net']
    name_found = None

    for suffix in endpoint_suffixes:
        if suffix in container_url:
            parts = container_url.split(suffix, 1)
            if len(parts) > 1 and parts[1].startswith('/'):
                path_part = parts[1].lstrip('/')
                name_found = path_part.split('/')[0].split('?')[0]
                break

    if not name_found:
        logging.warning("No se pudo extraer nombre de contenedor de ContainerURL.")

    return name_found


def _sanitize_key_for_filename(key: str) -> str:
    """Convierte la clave S3 en un nombre de archivo seguro."""
    return key.replace('/', '__')


def download_from_s3(aws_access_key: str, aws_secret_key: str, bucket_name: str,
                    object_key: str, region_name: str = "us-east-1",
                    progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
    """
    Descarga un archivo desde Amazon S3.

    Args:
        aws_access_key: Clave de acceso AWS
        aws_secret_key: Clave secreta AWS
        bucket_name: Nombre del bucket
        object_key: Clave del objeto a descargar
        region_name: Región de AWS
        progress_tracker: Tracker de progreso opcional

    Returns:
        Contenido del objeto en bytes
    """
    if not S3_AVAILABLE:
        raise ImportError("Amazon S3 no está disponible. Instalar boto3")

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )

        if progress_tracker:
            progress_tracker.update_bytes(0, f"Conectando a Amazon S3...")

        # Obtener metadatos del objeto para el tamaño
        try:
            head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            object_size = head_response.get('ContentLength', 0)

            if progress_tracker and object_size:
                progress_tracker.total_bytes = object_size
        except ClientError:
            object_size = 0

        # Descargar el objeto
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read()

        if progress_tracker:
            progress_tracker.update_bytes(len(content), f"Descarga completada desde S3")

        logging.info(f"Objeto '{object_key}' descargado exitosamente desde S3 ({len(content)} bytes)")
        return content

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logging.error(f"Objeto '{object_key}' no encontrado en bucket '{bucket_name}'")
            raise FileNotFoundError(f"Objeto '{object_key}' no encontrado")
        else:
            logging.error(f"Error al acceder a S3: {e}")
            raise
    except NoCredentialsError:
        logging.error("Credenciales de AWS no válidas o no encontradas")
        raise
    except Exception as e:
        logging.error(f"Error al descargar desde Amazon S3: {e}")
        raise


def download_from_sharepoint(site_url: str, username: str, password: str,
                           file_url: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
    """
    Descarga un archivo desde SharePoint.

    Args:
        site_url: URL del sitio de SharePoint
        username: Nombre de usuario
        password: Contraseña
        file_url: URL del archivo en SharePoint
        progress_tracker: Tracker de progreso opcional

    Returns:
        Contenido del archivo en bytes
    """
    if not SHAREPOINT_AVAILABLE:
        raise ImportError("SharePoint no está disponible. Instalar Office365-REST-Python-Client")

    try:
        if progress_tracker:
            progress_tracker.update_bytes(0, f"Conectando a SharePoint...")

        # Autenticación
        auth_context = AuthenticationContext(site_url)
        auth_context.acquire_token_for_user(username, password)

        # Conexión al contexto
        ctx = ClientContext(site_url, auth_context)

        # Obtener el archivo
        file_response = ctx.web.get_file_by_server_relative_url(file_url)
        ctx.load(file_response)
        ctx.execute_query()

        # Descargar contenido
        file_content = file_response.get_content()
        content = file_content.value

        if progress_tracker:
            progress_tracker.update_bytes(len(content), f"Descarga completada desde SharePoint")

        logging.info(f"Archivo descargado exitosamente desde SharePoint ({len(content)} bytes)")
        return content

    except Exception as e:
        logging.error(f"Error al descargar desde SharePoint: {e}")
        raise


def download_from_url(url: str, headers: Optional[Dict[str, str]] = None,
                     timeout: int = 30, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
    """
    Descarga un archivo desde una URL HTTP/HTTPS.

    Args:
        url: URL del archivo a descargar
        headers: Headers HTTP opcionales
        timeout: Timeout en segundos
        progress_tracker: Tracker de progreso opcional

    Returns:
        Contenido del archivo en bytes
    """
    try:
        import requests
    except ImportError:
        raise ImportError("requests no está disponible para descargas HTTP")

    try:
        if progress_tracker:
            progress_tracker.update_bytes(0, f"Descargando desde {url}...")

        response = requests.get(url, headers=headers or {}, timeout=timeout, stream=True)
        response.raise_for_status()

        # Obtener tamaño del archivo si está disponible
        content_length = response.headers.get('content-length')
        if content_length and progress_tracker:
            progress_tracker.total_bytes = int(content_length)

        # Descargar por chunks
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content += chunk
                if progress_tracker:
                    progress_tracker.update_bytes(len(chunk))

        if progress_tracker:
            progress_tracker.update_bytes(0, f"Descarga HTTP completada")

        logging.info(f"Archivo descargado exitosamente desde URL ({len(content)} bytes)")
        return content

    except requests.exceptions.RequestException as e:
        logging.error(f"Error al descargar desde URL: {e}")
        raise


def read_local_file(file_path: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
    """
    Lee un archivo local.

    Args:
        file_path: Ruta del archivo local
        progress_tracker: Tracker de progreso opcional

    Returns:
        Contenido del archivo en bytes
    """
    try:
        if progress_tracker:
            progress_tracker.update_bytes(0, f"Leyendo archivo local {file_path}...")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo local no encontrado: {file_path}")

        # Obtener tamaño del archivo
        file_size = os.path.getsize(file_path)
        if progress_tracker:
            progress_tracker.total_bytes = file_size

        with open(file_path, 'rb') as f:
            content = f.read()

        if progress_tracker:
            progress_tracker.update_bytes(len(content), f"Lectura de archivo local completada")

        logging.info(f"Archivo local leído exitosamente ({len(content)} bytes)")
        return content

    except Exception as e:
        logging.error(f"Error al leer archivo local: {e}")
        raise


def save_to_temp_file(content: bytes, prefix: str = "storage_", suffix: str = ".tmp") -> str:
    """
    Guarda contenido en un archivo temporal.

    Args:
        content: Contenido en bytes a guardar
        prefix: Prefijo del nombre del archivo
        suffix: Sufijo del nombre del archivo

    Returns:
        Ruta del archivo temporal creado
    """
    try:
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        logging.info(f"Contenido guardado en archivo temporal: {temp_path}")
        return temp_path

    except Exception as e:
        logging.error(f"Error al crear archivo temporal: {e}")
        raise


def _download_file_from_download_url(download_url: str, local_path: str):
    """
    Descarga un archivo usando la URL de descarga directa de Microsoft Graph.
    """
    try:
        # Crear directorio local si no existe
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        response = requests.get(download_url, verify=False, timeout=60, stream=True)
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    except Exception as e:
        logging.error(f"Error descargando archivo {local_path}: {e}")
        raise


# Clase contenedora para todas las utilidades de almacenamiento
class StorageUtils:
    """Clase contenedora para todas las utilidades de almacenamiento."""

    @staticmethod
    def validate_storage_config(storage_type: str, config: Dict[str, Any]) -> bool:
        return validate_storage_config(storage_type, config)

    @staticmethod
    def detect_storage_type_from_url(url: str) -> str:
        return detect_storage_type_from_url(url)

    @staticmethod
    def download_from_azure_blob(connection_string: str, container_name: str,
                               blob_name: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
        return download_from_azure_blob(connection_string, container_name, blob_name, progress_tracker)

    @staticmethod
    def download_from_s3(aws_access_key: str, aws_secret_key: str, bucket_name: str,
                        object_key: str, region_name: str = "us-east-1",
                        progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
        return download_from_s3(aws_access_key, aws_secret_key, bucket_name, object_key, region_name, progress_tracker)

    @staticmethod
    def download_from_sharepoint(site_url: str, username: str, password: str,
                               file_url: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
        return download_from_sharepoint(site_url, username, password, file_url, progress_tracker)

    @staticmethod
    def download_from_url(url: str, headers: Optional[Dict[str, str]] = None,
                         timeout: int = 30, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
        return download_from_url(url, headers, timeout, progress_tracker)

    @staticmethod
    def read_local_file(file_path: str, progress_tracker: Optional[DownloadProgressTracker] = None) -> bytes:
        return read_local_file(file_path, progress_tracker)

    @staticmethod
    def save_to_temp_file(content: bytes, prefix: str = "storage_", suffix: str = ".tmp") -> str:
        return save_to_temp_file(content, prefix, suffix)


def _parse_sharepoint_url(full_url: str) -> tuple:
    """
    Parsea una URL completa de SharePoint para extraer la URL base del sitio y la carpeta.

    Ejemplo:
    Input: https://ripleycorp.sharepoint.com/sites/Publicacinycontenido2/Documentos%20Publicacin/Foto%20estudios
    Output: ('https://ripleycorp.sharepoint.com/sites/Publicacinycontenido2', 'Documentos Publicacin/Foto estudios')
    """
    import re
    from urllib.parse import unquote

    # Decodificar URL
    decoded_url = unquote(full_url)

    # Extraer hostname y site path
    match = re.match(r'(https://[^/]+/sites/[^/]+)(?:/(.+))?', decoded_url)
    if not match:
        raise ValueError(f"URL de SharePoint inválida: {full_url}")

    site_base_url = match.group(1)
    folder_path = match.group(2) if match.group(2) else 'root'

    return site_base_url, folder_path


# Instancia global para fácil acceso
storage_utils = StorageUtils()