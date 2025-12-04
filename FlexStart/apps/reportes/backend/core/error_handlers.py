"""Centralized error handling system for the reports API.

Provides decorators and utility functions for consistent error handling
across all API endpoints.
"""

# Standard library
import functools
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional

# Third-party
from fastapi import HTTPException

# Exception classes
class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ConfigurationError(APIError):
    """System configuration error."""
    
    def __init__(self, message: str = "Configuración no disponible"):
        super().__init__(message, status_code=503)

class ValidationError(APIError):
    """Data validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)

class ProcessingError(APIError):
    """Data processing error."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, status_code=500, details=details)

# Error handling decorator
def api_error_handler(func: Callable) -> Callable:
    """Centralized error handling decorator for API endpoints.
    
    Converts exceptions into appropriate HTTP responses with consistent formatting.
    
    Args:
        func: The endpoint function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            # Errores controlados de la API
            logging.error("API Error in %s: %s", func.__name__, e.message, exc_info=True)
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "error": e.message,
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat(),
                    "details": e.details
                }
            )
        except ValueError as e:
            # Errores de validación
            logging.error("Validation error in %s: %s", func.__name__, str(e), exc_info=True)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Datos de entrada inválidos",
                    "message": str(e),
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except FileNotFoundError as e:
            # Archivos no encontrados
            logging.error("File not found in %s: %s", func.__name__, str(e))
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Recurso no encontrado",
                    "message": str(e),
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except PermissionError as e:
            # Errores de permisos
            logging.error("Permission error in %s: %s", func.__name__, str(e))
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Permisos insuficientes",
                    "message": "No se tiene acceso al recurso solicitado",
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except InterruptedError:
            # Operaciones canceladas
            logging.info("Operation interrupted in %s", func.__name__)
            raise HTTPException(
                status_code=499,
                detail={
                    "error": "Operación cancelada",
                    "message": "La operación fue cancelada por el usuario",
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            # Errores no controlados
            error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logging.error(
                "Unhandled error %s in %s: %s\nTraceback: %s",
                error_id, func.__name__, str(e), traceback.format_exc(),
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Error interno del servidor",
                    "message": "Se produjo un error inesperado. Contacte al administrador.",
                    "error_id": error_id,
                    "endpoint": func.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    return wrapper

# Utility functions
def validate_config(config_data: Dict[str, Any]) -> None:
    """Validate that configuration is available.
    
    Args:
        config_data: Configuration dictionary to validate
        
    Raises:
        ConfigurationError: If configuration is not properly set up
    """
    if not config_data.get("config_parser"):
        raise ConfigurationError("La configuración del sistema no está disponible")

def safe_json_loads(data: str, field_name: str = "data") -> Dict[str, Any]:
    """
    Parsea JSON de forma segura con manejo de errores mejorado.
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Formato JSON inválido en {field_name}: {str(e)}",
            field=field_name
        )

def log_operation_start(operation: str, details: Dict[str, Any] = None) -> str:
    """
    Registra el inicio de una operación y retorna un ID de operación.
    """
    operation_id = f"OP_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    details_str = json.dumps(details) if details else "N/A"
    
    logging.info(
        f"OPERATION_START: {operation_id} - {operation} - Details: {details_str}"
    )
    
    return operation_id

def log_operation_end(operation_id: str, operation: str, success: bool = True, 
                     details: Dict[str, Any] = None) -> None:
    """
    Registra el final de una operación.
    """
    status = "SUCCESS" if success else "FAILED"
    details_str = json.dumps(details) if details else "N/A"
    
    logging.info(
        f"OPERATION_END: {operation_id} - {operation} - Status: {status} - Details: {details_str}"
    )

# Constantes para tipos de operaciones comunes
class OperationType:
    DATA_LOAD = "DATA_LOAD"
    DATA_EXPORT = "DATA_EXPORT"
    FILE_UPLOAD = "FILE_UPLOAD"
    SHAREPOINT_SEARCH = "SHAREPOINT_SEARCH"
    SCRIPT_EXECUTION = "SCRIPT_EXECUTION"
