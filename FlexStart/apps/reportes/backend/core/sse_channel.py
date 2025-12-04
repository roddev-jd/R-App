"""Server-Sent Events (SSE) communication channels for real-time progress updates."""

# Standard library
import asyncio
import queue
from typing import Any

# Global SSE channels
search_progress_queue: asyncio.Queue[str] = asyncio.Queue()
# Usar queue.Queue (thread-safe) para progreso de carga porque se emite desde ThreadPoolExecutor
data_load_progress_queue: queue.Queue = queue.Queue()

async def emit_search_progress(message: str) -> None:
    """Emit a progress message to the search progress SSE channel.

    Args:
        message: Progress message to broadcast to connected clients
    """
    try:
        await search_progress_queue.put(message)
    except Exception:
        # Silently handle queue errors to prevent breaking the main flow
        pass

def emit_data_load_progress_sync(message_data: dict) -> None:
    """Emit a progress message to the data load progress channel (thread-safe).

    Esta versión síncrona es thread-safe y puede llamarse desde ThreadPoolExecutor
    sin necesidad de un event loop asíncrono.

    Args:
        message_data: Dictionary containing progress information with keys like:
            - type: 'progress' or 'complete'
            - progress_percent: 0-100
            - message: Human-readable status message
            - stage: Current processing stage
    """
    try:
        data_load_progress_queue.put_nowait(message_data)
    except Exception:
        # Silently handle queue errors to prevent breaking the main flow
        pass

async def emit_data_load_progress(message_data: dict) -> None:
    """Emit a progress message to the data load progress SSE channel.

    Wrapper async que llama a la versión síncrona para compatibilidad con código
    que espera una corutina.

    Args:
        message_data: Dictionary containing progress information with keys like:
            - type: 'progress' or 'complete'
            - progress_percent: 0-100
            - message: Human-readable status message
            - stage: Current processing stage
    """
    emit_data_load_progress_sync(message_data)

def get_search_progress_queue() -> asyncio.Queue[str]:
    """Get the search progress queue for SSE streaming.

    Returns:
        The asyncio queue used for search progress messages
    """
    return search_progress_queue

def get_data_load_progress_queue() -> queue.Queue:
    """Get the data load progress queue for SSE streaming.

    Returns:
        The standard queue.Queue used for data load progress messages (thread-safe)
    """
    return data_load_progress_queue

def clear_data_load_progress_queue() -> None:
    """Clear all pending messages from the data load progress queue.

    Esta función vacía el queue para eliminar mensajes antiguos de cargas anteriores.
    Debe llamarse antes de iniciar una nueva carga de datos para evitar que las cards
    antiguas aparezcan en el frontend.
    """
    while not data_load_progress_queue.empty():
        try:
            data_load_progress_queue.get_nowait()
        except queue.Empty:
            break 