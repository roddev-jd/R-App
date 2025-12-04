"""
FilterService - Centraliza la lógica de filtrado de datos.

Este servicio maneja:
- Aplicación de filtros por columnas y valores
- Filtros por SKU Hijo/Padre (archivo y manual)
- Filtros por tickets
- Paginación de resultados
- Extensión de búsqueda de SKUs

Extraído de main_logic.py para mejorar mantenibilidad y testabilidad.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

# DuckDB es opcional - importación condicional para compatibilidad con equipos legacy
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    DUCKDB_AVAILABLE = False
    logging.warning("DuckDB no disponible en filter_service - usando modo legacy")

# Imports de servicios de utilidades
from .dataframe_utils import dataframe_utils
from .csv_utils import csv_utils
from .progress_utils import progress_utils
from .storage_utils import storage_utils


class FilterService:
    """Servicio centralizado para filtrado de datos."""

    def __init__(self,
                 config_data: Dict[str, Any],
                 io_executor: ThreadPoolExecutor):
        """
        Inicializa el servicio de filtros.

        Args:
            config_data: Configuración global de la aplicación
            io_executor: ThreadPoolExecutor para operaciones I/O
        """
        self.config_data = config_data
        self.io_executor = io_executor

        # Estado de filtros de archivos (análogo a las variables globales)
        self.sku_hijo_filter_list: Optional[List[str]] = None
        self.sku_padre_filter_list: Optional[List[str]] = None
        self.ticket_filter_list: Optional[List[str]] = None

    def clear_filter_states(self,
                           use_sku_hijo_file: bool,
                           sku_hijo_manual_list: Optional[List[str]],
                           use_sku_padre_file: bool,
                           sku_padre_manual_list: Optional[List[str]],
                           use_ticket_file: bool,
                           ticket_manual_list: Optional[List[str]]):
        """Limpia estados de filtros según la configuración."""
        # Limpiar solo si no se está usando el filtro de archivo correspondiente
        if not use_sku_hijo_file and not sku_hijo_manual_list:
            self.sku_hijo_filter_list = None
            logging.info("Estado 'sku_hijo_filter_list' limpiado")

        if not use_sku_padre_file and not sku_padre_manual_list:
            self.sku_padre_filter_list = None
            logging.info("Estado 'sku_padre_filter_list' limpiado")

        if not use_ticket_file and not ticket_manual_list:
            self.ticket_filter_list = None
            logging.info("Estado 'ticket_filter_list' limpiado")

    def get_sku_column_candidates(self) -> tuple[List[str], List[str]]:
        """Obtiene listas de columnas candidatas para SKU hijo y padre."""
        sku_hijo_candidates = [
            'ean_hijo', 'EAN_HIJO', 'Ean_Hijo',
            'sku_hijo_largo', 'SKU_HIJO_LARGO', 'Sku_Hijo_Largo',
            'hijo_corto', 'HIJO_CORTO', 'Hijo_Corto'
        ]

        sku_padre_candidates = [
            'sku_padre_largo', 'SKU_PADRE_LARGO', 'Sku_Padre_Largo',
            'padre_corto', 'PADRE_CORTO', 'Padre_Corto'
        ]

        return sku_hijo_candidates, sku_padre_candidates

    def find_first_existing_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encuentra la primera columna que existe en el DataFrame."""
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        return None

    def log_filter_diagnostics(self):
        """Log diagnóstico del estado de filtros."""
        logging.info("--- DEBUG FilterService ---")
        logging.info(f"sku_hijo_filter_list: {self.sku_hijo_filter_list is not None}")
        logging.info(f"sku_padre_filter_list: {self.sku_padre_filter_list is not None}")
        logging.info(f"ticket_filter_list: {self.ticket_filter_list is not None}")
        logging.info("-----------------------------")

    def get_empty_filter_response(self, columns: List[str] = None) -> Dict[str, Any]:
        """Genera respuesta estándar para filtros sin datos."""
        return {
            "row_count_filtered": 0,
            "data": [],
            "columns_in_data": columns or [],
            "filter_options": {},
            "page": 1,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False,
            "skus_no_encontrados_hijo": [],
            "skus_no_encontrados_padre": []
        }

    async def apply_all_filters_safe(self,
                                   df_original: pd.DataFrame,
                                   duckdb_conn: Optional[Any],
                                   current_blob_display_name: str,
                                   value_filters: Dict[str, List[str]],
                                   use_sku_hijo_file: bool,
                                   extend_sku_hijo: bool,
                                   sku_hijo_manual_list: Optional[List[str]],
                                   use_sku_padre_file: bool,
                                   sku_padre_manual_list: Optional[List[str]],
                                   use_ticket_file: bool,
                                   ticket_manual_list: Optional[List[str]],
                                   lineamiento_manual_list: Optional[List[str]],
                                   selected_display_columns: Optional[List[str]] = None,
                                   enable_priority_coloring: bool = False,
                                   page: int = 1,
                                   page_size: int = 100,
                                   custom_text_filters: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Versión asíncrona de apply_all_filters - thread-safe y optimizada.

        Args:
            df_original: DataFrame con datos originales
            duckdb_conn: Conexión a DuckDB
            current_blob_display_name: Nombre del blob actual
            value_filters: Filtros por columnas y valores
            use_sku_hijo_file: Usar archivo SKU hijo
            extend_sku_hijo: Extender búsqueda SKU hijo
            sku_hijo_manual_list: Lista manual de SKUs hijo
            use_sku_padre_file: Usar archivo SKU padre
            sku_padre_manual_list: Lista manual de SKUs padre
            use_ticket_file: Usar archivo de tickets
            ticket_manual_list: Lista manual de tickets
            lineamiento_manual_list: Lista manual de lineamientos
            selected_display_columns: Columnas a mostrar
            enable_priority_coloring: Habilitar coloreado por prioridad
            page: Página actual
            page_size: Tamaño de página

        Returns:
            Diccionario con datos filtrados y metadatos
        """
        loop = asyncio.get_running_loop()

        # Ejecutar filtrado en pool dedicado para mejor rendimiento
        return await loop.run_in_executor(
            self.io_executor,
            self._apply_all_filters_sync,
            df_original,
            duckdb_conn,
            current_blob_display_name,
            value_filters,
            use_sku_hijo_file,
            extend_sku_hijo,
            sku_hijo_manual_list,
            use_sku_padre_file,
            sku_padre_manual_list,
            use_ticket_file,
            ticket_manual_list,
            lineamiento_manual_list,
            selected_display_columns,
            enable_priority_coloring,
            page,
            page_size,
            custom_text_filters
        )

    def _apply_all_filters_sync(self,
                               df_original: pd.DataFrame,
                               duckdb_conn: Optional[Any],
                               current_blob_display_name: str,
                               value_filters: Dict[str, List[str]],
                               use_sku_hijo_file: bool,
                               extend_sku_hijo: bool,
                               sku_hijo_manual_list: Optional[List[str]],
                               use_sku_padre_file: bool,
                               sku_padre_manual_list: Optional[List[str]],
                               use_ticket_file: bool,
                               ticket_manual_list: Optional[List[str]],
                               lineamiento_manual_list: Optional[List[str]],
                               selected_display_columns: Optional[List[str]] = None,
                               enable_priority_coloring: bool = False,
                               page: int = 1,
                               page_size: int = 100,
                               custom_text_filters: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Método síncrono para aplicar filtros.

        NOTA: Esta función mantiene la lógica completa de main_logic.apply_all_filters()
        pero operando sobre DataFrames pasados como parámetros en lugar de estado global.
        En las siguientes fases se refactorizará más para eliminar dependencias del estado global.
        """
        # Por ahora, importamos y llamamos la función original para mantener
        # compatibilidad completa durante la transición gradual
        import main_logic

        # Sincronizar nuestro estado con el estado global temporalmente
        main_logic.sku_hijo_filter_list = self.sku_hijo_filter_list
        main_logic.sku_padre_filter_list = self.sku_padre_filter_list
        main_logic.ticket_filter_list = self.ticket_filter_list

        # Asegurar que df_original está en estado global para compatibilidad
        main_logic.df_original = df_original
        main_logic.duckdb_conn = duckdb_conn
        main_logic.current_blob_display_name = current_blob_display_name

        # Llamar función original
        result = main_logic.apply_all_filters(
            value_filters=value_filters,
            use_sku_hijo_file=use_sku_hijo_file,
            extend_sku_hijo=extend_sku_hijo,
            sku_hijo_manual_list=sku_hijo_manual_list,
            use_sku_padre_file=use_sku_padre_file,
            sku_padre_manual_list=sku_padre_manual_list,
            use_ticket_file=use_ticket_file,
            ticket_manual_list=ticket_manual_list,
            lineamiento_manual_list=lineamiento_manual_list,
            selected_display_columns=selected_display_columns,
            enable_priority_coloring=enable_priority_coloring,
            page=page,
            page_size=page_size,
            custom_text_filters=custom_text_filters
        )

        # Sincronizar de vuelta nuestro estado
        self.sku_hijo_filter_list = main_logic.sku_hijo_filter_list
        self.sku_padre_filter_list = main_logic.sku_padre_filter_list
        self.ticket_filter_list = main_logic.ticket_filter_list

        return result

    # Métodos para gestión de filtros de archivos (análogos a main_logic)
    def set_sku_hijo_filter_list(self, sku_list: Optional[List[str]]):
        """Establece la lista de filtros SKU hijo."""
        self.sku_hijo_filter_list = sku_list
        logging.info(f"SKU hijo filter list actualizada: {len(sku_list) if sku_list else 0} elementos")

    def set_sku_padre_filter_list(self, sku_list: Optional[List[str]]):
        """Establece la lista de filtros SKU padre."""
        self.sku_padre_filter_list = sku_list
        logging.info(f"SKU padre filter list actualizada: {len(sku_list) if sku_list else 0} elementos")

    def set_ticket_filter_list(self, ticket_list: Optional[List[str]]):
        """Establece la lista de filtros de tickets."""
        self.ticket_filter_list = ticket_list
        logging.info(f"Ticket filter list actualizada: {len(ticket_list) if ticket_list else 0} elementos")

    def clear_all_filters(self):
        """Limpia todos los filtros de archivos."""
        self.sku_hijo_filter_list = None
        self.sku_padre_filter_list = None
        self.ticket_filter_list = None
        logging.info("Todos los filtros de archivos limpiados")


def _get_empty_filter_response(columns: List[str] = None) -> Dict[str, Any]:
    """Genera respuesta estándar para filtros sin datos."""
    return {
        "row_count_filtered": 0,
        "data": [],
        "columns_in_data": columns or [],
        "skus_no_encontrados_hijo": [],
        "skus_no_encontrados_padre": []
    }


def _get_sku_column_candidates(source_type: str = None, display_name: str = None) -> tuple[List[str], List[str]]:
    """Determina columnas SKU candidatas según el tipo de fuente."""
    from typing import Tuple

    display_name_upper = display_name.upper() if display_name else ""

    # Configuraciones por defecto
    sku_hijo_candidates = ['ean_hijo', 'sku_hijo', 'sku_hijo_largo']
    sku_padre_candidates = ['ean_padre', 'sku_padre', 'sku_padre_largo']

    # Configuraciones específicas
    if source_type == 'sharepoint':
        if display_name_upper in ["DATA SCRIPT PERU", "INFO MARCA PROPIA PERU"]:
            sku_padre_candidates = ['ean_padre', 'sku_padre', 'sku_padre_largo']
        elif display_name_upper == "PERU ESTUDIO CHILE":
            sku_hijo_candidates = ['sku_hijo']
            sku_padre_candidates = ['sku_padre']
        else:
            sku_padre_candidates = ['sku_padre_largo', 'sku_padre', 'ean_padre']
    elif display_name_upper == "INFO CARGAS MARCA PROPIA PERU":
        sku_hijo_candidates = ['sku_hijo', 'ean_hijo', 'sku_hijo_largo']
        sku_padre_candidates = ['sku_padre', 'ean_padre', 'sku_padre_largo']
    elif source_type == 'local_xlsx':
        sku_hijo_candidates = ['ean_hijo', 'sku_hijo', 'sku_hijo_largo']

    return sku_hijo_candidates, sku_padre_candidates


def _extract_filter_options(df: 'pd.DataFrame', blob_config: Dict[str, Any], filter_configs: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extrae opciones de filtro de un DataFrame basándose en la configuración del blob."""
    import logging

    filter_options = {}
    MAX_FILTER_OPTIONS = 5000

    # Obtener configuración de filtros
    key_for_blob_options_lookup = blob_config.get("display_name", "").upper()
    current_config_blob_settings = filter_configs.get(key_for_blob_options_lookup)

    if not current_config_blob_settings:
        logging.warning(f"No se encontró configuración de filtros para {key_for_blob_options_lookup}")
        return filter_options

    cfg_filter_cols_list = [col.lower().strip() for col in current_config_blob_settings.get('filter_cols', [])]
    cfg_hide_values_dict = {k.lower(): v for k, v in current_config_blob_settings.get('hide_values', {}).items()}

    for col_name_cfg in cfg_filter_cols_list:
        if col_name_cfg in df.columns:
            unique_vals = df[col_name_cfg].dropna().astype(str).unique()
            if len(unique_vals) > MAX_FILTER_OPTIONS:
                logging.warning(f"Columna '{col_name_cfg}' excede el límite de opciones de filtro.")
                continue
            values_to_hide = set(cfg_hide_values_dict.get(col_name_cfg, []))
            filter_options[col_name_cfg] = sorted([val for val in unique_vals if val not in values_to_hide])

    return filter_options


def create_filter_service(config_data: Dict[str, Any],
                         io_executor: ThreadPoolExecutor) -> FilterService:
    """
    Factory function para crear una instancia de FilterService.

    Args:
        config_data: Configuración global de la aplicación
        io_executor: ThreadPoolExecutor para operaciones I/O

    Returns:
        Instancia configurada de FilterService
    """
    return FilterService(config_data, io_executor)