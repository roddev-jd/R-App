"""
Sistema de cache persistente para bases específicas de Reportes.
Permite almacenar bases pesadas localmente para evitar descargas innecesarias.
"""

import os
import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone, timedelta
import requests
import pandas as pd
try:
    import dateutil.parser
except ImportError:
    # Fallback si dateutil no está disponible
    dateutil = None


class PersistentCache:
    """Maneja el cache persistente de bases específicas."""

    # ============================================================================
    # CONFIGURACIÓN DE CACHÉ (HITO: Mejoras de Verificación)
    # ============================================================================

    # Tolerancia de clock skew para comparaciones de timestamp (Issue #1)
    # Previene falsos positivos cuando el reloj local difiere del servidor
    TIMESTAMP_TOLERANCE = timedelta(minutes=2)

    # Política de expiración: edad máxima del caché (Issue: Expiración)
    # Caché más antiguo que esto se considera obsoleto automáticamente
    CACHE_MAX_AGE_DAYS = 30

    # Configuración de reintentos para verificaciones remotas (Issue #3)
    MAX_RETRY_ATTEMPTS = 3
    INITIAL_RETRY_DELAY = 0.5  # segundos
    RETRY_BACKOFF_FACTOR = 2.0

    # ============================================================================
    # BASES CACHEABLES
    # ============================================================================

    # Bases que utilizan cache persistente (HITO 1.4 - OPTIMIZACIÓN)
    # Expandido para incluir bases de Chile y otras fuentes frecuentes
    CACHEABLE_BASES = {
        # Peru (existentes)
        "UNIVERSO PERU",
        "INFO MARCA PROPIA PERU",

        # Chile (NUEVO - HITO 1.4)
        "UNIVERSO CHILE",           # Corresponde a Chile_Wop en config.ini
        "MEJORAS CHILE",            # Corresponde a Chile_MejorasCL
        "ESTUDIOS CHILE",           # Corresponde a Chile_Estudios

        # Otros (NUEVO - HITO 1.4)
        "INFO EQUIVALENCIAS PERU",  # Peru_eqs
    }

    # Columnas que deben mantenerse como string (evitar conversión a numérico)
    STRING_COLUMNS_BY_BASE = {
        "INFO MARCA PROPIA PERU": ['ean_hijo', 'ean_padre'],
        "UNIVERSO PERU": ['ean_hijo', 'ean_padre']
    }
    
    def __init__(self):
        self.cache_dir = self._get_cache_directory()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Cache persistente inicializado en: {self.cache_dir}")
    
    def _get_cache_directory(self) -> Path:
        """Obtiene el directorio de cache según el sistema operativo."""
        if os.name == 'nt':  # Windows
            cache_dir = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'AppSuite' / 'cache'
        else:  # macOS/Linux
            if os.uname().sysname == 'Darwin':  # macOS
                cache_dir = Path.home() / 'Library' / 'Caches' / 'AppSuite'
            else:  # Linux
                cache_dir = Path.home() / '.cache' / 'AppSuite'
        
        return cache_dir
    
    def _get_cache_filename(self, base_display_name: str, format: str = 'parquet') -> str:
        """
        Genera nombre de archivo de cache para una base.

        Args:
            base_display_name: Nombre de la base de datos
            format: Formato del archivo ('parquet' o 'csv.gz'). Default: 'parquet'
        """
        safe_name = base_display_name.lower().replace(' ', '_').replace('-', '_')
        if format == 'parquet':
            return f"{safe_name}.parquet"
        else:
            return f"{safe_name}.csv.gz"
    
    def _get_metadata_filename(self, base_display_name: str) -> str:
        """Genera nombre de archivo de metadata para una base."""
        safe_name = base_display_name.lower().replace(' ', '_').replace('-', '_')
        return f"{safe_name}_metadata.json"
    
    def is_cacheable(self, base_display_name: str) -> bool:
        """Verifica si una base debe usar cache persistente."""
        return base_display_name in self.CACHEABLE_BASES
    
    def has_cached_data(self, base_display_name: str) -> bool:
        """
        Verifica si existe cache local para una base.
        Busca primero formato Parquet, luego CSV.gz (compatibilidad hacia atrás).
        """
        if not self.is_cacheable(base_display_name):
            return False

        metadata_file = self.cache_dir / self._get_metadata_filename(base_display_name)

        # Intentar Parquet primero (formato nuevo y más eficiente)
        parquet_file = self.cache_dir / self._get_cache_filename(base_display_name, format='parquet')
        if parquet_file.exists() and metadata_file.exists():
            return True

        # Fallback a CSV.gz (compatibilidad con cachés antiguos)
        csv_file = self.cache_dir / self._get_cache_filename(base_display_name, format='csv.gz')
        return csv_file.exists() and metadata_file.exists()
    
    def get_cached_metadata(self, base_display_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene metadata del cache local."""
        if not self.has_cached_data(base_display_name):
            return None

        metadata_file = self.cache_dir / self._get_metadata_filename(base_display_name)

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error leyendo metadata de cache: {e}")
            return None

    def is_cache_expired(self, base_display_name: str) -> bool:
        """
        Verifica si el caché ha excedido la edad máxima permitida (Hito 2.3).

        Args:
            base_display_name: Nombre de la base de datos

        Returns:
            True si el caché está expirado por edad, False si aún es válido
        """
        metadata = self.get_cached_metadata(base_display_name)
        if not metadata:
            return True  # Sin metadata = considerado expirado

        cached_at_str = metadata.get('cached_at')
        if not cached_at_str:
            logging.warning(f"⚠️ Metadata sin timestamp para '{base_display_name}'")
            return True

        try:
            # Parsear timestamp del caché
            cached_at = datetime.fromisoformat(cached_at_str.replace('Z', '+00:00'))
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)

            # Calcular edad
            now = datetime.now(timezone.utc)
            age = now - cached_at
            max_age = timedelta(days=self.CACHE_MAX_AGE_DAYS)

            if age > max_age:
                logging.warning(
                    f"⏰ Caché EXPIRADO por edad para '{base_display_name}'\n"
                    f"   Edad: {age.days} días (máximo permitido: {self.CACHE_MAX_AGE_DAYS} días)\n"
                    f"   Cached at: {cached_at_str}\n"
                    f"   Requiere descarga fresca"
                )
                return True

            logging.info(
                f"✅ Caché dentro de política de edad para '{base_display_name}' "
                f"({age.days} días, máximo: {self.CACHE_MAX_AGE_DAYS})"
            )
            return False

        except Exception as e:
            logging.error(f"❌ Error verificando expiración de caché para '{base_display_name}': {e}")
            return True  # En caso de error, considerar expirado por seguridad

    def load_cached_data(self, base_display_name: str, columns: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Carga datos desde cache local con validación de integridad (Hito 1.2).
        Intenta primero Parquet (más eficiente), fallback a CSV.gz (compatibilidad).

        Args:
            base_display_name: Nombre de la base de datos
            columns: Lista opcional de columnas a cargar (solo Parquet soporta lectura columnar)
        """
        if not self.has_cached_data(base_display_name):
            return None

        # Obtener metadata para validación
        metadata = self.get_cached_metadata(base_display_name)

        # Intentar cargar desde Parquet primero (formato nuevo)
        parquet_file = self.cache_dir / self._get_cache_filename(base_display_name, format='parquet')
        if parquet_file.exists():
            try:
                # ✅ HITO 1.2: Validar integridad del archivo con checksum
                if metadata and 'checksum' in metadata:
                    logging.info(f"🔍 Validando integridad de caché para '{base_display_name}'...")

                    with open(parquet_file, 'rb') as f:
                        actual_checksum = hashlib.md5(f.read()).hexdigest()

                    expected_checksum = metadata.get('checksum')

                    if actual_checksum != expected_checksum:
                        logging.error(
                            f"⚠️ CORRUPCIÓN DETECTADA en caché '{base_display_name}'\n"
                            f"   Archivo: {parquet_file}\n"
                            f"   Checksum esperado: {expected_checksum}\n"
                            f"   Checksum actual:   {actual_checksum}\n"
                            f"   🗑️  Limpiando caché corrupto..."
                        )
                        self.clear_cache(base_display_name)
                        return None

                    logging.info(f"✅ Integridad verificada (checksum: {actual_checksum[:8]}...)")
                else:
                    logging.warning(
                        f"⚠️ Metadata sin checksum para '{base_display_name}' - "
                        f"Saltando validación (caché legacy)"
                    )

                # Cargar datos
                if columns:
                    logging.info(f"Cargando {len(columns)} columnas desde cache Parquet: {parquet_file}")
                    df = pd.read_parquet(parquet_file, engine='pyarrow', columns=columns)
                else:
                    logging.info(f"Cargando datos desde cache Parquet: {parquet_file}")
                    df = pd.read_parquet(parquet_file, engine='pyarrow')

                # Asegurar que columnas específicas sean string
                if base_display_name in self.STRING_COLUMNS_BY_BASE:
                    string_columns = self.STRING_COLUMNS_BY_BASE[base_display_name]
                    for col in string_columns:
                        if col in df.columns:
                            df[col] = df[col].astype(str)
                    logging.info(f"Convirtiendo a string columnas: {string_columns}")

                logging.info(f"✅ Cache Parquet cargado: {len(df):,} filas, {len(df.columns)} columnas")
                return df
            except Exception as e:
                logging.error(f"❌ Error cargando desde Parquet: {e}")
                # Si el error es por corrupción, limpiar y retornar None
                if "parquet" in str(e).lower() or "invalid" in str(e).lower():
                    logging.error(f"🗑️  Posible corrupción de Parquet - Limpiando caché")
                    self.clear_cache(base_display_name)
                    return None
                logging.info("Intentando CSV.gz...")

        # Fallback a CSV.gz (compatibilidad con cachés antiguos)
        csv_file = self.cache_dir / self._get_cache_filename(base_display_name, format='csv.gz')
        if csv_file.exists():
            try:
                logging.info(f"Cargando datos desde cache CSV.gz: {csv_file}")

                # Preparar dtype dict para columnas que deben ser string
                dtype_dict = None
                if base_display_name in self.STRING_COLUMNS_BY_BASE:
                    string_columns = self.STRING_COLUMNS_BY_BASE[base_display_name]
                    dtype_dict = {col: str for col in string_columns}
                    logging.info(f"Aplicando dtype str a columnas: {string_columns}")

                df = pd.read_csv(csv_file, encoding='utf-8', compression='gzip', dtype=dtype_dict)
                logging.info(f"Cache CSV.gz cargado: {len(df)} filas, {len(df.columns)} columnas")
                return df
            except Exception as e:
                logging.error(f"Error cargando datos desde cache CSV.gz: {e}")
                return None

        return None
    
    def save_to_cache(self, base_display_name: str, df: pd.DataFrame, source_url: str) -> bool:
        """
        Guarda datos y metadata en cache local usando formato Parquet con operaciones atómicas (Hito 2.2).
        Parquet ofrece: mejor compresión, lectura más rápida, y soporte columnar nativo.
        Ver: OPTIMIZACION_RENDIMIENTO.md - Fase 2
        """
        if not self.is_cacheable(base_display_name):
            return False

        # Generar nombres de archivos finales y temporales
        final_cache_file = self.cache_dir / self._get_cache_filename(base_display_name, format='parquet')
        final_metadata_file = self.cache_dir / self._get_metadata_filename(base_display_name)

        # ✅ HITO 2.2: Archivos temporales para operación atómica
        temp_cache_file = self.cache_dir / f".tmp_{base_display_name.lower().replace(' ', '_')}.parquet"
        temp_metadata_file = self.cache_dir / f".tmp_{base_display_name.lower().replace(' ', '_')}_metadata.json"

        try:
            # Asegurar que columnas específicas sean string antes de guardar
            df_to_save = df.copy()
            if base_display_name in self.STRING_COLUMNS_BY_BASE:
                string_columns = self.STRING_COLUMNS_BY_BASE[base_display_name]
                for col in string_columns:
                    if col in df_to_save.columns:
                        df_to_save[col] = df_to_save[col].astype(str)
                logging.info(f"Convirtiendo a string antes de guardar: {string_columns}")

            # 1️⃣ Guardar Parquet en archivo TEMPORAL
            logging.info(f"💾 Guardando datos temporales para '{base_display_name}'...")
            df_to_save.to_parquet(
                temp_cache_file,
                engine='pyarrow',
                compression='snappy',
                index=False
            )

            # 2️⃣ Generar checksum del archivo temporal
            with open(temp_cache_file, 'rb') as f:
                content = f.read()
                checksum = hashlib.md5(content).hexdigest()

            # 3️⃣ Guardar metadata en archivo TEMPORAL
            metadata = {
                'base_display_name': base_display_name,
                'source_url': source_url,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'checksum': checksum,
                'row_count': len(df_to_save),
                'column_count': len(df_to_save.columns),
                'file_size_bytes': len(content),
                'format': 'parquet'
            }

            with open(temp_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # 4️⃣ ✅ OPERACIÓN ATÓMICA: Mover archivos temporales a finales
            # En sistemas POSIX, Path.replace() es atómico si están en el mismo filesystem
            logging.info(f"🔄 Aplicando cambios atómicos...")
            temp_cache_file.replace(final_cache_file)        # Atómico
            temp_metadata_file.replace(final_metadata_file)  # Atómico

            logging.info(
                f"✅ Caché guardado exitosamente: {base_display_name}\n"
                f"   📁 Archivo: {final_cache_file.name}\n"
                f"   📊 Tamaño: {len(content):,} bytes ({len(content) / 1024 / 1024:.2f} MB)\n"
                f"   📈 Registros: {len(df_to_save):,}\n"
                f"   🔒 Checksum: {checksum}"
            )
            return True

        except Exception as e:
            logging.error(f"❌ Error guardando caché para '{base_display_name}': {e}")

            # 🧹 Limpiar archivos temporales si existen
            for temp_file in [temp_cache_file, temp_metadata_file]:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                        logging.info(f"🧹 Limpiado archivo temporal: {temp_file.name}")
                    except Exception as cleanup_error:
                        logging.warning(f"⚠️ Error limpiando temporal {temp_file.name}: {cleanup_error}")

            return False

    def _retry_with_backoff(self,
                           func: Callable,
                           operation_name: str = "operación",
                           exceptions: tuple = (requests.exceptions.Timeout,
                                              requests.exceptions.ConnectionError,
                                              requests.exceptions.RequestException)) -> Any:
        """
        Reintenta una función con backoff exponencial (Hito 2.1).

        Args:
            func: Función a ejecutar (sin argumentos, usar lambda si es necesario)
            operation_name: Nombre descriptivo de la operación para logs
            exceptions: Tupla de excepciones que disparan reintentos

        Returns:
            Resultado de la función

        Raises:
            Última excepción si todos los intentos fallan
        """
        delay = self.INITIAL_RETRY_DELAY
        last_exception = None

        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                if attempt == self.MAX_RETRY_ATTEMPTS:
                    logging.error(
                        f"❌ {operation_name} falló después de {self.MAX_RETRY_ATTEMPTS} intentos: {e}"
                    )
                    raise

                logging.warning(
                    f"⚠️ {operation_name} - Intento {attempt}/{self.MAX_RETRY_ATTEMPTS} falló: {e}. "
                    f"Reintentando en {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= self.RETRY_BACKOFF_FACTOR

        raise last_exception

    def check_remote_update(self,
                           base_display_name: str,
                           source_url: str,
                           auth_headers: Optional[Dict] = None,
                           source_type: str = "sharepoint",
                           azure_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Verifica si hay actualizaciones disponibles en la fuente remota.

        Soporta SharePoint (Graph API) y Azure Blob Storage (blob properties).

        Args:
            base_display_name: Nombre de la base para identificar caché
            source_url: URL de la fuente (SharePoint) o nombre del blob (Azure)
            auth_headers: Headers de autenticación (solo para SharePoint)
            source_type: Tipo de fuente ("sharepoint" o "azure")
            azure_config: Configuración Azure (connection_string, container_name, blob_name)

        Returns:
            dict: {
                'update_available': bool,
                'remote_last_modified': str,
                'cache_timestamp': str,
                'comparison_details': str,
                'error': str (opcional)
            }
        """
        from datetime import datetime, timezone

        result = {
            'update_available': False,
            'remote_last_modified': None,
            'cache_timestamp': None,
            'comparison_details': '',
            'error': None
        }

        # Obtener metadata local
        metadata = self.get_cached_metadata(base_display_name)
        if not metadata:
            result['update_available'] = True
            result['error'] = 'No hay cache local'
            result['comparison_details'] = 'Cache local no encontrado'
            return result

        result['cache_timestamp'] = metadata.get('cached_at')

        try:
            # BRANCH 1: SharePoint (código existente - NO MODIFICAR)
            if source_type == "sharepoint":
                import base64

                headers = auth_headers or {}
                logging.info(f"Verificando actualizaciones para {base_display_name} con URL: {source_url}")
                logging.info(f"Headers de autenticación: {'Sí' if headers else 'No'}")

                # Validar que el URL no esté vacío
                if not source_url or not source_url.strip():
                    result['error'] = 'URL de SharePoint vacía en configuración'
                    result['comparison_details'] = 'Falta source_url en blob_attrs - revisar _build_blob_config()'
                    logging.error(f"⚠️ URL vacía para '{base_display_name}' - saltando verificación de actualización")
                    return result

                # Codificar la URL de SharePoint igual que en _download_sharepoint_file_chunked
                if '#' in source_url:
                    source_url = source_url.split('#')[0].strip()

                sharepoint_url_bytes = source_url.encode('utf-8')
                encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')

                # Usar Graph API para obtener metadata del archivo
                graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/driveItem"
                logging.info(f"Graph API URL: {graph_url}")

                # ✅ HITO 2.1: Usar reintentos con backoff para llamada a Graph API
                def _fetch_sharepoint_metadata():
                    """Función interna para Graph API call con reintentos."""
                    resp = requests.get(graph_url, headers=headers, timeout=15, verify=False)
                    logging.info(f"Response status: {resp.status_code}")
                    return resp

                try:
                    response = self._retry_with_backoff(
                        _fetch_sharepoint_metadata,
                        operation_name=f"Verificación SharePoint '{base_display_name}'",
                        exceptions=(
                            requests.exceptions.Timeout,
                            requests.exceptions.ConnectionError,
                            requests.exceptions.RequestException
                        )
                    )
                except (requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.RequestException) as retry_error:
                    # Si falló después de todos los reintentos, registrar y continuar
                    result['error'] = f'Error de red después de {self.MAX_RETRY_ATTEMPTS} intentos: {str(retry_error)}'
                    result['comparison_details'] = 'Timeout o error de conexión persistente con SharePoint'
                    return result

                if response.status_code == 200:
                    # Graph API devuelve JSON con metadata del archivo
                    file_data = response.json()
                    remote_last_modified = file_data.get('lastModifiedDateTime')

                    if remote_last_modified:
                        result['remote_last_modified'] = remote_last_modified

                        # Parsear timestamps para comparación
                        cache_time = datetime.fromisoformat(metadata['cached_at'].replace('Z', '+00:00'))
                        if cache_time.tzinfo is None:
                            cache_time = cache_time.replace(tzinfo=timezone.utc)

                        # Graph API devuelve timestamps en formato ISO8601
                        remote_time = datetime.fromisoformat(remote_last_modified.replace('Z', '+00:00'))
                        if remote_time.tzinfo is None:
                            remote_time = remote_time.replace(tzinfo=timezone.utc)

                        # ✅ HITO 1.1: Comparar timestamps con tolerancia de clock skew
                        # Previene falsos positivos cuando el reloj local difiere del servidor
                        if remote_time > (cache_time + self.TIMESTAMP_TOLERANCE):
                            result['update_available'] = True
                            diff = (remote_time - cache_time).total_seconds() / 60
                            result['comparison_details'] = (
                                f'🔄 Archivo de SharePoint más reciente: {remote_last_modified} '
                                f'vs Cache: {metadata["cached_at"]} (diferencia: {diff:.1f} min)'
                            )
                            result['reason'] = f'Remoto más reciente por {diff:.1f} minutos'
                        else:
                            result['update_available'] = False
                            diff = (cache_time - remote_time).total_seconds() / 60
                            result['comparison_details'] = (
                                f'✅ Cache actualizado: {metadata["cached_at"]} '
                                f'vs SharePoint: {remote_last_modified} (diferencia: {diff:.1f} min, dentro de tolerancia)'
                            )
                            result['reason'] = 'Cache dentro del margen de tolerancia'

                    else:
                        # Si no hay lastModifiedDateTime, verificar eTag
                        etag = file_data.get('eTag') or response.headers.get('ETag')
                        if etag:
                            result['update_available'] = True
                            result['comparison_details'] = 'No se pudo comparar timestamps, usando ETag como referencia'
                        else:
                            result['update_available'] = True
                            result['error'] = 'No se pudo obtener timestamp remoto ni ETag'
                            result['comparison_details'] = 'SharePoint no proporciona información de modificación'
                elif response.status_code == 400:
                    # HTTP 400 Bad Request - típicamente por token sin scopes adecuados o URL mal formada
                    result['error'] = f'Error HTTP: {response.status_code} - Bad Request'
                    try:
                        error_detail = response.json()
                        result['comparison_details'] = f"Detalles: {error_detail.get('error', {}).get('message', 'URL mal formada o token sin permisos')}"
                        logging.error(f"⚠️ HTTP 400 para '{base_display_name}': {error_detail}")
                    except:
                        result['comparison_details'] = 'Posible problema: URL codificada incorrectamente o token sin scope Files.ReadWrite.All'
                        logging.error(f"⚠️ HTTP 400 para '{base_display_name}' - URL original: {source_url}")
                        logging.error(f"⚠️ URL codificada: {encoded_url[:50]}...")
                elif response.status_code == 401:
                    result['error'] = 'Error de autorización - token expirado o inválido'
                    result['comparison_details'] = 'Requiere reautenticación con SharePoint'
                elif response.status_code == 404:
                    result['error'] = 'Archivo no encontrado en SharePoint'
                    result['comparison_details'] = 'El archivo puede haber sido movido o eliminado'
                else:
                    result['error'] = f'Error HTTP: {response.status_code}'
                    result['comparison_details'] = f'Respuesta inesperada del servidor SharePoint'

            # BRANCH 2: Azure Blob Storage (NUEVO - HITO 1.4)
            elif source_type == "azure":
                from azure.storage.blob import BlobServiceClient
                from azure.core.exceptions import ResourceNotFoundError

                logging.info(f"🔍 Verificando actualizaciones Azure para '{base_display_name}'...")

                # Validar configuración
                if not azure_config:
                    result['error'] = 'Falta configuración Azure (azure_config)'
                    return result

                connection_string = azure_config.get('connection_string')
                container_name = azure_config.get('container_name')
                blob_name = azure_config.get('blob_name')

                if not all([connection_string, container_name, blob_name]):
                    result['error'] = 'Configuración Azure incompleta (falta connection_string, container o blob_name)'
                    result['comparison_details'] = f'Config recibida: {list(azure_config.keys())}'
                    return result

                # Obtener metadata del blob (HEAD request, no descarga)
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )

                # ✅ HITO 2.1: Usar reintentos con backoff para llamada a Azure
                def _fetch_azure_blob_properties():
                    """Función interna para Azure blob properties con reintentos."""
                    return blob_client.get_blob_properties()

                try:
                    from azure.core.exceptions import AzureError

                    blob_properties = self._retry_with_backoff(
                        _fetch_azure_blob_properties,
                        operation_name=f"Verificación Azure '{base_display_name}'",
                        exceptions=(
                            AzureError,  # Azure SDK exceptions
                            requests.exceptions.Timeout,
                            requests.exceptions.ConnectionError,
                            ConnectionError
                        )
                    )
                    remote_last_modified = blob_properties.last_modified

                    result['remote_last_modified'] = remote_last_modified.isoformat()

                    # Parsear timestamps para comparación
                    cache_time_str = metadata.get('cached_at')
                    if not cache_time_str:
                        result['error'] = 'Metadata de caché no tiene timestamp (cached_at)'
                        return result

                    # Convertir a datetime con timezone
                    cache_time = datetime.fromisoformat(cache_time_str.replace('Z', '+00:00'))
                    if cache_time.tzinfo is None:
                        cache_time = cache_time.replace(tzinfo=timezone.utc)

                    remote_time = remote_last_modified
                    if remote_time.tzinfo is None:
                        remote_time = remote_time.replace(tzinfo=timezone.utc)

                    # ✅ HITO 1.1: Comparar timestamps con tolerancia de clock skew
                    if remote_time > (cache_time + self.TIMESTAMP_TOLERANCE):
                        result['update_available'] = True
                        diff = (remote_time - cache_time).total_seconds() / 60
                        result['comparison_details'] = (
                            f"🔄 Blob de Azure actualizado: {remote_time.isoformat()} "
                            f"vs Caché: {cache_time.isoformat()} (diferencia: {diff:.1f} min)"
                        )
                        result['reason'] = f'Blob modificado hace {diff:.1f} minutos'
                        logging.info(f"✅ {result['comparison_details']}")
                    else:
                        result['update_available'] = False
                        diff = abs((cache_time - remote_time).total_seconds() / 60)
                        result['comparison_details'] = (
                            f"✅ Caché actualizado: {cache_time.isoformat()} "
                            f"vs Blob: {remote_time.isoformat()} (diferencia: {diff:.1f} min, dentro de tolerancia)"
                        )
                        result['reason'] = 'Caché dentro del margen de tolerancia'
                        logging.info(f"✅ {result['comparison_details']}")

                except ResourceNotFoundError:
                    result['error'] = 'Blob no encontrado en Azure'
                    result['comparison_details'] = 'El blob puede haber sido movido o eliminado'
                    logging.warning(f"⚠️ {result['error']} - {result['comparison_details']}")
                except (AzureError, ConnectionError, requests.exceptions.RequestException) as azure_retry_error:
                    # Si falló después de todos los reintentos
                    result['error'] = f'Error de Azure después de {self.MAX_RETRY_ATTEMPTS} intentos: {str(azure_retry_error)}'
                    result['comparison_details'] = 'Error persistente conectando con Azure Blob Storage'
                    logging.warning(f"⚠️ {result['error']}")

            # BRANCH 3: CSV Particionados Locales (NUEVO)
            elif source_type == "local_partitioned_csv":
                import glob
                import os

                logging.info(f"🔍 Verificando actualizaciones en archivos particionados locales para '{base_display_name}'...")

                # Validar configuración
                if not azure_config:  # Reutilizamos este parámetro para pasar config
                    result['error'] = 'Falta configuración para local_partitioned_csv'
                    return result

                base_directory = azure_config.get('base_directory')
                file_pattern = azure_config.get('file_pattern', '*.csv')

                if not base_directory:
                    result['error'] = 'Configuración incompleta (falta base_directory)'
                    return result

                # Validar que el directorio existe
                if not os.path.exists(base_directory):
                    result['error'] = f"Directorio no encontrado: '{base_directory}'"
                    result['comparison_details'] = 'Verifique que OneDrive esté sincronizado'
                    return result

                # Descubrir archivos con patrón
                try:
                    full_pattern = os.path.join(base_directory, file_pattern)
                    partition_files = sorted(glob.glob(full_pattern))

                    if not partition_files:
                        result['error'] = f"No se encontraron archivos con patrón '{file_pattern}'"
                        result['comparison_details'] = f"Patrón: {full_pattern}"
                        return result

                    logging.info(f"Encontrados {len(partition_files)} archivos particionados")

                    # Obtener mtime más reciente de cualquier partición
                    latest_mtime = None
                    latest_file = None

                    for filepath in partition_files:
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=timezone.utc)
                            if latest_mtime is None or mtime > latest_mtime:
                                latest_mtime = mtime
                                latest_file = os.path.basename(filepath)
                        except OSError as e:
                            logging.warning(f"⚠️ No se pudo obtener mtime de '{os.path.basename(filepath)}': {e}")
                            continue

                    if latest_mtime is None:
                        result['error'] = 'No se pudo obtener mtime de ningún archivo'
                        result['comparison_details'] = 'Error accediendo a los archivos locales'
                        return result

                    result['remote_last_modified'] = latest_mtime.isoformat()

                    # Parsear timestamp del caché
                    cache_time_str = metadata.get('cached_at')
                    if not cache_time_str:
                        result['error'] = 'Metadata de caché no tiene timestamp (cached_at)'
                        return result

                    # Convertir a datetime con timezone
                    cache_time = datetime.fromisoformat(cache_time_str.replace('Z', '+00:00'))
                    if cache_time.tzinfo is None:
                        cache_time = cache_time.replace(tzinfo=timezone.utc)

                    # Comparar timestamps con tolerancia de clock skew (2 minutos)
                    if latest_mtime > (cache_time + self.TIMESTAMP_TOLERANCE):
                        result['update_available'] = True
                        diff = (latest_mtime - cache_time).total_seconds() / 60
                        result['comparison_details'] = (
                            f"🔄 Archivo '{latest_file}' modificado: {latest_mtime.isoformat()} "
                            f"vs Caché: {cache_time.isoformat()} (diferencia: {diff:.1f} min)"
                        )
                        result['reason'] = f'Archivo modificado hace {diff:.1f} minutos'
                        logging.info(f"✅ {result['comparison_details']}")
                    else:
                        result['update_available'] = False
                        diff = abs((cache_time - latest_mtime).total_seconds() / 60)
                        result['comparison_details'] = (
                            f"✅ Caché actualizado: {cache_time.isoformat()} "
                            f"vs Archivos: {latest_mtime.isoformat()} (diferencia: {diff:.1f} min, dentro de tolerancia)"
                        )
                        result['reason'] = 'Caché dentro del margen de tolerancia'
                        logging.info(f"✅ {result['comparison_details']}")

                except Exception as e:
                    result['error'] = f'Error verificando archivos locales: {str(e)}'
                    result['comparison_details'] = 'Error accediendo a archivos locales'
                    logging.warning(f"⚠️ {result['error']}")

            else:
                result['error'] = f'Tipo de fuente no soportado: {source_type}'
                
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout conectando con SharePoint para {base_display_name}")
            result['error'] = 'Timeout conectando con SharePoint'
            result['comparison_details'] = 'Conexión lenta o servidor no disponible'
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Error de conexión con SharePoint para {base_display_name}: {e}")
            result['error'] = 'Error de conexión con SharePoint'
            result['comparison_details'] = 'Verificar conectividad de red'
        except Exception as e:
            logging.warning(f"Error verificando actualizaciones remotas para {base_display_name}: {e}")
            result['error'] = str(e)
            result['comparison_details'] = 'Error inesperado durante la verificación'
        
        return result
    
    def clear_cache(self, base_display_name: str) -> bool:
        """Elimina cache local para una base específica."""
        if not self.is_cacheable(base_display_name):
            return False
        
        cache_file = self.cache_dir / self._get_cache_filename(base_display_name)
        metadata_file = self.cache_dir / self._get_metadata_filename(base_display_name)
        
        try:
            if cache_file.exists():
                cache_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            logging.info(f"Cache limpiado para: {base_display_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error limpiando cache: {e}")
            return False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Obtiene estado general del cache persistente."""
        status = {
            'cache_directory': str(self.cache_dir),
            'cacheable_bases': list(self.CACHEABLE_BASES),
            'cached_bases': []
        }
        
        for base_name in self.CACHEABLE_BASES:
            if self.has_cached_data(base_name):
                metadata = self.get_cached_metadata(base_name)
                status['cached_bases'].append({
                    'name': base_name,
                    'cached_at': metadata.get('cached_at') if metadata else None,
                    'row_count': metadata.get('row_count') if metadata else None,
                    'file_size_mb': round(metadata.get('file_size_bytes', 0) / 1024 / 1024, 2) if metadata else None
                })
        
        return status


# Instancia global del cache persistente
persistent_cache = PersistentCache()