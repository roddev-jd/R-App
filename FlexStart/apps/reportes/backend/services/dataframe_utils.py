"""
DataFrame Utils - Utilidades para procesamiento y optimización de DataFrames.

Este módulo contiene funciones auxiliares para:
- Detección y manejo de valores NaN/NAT
- Optimización de tipos de datos
- Información de prioridades
- Enriquecimiento de datos
- Optimizaciones de memoria

Extraído de main_logic.py para mejorar reutilización y mantenibilidad.
"""

import logging
from typing import Dict, Any, Optional, List

import pandas as pd
import numpy as np


def create_nan_mask(series: pd.Series) -> pd.Series:
    """
    Crea una máscara booleana para identificar valores NaN, NaT y strings vacíos.

    Args:
        series: Serie de pandas a procesar

    Returns:
        Serie booleana con True para valores considerados "vacíos"
    """
    mask = series.isna()

    # Para series de strings, también considerar strings vacíos y solo espacios
    if series.dtype == 'object':
        string_mask = series.astype(str).str.strip().isin(['', 'nan', 'NaN', 'None'])
        mask = mask | string_mask

    return mask


def _create_nan_mask(series: pd.Series) -> pd.Series:
    """Crea máscara para identificar valores NaN/NaT en una serie."""
    mask = pd.isna(series)
    str_series = series.astype(str)
    text_mask = (
        str_series.str.lower().eq('nan') |
        str_series.str.lower().eq('nat') |
        str_series.str.contains(r'^nan$|^NaN$|^NaT$', na=False, regex=True) |
        str_series.str.contains('NaT', na=False)
    )
    return mask | text_mask


def _get_priority_info(df_full: pd.DataFrame, df_page: pd.DataFrame = None, start_idx: int = 0) -> Dict[str, Any]:
    """
    Extrae información de prioridad de los datos para el coloreado de filas.

    Args:
        df_full: DataFrame completo filtrado para detectar columna de prioridad
        df_page: DataFrame de la página actual (opcional)
        start_idx: Índice inicial de la página

    Returns:
        Dict con información de prioridades por fila
    """
    priority_info = {
        "has_priority_column": False,
        "row_priorities": {},
        "priority_counts": {
            "PRIORIDAD_1": 0,
            "PRIORIDAD_2": 0,
            "PRIORIDAD_3": 0,
            "other": 0
        }
    }

    # Buscar columna de prioridad en el DataFrame completo
    priority_column = None
    possible_names = ['prioridad', 'PRIORIDAD', 'Prioridad', 'priority', 'PRIORITY', 'Priority']

    for col_name in possible_names:
        if col_name in df_full.columns:
            priority_column = col_name
            break

    if priority_column is None:
        logging.info(f"No se encontró columna de prioridad en los datos. Columnas disponibles: {list(df_full.columns)}")
        return priority_info

    priority_info["has_priority_column"] = True
    priority_info["column_name"] = priority_column

    # Primero, calcular conteos totales desde df_full para porcentajes correctos
    for _, row in df_full.iterrows():
        priority_value = str(row[priority_column]).strip().upper()

        # Contar prioridades en el dataset completo
        if priority_value in ["PRIORIDAD_1", "PRIORITY_1"]:
            priority_info["priority_counts"]["PRIORIDAD_1"] += 1
        elif priority_value in ["PRIORIDAD_2", "PRIORITY_2"]:
            priority_info["priority_counts"]["PRIORIDAD_2"] += 1
        elif priority_value in ["PRIORIDAD_3", "PRIORITY_3"]:
            priority_info["priority_counts"]["PRIORIDAD_3"] += 1
        else:
            priority_info["priority_counts"]["other"] += 1

    # Luego, procesar las filas específicas de la página si df_page está disponible
    if df_page is not None and priority_column is not None:
        # Verificar que la columna de prioridad existe en df_page
        if priority_column in df_page.columns:
            for row_num, (index, row) in enumerate(df_page.iterrows()):
                priority_value = str(row[priority_column]).strip().upper()
                # Usar el número de fila secuencial para paginación
                priority_info["row_priorities"][row_num] = priority_value
        else:
            logging.warning(f"Columna de prioridad '{priority_column}' no está disponible en df_page. Columnas disponibles: {list(df_page.columns)}")

    logging.info(f"Columna de prioridad '{priority_column}' encontrada. Información procesada: {priority_info['priority_counts']}")
    return priority_info


def get_priority_info(df_full: pd.DataFrame, df_page: pd.DataFrame = None, start_idx: int = 0) -> Dict[str, Any]:
    """
    Genera información detallada sobre las prioridades en un DataFrame.

    Args:
        df_full: DataFrame completo para estadísticas globales
        df_page: DataFrame de la página actual (opcional)
        start_idx: Índice de inicio para la página actual

    Returns:
        Diccionario con información de prioridades y índices de filas
    """
    if not has_priority_column(df_full):
        return {}

    priority_col = 'prioridad'

    # Contar prioridades en el DataFrame completo
    priority_counts = df_full[priority_col].value_counts().to_dict()

    # Información base
    priority_info = {
        'total_rows': len(df_full),
        'priority_counts': priority_counts,
        'has_priority_data': len(priority_counts) > 0
    }

    # Si se proporciona DataFrame de página, agregar información específica
    if df_page is not None:
        page_priority_counts = df_page[priority_col].value_counts().to_dict()
        priority_info.update({
            'page_rows': len(df_page),
            'page_priority_counts': page_priority_counts,
            'start_index': start_idx
        })

        # Generar mapeo de índices de fila a información de prioridad
        if len(df_page) > 0:
            row_info = {}
            for idx, row in df_page.iterrows():
                actual_row_idx = start_idx + (idx - df_page.index[0])
                priority_value = row.get(priority_col, 'UNKNOWN')
                row_info[actual_row_idx] = {
                    'priority': priority_value,
                    'row_index': actual_row_idx
                }
            priority_info['row_mapping'] = row_info

    # Normalizar conteos con nombres estándar
    normalized_counts = {}
    for priority, count in priority_counts.items():
        if 'PRIORIDAD_1' in str(priority):
            normalized_counts['PRIORIDAD_1'] = count
        elif 'PRIORIDAD_2' in str(priority):
            normalized_counts['PRIORIDAD_2'] = count
        elif 'PRIORIDAD_3' in str(priority):
            normalized_counts['PRIORIDAD_3'] = count
        else:
            normalized_counts['other'] = normalized_counts.get('other', 0) + count

    priority_info['normalized_counts'] = normalized_counts

    return priority_info


def has_priority_column(df: pd.DataFrame) -> bool:
    """
    Verifica si el DataFrame tiene una columna de prioridad válida.

    Args:
        df: DataFrame a verificar

    Returns:
        True si tiene columna de prioridad con datos válidos
    """
    if df.empty:
        return False

    priority_candidates = ['prioridad', 'priority', 'Prioridad', 'PRIORIDAD']

    for col in priority_candidates:
        if col in df.columns:
            # Verificar que la columna tenga datos no nulos
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                # Verificar que contenga valores de prioridad reconocibles
                priority_values = non_null_values.astype(str).str.upper()
                has_priority_data = any(
                    'PRIORIDAD' in val or 'PRIORITY' in val
                    for val in priority_values.unique()
                )
                if has_priority_data:
                    return True

    return False


def find_first_existing_column(df, candidates):
    """
    Busca la primera columna existente en el DataFrame de una lista de candidatos.
    Incluye búsqueda por similitud ignorando guiones, espacios y case.
    """
    for col in candidates:
        if col in df.columns:
            return col
    # Buscar variantes por similitud (ignorando guiones, espacios, etc.)
    for col in candidates:
        target_clean = col.replace('_', '').replace('-', '').replace(' ', '').lower()
        for df_col in df.columns:
            df_col_clean = df_col.replace('_', '').replace('-', '').replace(' ', '').lower()
            if df_col_clean == target_clean:
                return df_col
    return None


def get_optimal_int_dtype(min_val, max_val):
    """
    Determina el tipo de entero más eficiente para un rango de valores.

    Args:
        min_val: Valor mínimo
        max_val: Valor máximo

    Returns:
        Tipo de datos numpy más eficiente
    """
    if min_val >= 0:
        # Enteros sin signo
        if max_val <= np.iinfo(np.uint8).max:
            return np.uint8
        elif max_val <= np.iinfo(np.uint16).max:
            return np.uint16
        elif max_val <= np.iinfo(np.uint32).max:
            return np.uint32
        else:
            return np.uint64
    else:
        # Enteros con signo
        if min_val >= np.iinfo(np.int8).min and max_val <= np.iinfo(np.int8).max:
            return np.int8
        elif min_val >= np.iinfo(np.int16).min and max_val <= np.iinfo(np.int16).max:
            return np.int16
        elif min_val >= np.iinfo(np.int32).min and max_val <= np.iinfo(np.int32).max:
            return np.int32
        else:
            return np.int64


def should_convert_to_category(series: pd.Series) -> bool:
    """
    Determina si una serie debería convertirse a tipo categorical.

    Args:
        series: Serie de pandas a evaluar

    Returns:
        True si la conversión a categorical sería beneficiosa
    """
    if len(series) < 100:  # No vale la pena para series pequeñas
        return False

    unique_count = series.nunique()
    total_count = len(series)

    # Convertir si hay menos del 50% de valores únicos
    return unique_count / total_count < 0.5


def _optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Reduce memory usage optimizando tipos de datos con métricas de mejora."""

    # Calcular memoria inicial
    memory_before = df.memory_usage(deep=True).sum()
    logging.info(f"Memoria antes de optimización: {memory_before / 1024 / 1024:.2f} MB")

    # Optimizaciones específicas para columnas comunes de bases pesadas
    heavy_db_optimizations = {
        'sku_hijo': 'category',
        'sku_padre': 'category',
        'ean_hijo': 'category',
        'depto': 'category',
        'marca': 'category',
        'color': 'category',
        'estado': 'category',
        'nom_estado': 'category',
        'celula': 'category',
        'prioridad': 'category',
        'division': 'category'
    }

    for col in df.columns:
        series = df[col]

        # Aplicar optimizaciones específicas primero
        col_lower = col.lower()
        if col_lower in heavy_db_optimizations:
            try:
                df[col] = series.astype(heavy_db_optimizations[col_lower])
                continue
            except Exception as e:
                logging.warning(f"No se pudo convertir {col} a {heavy_db_optimizations[col_lower]}: {e}")

        if pd.api.types.is_object_dtype(series):
            # Intentar conversión numérica
            num_series = pd.to_numeric(series, errors="coerce")
            if num_series.notna().all():
                if (num_series % 1 == 0).all():  # Es entero
                    min_val, max_val = num_series.min(), num_series.max()
                    df[col] = num_series.astype(get_optimal_int_dtype(min_val, max_val))
                else:  # Es float
                    df[col] = num_series.astype("float32")
                continue

            # Considerar categorical para strings
            if should_convert_to_category(series):
                df[col] = series.astype("category")

        elif pd.api.types.is_integer_dtype(series):
            min_val, max_val = series.min(), series.max()
            df[col] = series.astype(get_optimal_int_dtype(min_val, max_val))

        elif pd.api.types.is_float_dtype(series):
            df[col] = series.astype("float32")

    # Calcular mejora de memoria
    memory_after = df.memory_usage(deep=True).sum()
    memory_saved = memory_before - memory_after
    reduction_pct = (memory_saved / memory_before) * 100

    logging.info(f"Memoria después de optimización: {memory_after / 1024 / 1024:.2f} MB")
    logging.info(f"Memoria ahorrada: {memory_saved / 1024 / 1024:.2f} MB ({reduction_pct:.1f}%)")

    return df


def optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimiza los tipos de datos de un DataFrame para reducir uso de memoria.

    Args:
        df: DataFrame a optimizar

    Returns:
        DataFrame optimizado (copia)
    """
    if df.empty:
        return df.copy()

    df_optimized = df.copy()
    original_memory = df_optimized.memory_usage(deep=True).sum()

    for col in df_optimized.columns:
        col_type = df_optimized[col].dtype

        # Optimizar columnas numéricas
        if pd.api.types.is_numeric_dtype(col_type):
            # Enteros
            if pd.api.types.is_integer_dtype(col_type):
                min_val = df_optimized[col].min()
                max_val = df_optimized[col].max()
                optimal_dtype = get_optimal_int_dtype(min_val, max_val)
                df_optimized[col] = df_optimized[col].astype(optimal_dtype)

            # Flotantes
            elif pd.api.types.is_float_dtype(col_type):
                # Verificar si se puede convertir a entero
                if df_optimized[col].notnull().all() and (df_optimized[col] % 1 == 0).all():
                    min_val = int(df_optimized[col].min())
                    max_val = int(df_optimized[col].max())
                    optimal_dtype = get_optimal_int_dtype(min_val, max_val)
                    df_optimized[col] = df_optimized[col].astype(optimal_dtype)
                else:
                    # Usar float32 si es posible
                    if col_type == np.float64:
                        df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='float')

        # Optimizar columnas de objeto
        elif col_type == 'object':
            if should_convert_to_category(df_optimized[col]):
                df_optimized[col] = df_optimized[col].astype('category')

    optimized_memory = df_optimized.memory_usage(deep=True).sum()
    memory_saved = original_memory - optimized_memory
    reduction_percent = (memory_saved / original_memory) * 100

    logging.info(f"Memoria antes de optimización: {original_memory / 1024 / 1024:.2f} MB")
    logging.info(f"Memoria después de optimización: {optimized_memory / 1024 / 1024:.2f} MB")
    logging.info(f"Memoria ahorrada: {memory_saved / 1024 / 1024:.2f} MB ({reduction_percent:.1f}%)")

    return df_optimized


def _enrich_dataframe(df_main: pd.DataFrame, df_enrichment: pd.DataFrame, join_column: str, enrichment_columns: List[str]) -> pd.DataFrame:
    """
    Enriquece el DataFrame principal con datos del DataFrame de enriquecimiento.
    """
    logging.info(f"Iniciando enriquecimiento con {len(df_main)} filas principales y {len(df_enrichment)} filas de enriquecimiento")

    # Normalizar nombres de columnas para el JOIN
    join_column_main = 'sku_hijo_largo'  # Columna en el DataFrame principal
    join_column_enrichment = join_column  # Columna en el DataFrame de enriquecimiento

    # Verificar que las columnas de JOIN existan
    if join_column_main not in df_main.columns:
        logging.error(f"Columna de JOIN '{join_column_main}' no encontrada en DataFrame principal")
        return df_main

    if join_column_enrichment not in df_enrichment.columns:
        logging.error(f"Columna de JOIN '{join_column_enrichment}' no encontrada en DataFrame de enriquecimiento")
        return df_main

    # Preparar columnas de enriquecimiento (solo las que existen)
    available_enrichment_columns = [col for col in enrichment_columns if col in df_enrichment.columns]
    if not available_enrichment_columns:
        logging.warning("Ninguna columna de enriquecimiento disponible")
        return df_main

    # Crear DataFrame de enriquecimiento con solo las columnas necesarias
    df_enrichment_subset = df_enrichment[[join_column_enrichment] + available_enrichment_columns].copy()

    # Renombrar columna de JOIN en el DataFrame de enriquecimiento para evitar conflictos
    df_enrichment_subset = df_enrichment_subset.rename(columns={join_column_enrichment: join_column_main})

    # Realizar LEFT JOIN
    df_enriched = df_main.merge(
        df_enrichment_subset,
        on=join_column_main,
        how='left',
        suffixes=('', '_enrichment')
    )

    # Log de resultados
    matched_rows = df_enriched[available_enrichment_columns[0]].notna().sum()
    total_rows = len(df_enriched)
    match_percentage = (matched_rows / total_rows * 100) if total_rows > 0 else 0

    logging.info(f"Enriquecimiento completado:")
    logging.info(f"  - Filas totales: {total_rows}")
    logging.info(f"  - Filas con datos de enriquecimiento: {matched_rows}")
    logging.info(f"  - Porcentaje de coincidencia: {match_percentage:.1f}%")
    logging.info(f"  - Columnas agregadas: {available_enrichment_columns}")

    return df_enriched


def enrich_dataframe(df_main: pd.DataFrame, df_enrichment: pd.DataFrame,
                    join_column: str, enrichment_columns: List[str]) -> pd.DataFrame:
    """
    Enriquece un DataFrame principal con datos de otro DataFrame.

    Args:
        df_main: DataFrame principal a enriquecer
        df_enrichment: DataFrame con datos de enriquecimiento
        join_column: Columna para hacer el JOIN
        enrichment_columns: Columnas a agregar del DataFrame de enriquecimiento

    Returns:
        DataFrame enriquecido
    """
    if df_main.empty or df_enrichment.empty:
        logging.warning("Uno de los DataFrames está vacío, omitiendo enriquecimiento")
        return df_main.copy()

    if join_column not in df_main.columns:
        logging.warning(f"Columna de JOIN '{join_column}' no encontrada en DataFrame principal")
        return df_main.copy()

    if join_column not in df_enrichment.columns:
        logging.warning(f"Columna de JOIN '{join_column}' no encontrada en DataFrame de enriquecimiento")
        return df_main.copy()

    # Verificar que las columnas de enriquecimiento existan
    valid_enrichment_columns = [col for col in enrichment_columns if col in df_enrichment.columns]
    if not valid_enrichment_columns:
        logging.warning("Ninguna columna de enriquecimiento válida encontrada")
        return df_main.copy()

    # Preparar DataFrame de enriquecimiento (solo columnas necesarias)
    enrichment_subset = df_enrichment[[join_column] + valid_enrichment_columns].copy()

    # Eliminar duplicados en el DataFrame de enriquecimiento
    enrichment_subset = enrichment_subset.drop_duplicates(subset=[join_column])

    # Realizar LEFT JOIN
    try:
        df_enriched = df_main.merge(
            enrichment_subset,
            on=join_column,
            how='left',
            suffixes=('', '_enrichment')
        )

        logging.info(f"Enriquecimiento completado: {len(valid_enrichment_columns)} columnas agregadas")
        return df_enriched

    except Exception as e:
        logging.error(f"Error durante el enriquecimiento: {e}")
        return df_main.copy()


# Funciones para limpiar datos comunes
def clean_date_strings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia strings de fechas con formatos problemáticos antes de cargar en DuckDB.

    Problemas detectados y solucionados:
    - Doble slash: "01/10//2024" -> "01/10/2024"
    - Slashes múltiples: "01///10/2024" -> "01/10/2024"
    - Espacios extra en fechas

    Args:
        df: DataFrame a limpiar

    Returns:
        DataFrame con fechas corregidas
    """
    import re

    df_clean = df.copy()

    # Detectar columnas que probablemente contienen fechas
    date_patterns = ['fecha', 'date', 'ingreso', 'actualizacion', 'creacion', 'modificacion']

    for col in df_clean.columns:
        # Verificar si es columna de tipo object (string)
        if df_clean[col].dtype == 'object':
            # Verificar si el nombre sugiere que es una fecha
            col_lower = col.lower()
            is_date_column = any(pattern in col_lower for pattern in date_patterns)

            if is_date_column:
                try:
                    # Limpiar dobles slashes y múltiples slashes consecutivos
                    df_clean[col] = df_clean[col].astype(str).apply(
                        lambda x: re.sub(r'/+', '/', x) if x and x != 'nan' else x
                    )

                    # Limpiar espacios extra
                    df_clean[col] = df_clean[col].str.strip()

                    logging.debug(f"Columna de fecha limpiada: '{col}'")
                except Exception as e:
                    logging.warning(f"No se pudo limpiar fechas en columna '{col}': {e}")

    return df_clean


def clean_nan_nat_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia valores NaN, NaT y strings problemáticos en un DataFrame.
    Convierte valores problemáticos a strings vacíos para una presentación limpia.

    Args:
        df: DataFrame a limpiar

    Returns:
        DataFrame limpio con celdas vacías para valores faltantes
    """
    df_clean = df.copy()

    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Reemplazar strings problemáticos con string vacío
            df_clean[col] = df_clean[col].replace({
                'nan': '',
                'NaN': '',
                'None': '',
                'null': '',
                'NaT': '',
                'nat': ''
            })

            # Limpiar espacios en blanco y convertir 'nan' strings a vacío
            df_clean[col] = df_clean[col].astype(str).str.strip()
            df_clean[col] = df_clean[col].replace({
                'nan': '',
                'None': '',
                'NaT': ''
            })

        # Para columnas numéricas, reemplazar NaN con string vacío
        elif df_clean[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), '')

        # Para columnas numéricas nullable de pandas (Int8, Int16, Int32, Int64, etc.)
        # SOLUCIÓN: Convertir a string PRIMERO, luego limpiar NaN
        elif pd.api.types.is_integer_dtype(df_clean[col]) or str(df_clean[col].dtype).startswith('Int'):
            # Convertir a string preservando valores y reemplazando NA
            df_clean[col] = df_clean[col].astype(str).replace({'<NA>': '', 'nan': '', 'None': ''})

        # Para columnas datetime, convertir NaT a string vacío
        elif pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), '')

        # Para cualquier tipo restante, convertir NaN/None a string vacío de forma segura
        else:
            try:
                df_clean[col] = df_clean[col].fillna('')
            except TypeError:
                # Si fillna('') falla (ej: tipos nullable especiales), usar where
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), '')

    # Paso final: asegurar que todos los None se conviertan a string vacío (con manejo de errores)
    try:
        df_clean = df_clean.fillna('')
    except TypeError:
        # Si hay columnas con tipos especiales que no aceptan '', iterar columna por columna
        for col in df_clean.columns:
            try:
                if df_clean[col].isna().any():
                    df_clean[col] = df_clean[col].fillna('')
            except TypeError:
                # Último recurso: convertir a string primero
                df_clean[col] = df_clean[col].astype(str).replace('nan', '').replace('None', '')

    return df_clean


def _has_priority_column(df: pd.DataFrame) -> bool:
    """
    Verifica si el DataFrame tiene una columna de prioridad disponible.

    Args:
        df: DataFrame a verificar

    Returns:
        True si hay columna de prioridad, False si no
    """
    possible_names = ['prioridad', 'PRIORIDAD', 'Prioridad', 'priority', 'PRIORITY', 'Priority']

    for col_name in possible_names:
        if col_name in df.columns:
            return True
    return False


# Factory para todas las utilidades de DataFrame
class DataFrameUtils:
    """Clase contenedora para todas las utilidades de DataFrame."""

    @staticmethod
    def create_nan_mask(series: pd.Series) -> pd.Series:
        return create_nan_mask(series)

    @staticmethod
    def _create_nan_mask(series: pd.Series) -> pd.Series:
        return _create_nan_mask(series)

    @staticmethod
    def _get_priority_info(df_full: pd.DataFrame, df_page: pd.DataFrame = None, start_idx: int = 0) -> Dict[str, Any]:
        return _get_priority_info(df_full, df_page, start_idx)

    @staticmethod
    def get_priority_info(df_full: pd.DataFrame, df_page: pd.DataFrame = None, start_idx: int = 0) -> Dict[str, Any]:
        return get_priority_info(df_full, df_page, start_idx)

    @staticmethod
    def has_priority_column(df: pd.DataFrame) -> bool:
        return has_priority_column(df)

    @staticmethod
    def _optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        return _optimize_dataframe_dtypes(df)

    @staticmethod
    def optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        return optimize_dataframe_dtypes(df)

    @staticmethod
    def _enrich_dataframe(df_main: pd.DataFrame, df_enrichment: pd.DataFrame,
                         join_column: str, enrichment_columns: List[str]) -> pd.DataFrame:
        return _enrich_dataframe(df_main, df_enrichment, join_column, enrichment_columns)

    @staticmethod
    def enrich_dataframe(df_main: pd.DataFrame, df_enrichment: pd.DataFrame,
                        join_column: str, enrichment_columns: List[str]) -> pd.DataFrame:
        return enrich_dataframe(df_main, df_enrichment, join_column, enrichment_columns)

    @staticmethod
    def clean_date_strings(df: pd.DataFrame) -> pd.DataFrame:
        return clean_date_strings(df)

    @staticmethod
    def clean_nan_nat_values(df: pd.DataFrame) -> pd.DataFrame:
        return clean_nan_nat_values(df)

    @staticmethod
    def _has_priority_column(df: pd.DataFrame) -> bool:
        return _has_priority_column(df)

    @staticmethod
    def find_first_existing_column(df, candidates):
        return find_first_existing_column(df, candidates)



# Instancia global para fácil acceso
dataframe_utils = DataFrameUtils()