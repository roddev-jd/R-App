"""
Endpoints especializados para funcionalidades de SharePoint y búsqueda de carpetas.
Separados de app.py para mejor organización y mantenibilidad.
"""

# Standard library
import asyncio
import io
import logging
from typing import Any, Dict

# Third-party
import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Local imports
import main_logic
from core.sse_channel import search_progress_queue

# Router configuration
router = APIRouter(prefix="/api", tags=["sharepoint"])

# Request models
class FolderSearchRequest(BaseModel):
    drive_id: str
    start_folder_path: str = "root"
    download_path: str
    column_name: str

class BrowseFolderRequest(BaseModel):
    drive_id: str
    folder_path: str = "root"

# Helper functions
def _validate_excel_file(filename: str) -> None:
    """Validate Excel file extension."""
    if not filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")

def _read_excel_columns(contents: bytes) -> tuple[list, int]:
    """Read Excel and return columns and row count."""
    df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
    return list(df.columns), len(df)

def _extract_folder_names(excel_data: bytes, column_name: str) -> list[str]:
    """Extract folder names from Excel column."""
    df = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl')
    
    if column_name not in df.columns:
        raise HTTPException(status_code=400, detail=f"La columna '{column_name}' no existe en el Excel")
    
    folder_names = df[column_name].dropna().astype(str).unique().tolist()
    
    if not folder_names:
        raise HTTPException(status_code=400, detail=f"No se encontraron nombres de carpetas en la columna '{column_name}'")
    
    return folder_names

def _format_search_response(result: dict, folder_count: int) -> dict:
    """Format search operation response."""
    return {
        "success": True,
        "message": f"Proceso completado. {len(result['found'])} carpetas encontradas, {len(result['not_found'])} no encontradas",
        "total_folders": folder_count,
        "found_count": len(result['found']),
        "not_found_count": len(result['not_found']),
        "error_count": len(result['errors']),
        "found_folders": result['found'],
        "not_found_folders": result['not_found'],
        "errors": result['errors']
    }

# Excel upload endpoint
@router.post("/folder-search/upload-excel", summary="Subir Excel para buscador integral")
async def upload_excel_folder_search(file: UploadFile = File(...)):
    """Sube un archivo Excel para el buscador integral y retorna las columnas disponibles."""
    _validate_excel_file(file.filename)
    
    try:
        contents = await file.read()
        columns, row_count = _read_excel_columns(contents)
        
        # Store temporarily for later use
        main_logic.folder_search_excel_data = contents
        
        return {
            "success": True,
            "message": f"Archivo Excel '{file.filename}' cargado exitosamente",
            "columns": columns,
            "row_count": row_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error al procesar archivo Excel: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}") from e

# Folder search endpoint
@router.post("/folder-search/search-and-download", summary="Buscar y descargar carpetas desde SharePoint")
async def search_and_download_folders(request: FolderSearchRequest):
    """Busca y descarga carpetas desde SharePoint basado en los nombres del Excel."""
    if not hasattr(main_logic, 'folder_search_excel_data') or not main_logic.folder_search_excel_data:
        raise HTTPException(status_code=400, detail="Primero debe subir un archivo Excel")
    
    try:
        folder_names = _extract_folder_names(main_logic.folder_search_excel_data, request.column_name)
        
        logging.info("Iniciando búsqueda de %d carpetas en SharePoint desde %s", 
                    len(folder_names), request.start_folder_path)
        
        result = main_logic.search_and_download_folders_from_sharepoint_drive(
            drive_id=request.drive_id,
            start_folder_path=request.start_folder_path,
            folder_names=folder_names,
            download_path=request.download_path
        )
        
        # Clear temporary data if search was processed
        if result.get('found') or result.get('not_found'):
            main_logic.folder_search_excel_data = None
        
        return _format_search_response(result, len(folder_names))
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error en búsqueda y descarga de carpetas: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e

# Manual search endpoint
@router.post("/folder-search/search-and-download-manual", summary="Buscar y descargar carpetas desde SharePoint usando URL manual")
async def search_and_download_folders_manual(request: Dict[str, Any]):
    """Busca y descarga carpetas desde SharePoint usando URL manual (modo de compatibilidad)."""
    if not hasattr(main_logic, 'folder_search_excel_data') or not main_logic.folder_search_excel_data:
        raise HTTPException(status_code=400, detail="Primero debe subir un archivo Excel")
    
    try:
        # Extract and validate parameters
        column_name = request.get('column_name')
        download_path = request.get('download_path')
        sharepoint_url = request.get('sharepoint_url')
        
        if not all([column_name, download_path, sharepoint_url]):
            raise HTTPException(status_code=400, detail="Faltan parámetros requeridos")
        
        folder_names = _extract_folder_names(main_logic.folder_search_excel_data, column_name)
        
        logging.info("Iniciando búsqueda manual de %d carpetas en SharePoint URL: %s", 
                    len(folder_names), sharepoint_url)
        
        result = main_logic.search_and_download_folders_from_sharepoint_manual(
            sharepoint_url=sharepoint_url,
            folder_names=folder_names,
            download_path=download_path
        )
        
        # Clear temporary data if search was processed
        if result.get('found') or result.get('not_found'):
            main_logic.folder_search_excel_data = None
        
        return _format_search_response(result, len(folder_names))
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error en búsqueda manual de carpetas: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e

# Clear Excel data endpoint
@router.delete("/folder-search/clear-excel", summary="Limpiar datos de Excel cargado")
async def clear_folder_search_excel():
    """Limpia los datos del Excel cargado para el buscador integral."""
    main_logic.folder_search_excel_data = None
    return {"success": True, "message": "Datos de Excel limpiados exitosamente"}

# SharePoint navigation endpoints
@router.get("/sharepoint/libraries", summary="Obtener bibliotecas de documentos del sitio SharePoint por defecto")
async def get_sharepoint_libraries():
    """Obtiene las bibliotecas de documentos disponibles en el sitio SharePoint configurado."""
    try:
        return main_logic.get_default_sharepoint_libraries()
    except Exception as e:
        logging.error("Error obteniendo bibliotecas de SharePoint: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e

@router.post("/sharepoint/browse", summary="Navegar por carpetas de SharePoint")
async def browse_sharepoint_folder(request: BrowseFolderRequest):
    """Navega por una carpeta específica en SharePoint y retorna su contenido."""
    try:
        return main_logic.browse_sharepoint_folder(request.drive_id, request.folder_path)
    except Exception as e:
        logging.error("Error navegando carpeta de SharePoint: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e

# SSE progress endpoint
@router.get("/folder-search/progress", summary="Progreso en tiempo real de la búsqueda de carpetas", response_class=StreamingResponse)
async def sse_folder_search_progress(request: Request):
    """Endpoint SSE para emitir mensajes de progreso de la búsqueda de carpetas."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(search_progress_queue.get(), timeout=10)
                yield f"data: {message}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")