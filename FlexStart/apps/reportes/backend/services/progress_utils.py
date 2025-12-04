"""
Progress Utils - Utilidades para tracking de progreso y descargas.

Este módulo contiene funciones auxiliares para:
- Emisión de mensajes de progreso via SSE
- Cálculo de velocidades de descarga
- Tracking de operaciones largas
- Formateo de tiempos y tamaños

Extraído de main_logic.py para mejorar reutilización y mantenibilidad.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

# Import del sistema de SSE existente
try:
    from core.sse_channel import (
        search_progress_queue,
        data_load_progress_queue,
        emit_data_load_progress,
        emit_data_load_progress_sync  # Versión síncrona para ThreadPoolExecutor
    )
except ImportError:
    search_progress_queue = None
    data_load_progress_queue = None
    emit_data_load_progress = None
    emit_data_load_progress_sync = None
    logging.warning("SSE channel no disponible - funcionalidad de progreso limitada")


def emit_progress_message(message_data: dict):
    """
    Emite un mensaje de progreso a través del canal SSE de forma asíncrona.

    Args:
        message_data: Diccionario con datos del mensaje a enviar
    """
    if search_progress_queue is None:
        logging.debug("SSE no disponible, omitiendo mensaje de progreso")
        return

    try:
        # Obtener el loop de eventos actual
        loop = asyncio.get_running_loop()

        # Programar la emisión del mensaje
        if loop.is_running():
            asyncio.create_task(search_progress_queue.put(message_data))
        else:
            loop.run_until_complete(search_progress_queue.put(message_data))

    except Exception as e:
        logging.debug(f"Error al emitir mensaje de progreso: {e}")


def calculate_download_speed(bytes_downloaded: int, elapsed_time: float) -> float:
    """
    Calcula la velocidad de descarga en bytes por segundo.

    Args:
        bytes_downloaded: Número de bytes descargados
        elapsed_time: Tiempo transcurrido en segundos

    Returns:
        Velocidad en bytes por segundo
    """
    if elapsed_time <= 0:
        return 0.0
    return bytes_downloaded / elapsed_time


def format_file_size(size_bytes: int) -> str:
    """
    Formatea un tamaño en bytes a una representación legible.

    Args:
        size_bytes: Tamaño en bytes

    Returns:
        String formateado (ej: "1.5 MB", "234 KB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_bytes = float(size_bytes)
    i = 0

    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def format_speed(speed_bps: float) -> str:
    """
    Formatea una velocidad en bytes por segundo a representación legible.

    Args:
        speed_bps: Velocidad en bytes por segundo

    Returns:
        String formateado (ej: "1.5 MB/s", "234 KB/s")
    """
    return f"{format_file_size(int(speed_bps))}/s"


def format_time_elapsed(seconds: float) -> str:
    """
    Formatea tiempo transcurrido a representación legible.

    Args:
        seconds: Tiempo en segundos

    Returns:
        String formateado (ej: "2m 30s", "1h 15m")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def estimate_time_remaining(bytes_downloaded: int, total_bytes: int,
                          elapsed_time: float) -> Optional[float]:
    """
    Estima el tiempo restante para completar una descarga.

    Args:
        bytes_downloaded: Bytes ya descargados
        total_bytes: Total de bytes a descargar
        elapsed_time: Tiempo transcurrido en segundos

    Returns:
        Tiempo estimado restante en segundos, o None si no se puede calcular
    """
    if bytes_downloaded <= 0 or elapsed_time <= 0 or total_bytes <= bytes_downloaded:
        return None

    speed = calculate_download_speed(bytes_downloaded, elapsed_time)
    if speed <= 0:
        return None

    remaining_bytes = total_bytes - bytes_downloaded
    return remaining_bytes / speed


class ProgressTracker:
    """
    Clase para trackear el progreso de operaciones largas.
    """

    def __init__(self, operation_name: str, total_items: int = None):
        """
        Inicializa el tracker de progreso.

        Args:
            operation_name: Nombre de la operación
            total_items: Número total de items a procesar (opcional)
        """
        self.operation_name = operation_name
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_progress_emit = self.start_time

        # Configuración para emisión de progreso
        self.update_interval = 1.0  # Segundos entre updates
        self.progress_emit_interval = 2.0  # Segundos entre emisiones SSE

    def update(self, items_processed: int = 1, custom_message: str = None):
        """
        Actualiza el progreso de la operación.

        Args:
            items_processed: Número de items procesados en esta actualización
            custom_message: Mensaje personalizado (opcional)
        """
        self.processed_items += items_processed
        current_time = time.time()

        # Verificar si es tiempo de emitir progreso
        time_since_last_emit = current_time - self.last_progress_emit

        if time_since_last_emit >= self.progress_emit_interval:
            self._emit_progress_update(custom_message)
            self.last_progress_emit = current_time

        self.last_update_time = current_time

    def _emit_progress_update(self, custom_message: str = None):
        """Emite un mensaje de progreso via SSE."""
        elapsed_time = time.time() - self.start_time

        message_data = {
            'type': 'progress',
            'operation': self.operation_name,
            'processed': self.processed_items,
            'elapsed_time': format_time_elapsed(elapsed_time)
        }

        if self.total_items:
            progress_percent = (self.processed_items / self.total_items) * 100
            message_data.update({
                'total': self.total_items,
                'progress_percent': round(progress_percent, 1),
                'estimated_remaining': None
            })

            # Estimar tiempo restante
            if self.processed_items > 0 and elapsed_time > 0:
                items_per_second = self.processed_items / elapsed_time
                remaining_items = self.total_items - self.processed_items
                if items_per_second > 0 and remaining_items > 0:
                    estimated_seconds = remaining_items / items_per_second
                    message_data['estimated_remaining'] = format_time_elapsed(estimated_seconds)

        if custom_message:
            message_data['message'] = custom_message

        emit_progress_message(message_data)

    def finish(self, success: bool = True, final_message: str = None):
        """
        Marca la operación como terminada.

        Args:
            success: Si la operación fue exitosa
            final_message: Mensaje final (opcional)
        """
        total_time = time.time() - self.start_time

        message_data = {
            'type': 'complete',
            'operation': self.operation_name,
            'success': success,
            'total_time': format_time_elapsed(total_time),
            'processed': self.processed_items
        }

        if self.total_items:
            message_data['total'] = self.total_items

        if final_message:
            message_data['message'] = final_message

        emit_progress_message(message_data)


class DownloadProgressTracker(ProgressTracker):
    """
    Especialización del ProgressTracker para descargas de archivos.
    """

    def __init__(self, operation_name: str, total_bytes: int = None):
        super().__init__(operation_name, total_bytes)
        self.bytes_downloaded = 0
        self.total_bytes = total_bytes

    def update_bytes(self, bytes_downloaded: int, custom_message: str = None):
        """
        Actualiza el progreso basado en bytes descargados.

        Args:
            bytes_downloaded: Bytes descargados en esta actualización
            custom_message: Mensaje personalizado (opcional)
        """
        self.bytes_downloaded += bytes_downloaded
        current_time = time.time()

        # Verificar si es tiempo de emitir progreso
        time_since_last_emit = current_time - self.last_progress_emit

        if time_since_last_emit >= self.progress_emit_interval:
            self._emit_download_progress(custom_message)
            self.last_progress_emit = current_time

        self.last_update_time = current_time

    def _emit_download_progress(self, custom_message: str = None):
        """Emite un mensaje de progreso específico para descargas."""
        elapsed_time = time.time() - self.start_time
        speed = calculate_download_speed(self.bytes_downloaded, elapsed_time)

        message_data = {
            'type': 'download_progress',
            'operation': self.operation_name,
            'bytes_downloaded': self.bytes_downloaded,
            'bytes_downloaded_formatted': format_file_size(self.bytes_downloaded),
            'speed': format_speed(speed),
            'elapsed_time': format_time_elapsed(elapsed_time)
        }

        if self.total_bytes:
            progress_percent = (self.bytes_downloaded / self.total_bytes) * 100
            estimated_remaining = estimate_time_remaining(
                self.bytes_downloaded, self.total_bytes, elapsed_time
            )

            message_data.update({
                'total_bytes': self.total_bytes,
                'total_bytes_formatted': format_file_size(self.total_bytes),
                'progress_percent': round(progress_percent, 1),
                'estimated_remaining': format_time_elapsed(estimated_remaining) if estimated_remaining else None
            })

        if custom_message:
            message_data['message'] = custom_message

        emit_progress_message(message_data)


class DataLoadProgressTracker:
    """
    Especialización para tracking de progreso de carga de datos.

    Envía actualizaciones específicas al canal SSE de data_load_progress_queue
    con formato optimizado para el overlay de carga del frontend.
    """

    def __init__(self, operation_name: str, blob_display_name: str = ""):
        """
        Inicializa el tracker de progreso de carga de datos.

        Args:
            operation_name: Nombre de la operación
            blob_display_name: Nombre del blob que se está cargando
        """
        self.operation_name = operation_name
        self.blob_display_name = blob_display_name
        self.current_stage = ""
        self.progress_percent = 0
        self.start_time = time.time()

    def update_progress(self, progress_percent: int, stage: str, message: str):
        """
        Actualiza el progreso con valores específicos.

        Args:
            progress_percent: Porcentaje de progreso (0-100)
            stage: Etapa actual (download, processing, enrichment, etc.)
            message: Mensaje descriptivo para mostrar al usuario
        """
        self.progress_percent = min(100, max(0, progress_percent))
        self.current_stage = stage

        elapsed_time = time.time() - self.start_time

        message_data = {
            'type': 'progress',
            'progress_percent': self.progress_percent,
            'stage': stage,
            'message': message,
            'blob_name': self.blob_display_name,
            'elapsed_time': format_time_elapsed(elapsed_time)
        }

        self._emit_to_data_load_channel(message_data)

    def finish(self, success: bool = True, final_message: str = None):
        """
        Marca la carga como completada.

        Args:
            success: Si la operación fue exitosa
            final_message: Mensaje final opcional
        """
        total_time = time.time() - self.start_time

        message_data = {
            'type': 'complete',
            'success': success,
            'progress_percent': 100 if success else self.progress_percent,
            'message': final_message or ('Carga completada exitosamente' if success else 'Error en la carga'),
            'blob_name': self.blob_display_name,
            'total_time': format_time_elapsed(total_time)
        }

        self._emit_to_data_load_channel(message_data)

    def error(self, error_message: str):
        """
        Reporta un error en la carga.

        Args:
            error_message: Mensaje de error
        """
        message_data = {
            'type': 'error',
            'progress_percent': self.progress_percent,
            'message': error_message,
            'blob_name': self.blob_display_name,
            'stage': self.current_stage
        }

        self._emit_to_data_load_channel(message_data)

    def _emit_to_data_load_channel(self, message_data: dict):
        """Emite mensaje al canal SSE de carga de datos (thread-safe).

        Usa la versión síncrona emit_data_load_progress_sync() que es thread-safe
        y funciona correctamente desde ThreadPoolExecutor sin necesidad de event loop.
        """
        if emit_data_load_progress_sync is None or data_load_progress_queue is None:
            logging.debug("Canal de progreso de carga no disponible, omitiendo mensaje")
            return

        try:
            # Usar versión síncrona - funciona desde cualquier thread
            emit_data_load_progress_sync(message_data)
        except Exception as e:
            # Usar WARNING para que sea visible en logs (no DEBUG)
            logging.warning(f"Error al emitir mensaje de progreso de carga: {e}")


# Clase contenedora para todas las utilidades de progreso
class ProgressUtils:
    """Clase contenedora para todas las utilidades de progreso."""

    @staticmethod
    def emit_progress_message(message_data: dict):
        return emit_progress_message(message_data)

    @staticmethod
    def calculate_download_speed(bytes_downloaded: int, elapsed_time: float) -> float:
        return calculate_download_speed(bytes_downloaded, elapsed_time)

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        return format_file_size(size_bytes)

    @staticmethod
    def format_speed(speed_bps: float) -> str:
        return format_speed(speed_bps)

    @staticmethod
    def format_time_elapsed(seconds: float) -> str:
        return format_time_elapsed(seconds)

    @staticmethod
    def create_progress_tracker(operation_name: str, total_items: int = None) -> ProgressTracker:
        return ProgressTracker(operation_name, total_items)

    @staticmethod
    def create_download_tracker(operation_name: str, total_bytes: int = None) -> DownloadProgressTracker:
        return DownloadProgressTracker(operation_name, total_bytes)


# Instancia global para fácil acceso
progress_utils = ProgressUtils()