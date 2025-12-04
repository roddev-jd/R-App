"""
Detección de capabilities del sistema para adaptar funcionalidades
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def check_duckdb_available() -> bool:
    """
    Verifica si DuckDB está disponible en el sistema
    """
    try:
        import duckdb
        # Prueba básica de funcionalidad
        conn = duckdb.connect(database=':memory:')
        conn.close()
        return True
    except ImportError:
        logger.info("DuckDB no está disponible")
        return False
    except Exception as e:
        logger.warning(f"DuckDB instalado pero con problemas: {e}")
        return False

def check_opencv_available() -> bool:
    """
    Verifica si OpenCV está disponible en el sistema
    """
    try:
        import cv2
        # Prueba básica de funcionalidad
        return True
    except ImportError:
        logger.info("OpenCV no está disponible - AHEAD deshabilitado")
        return False
    except Exception as e:
        logger.warning(f"OpenCV instalado pero con problemas: {e}")
        return False

def get_system_capabilities() -> Dict[str, bool]:
    """
    Obtiene todas las capabilities del sistema
    """
    capabilities = {
        "duckdb_available": check_duckdb_available(),
        "opencv_available": check_opencv_available(),
    }
    
    # Capabilities derivadas
    capabilities.update({
        "reportes_available": capabilities["duckdb_available"],
        "ahead_tool": capabilities["opencv_available"],
    })
    
    logger.info(f"System capabilities: {capabilities}")
    return capabilities