"""
CSV Utils - Utilidades para procesamiento de archivos CSV.

Este módulo contiene funciones auxiliares para:
- Detección de encoding de archivos CSV
- Detección automática de separadores
- Parseo robusto de archivos CSV
- Manejo de errores de codificación
- Conversión de bytes a DataFrames

Extraído de main_logic.py para mejorar reutilización y mantenibilidad.
"""

import io
import logging
from typing import Tuple, Optional, List

import pandas as pd


def decode_csv_bytes(blob_content_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Decodifica bytes de un archivo CSV detectando automáticamente el encoding.

    Args:
        blob_content_bytes: Contenido del archivo en bytes
        filename: Nombre del archivo (para logging)

    Returns:
        Tuple con (contenido_decodificado, encoding_usado)
    """
    # Lista de encodings a probar, en orden de preferencia
    encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']

    for encoding in encodings_to_try:
        try:
            csv_content = blob_content_bytes.decode(encoding)
            logging.info(f"Archivo '{filename}' decodificado exitosamente con encoding: {encoding}")
            return csv_content, encoding
        except (UnicodeDecodeError, UnicodeError) as e:
            logging.debug(f"Encoding {encoding} falló para '{filename}': {e}")
            continue

    # Si todos los encodings fallan, usar utf-8 con manejo de errores
    try:
        csv_content = blob_content_bytes.decode('utf-8', errors='replace')
        logging.warning(f"Usando utf-8 con reemplazo de caracteres problemáticos para '{filename}'")
        return csv_content, 'utf-8-replace'
    except Exception as e:
        logging.error(f"Error crítico al decodificar '{filename}': {e}")
        raise ValueError(f"No se pudo decodificar el archivo CSV '{filename}' con ningún encoding")


def detect_csv_separator(csv_content: str, filename: str) -> str:
    """
    Detecta automáticamente el separador de un archivo CSV.

    Args:
        csv_content: Contenido del CSV como string
        filename: Nombre del archivo (para logging)

    Returns:
        Separador detectado
    """
    # Separadores comunes a probar
    separators_to_try = [',', ';', '\t', '|']

    # Tomar una muestra del archivo para análisis (primeras 5 líneas)
    sample_lines = csv_content.split('\n')[:5]
    sample_content = '\n'.join(sample_lines)

    best_separator = ','
    max_columns = 0

    for separator in separators_to_try:
        try:
            # Intentar parsear la muestra con este separador
            df_sample = pd.read_csv(
                io.StringIO(sample_content),
                separator=separator,
                nrows=3,
                header=0
            )

            num_columns = len(df_sample.columns)
            logging.debug(f"Separador '{separator}' resultó en {num_columns} columnas para '{filename}'")

            # El separador correcto debería resultar en el mayor número de columnas válidas
            if num_columns > max_columns and num_columns > 1:
                max_columns = num_columns
                best_separator = separator

        except Exception as e:
            logging.debug(f"Separador '{separator}' falló para '{filename}': {e}")
            continue

    logging.info(f"Separador detectado para '{filename}': '{best_separator}' ({max_columns} columnas)")
    return best_separator


def try_parse_csv(csv_file_like, separator: str, filename: str, usecols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Intenta parsear un archivo CSV con configuraciones robustas.

    Args:
        csv_file_like: Objeto similar a archivo (StringIO, etc.)
        separator: Separador a usar
        filename: Nombre del archivo (para logging)
        usecols: Lista opcional de nombres de columnas a cargar (reduce uso de RAM)

    Returns:
        DataFrame parseado
    """
    parse_configs = [
        # Configuración estándar
        {
            'sep': separator,
            'encoding': None,  # Ya está decodificado
            'low_memory': False,
            'dtype': str  # Leer todo como string inicialmente
        },
        # Configuración con manejo de errores
        {
            'sep': separator,
            'encoding': None,
            'low_memory': False,
            'dtype': str,
            'error_bad_lines': False,
            'warn_bad_lines': True,
            'on_bad_lines': 'warn'  # Para pandas >= 1.3
        },
        # Configuración más permisiva
        {
            'sep': separator,
            'encoding': None,
            'low_memory': False,
            'dtype': str,
            'quoting': 1,  # QUOTE_ALL
            'skipinitialspace': True
        }
    ]

    for i, config in enumerate(parse_configs):
        try:
            # Filtrar parámetros no soportados en versiones específicas de pandas
            if 'on_bad_lines' in config and not hasattr(pd.read_csv, '__code__'):
                config.pop('on_bad_lines', None)

            df = pd.read_csv(csv_file_like, **config)

            if not df.empty:
                logging.info(f"CSV '{filename}' parseado exitosamente con configuración {i + 1}")
                return df
            else:
                logging.warning(f"CSV '{filename}' resultó en DataFrame vacío con configuración {i + 1}")

        except Exception as e:
            logging.debug(f"Configuración {i + 1} falló para '{filename}': {e}")
            # Resetear el puntero del archivo para el siguiente intento
            if hasattr(csv_file_like, 'seek'):
                csv_file_like.seek(0)
            continue

    # Si todas las configuraciones fallan, lanzar error
    raise ValueError(f"No se pudo parsear el archivo CSV '{filename}' con ninguna configuración")


def fix_ean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte columnas EAN a tipo string para evitar conversión a decimal.

    Args:
        df: DataFrame a procesar

    Returns:
        DataFrame con columnas EAN como string
    """
    ean_column_names = ['ean_hijo', 'ean_padre', 'ean', 'EAN', 'EAN_HIJO', 'EAN_PADRE']

    for col in ean_column_names:
        if col in df.columns:
            # Convertir a string, eliminando .0 de valores numéricos
            df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.', '').replace('-', '').isdigit() else str(x) if pd.notna(x) else '')
            logging.info(f"Columna '{col}' convertida a string para prevenir decimales")

    return df


def read_csv_from_bytes(blob_content_bytes: bytes, filename_for_log: str, usecols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Convierte bytes de un archivo CSV a DataFrame de forma robusta.

    Esta función:
    1. Detecta automáticamente el encoding
    2. Detecta automáticamente el separador
    3. Intenta múltiples configuraciones de parseo
    4. Maneja errores de forma elegante
    5. Corrige columnas EAN para evitar conversión a decimal
    6. Opcionalmente carga solo columnas especificadas (reduce uso de RAM)

    Args:
        blob_content_bytes: Contenido del archivo en bytes
        filename_for_log: Nombre del archivo para logging
        usecols: Lista opcional de nombres de columnas a cargar (optimización de RAM)

    Returns:
        DataFrame con los datos del CSV
    """
    if not blob_content_bytes:
        logging.warning(f"Archivo '{filename_for_log}' está vacío")
        return pd.DataFrame()

    try:
        # Paso 1: Decodificar bytes a string
        csv_content, encoding_used = decode_csv_bytes(blob_content_bytes, filename_for_log)

        if not csv_content.strip():
            logging.warning(f"Archivo '{filename_for_log}' no contiene datos después de decodificación")
            return pd.DataFrame()

        # Paso 2: Detectar separador
        separator = detect_csv_separator(csv_content, filename_for_log)

        # Paso 3: Parsear CSV (SIN usecols para evitar problemas de nombres de columnas)
        # Nota: usecols requiere nombres exactos del CSV, pero nosotros los normalizamos después
        csv_file_like = io.StringIO(csv_content)
        df = try_parse_csv(csv_file_like, separator, filename_for_log, usecols=None)

        # Validar resultado
        if df.empty:
            logging.warning(f"DataFrame resultante está vacío para '{filename_for_log}'")
            return pd.DataFrame()

        # Paso 4: Normalizar nombres de columnas (lowercase, strip)
        df.columns = df.columns.str.strip().str.lower()

        # Paso 5: Filtrar columnas si se especificó usecols
        if usecols:
            # Verificar qué columnas existen realmente
            available_cols = [col for col in usecols if col in df.columns]
            missing_cols = [col for col in usecols if col not in df.columns]

            if missing_cols:
                logging.warning(f"Columnas solicitadas no encontradas en '{filename_for_log}': {missing_cols}")

            if available_cols:
                logging.info(f"Filtrando a {len(available_cols)} columnas de '{filename_for_log}': {available_cols}")
                df = df[available_cols]
            else:
                logging.error(f"Ninguna de las columnas solicitadas existe en '{filename_for_log}'")
                logging.info(f"Columnas disponibles: {list(df.columns)}")

        # Paso 6: Corregir columnas EAN
        df = fix_ean_columns(df)

        logging.info(f"CSV '{filename_for_log}' cargado exitosamente: {len(df)} filas, {len(df.columns)} columnas")
        logging.debug(f"Columnas finales: {list(df.columns)}")

        return df

    except Exception as e:
        logging.error(f"Error al procesar CSV '{filename_for_log}': {e}", exc_info=True)
        raise ValueError(f"No se pudo cargar el archivo CSV '{filename_for_log}': {e}")


def read_partitioned_csv_from_directory(
    base_directory: str,
    file_pattern: str,
    usecols: Optional[List[str]] = None,
    log_prefix: str = "partitioned_csv"
) -> pd.DataFrame:
    """
    Lee y concatena múltiples archivos CSV particionados de un directorio local.

    Esta función descubre archivos automáticamente por patrón glob, valida consistencia
    de esquemas entre particiones, y concatena eficientemente aplicando selección de columnas.

    Características:
    - Descubre archivos automáticamente por patrón glob (ej: "SABANA_part*.csv")
    - Valida consistencia de esquemas (columnas) entre todas las particiones
    - Aplica usecols a cada partición antes de cargar (optimización de RAM: reduce 85%+)
    - Concatena eficientemente con pd.concat()
    - Manejo robusto de errores (archivos corruptos, faltantes)
    - Progreso detallado por archivo en logging

    Args:
        base_directory: Ruta al directorio con archivos particionados
        file_pattern: Patrón glob para descubrir archivos (ej: "SABANA_part*.csv", "data_*.csv")
        usecols: Lista opcional de columnas (lowercase) a cargar. Si se especifica, reduce
                 uso de RAM significativamente. Si None, carga todas las columnas.
        log_prefix: Prefijo para mensajes de logging (útil para identificar fuente)

    Returns:
        pd.DataFrame: DataFrame consolidado con todas las particiones concatenadas

    Raises:
        FileNotFoundError: Directorio no existe o no se encuentran archivos con el patrón
        ValueError: Inconsistencia de esquema entre particiones o datos vacíos

    Example:
        >>> # Cargar todas las columnas de archivos SABANA_part*.csv
        >>> df = read_partitioned_csv_from_directory(
        ...     "/path/to/sabana/",
        ...     "SABANA_part*.csv"
        ... )
        >>>
        >>> # Cargar solo columnas específicas (optimizado para RAM)
        >>> df = read_partitioned_csv_from_directory(
        ...     "/path/to/sabana/",
        ...     "SABANA_part*.csv",
        ...     usecols=["ean_hijo", "sku_padre_largo", "depto", "marca"]
        ... )
    """
    import glob
    import os
    from pathlib import Path

    # 1. Validar directorio existe
    if not os.path.exists(base_directory):
        raise FileNotFoundError(
            f"Directorio de particiones no encontrado: '{base_directory}'. "
            f"Verifique que la ruta sea correcta y que OneDrive esté sincronizado."
        )

    # 2. Descubrir archivos con patrón glob
    full_pattern = os.path.join(base_directory, file_pattern)
    partition_files = sorted(glob.glob(full_pattern))

    if not partition_files:
        raise FileNotFoundError(
            f"No se encontraron archivos con patrón '{file_pattern}' en directorio '{base_directory}'. "
            f"Verifique que los archivos existan y el patrón sea correcto."
        )

    logging.info(
        f"[{log_prefix}] 📂 Descubiertos {len(partition_files)} archivos particionados "
        f"en '{base_directory}' con patrón '{file_pattern}'"
    )

    # 3. Leer primera partición (establece esquema base)
    first_file = partition_files[0]
    first_filename = os.path.basename(first_file)
    logging.info(f"[{log_prefix}] 📄 [1/{len(partition_files)}] Leyendo esquema desde '{first_filename}'...")

    try:
        with open(first_file, 'rb') as f:
            file_bytes = f.read()

        df_first = read_csv_from_bytes(file_bytes, first_filename, usecols=usecols)
        first_schema = set(df_first.columns)
        chunks = [df_first]

        logging.info(
            f"[{log_prefix}]   ✅ Esquema establecido: {len(first_schema)} columnas, "
            f"{len(df_first):,} filas"
        )
        logging.debug(f"[{log_prefix}]   Columnas: {sorted(first_schema)}")

    except Exception as e:
        logging.error(f"[{log_prefix}] ❌ Error crítico leyendo primera partición '{first_filename}': {e}")
        raise ValueError(
            f"No se pudo leer la primera partición '{first_filename}'. "
            f"Verifique que el archivo no esté corrupto. Error: {e}"
        )

    # 4. Leer particiones restantes
    for idx, filepath in enumerate(partition_files[1:], start=2):
        filename = os.path.basename(filepath)
        logging.info(f"[{log_prefix}] 📄 [{idx}/{len(partition_files)}] Leyendo '{filename}'...")

        try:
            with open(filepath, 'rb') as f:
                file_bytes = f.read()

            df_chunk = read_csv_from_bytes(file_bytes, filename, usecols=usecols)

            # Validar esquema (columnas) coincide con primera partición
            chunk_schema = set(df_chunk.columns)
            if chunk_schema != first_schema:
                missing_cols = first_schema - chunk_schema
                extra_cols = chunk_schema - first_schema
                error_msg = (
                    f"Inconsistencia de esquema detectada en '{filename}':\n"
                    f"  • Columnas faltantes (vs primera partición): {sorted(missing_cols) if missing_cols else 'ninguna'}\n"
                    f"  • Columnas adicionales (vs primera partición): {sorted(extra_cols) if extra_cols else 'ninguna'}\n"
                    f"  • Archivo de referencia: '{first_filename}'\n"
                    f"Todas las particiones deben tener las mismas columnas."
                )
                logging.error(f"[{log_prefix}] ❌ {error_msg}")
                raise ValueError(error_msg)

            chunks.append(df_chunk)
            logging.info(f"[{log_prefix}]   ✅ {len(df_chunk):,} filas cargadas")

        except ValueError as ve:
            # ValueError de esquema inconsistente - propagar (error crítico)
            raise
        except Exception as e:
            # Otros errores (archivo corrupto, etc.) - log y continuar
            logging.error(
                f"[{log_prefix}] ⚠️ Error procesando '{filename}': {e}. "
                f"Saltando este archivo y continuando con los demás..."
            )
            continue

    # 5. Validar que se cargaron datos
    if not chunks:
        raise ValueError(
            f"No se pudieron cargar datos de ningún archivo en '{base_directory}'. "
            f"Verifique que los archivos no estén corruptos."
        )

    if len(chunks) < len(partition_files):
        logging.warning(
            f"[{log_prefix}] ⚠️ Solo se cargaron {len(chunks)} de {len(partition_files)} archivos. "
            f"Algunos archivos fueron saltados por errores."
        )

    # 6. Concatenar todas las particiones
    logging.info(f"[{log_prefix}] 🔗 Concatenando {len(chunks)} particiones...")
    df_combined = pd.concat(chunks, ignore_index=True)

    if df_combined.empty:
        raise ValueError(
            f"Resultado vacío después de concatenar archivos de '{base_directory}'. "
            f"Verifique que los archivos contengan datos."
        )

    logging.info(
        f"[{log_prefix}] ✅ Carga particionada completada exitosamente: "
        f"{len(df_combined):,} filas totales, {len(df_combined.columns)} columnas"
    )
    logging.debug(f"[{log_prefix}]   Columnas finales: {sorted(df_combined.columns)}")

    return df_combined


def read_partitioned_csv_from_sharepoint(
    sharepoint_folder_url: str,
    file_pattern: str,
    usecols: Optional[List[str]] = None,
    log_prefix: str = "sharepoint_partitioned"
) -> pd.DataFrame:
    """
    Lee múltiples archivos CSV particionados desde SharePoint y los concatena.
    Replica la lógica de read_partitioned_csv_from_directory pero usando Graph API.

    Args:
        sharepoint_folder_url: URL de la carpeta SharePoint
        file_pattern: Patrón para filtrar archivos (ej: "SABANA_part*.csv")
        usecols: Columnas a leer (optimización de RAM)
        log_prefix: Prefijo para logs

    Returns:
        DataFrame con todas las particiones concatenadas
    """
    import logging

    # Imports absolutos para evitar problemas de módulos
    from services import storage_utils
    from main_logic import get_sharepoint_authenticator
    import requests

    logging.info(f"[{log_prefix}] 📦 Iniciando descarga particionada desde SharePoint")
    logging.info(f"[{log_prefix}]   URL: {sharepoint_folder_url}")
    logging.info(f"[{log_prefix}]   Patrón: {file_pattern}")

    # 1. Autenticación
    auth = get_sharepoint_authenticator()
    access_token = auth.get_token()

    # 2. Listar archivos que coincidan con el patrón
    files = storage_utils.list_sharepoint_directory_files(
        sharepoint_folder_url,
        file_pattern,
        access_token
    )

    if not files:
        raise FileNotFoundError(
            f"No se encontraron archivos con patrón '{file_pattern}' en:\n"
            f"  {sharepoint_folder_url}\n"
            f"Verifique permisos y validez de la URL."
        )

    logging.info(f"[{log_prefix}] 📋 {len(files)} particiones encontradas")

    # Helper function para descargar desde Graph API directamente
    def _download_from_graph_api(download_url: str, access_token: str) -> bytes:
        """Descarga un archivo directamente desde Graph API."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(download_url, headers=headers, stream=True, timeout=300, verify=False)
        response.raise_for_status()

        content_chunks = []
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content_chunks.append(chunk)

        return b''.join(content_chunks)

    # 3. Descargar y parsear primera partición (establecer esquema de referencia)
    first_file = files[0]
    logging.info(
        f"[{log_prefix}] ⬇️  Descargando partición 1/{len(files)}: "
        f"{first_file['name']} ({first_file['size'] / 1024:.0f} KB)"
    )

    first_bytes = _download_from_graph_api(first_file['download_url'], access_token)
    df_first = read_csv_from_bytes(
        blob_content_bytes=first_bytes,
        filename_for_log=first_file['name'],
        usecols=usecols
    )

    first_schema = set(df_first.columns)
    first_filename = first_file['name']
    logging.info(
        f"[{log_prefix}] ✓ Partición 1: {len(df_first):,} filas, "
        f"{len(df_first.columns)} columnas"
    )

    chunks = [df_first]

    # 4. Descargar y parsear particiones restantes (con validación de esquema)
    for idx, file_info in enumerate(files[1:], start=2):
        logging.info(
            f"[{log_prefix}] ⬇️  Descargando partición {idx}/{len(files)}: "
            f"{file_info['name']} ({file_info['size'] / 1024:.0f} KB)"
        )

        try:
            # Descargar archivo
            file_bytes = _download_from_graph_api(file_info['download_url'], access_token)

            # Parsear CSV
            df_chunk = read_csv_from_bytes(
                blob_content_bytes=file_bytes,
                filename_for_log=file_info['name'],
                usecols=usecols
            )

            # Validación de esquema (mismo que local_partitioned_csv)
            chunk_schema = set(df_chunk.columns)
            if chunk_schema != first_schema:
                missing = first_schema - chunk_schema
                extra = chunk_schema - first_schema
                raise ValueError(
                    f"Schema mismatch en partición '{file_info['name']}':\n"
                    f"  Columnas faltantes: {sorted(missing)}\n"
                    f"  Columnas adicionales: {sorted(extra)}\n"
                    f"  Partición de referencia: '{first_filename}'"
                )

            logging.info(f"[{log_prefix}] ✓ Partición {idx}: {len(df_chunk):,} filas")
            chunks.append(df_chunk)

        except ValueError as ve:
            # Error de esquema - crítico, detener proceso
            logging.error(f"[{log_prefix}] ✗ Error de esquema en '{file_info['name']}': {ve}")
            raise
        except Exception as e:
            # Otros errores - registrar y continuar (permite partial success)
            logging.warning(
                f"[{log_prefix}] ⚠️  Error procesando '{file_info['name']}': {e}"
            )
            logging.warning(f"[{log_prefix}] ⚠️  Saltando partición corrupta y continuando...")
            continue

    # 5. Concatenar todas las particiones
    if not chunks:
        raise ValueError("No se pudieron cargar particiones válidas")

    logging.info(f"[{log_prefix}] 🔗 Concatenando {len(chunks)} particiones válidas...")
    df_combined = pd.concat(chunks, ignore_index=True)

    logging.info(
        f"[{log_prefix}] ✅ Carga completa: {len(df_combined):,} filas totales, "
        f"{len(df_combined.columns)} columnas"
    )

    return df_combined


# Clase contenedora para todas las utilidades CSV
class CSVUtils:
    """Clase contenedora para todas las utilidades de CSV."""

    @staticmethod
    def decode_csv_bytes(blob_content_bytes: bytes, filename: str) -> Tuple[str, str]:
        return decode_csv_bytes(blob_content_bytes, filename)

    @staticmethod
    def detect_csv_separator(csv_content: str, filename: str) -> str:
        return detect_csv_separator(csv_content, filename)

    @staticmethod
    def try_parse_csv(csv_file_like, separator: str, filename: str, usecols: Optional[List[str]] = None) -> pd.DataFrame:
        return try_parse_csv(csv_file_like, separator, filename, usecols=usecols)

    @staticmethod
    def fix_ean_columns(df: pd.DataFrame) -> pd.DataFrame:
        return fix_ean_columns(df)

    @staticmethod
    def read_csv_from_bytes(blob_content_bytes: bytes, filename_for_log: str, usecols: Optional[List[str]] = None) -> pd.DataFrame:
        return read_csv_from_bytes(blob_content_bytes, filename_for_log, usecols=usecols)

    @staticmethod
    def read_partitioned_csv_from_directory(
        base_directory: str,
        file_pattern: str,
        usecols: Optional[List[str]] = None,
        log_prefix: str = "partitioned_csv"
    ) -> pd.DataFrame:
        """
        Método estático wrapper para read_partitioned_csv_from_directory.
        Sigue el mismo patrón que los otros métodos de CSVUtils.
        """
        return read_partitioned_csv_from_directory(base_directory, file_pattern, usecols, log_prefix)

    @staticmethod
    def read_partitioned_csv_from_sharepoint(
        sharepoint_folder_url: str,
        file_pattern: str,
        usecols: Optional[List[str]] = None,
        log_prefix: str = "sharepoint_partitioned"
    ) -> pd.DataFrame:
        """
        Método estático wrapper para read_partitioned_csv_from_sharepoint.
        Sigue el mismo patrón que los otros métodos de CSVUtils.
        """
        return read_partitioned_csv_from_sharepoint(sharepoint_folder_url, file_pattern, usecols, log_prefix)


def process_sku_file_upload(file_content: bytes, filename: Optional[str] = None) -> List[str]:
    """
    Lee de forma robusta un archivo (Excel, CSV, TXT), extrae los valores de la primera
    columna y los devuelve como una lista de strings únicos, limpios y validados.
    """
    log_filename = filename if filename else "archivo sin nombre"
    logging.info(f"Iniciando procesamiento de archivo para filtro: {log_filename}")

    file_stream = io.BytesIO(file_content)
    df = pd.DataFrame()

    try:
        # Intento 1: Leer como Excel si la extensión lo sugiere
        if filename and filename.lower().endswith(('.xlsx', '.xls')):
            # Clave: dtype=str fuerza que todo se lea como texto desde el principio.
            df = pd.read_excel(file_stream, header=None, dtype=str)
        else:
            # Intento 2: Leer como texto delimitado (CSV, TXT)
            # Volvemos a decodificar el contenido para leerlo como texto.
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = file_content.decode('latin-1', errors='ignore')

            # Pandas es excelente para auto-detectar separadores en CSV
            # al pasarle el contenido como un stream de texto.
            df = pd.read_csv(io.StringIO(content_str), header=None, dtype=str, sep=None, engine='python')

    except Exception as e:
        logging.error(f"No se pudo leer el archivo '{log_filename}' con los métodos estándar. Error: {e}")
        # Se devuelve una lista vacía para no romper el flujo.
        return []

    # --- PROCESAMIENTO CENTRALIZADO Y ROBUSTO ---
    if df.empty or df.shape[1] == 0:
        logging.warning(f"El archivo '{log_filename}' está vacío o no se pudo interpretar correctamente.")
        return []

    # 1. Seleccionar solo la primera columna.
    # 2. .dropna() elimina cualquier fila completamente vacía (NaN).
    # 3. .astype(str) se asegura de que todo sea un string.
    # 4. .str.strip() es el paso CRÍTICO: elimina espacios al inicio y final de CADA string.
    # 5. Filtramos para quitar cualquier string que haya quedado vacío DESPUÉS de limpiar.
    # 6. .unique() nos da solo los valores distintos.
    # 7. .tolist() lo convierte en la lista que necesitamos.

    first_column = df.iloc[:, 0]
    cleaned_ids = first_column.dropna().astype(str).str.strip()
    processed_ids = cleaned_ids[cleaned_ids != ''].unique().tolist()

    logging.info(f"Se extrajeron {len(processed_ids)} IDs únicos y limpios del archivo '{log_filename}'.")

    return processed_ids


# Instancia global para fácil acceso
csv_utils = CSVUtils()