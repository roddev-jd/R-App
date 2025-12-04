"""
Backend Central Gateway - SUITE
Punto de entrada único para todas las aplicaciones del proyecto SUITE.
Este gateway integra y sirve todas las sub-aplicaciones manteniendo separación de responsabilidades.
"""

import os
import sys
import logging
import subprocess
import asyncio
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import zipfile
import io

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] (%(module)s:%(lineno)d) %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI principal
app = FastAPI(
    title="SUITE Gateway", 
    description="Backend central para todas las aplicaciones SUITE",
    version="1.0.0"
)

# Configuración de directorios
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FLEXSTART_DIR = os.path.dirname(BACKEND_DIR)
APPS_DIR = os.path.join(FLEXSTART_DIR, "apps")
HERRAMIENTAS_DIR = os.path.join(FLEXSTART_DIR, "herramientas")
SHARED_DIR = os.path.join(FLEXSTART_DIR, "shared")

# Agregar backend y shared al path
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

# ThreadPoolExecutor para ejecución de scripts
script_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ScriptExec")

# Modelo para solicitudes de scripts
class ScriptRequest(BaseModel):
    script_id: str

def get_allowed_scripts():
    """Genera diccionario de scripts permitidos."""
    diseno_dir = os.path.join(APPS_DIR, "diseno")
    return {
        "buscador_diseno": os.path.join(diseno_dir, "BUSCADOR", "Buscador.py"),
        "miniaturas_diseno": os.path.join(diseno_dir, "MINIATURAS", "Miniaturas.py"),
        "CLdownloader": os.path.join(diseno_dir, "CLDOWNLOADER", "CLdownloader.py"),
        "PEdownloader": os.path.join(diseno_dir, "PEDOWNLOADER", "PEdownloader.py"),
        "RipleyDownloader": os.path.join(diseno_dir, "RIPLEYDOWNLOADER", "RipleyDownloader.py"),
        "Scrapper": os.path.join(diseno_dir, "SCRAPPER", "Scrapper.py"),
        "Renamer-PH": os.path.join(diseno_dir, "RENAMER_PH", "Renamer-PH.py"),
        "Renamer-Rimage": os.path.join(diseno_dir, "RENAMER_RIMAGE", "Renamer-Rimage.py"),
        "SVC-OK": os.path.join(diseno_dir, "SVC-OK", "SVC-OK.py"),
        "Renamer-ImgFile": os.path.join(diseno_dir, "RENAMER_IMG", "Renamer-ImgFile-Mejorado.py"),
        "Renamer-Muestras": os.path.join(diseno_dir, "RENAMER_MUESTRAS", "Renamer-Muestras.py"),
        "lastImage": os.path.join(diseno_dir, "LAST_IMAGE", "lastImage.py"),
        "Insert": os.path.join(diseno_dir, "INSERTAR", "Insert.py"),
        "Dept": os.path.join(diseno_dir, "DEPT", "Dept.py"),
        "Encarpetar": os.path.join(diseno_dir, "ENCARPETAR", "Encarpetar.py"),
        "Indexar": os.path.join(diseno_dir, "INDEXAR", "run_app.py"),
        "Prod-Selector": os.path.join(diseno_dir, "PROD_SELECTOR", "Prod-Selector.py"),
        "TeamSearch": os.path.join(diseno_dir, "TEAMSEARCH", "TeamSearch.py"),
        "Compresor": os.path.join(diseno_dir, "COMPRESOR", "Compresor.py"),
        "Convertidor": os.path.join(diseno_dir, "CONVERTIDOR", "Convertidor.py"),
        "RotateImg": os.path.join(diseno_dir, "ROTATE_IMAGE", "RotateImg.py"),
        "Multi-Tags-moda-producto": os.path.join(diseno_dir, "MULTITAG", "multitag.py"),
        "Validador_tamano": os.path.join(diseno_dir, "IMAGE_VALIDATOR", "image_validator.py"),
    }

ALLOWED_SCRIPTS = get_allowed_scripts()

def get_allowed_folders():
    """Genera diccionario de carpetas permitidas para descarga."""
    diseno_dir = os.path.join(APPS_DIR, "diseno")
    return {
        "buscador_diseno": os.path.join(diseno_dir, "BUSCADOR"),
        "miniaturas_diseno": os.path.join(diseno_dir, "MINIATURAS"),
        "CLdownloader": os.path.join(diseno_dir, "CLDOWNLOADER"),
        "PEdownloader": os.path.join(diseno_dir, "PEDOWNLOADER"),
        "RipleyDownloader": os.path.join(diseno_dir, "RIPLEYDOWNLOADER"),
        "Scrapper": os.path.join(diseno_dir, "SCRAPPER"),
        "Renamer-PH": os.path.join(diseno_dir, "RENAMER_PH"),
        "Renamer-Rimage": os.path.join(diseno_dir, "RENAMER_RIMAGE"),
        "SVC-OK": os.path.join(diseno_dir, "SVC-OK"),
        "Renamer-ImgFile": os.path.join(diseno_dir, "RENAMER_IMG"),
        "Renamer-Muestras": os.path.join(diseno_dir, "RENAMER_MUESTRAS"),
        "lastImage": os.path.join(diseno_dir, "LAST_IMAGE"),
        "Insert": os.path.join(diseno_dir, "INSERTAR"),
        "Dept": os.path.join(diseno_dir, "DEPT"),
        "Encarpetar": os.path.join(diseno_dir, "ENCARPETAR"),
        "Indexar": os.path.join(diseno_dir, "INDEXAR"),
        "Prod-Selector": os.path.join(diseno_dir, "PROD_SELECTOR"),
        "TeamSearch": os.path.join(diseno_dir, "TEAMSEARCH"),
        "Compresor": os.path.join(diseno_dir, "COMPRESOR"),
        "Convertidor": os.path.join(diseno_dir, "CONVERTIDOR"),
        "RotateImg": os.path.join(diseno_dir, "ROTATE_IMAGE"),
        "Multi-Tags-moda-producto": os.path.join(diseno_dir, "MULTITAG"),
        "Validador_tamano": os.path.join(diseno_dir, "IMAGE_VALIDATOR"),
    }

ALLOWED_FOLDERS = get_allowed_folders()

def _execute_script_sync(script_path: str, script_dir: str) -> dict:
    """
    Función síncrona para ejecutar un script en un proceso separado.
    Esta función se ejecuta en un thread separado para no bloquear el event loop.
    """
    try:
        # Preparar el ambiente con PYTHONPATH para que los scripts puedan importar
        # módulos locales desde su propio directorio
        env = os.environ.copy()
        current_pythonpath = env.get('PYTHONPATH', '')
        if current_pythonpath:
            env['PYTHONPATH'] = script_dir + os.pathsep + current_pythonpath
        else:
            env['PYTHONPATH'] = script_dir

        # Ejecuta el script en un proceso separado para no bloquear la API.
        # El script abrirá su propia ventana si es una app de GUI.
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=script_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Esperar un momento breve para detectar fallos inmediatos
        import time
        time.sleep(0.5)

        # Verificar si el proceso falló inmediatamente
        poll_result = process.poll()
        if poll_result is not None:
            # El proceso ya terminó - probablemente un error
            stdout, stderr = process.communicate()
            error_msg = f"El script falló al iniciar.\n"
            if stderr:
                error_msg += f"Error: {stderr[:500]}"  # Limitar longitud
            if stdout:
                error_msg += f"\nSalida: {stdout[:500]}"

            logger.error(f"Script {os.path.basename(script_path)} failed: {stderr}")
            return {
                "success": False,
                "message": error_msg
            }

        # No esperamos a que termine el proceso para permitir scripts GUI de larga duración
        # El script se inició correctamente
        return {
            "success": True,
            "pid": process.pid,
            "message": f"Script iniciado con PID {process.pid}"
        }
    except Exception as e:
        logger.error(f"Exception launching script {script_path}: {str(e)}")
        return {
            "success": False,
            "message": f"Error al ejecutar script: {str(e)}"
        }

def integrate_reportes():
    """Integra aplicación reportes."""
    try:
        # Primero configurar archivos estáticos de reportes
        reportes_frontend_dir = os.path.join(APPS_DIR, "reportes", "frontend")
        if os.path.exists(reportes_frontend_dir):
            # Montar CSS, JS y assets de reportes ANTES de montar la app
            app.mount("/reportes/css", 
                     StaticFiles(directory=os.path.join(reportes_frontend_dir, "css")), 
                     name="reportes_css")
            app.mount("/reportes/static", 
                     StaticFiles(directory=os.path.join(reportes_frontend_dir, "js")), 
                     name="reportes_js")
            app.mount("/reportes/assets", 
                     StaticFiles(directory=os.path.join(reportes_frontend_dir, "assets")), 
                     name="reportes_assets")
            logging.info(f"Archivos estáticos de reportes montados desde: {reportes_frontend_dir}")
        else:
            logging.warning(f"No se encontró directorio frontend de reportes en: {reportes_frontend_dir}")
        
        # Agregar path al sys.path
        reportes_backend_path = os.path.join(APPS_DIR, "reportes", "backend")
        if reportes_backend_path not in sys.path:
            sys.path.insert(0, reportes_backend_path)

        # Importar la app de reportes usando importlib para evitar conflictos
        import importlib.util
        spec = importlib.util.spec_from_file_location("reportes_app", os.path.join(reportes_backend_path, "app.py"))
        reportes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reportes_module)
        reportes_app = reportes_module.app
        
        # Montar reportes en /reportes DESPUÉS de las rutas estáticas
        app.mount("/reportes", reportes_app, name="reportes")
        
        logging.info("Aplicación Reportes integrada correctamente en /reportes")
    except ImportError as e:
        logging.warning(f"No se pudo integrar reportes: {e}")
    except Exception as e:
        logging.error(f"Error al integrar reportes: {e}")

def integrate_prod_peru():
    """Integra aplicación prod_peru."""
    try:
        # Primero configurar archivos estáticos de prod_peru
        prod_peru_frontend_dir = os.path.join(APPS_DIR, "prod_peru", "frontend")
        if os.path.exists(prod_peru_frontend_dir):
            # Montar CSS, JS y assets de prod_peru ANTES de montar la app
            app.mount("/prod_peru/css", 
                     StaticFiles(directory=os.path.join(prod_peru_frontend_dir, "css")), 
                     name="prod_peru_css")
            app.mount("/prod_peru/js", 
                     StaticFiles(directory=os.path.join(prod_peru_frontend_dir, "js")), 
                     name="prod_peru_js")
            app.mount("/prod_peru/assets", 
                     StaticFiles(directory=os.path.join(prod_peru_frontend_dir, "assets")), 
                     name="prod_peru_assets")
            logging.info(f"Archivos estáticos de prod_peru montados desde: {prod_peru_frontend_dir}")
        else:
            logging.warning(f"No se encontró directorio frontend de prod_peru en: {prod_peru_frontend_dir}")
        
        # Importar dinámicamente la app de prod_peru
        import importlib.util
        prod_peru_backend_path = os.path.join(APPS_DIR, "prod_peru", "backend")
        spec = importlib.util.spec_from_file_location("prod_peru_app", os.path.join(prod_peru_backend_path, "app.py"))
        prod_peru_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prod_peru_module)
        
        # Montar prod_peru en /prod_peru DESPUÉS de las rutas estáticas
        app.mount("/prod_peru", prod_peru_module.app, name="prod_peru")
        
        logging.info("Aplicación Prod PERÚ integrada correctamente en /prod_peru")
    except ImportError as e:
        logging.warning(f"No se pudo integrar prod_peru: {e}")
    except Exception as e:
        logging.error(f"Error al integrar prod_peru: {e}")


def setup_static_routes():
    """Configura todas las rutas estáticas del proyecto."""
    # Assets de FlexStart
    app.mount("/assets_flexstart",
              StaticFiles(directory=os.path.join(FLEXSTART_DIR, "assets")),
              name="flexstart_assets")

    # Manuales PDF
    manuales_dir = os.path.join(FLEXSTART_DIR, "manuales")
    if os.path.exists(manuales_dir):
        app.mount("/manuales",
                  StaticFiles(directory=manuales_dir),
                  name="manuales")
        logging.info(f"Manuales montados desde: {manuales_dir}")

    # Data directory (para birthdays.json, etc)
    data_dir = os.path.join(FLEXSTART_DIR, "data")
    if os.path.exists(data_dir):
        app.mount("/data",
                  StaticFiles(directory=data_dir),
                  name="data")
        logging.info(f"Data directory montado desde: {data_dir}")

    # Herramientas HTML
    app.mount("/herramientas",
              StaticFiles(directory=HERRAMIENTAS_DIR, html=True),
              name="herramientas")

    logging.info("Rutas estáticas configuradas correctamente")

@app.get("/")
async def root():
    """Sirve el index.html principal de FlexStart."""
    index_path = os.path.join(FLEXSTART_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "SUITE Gateway funcionando", "status": "ok"}

@app.get("/birthdays.html")
async def birthdays_page():
    """Sirve la página de cumpleaños."""
    birthdays_path = os.path.join(FLEXSTART_DIR, "birthdays.html")
    if os.path.exists(birthdays_path):
        return FileResponse(birthdays_path)
    else:
        raise HTTPException(status_code=404, detail="Página de cumpleaños no encontrada")


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy", "service": "SUITE Gateway"}

@app.get("/api/system/capabilities")
async def get_system_capabilities():
    """Endpoint para obtener las capacidades del sistema."""
    try:
        from capabilities import get_system_capabilities
        capabilities = get_system_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities
        }
    except Exception as e:
        logging.error(f"Error al obtener capabilities: {e}")
        return {
            "status": "error",
            "message": str(e),
            "capabilities": {
                "duckdb_available": False,
                "opencv_available": False,
                "reportes_available": False,
                "ahead_tool": False
            }
        }

@app.get("/api/birthdays/current-month")
async def get_current_month_birthdays():
    """Obtiene los cumpleaños del mes actual."""
    try:
        # Ruta al archivo de cumpleaños
        birthdays_file = os.path.join(FLEXSTART_DIR, "data", "birthdays.json")

        # Verificar si existe el archivo
        if not os.path.exists(birthdays_file):
            return {
                "status": "error",
                "message": "Archivo de cumpleaños no encontrado",
                "birthdays": []
            }

        # Leer el archivo JSON
        with open(birthdays_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Obtener el mes actual
        current_month = datetime.now().month

        # Filtrar usuarios cuyo cumpleaños es en el mes actual
        current_month_birthdays = []
        for user in data.get("users", []):
            birthday = user.get("birthday", "")
            # El formato es MM-DD
            if birthday:
                month = int(birthday.split("-")[0])
                if month == current_month:
                    # Agregar el día para ordenar
                    day = int(birthday.split("-")[1])
                    user_with_day = user.copy()
                    user_with_day["day"] = day
                    current_month_birthdays.append(user_with_day)

        # Ordenar por día del mes
        current_month_birthdays.sort(key=lambda x: x["day"])

        return {
            "status": "success",
            "current_month": current_month,
            "count": len(current_month_birthdays),
            "birthdays": current_month_birthdays
        }
    except Exception as e:
        logging.error(f"Error al obtener cumpleaños: {e}")
        return {
            "status": "error",
            "message": str(e),
            "birthdays": []
        }

@app.get("/api/birthdays/all")
async def get_all_birthdays():
    """Obtiene todos los cumpleaños agrupados por mes."""
    try:
        # Ruta al archivo de cumpleaños
        birthdays_file = os.path.join(FLEXSTART_DIR, "data", "birthdays.json")

        # Verificar si existe el archivo
        if not os.path.exists(birthdays_file):
            return {
                "status": "error",
                "message": "Archivo de cumpleaños no encontrado",
                "birthdays_by_month": {}
            }

        # Leer el archivo JSON
        with open(birthdays_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Agrupar por mes
        birthdays_by_month = {}
        for month in range(1, 13):
            birthdays_by_month[month] = []

        for user in data.get("users", []):
            birthday = user.get("birthday", "")
            if birthday:
                month = int(birthday.split("-")[0])
                day = int(birthday.split("-")[1])
                user_with_day = user.copy()
                user_with_day["day"] = day
                birthdays_by_month[month].append(user_with_day)

        # Ordenar cada mes por día
        for month in birthdays_by_month:
            birthdays_by_month[month].sort(key=lambda x: x["day"])

        return {
            "status": "success",
            "metadata": data.get("metadata", {}),
            "total_users": len(data.get("users", [])),
            "birthdays_by_month": birthdays_by_month
        }
    except Exception as e:
        logging.error(f"Error al obtener todos los cumpleaños: {e}")
        return {
            "status": "error",
            "message": str(e),
            "birthdays_by_month": {}
        }

@app.get("/api/birthdays/month/{month}")
async def get_birthdays_by_month(month: int):
    """Obtiene los cumpleaños de un mes específico."""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mes inválido. Debe estar entre 1 y 12.")

    try:
        # Ruta al archivo de cumpleaños
        birthdays_file = os.path.join(FLEXSTART_DIR, "data", "birthdays.json")

        # Verificar si existe el archivo
        if not os.path.exists(birthdays_file):
            return {
                "status": "error",
                "message": "Archivo de cumpleaños no encontrado",
                "birthdays": []
            }

        # Leer el archivo JSON
        with open(birthdays_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Filtrar usuarios del mes solicitado
        month_birthdays = []
        for user in data.get("users", []):
            birthday = user.get("birthday", "")
            if birthday:
                user_month = int(birthday.split("-")[0])
                if user_month == month:
                    day = int(birthday.split("-")[1])
                    user_with_day = user.copy()
                    user_with_day["day"] = day
                    month_birthdays.append(user_with_day)

        # Ordenar por día del mes
        month_birthdays.sort(key=lambda x: x["day"])

        return {
            "status": "success",
            "month": month,
            "count": len(month_birthdays),
            "birthdays": month_birthdays
        }
    except Exception as e:
        logging.error(f"Error al obtener cumpleaños del mes {month}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "birthdays": []
        }

@app.post("/api/run-script", summary="Ejecutar un script de herramienta local de forma asíncrona")
async def run_script(request: ScriptRequest):
    """Ejecuta una herramienta de diseño de forma asíncrona."""
    script_path = ALLOWED_SCRIPTS.get(request.script_id)

    if not script_path:
        raise HTTPException(status_code=404, detail="Script no encontrado o no permitido.")

    if not os.path.exists(script_path):
        logging.error(f"El archivo de script no existe en la ruta: {script_path}")
        raise HTTPException(status_code=500, detail="El archivo de script no fue encontrado en el servidor.")

    try:
        script_dir = os.path.dirname(script_path)

        # Ejecutar el script de forma asíncrona usando ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            script_executor,
            _execute_script_sync,
            script_path,
            script_dir
        )

        if result["success"]:
            logging.info(f"Script '{request.script_id}' iniciado exitosamente. PID: {result.get('pid')}")
            return {
                "message": f"El script '{request.script_id}' se ha iniciado de forma asíncrona.",
                "script_id": request.script_id,
                "pid": result.get("pid"),
                "status": "started"
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint run_script para '{request.script_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al iniciar el script: {str(e)}")


@app.get("/api/download-tool/{script_id}", summary="Descargar herramienta como ZIP")
async def download_tool(script_id: str):
    """Descarga una herramienta de diseño como archivo ZIP."""
    folder_path = ALLOWED_FOLDERS.get(script_id)

    if not folder_path:
        raise HTTPException(status_code=404, detail="Herramienta no encontrada o no permitida.")

    if not os.path.exists(folder_path):
        logging.error(f"La carpeta de la herramienta no existe en la ruta: {folder_path}")
        raise HTTPException(status_code=500, detail="La carpeta de la herramienta no fue encontrada en el servidor.")

    if not os.path.isdir(folder_path):
        logging.error(f"La ruta no es una carpeta: {folder_path}")
        raise HTTPException(status_code=500, detail="La ruta especificada no es una carpeta válida.")

    try:
        # Crear ZIP en memoria
        zip_buffer = io.BytesIO()
        folder_name = os.path.basename(folder_path)

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(folder_path):
                # Excluir carpetas no deseadas
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.DS_Store']]

                for file in files:
                    # Excluir archivos no deseados
                    if file in ['.DS_Store'] or file.endswith('.pyc'):
                        continue

                    file_path = os.path.join(root, file)
                    # Calcular la ruta relativa dentro del ZIP
                    arcname = os.path.join(folder_name, os.path.relpath(file_path, folder_path))
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)

        # Nombre del archivo ZIP
        zip_filename = f"{folder_name}.zip"

        logging.info(f"Herramienta '{script_id}' preparada para descarga como {zip_filename}")

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}"
            }
        )

    except Exception as e:
        logging.error(f"Error al crear ZIP para '{script_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al preparar la descarga: {str(e)}")




# Configurar todas las integraciones
setup_static_routes()
integrate_reportes()
integrate_prod_peru()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)