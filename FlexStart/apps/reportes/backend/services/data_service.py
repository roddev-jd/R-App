"""
DataService - Centraliza la lógica de carga y gestión de datos.

Este servicio maneja:
- Carga de datos desde múltiples fuentes (Azure, SharePoint, FTP, S3, local)
- Procesamiento inicial de DataFrames
- Validación de integridad de datos
- Gestión de metadatos de las bases de datos
- Interfaz con el sistema de caché persistente

Extraído de main_logic.py para mejorar mantenibilidad y testabilidad.

FASE 2.1: Soporte para operaciones I/O asíncronas verdaderas
- Usa main_logic_async.load_blob_data_async() cuando está disponible
- Fallback automático a versión síncrona si async no disponible
"""

import asyncio
import configparser
import io
import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

# DuckDB es opcional - importación condicional para compatibilidad con equipos legacy
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    DUCKDB_AVAILABLE = False
    logging.warning("DuckDB no disponible en data_service - funcionalidad limitada")

# Imports del sistema existente
from services.cache_service import persistent_cache

# Imports de servicios de utilidades
from .dataframe_utils import dataframe_utils
from .csv_utils import csv_utils
from .progress_utils import progress_utils
from .storage_utils import storage_utils


class DataService:
    """Servicio centralizado para carga y gestión de datos."""

    def __init__(self,
                 config_data: Dict[str, Any],
                 io_executor: ThreadPoolExecutor):
        """
        Inicializa el servicio de datos.

        Args:
            config_data: Configuración global de la aplicación
            io_executor: ThreadPoolExecutor para operaciones I/O
        """
        self.config_data = config_data
        self.io_executor = io_executor

    def get_blob_options_for_api(self) -> Dict[str, Any]:
        """
        Prepara las opciones de blobs agrupadas por país para la API.
        Devuelve un diccionario con una lista de países y un mapa
        de país a sus fuentes de datos.
        """
        sources_by_country: Dict[str, List[Dict[str, str]]] = {}

        if "blob_options" in self.config_data:
            for dn_upper, blob_attrs in self.config_data["blob_options"].items():
                # Obtener el país, con 'General' como valor por defecto si no está definido
                country = blob_attrs.get("country", "General")

                # Inicializar la lista para el país si es la primera vez que se ve
                if country not in sources_by_country:
                    sources_by_country[country] = []

                # Añadir la información del blob a la lista del país correspondiente
                # Usamos las claves correctas de nuestro nuevo formato
                sources_by_country[country].append({
                    "display_name": blob_attrs.get("display_name", dn_upper),
                    "filename": blob_attrs.get("value"), # 'value' ahora contiene el nombre del archivo
                    "description": blob_attrs.get("description", "")
                })

        # Ordenar alfabéticamente las fuentes de datos dentro de cada país
        for country in sources_by_country:
            sources_by_country[country] = sorted(sources_by_country[country], key=lambda x: x["display_name"])

        # Obtener una lista ordenada de los países.
        countries_list = sorted(sources_by_country.keys())

        return {
            "countries": countries_list,
            "sources_by_country": sources_by_country,
            "default_blob_filename": self.config_data.get("default_blob_filename")
        }

    def get_config_settings_for_api(self, blob_display_name_from_frontend: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración de filtros para un blob específico.

        Args:
            blob_display_name_from_frontend: Nombre del blob desde el frontend

        Returns:
            Configuración de filtros o None si no se encuentra
        """
        logging.info(f"--- get_config_settings_for_api ---")
        logging.info(f"  Solicitud para blob_display_name_from_frontend: '{blob_display_name_from_frontend}'")

        # blob_display_name_from_frontend es el original_display_name (case preservado de config.ini)
        # Las claves en config_data["filter_configs"] son la versión .upper() del original_display_name
        key_to_find_in_filter_configs = blob_display_name_from_frontend.upper()
        logging.info(f"  Clave normalizada para búsqueda en config_data['filter_configs'] (key_to_find_in_filter_configs): '{key_to_find_in_filter_configs}'")
        logging.info(f"  Claves disponibles en config_data['filter_configs']: {list(self.config_data.get('filter_configs', {}).keys())}")

        # Buscar directamente con la clave UPPER en filter_configs
        # Esta es la forma principal y esperada de encontrar la config
        if key_to_find_in_filter_configs in self.config_data.get("filter_configs", {}):
            retrieved_config = self.config_data["filter_configs"].get(key_to_find_in_filter_configs)
            logging.info(f"  Configuración ENCONTRADA para '{key_to_find_in_filter_configs}': {retrieved_config}")
            return retrieved_config
        else:
            # Fallback si la clave UPPER directa no se encontró (menos probable si load_app_config es correcto)
            logging.warning(f"  Configuración NO encontrada directamente para '{key_to_find_in_filter_configs}' usando '{blob_display_name_from_frontend}'.upper(). Intentando fallback por original_display_name en blob_options...")
            for key_upper_option_iter, attrs_iter_option in self.config_data.get("blob_options", {}).items():
                # attrs_iter_option["original_display_name"] tiene el case original de config.ini
                # key_upper_option_iter es attrs_iter_option["original_display_name"].upper()
                if attrs_iter_option.get("original_display_name") == blob_display_name_from_frontend:
                    logging.info(f"    Fallback: original_display_name '{attrs_iter_option.get('original_display_name')}' coincide con '{blob_display_name_from_frontend}'.")
                    # Usar la clave UPPER del blob_option (key_upper_option_iter) para buscar en filter_configs
                    retrieved_config_fallback = self.config_data["filter_configs"].get(key_upper_option_iter)
                    logging.info(f"    Configuración ENCONTRADA vía fallback para '{key_upper_option_iter}': {retrieved_config_fallback}")
                    return retrieved_config_fallback

            logging.error(f"  Configuración NO ENCONTRADA para '{blob_display_name_from_frontend}' (buscando como '{key_to_find_in_filter_configs}') después de todos los intentos.")
            return None

    async def load_blob_data_safe(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Versión asíncrona de load_blob_data - thread-safe y optimizada.

        Args:
            param_from_frontend_url: Identificador de la fuente de datos
            selected_columns: Lista opcional de columnas específicas para cargar (optimización)

        Returns:
            Diccionario con información de la carga realizada
        """
        # Crear tarea para ejecutar la carga en background con mejor control
        load_task = asyncio.create_task(
            self._load_blob_data_async(param_from_frontend_url, selected_columns)
        )

        # Esperamos el resultado de la tarea
        return await load_task

    async def _load_blob_data_async(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Versión completamente asíncrona de load_blob_data (FASE 2.1).

        Usa operaciones I/O verdaderamente asíncronas sin bloquear el event loop.
        Si las dependencias async no están disponibles, hace fallback a sync.
        """
        # Verificar si el modo async está disponible
        try:
            from main_logic_async import load_blob_data_async, ASYNC_STORAGE_AVAILABLE

            if ASYNC_STORAGE_AVAILABLE:
                logging.info(f"⚡ [ASYNC] Usando load_blob_data_async para '{param_from_frontend_url}'")

                # Llamar a la versión async verdadera (sin run_in_executor)
                result = await load_blob_data_async(
                    param_from_frontend_url=param_from_frontend_url,
                    selected_columns_from_api=selected_columns,
                    config_data=self.config_data,
                    progress_tracker=None  # Se crea internamente
                )

                return result
            else:
                logging.warning(f"⚠️ Dependencias async no disponibles - usando fallback síncrono")
                raise ImportError("Async storage not available")

        except ImportError as e:
            # Fallback a versión síncrona si async no está disponible
            logging.info(f"Fallback a modo síncrono para '{param_from_frontend_url}': {e}")
            loop = asyncio.get_running_loop()

            return await loop.run_in_executor(
                self.io_executor,
                self._load_blob_data_sync,
                param_from_frontend_url,
                selected_columns
            )

    async def refresh_blob_data_safe(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Versión asíncrona de refresh_blob_data - thread-safe y optimizada.

        Args:
            param_from_frontend_url: Identificador de la fuente de datos
            selected_columns: Lista opcional de columnas específicas para cargar (optimización)

        Returns:
            Diccionario con información del refresh realizado
        """
        # Crear tarea para ejecutar el refresh en background con mejor control
        refresh_task = asyncio.create_task(
            self._refresh_blob_data_async(param_from_frontend_url, selected_columns)
        )

        # Esperamos el resultado de la tarea
        return await refresh_task

    async def _refresh_blob_data_async(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Versión completamente asíncrona de refresh_blob_data."""
        loop = asyncio.get_running_loop()

        # Ejecutar operaciones I/O bound en pool dedicado para mejor rendimiento
        return await loop.run_in_executor(
            self.io_executor,
            self._refresh_blob_data_sync,
            param_from_frontend_url,
            selected_columns
        )

    def _load_blob_data_sync(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Método síncrono para cargar datos de blob.

        Args:
            param_from_frontend_url: Identificador de la fuente de datos
            selected_columns: Lista opcional de columnas específicas para cargar

        NOTA: Esta función mantiene la lógica completa de main_logic.load_blob_data()
        pero sin depender del estado global. En las siguientes fases se refactorizará
        más para eliminar dependencias del estado global de main_logic.
        """
        # Por ahora, importamos y llamamos la función original para mantener
        # compatibilidad completa durante la transición
        import main_logic
        return main_logic.load_blob_data(param_from_frontend_url, selected_columns_from_api=selected_columns)

    def _refresh_blob_data_sync(self, param_from_frontend_url: str, selected_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Método síncrono para refrescar datos de blob.

        Args:
            param_from_frontend_url: Identificador de la fuente de datos
            selected_columns: Lista opcional de columnas específicas para cargar

        NOTA: Similar a _load_blob_data_sync, mantiene compatibilidad durante
        la transición gradual.
        """
        # Por ahora, importamos y llamamos la función original
        import main_logic
        return main_logic.refresh_blob_data(param_from_frontend_url, selected_columns_from_api=selected_columns)


def _create_config_parser():
    """Crea y configura el parser de configuración."""
    parser = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    parser.optionxform = str
    return parser


def _parse_filter_section(parser, section_name):
    """Parsea una sección de filtros específica."""
    f_config = {}

    # Columnas básicas
    filter_cols_str = parser.get(section_name, 'filtercolumns', fallback="")
    f_config['filter_cols'] = [col.strip() for col in filter_cols_str.split(',') if col.strip()]

    hide_cols_str = parser.get(section_name, 'hidecolumns', fallback="")
    f_config['hide_cols'] = [col.strip() for col in hide_cols_str.split(',') if col.strip()]

    not_empty_cols_str = parser.get(section_name, 'notemptycolumns', fallback="")
    f_config['not_empty_cols'] = [col.strip() for col in not_empty_cols_str.split(',') if col.strip()]

    # Selección de columnas (Fase 3 - OPTIMIZACION_RENDIMIENTO.md)
    select_cols_str = parser.get(section_name, 'selectcolumns', fallback="")
    f_config['selectcolumns'] = select_cols_str.strip() if select_cols_str else ""

    # Columnas disponibles para el selector (Selector de Columnas - UI)
    available_cols_str = parser.get(section_name, 'availablecolumns', fallback="")
    f_config['availablecolumns'] = [col.strip() for col in available_cols_str.split(',') if col.strip()] if available_cols_str else []

    # Columnas esenciales (preseleccionadas en el selector)
    essential_cols_str = parser.get(section_name, 'essentialcolumns', fallback="")
    f_config['essentialcolumns'] = [col.strip() for col in essential_cols_str.split(',') if col.strip()] if essential_cols_str else []

    # Valores a ocultar
    values_to_hide = {}
    exclude_rules = {}

    for key_opt in parser.options(section_name):
        if key_opt.lower().startswith('hidevalues_'):
            col_name = key_opt.split('_', 1)[1] if '_' in key_opt else ''
            if col_name:
                values_str = parser.get(section_name, key_opt, fallback='')
                vals = [v.strip() if v.strip() != '""' else '' for v in values_str.split(',')
                       if v.strip() or v.strip() == '""'] if values_str else []
                values_to_hide[col_name.lower()] = vals

        elif key_opt.lower().startswith('excluderowif_'):
            col_name = key_opt.split('_', 1)[1] if '_' in key_opt else ''
            if col_name:
                values_str = parser.get(section_name, key_opt, fallback='')
                exclude_vals = [v.strip() for v in values_str.split(',') if v.strip()]
                if exclude_vals:
                    exclude_rules[col_name.lower()] = exclude_vals

    f_config['hide_values'] = values_to_hide
    f_config['exclude_rows'] = exclude_rules

    # NUEVO: Configuración de visibilidad de filtros especiales
    f_config['show_ticket_filter'] = parser.getboolean(
        section_name, 'show_ticket_filter', fallback=True
    )
    f_config['show_lineamiento_filter'] = parser.getboolean(
        section_name, 'show_lineamiento_filter', fallback=True
    )
    f_config['show_sku_hijo_filter'] = parser.getboolean(
        section_name, 'show_sku_hijo_filter', fallback=True
    )
    f_config['show_sku_padre_filter'] = parser.getboolean(
        section_name, 'show_sku_padre_filter', fallback=True
    )

    # NUEVO: Filtros personalizados de texto (búsqueda por coincidencias)
    custom_text_filters_str = parser.get(section_name, 'custom_text_filters', fallback='')
    if custom_text_filters_str:
        # Formato: "columna1, columna2, columna3"
        f_config['custom_text_filters'] = [
            col.strip() for col in custom_text_filters_str.split(',') if col.strip()
        ]
    else:
        f_config['custom_text_filters'] = []

    return f_config


def _build_blob_config(parser, key, display_name):
    """Construye configuración de un blob específico."""
    return {
        "key": key,
        "value": parser.get('Blobs', key),
        "filename": parser.get('Blobs', key),
        "source_url": parser.get('Blobs', key),
        "display_name": display_name,
        "source_type": parser.get('Blobs', f"{key}_source_type", fallback="azure"),
        "country": parser.get('Blobs', f"{key}_country", fallback="General"),
        "description": parser.get('Blobs', f"{key}_description", fallback=""),
        "filter_config_ref": parser.get('Blobs', f"{key}_filter_config_ref", fallback=key).upper(),
        "local_path": parser.get('Blobs', f"{key}_local_path", fallback=None),
        "use_local": parser.getboolean('Blobs', f"{key}_use_local", fallback=False),
        "prefilter_nom_estado": parser.get('Blobs', f"{key}_prefilter_nom_estado", fallback=None),
        "enrichment_source": parser.get('Blobs', f"{key}_enrichment_source", fallback=None),
        "enrichment_join_column": parser.get('Blobs', f"{key}_enrichment_join_column", fallback=None),
        "enrichment_columns": parser.get('Blobs', f"{key}_enrichment_columns", fallback=None),
        "sheet_name": parser.get('Blobs', f"{key}_sheet_name", fallback=None),
        "values_only": parser.getboolean('Blobs', f"{key}_values_only", fallback=False),
        "file_pattern": parser.get('Blobs', f"{key}_file_pattern", fallback="*.csv")
    }


def get_dynamic_config_path(script_dir: str) -> str:
    """Determina la ruta del config.ini a usar."""
    import os
    import logging

    local_path = os.path.join(script_dir, 'config.ini')
    logging.info(f"Usando config.ini desde: {local_path}")
    return local_path


def get_blob_config(display_name: str, config_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Obtiene la configuración de un blob por su display_name."""
    key_for_blob_options_lookup = display_name.upper()
    return config_data.get("blob_options", {}).get(key_for_blob_options_lookup)


def create_data_service(config_data: Dict[str, Any],
                       io_executor: ThreadPoolExecutor) -> DataService:
    """
    Factory function para crear una instancia de DataService.

    Args:
        config_data: Configuración global de la aplicación
        io_executor: ThreadPoolExecutor para operaciones I/O

    Returns:
        Instancia configurada de DataService
    """
    return DataService(config_data, io_executor)