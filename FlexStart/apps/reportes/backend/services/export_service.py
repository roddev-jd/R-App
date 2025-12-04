"""
ExportService - Centraliza la lógica de exportación de datos.

Este servicio maneja:
- Exportación a Excel con formato y estilos
- Exportación a CSV con streaming
- Aplicación de filtros antes de exportar
- Cancelación de exportaciones en curso
- Coloreado por prioridad en Excel

Extraído de main_logic.py para mejorar mantenibilidad y testabilidad.
"""

import asyncio
import logging
import tempfile
from typing import Dict, Any, Optional, List, Callable, Iterator, Union
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

# DuckDB es opcional - importación condicional para compatibilidad con equipos legacy
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    DUCKDB_AVAILABLE = False
    logging.warning("DuckDB no disponible en export_service - usando modo legacy")

# Imports de servicios de utilidades
from .dataframe_utils import dataframe_utils
from .csv_utils import csv_utils
from .progress_utils import progress_utils
from .storage_utils import storage_utils


class ExportService:
    """Servicio centralizado para exportación de datos."""

    def __init__(self,
                 config_data: Dict[str, Any],
                 io_executor: ThreadPoolExecutor):
        """
        Inicializa el servicio de exportación.

        Args:
            config_data: Configuración global de la aplicación
            io_executor: ThreadPoolExecutor para operaciones I/O
        """
        self.config_data = config_data
        self.io_executor = io_executor

        # Estado de cancelación de exportaciones
        self.export_cancellation_requested = False

    def request_export_cancellation(self):
        """Solicita la cancelación de la exportación en curso."""
        self.export_cancellation_requested = True
        logging.info("Cancelación de exportación solicitada")

    def reset_export_cancellation(self):
        """Resetea el estado de cancelación de exportación."""
        self.export_cancellation_requested = False

    def check_export_cancellation(self):
        """Verifica si se ha solicitado cancelación y lanza excepción si es así."""
        if self.export_cancellation_requested:
            logging.info("Exportación cancelada por el usuario")
            raise InterruptedError("Exportación cancelada por el usuario")

    async def get_excel_export_safe(self,
                                  df_original: pd.DataFrame,
                                  duckdb_conn: Optional[Any],
                                  current_blob_display_name: str,
                                  filter_service,  # FilterService instance
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
                                  custom_text_filters: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Versión asíncrona para exportar datos filtrados a Excel.

        Args:
            df_original: DataFrame con datos originales
            duckdb_conn: Conexión a DuckDB
            current_blob_display_name: Nombre del blob actual
            filter_service: Instancia del FilterService para aplicar filtros
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
            custom_text_filters: Filtros personalizados de texto

        Returns:
            Ruta del archivo Excel generado
        """
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.io_executor,
            self._get_excel_export_sync,
            df_original,
            duckdb_conn,
            current_blob_display_name,
            filter_service,
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
            custom_text_filters
        )

    async def get_csv_export_safe(self,
                                df_original: pd.DataFrame,
                                duckdb_conn: Optional[Any],
                                current_blob_display_name: str,
                                filter_service,  # FilterService instance
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
                                custom_text_filters: Optional[Dict[str, List[str]]] = None) -> Callable[[], Iterator[bytes]]:
        """
        Versión asíncrona para exportar datos filtrados a CSV.

        Args:
            [Mismos argumentos que get_excel_export_safe]

        Returns:
            Función generadora para streaming de CSV
        """
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.io_executor,
            self._get_csv_export_sync,
            df_original,
            duckdb_conn,
            current_blob_display_name,
            filter_service,
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
            custom_text_filters
        )

    def _get_excel_export_sync(self,
                             df_original: pd.DataFrame,
                             duckdb_conn: Optional[Any],
                             current_blob_display_name: str,
                             filter_service,
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
                             custom_text_filters: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Método síncrono para exportar a Excel.

        NOTA: Esta función mantiene la lógica completa de main_logic.get_excel_export()
        pero operando sobre DataFrames pasados como parámetros en lugar de estado global.
        En las siguientes fases se refactorizará más para eliminar dependencias del estado global.
        """
        # Por ahora, importamos y llamamos la función original para mantener
        # compatibilidad completa durante la transición gradual
        import main_logic

        # Sincronizar estado global temporalmente para compatibilidad
        main_logic.df_original = df_original
        main_logic.duckdb_conn = duckdb_conn
        main_logic.current_blob_display_name = current_blob_display_name

        # Sincronizar estado de cancelación
        main_logic.export_cancellation_requested = self.export_cancellation_requested

        try:
            # Llamar función original
            result = main_logic.get_excel_export(
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
                custom_text_filters=custom_text_filters
            )

            # Sincronizar de vuelta el estado de cancelación
            self.export_cancellation_requested = main_logic.export_cancellation_requested

            return result

        except InterruptedError:
            # Re-lanzar la excepción de cancelación
            self.export_cancellation_requested = main_logic.export_cancellation_requested
            raise

    def _get_csv_export_sync(self,
                           df_original: pd.DataFrame,
                           duckdb_conn: Optional[Any],
                           current_blob_display_name: str,
                           filter_service,
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
                           custom_text_filters: Optional[Dict[str, List[str]]] = None) -> Callable[[], Iterator[bytes]]:
        """
        Método síncrono para exportar a CSV.

        Similar a _get_excel_export_sync, mantiene compatibilidad durante la transición.
        """
        # Por ahora, importamos y llamamos la función original
        import main_logic

        # Sincronizar estado global temporalmente
        main_logic.df_original = df_original
        main_logic.duckdb_conn = duckdb_conn
        main_logic.current_blob_display_name = current_blob_display_name
        main_logic.export_cancellation_requested = self.export_cancellation_requested

        try:
            # Llamar función original
            result = main_logic.get_csv_export(
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
                custom_text_filters=custom_text_filters
            )

            # Sincronizar de vuelta el estado de cancelación
            self.export_cancellation_requested = main_logic.export_cancellation_requested

            return result

        except InterruptedError:
            # Re-lanzar la excepción de cancelación
            self.export_cancellation_requested = main_logic.export_cancellation_requested
            raise


def create_export_service(config_data: Dict[str, Any],
                         io_executor: ThreadPoolExecutor) -> ExportService:
    """
    Factory function para crear una instancia de ExportService.

    Args:
        config_data: Configuración global de la aplicación
        io_executor: ThreadPoolExecutor para operaciones I/O

    Returns:
        Instancia configurada de ExportService
    """
    return ExportService(config_data, io_executor)