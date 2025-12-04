"""
Backend de Producción PERÚ - SUITE
API independiente para la gestión de producción PERÚ con autenticación de usuarios.
"""

import logging
import sys
import configparser
import os
import tempfile
import base64
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import io
import boto3
from botocore.exceptions import ClientError

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Añadir el directorio actual al path para importar auth_service
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Importar servicio de autenticación local
from auth_service import init_auth_service, get_auth_service

# Añadir el directorio shared al path para importar servicios compartidos
shared_services_dir = Path(__file__).parent.parent.parent.parent / "shared" / "services"
sys.path.insert(0, str(shared_services_dir))

# Importar autenticación SharePoint desde módulo compartido
try:
    import sharepoint_service as sharepoint_auth
except ImportError as e:
    logging.error("Error importando sharepoint_auth desde shared/services: %s", e)
    sharepoint_auth = None

app = FastAPI(title="Producción PERÚ API", version="1.0.0")

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directorio base de la aplicación
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
CONFIG_PATH = Path(__file__).parent / "config.ini"

# Cargar configuración local (sin interpolación para evitar problemas con URLs)
config_parser = configparser.ConfigParser(interpolation=None)
if CONFIG_PATH.exists():
    config_parser.read(CONFIG_PATH)
    logging.info(f"Configuración cargada desde: {CONFIG_PATH}")
else:
    logging.error(f"Archivo de configuración no encontrado: {CONFIG_PATH}")

# Autenticador SharePoint global
sharepoint_authenticator = None

# Cliente S3 global
s3_client = None
S3_BUCKET = None
S3_REGION = None

# Inicializar servicio de autenticación
auth_service = init_auth_service(config_parser)

# Lista de usuarios válidos (reemplaza USER_PASSWORDS)
# Estos son los usuarios que tienen acceso al sistema
VALID_USERS = [
    "rjarad",
    "vsarmientos",
    "fmonsalvec",
    "lmunozp",
    "mlledoa",
    "gdeliberom",
    "bfernandezm",
    "dmenanteaum",
    "ctamayol",
    "ngaticac",
    "nsanchezp",
    "vbenavidesa",
    "pzarsosa_diseno",
    "pzarsosa_redaccion",
    "iaranibar_diseno",
    "iaranibar_redaccion",
    "dbernal_diseno",
    "dbernal_redaccion",
]

# Mapeo de usuarios técnicos a nombres reales y género
USER_INFO = {
    "rjarad": {"name": "Rodrigo", "gender": "male"},
    "vsarmientos": {"name": "Vania", "gender": "female"},
    "fmonsalvec": {"name": "Fernanda", "gender": "female"},
    "lmunozp": {"name": "Lilian", "gender": "female"},
    "mlledoa": {"name": "Mauricio", "gender": "male"},
    "gdeliberom": {"name": "Geancarlo", "gender": "male"},
    "bfernandezm": {"name": "Constanza", "gender": "female"},
    "dmenanteaum": {"name": "Dominicque", "gender": "female"},
    "ctamayol": {"name": "Constanza", "gender": "female"},
    "ngaticac": {"name": "Nicole", "gender": "female"},
    "nsanchezp": {"name": "Natalia", "gender": "female"},
    "pzarsosa_diseno": {"name": "chicos", "gender": "female"},
    "pzarsosa_redaccion": {"name": "chicos", "gender": "female"},
    "iaranibar_diseno": {"name": "chicos", "gender": "male"},
    "iaranibar_redaccion": {"name": "chicos", "gender": "male"},
    "dbernal_diseno": {"name": "chicos", "gender": "male"},
    "dbernal_redaccion": {"name": "chicos", "gender": "male"},
}

# Montar archivos estáticos (rutas relativas para cuando la app se monta en un path)
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

# Modelos de datos
class DeclarationRequest(BaseModel):
    """Modelo para solicitudes de declaración"""
    team_member: str
    declaration_text: str

class RejectionRequest(BaseModel):
    """Modelo para solicitudes de rechazo"""
    team_member: str
    rejection_text: str
    rejection_obs: str

class PendingDesignRequest(BaseModel):
    """Modelo para solicitudes de diseño pendiente"""
    team_member: str
    pending_design_text: str

# Funciones auxiliares

# Lista de usuarios con acceso a diseño pendiente
PENDING_DESIGN_USERS = [
    "rjarad",
    "vsarmientos",
    "fmonsalvec",
    "lmunozp",
    "mlledoa",
    "gdeliberom"
]

def has_pending_design_access(username: str) -> bool:
    """Verificar si el usuario tiene acceso a la funcionalidad de diseño pendiente"""
    return username in PENDING_DESIGN_USERS

def get_current_user_from_token(request: Request) -> str:
    """
    Extrae y valida el usuario del token JWT en el header Authorization.

    Args:
        request: Request de FastAPI

    Returns:
        Username del usuario autenticado

    Raises:
        HTTPException: Si el token es inválido o no está presente
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=401,
            detail="Token de autenticación no proporcionado"
        )

    token = auth_header[7:]  # Remover "Bearer "

    auth_svc = get_auth_service()
    if not auth_svc:
        raise HTTPException(
            status_code=500,
            detail="Servicio de autenticación no disponible"
        )

    user_data = auth_svc.validate_token(token)

    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado. Por favor, inicia sesión nuevamente."
        )

    username = user_data.get('username')

    if username not in VALID_USERS:
        raise HTTPException(
            status_code=403,
            detail="Usuario no autorizado"
        )

    return username

def get_sharepoint_authenticator():
    """Obtener autenticador SharePoint"""
    global sharepoint_authenticator
    if sharepoint_authenticator is None and sharepoint_auth is not None:
        sharepoint_authenticator = sharepoint_auth.SharePointAuth()
    return sharepoint_authenticator

def get_s3_client():
    """Obtener cliente S3 configurado"""
    global s3_client, S3_BUCKET, S3_REGION

    if s3_client is None:
        # Priorizar variables de entorno
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        S3_BUCKET = os.getenv('AWS_S3_BUCKET')
        S3_REGION = os.getenv('AWS_S3_REGION', 'us-east-1')

        credentials_source = "variables de entorno"

        # Fallback a config.ini si no hay variables de entorno completas
        if not all([aws_access_key, aws_secret_key, S3_BUCKET]):
            credentials_source = "config.ini"
            if config_parser.has_section('S3'):
                aws_access_key = aws_access_key or config_parser.get('S3', 'aws_access_key_id', fallback=None)
                aws_secret_key = aws_secret_key or config_parser.get('S3', 'aws_secret_access_key', fallback=None)
                S3_BUCKET = S3_BUCKET or config_parser.get('S3', 'bucket', fallback=None)
                S3_REGION = S3_REGION or config_parser.get('S3', 'region', fallback='us-east-1')
                logging.info("Credenciales AWS cargadas desde config.ini (fallback)")
            else:
                logging.warning("Sección [S3] no encontrada en config.ini y variables de entorno no configuradas")

        if aws_access_key and aws_secret_key and S3_BUCKET:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=S3_REGION
            )
            logging.info(f"Cliente S3 inicializado desde {credentials_source}. Bucket: {S3_BUCKET}, Region: {S3_REGION}")
        else:
            logging.warning("Configuración de S3 incompleta. Verifique variables de entorno o config.ini")

    return s3_client

def _read_file_from_s3(s3_key: str) -> pd.DataFrame:
    """Leer archivo Excel desde S3"""
    try:
        s3 = get_s3_client()
        if not s3:
            raise ValueError("Cliente S3 no disponible")

        logging.info(f"Leyendo archivo desde S3: {S3_BUCKET}/{s3_key}")

        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_content = response['Body'].read()

        return pd.read_excel(io.BytesIO(file_content))

    except s3.exceptions.NoSuchKey:
        logging.warning(f"Archivo no existe en S3: {s3_key}. Retornando DataFrame vacío.")
        return pd.DataFrame()

    except Exception as e:
        logging.error(f"Error leyendo archivo desde S3: {e}")
        raise

def _upload_file_to_s3(s3_key: str, file_path: str) -> bool:
    """Subir archivo a S3"""
    try:
        s3 = get_s3_client()
        if not s3:
            raise ValueError("Cliente S3 no disponible")

        logging.info(f"Subiendo archivo a S3: {S3_BUCKET}/{s3_key}")

        s3.upload_file(
            file_path,
            S3_BUCKET,
            s3_key,
            ExtraArgs={'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
        )

        logging.info(f"Archivo subido exitosamente a S3")
        return True

    except Exception as e:
        logging.error(f"Error subiendo archivo a S3: {e}")
        raise

def get_team_members() -> List[Dict[str, str]]:
    """Obtener lista de integrantes del equipo desde la configuración local"""
    if not config_parser.has_section('TeamMembers'):
        logging.warning("Sección [TeamMembers] no encontrada en config.ini")
        return []

    team_members = []
    for member_id, excel_url in config_parser.items('TeamMembers'):
        display_name = member_id.replace('_', ' ').title()
        team_members.append({
            'member_id': member_id,
            'display_name': display_name,
            'excel_url': excel_url
        })

    return team_members

def get_team_members_reject() -> List[Dict[str, str]]:
    """Obtener lista de integrantes del equipo para rechazos desde la configuración local"""
    if not config_parser.has_section('TeamMembersReject'):
        logging.warning("Sección [TeamMembersReject] no encontrada en config.ini")
        return []

    team_members = []
    for member_id, excel_url in config_parser.items('TeamMembersReject'):
        display_name = member_id.replace('_', ' ').title()
        team_members.append({
            'member_id': member_id,
            'display_name': display_name,
            'excel_url': excel_url
        })

    return team_members

def get_team_members_pending_design() -> List[Dict[str, str]]:
    """Obtener lista de integrantes del equipo para diseño pendiente desde la configuración local"""
    if not config_parser.has_section('TeamMembersPendingDesign'):
        logging.warning("Sección [TeamMembersPendingDesign] no encontrada en config.ini")
        return []

    team_members = []
    for member_id, excel_url in config_parser.items('TeamMembersPendingDesign'):
        display_name = member_id.replace('_', ' ').title()
        team_members.append({
            'member_id': member_id,
            'display_name': display_name,
            'excel_url': excel_url
        })

    return team_members

def _parse_sharepoint_url(sharepoint_url: str) -> tuple:
    """Extraer site, drive y filepath de una URL de SharePoint"""
    import urllib.parse
    from urllib.parse import urlparse, unquote

    # Parsear la URL
    parsed = urlparse(sharepoint_url)
    path_parts = parsed.path.split('/')

    # Extraer el site (ejemplo: sites/Equipopyc o sites/Publicacinycontenido2)
    if 'sites' in path_parts:
        site_index = path_parts.index('sites')
        site_name = path_parts[site_index + 1]
    else:
        raise ValueError(f"No se pudo identificar el sitio en la URL: {sharepoint_url}")

    # El hostname es ripleycorp.sharepoint.com
    hostname = parsed.netloc

    # Construir la ruta del archivo
    # Ejemplo: /sites/Publicacinycontenido2/Documentos Publicacin/Metricas/BLANDOS MODA MUJER/MUJER.xlsx
    file_path = unquote(parsed.path)

    return hostname, site_name, file_path

def _download_sharepoint_file_chunked(filename: str, chunk_size: int = 8192) -> bytes:
    """Descargar archivo desde SharePoint en chunks usando método directo"""
    auth = get_sharepoint_authenticator()
    if not auth:
        raise ValueError("Autenticador SharePoint no disponible")

    access_token = auth.get_token()

    try:
        # Intentar primero con el método de sharing (actual)
        sharepoint_url_bytes = filename.encode('utf-8')
        encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')
        graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/root/content"
        headers = {'Authorization': f'Bearer {access_token}'}

        logging.info(f"Método 1: Intentando acceder via sharing URL")
        logging.info(f"Graph URL: {graph_url}")

        response = requests.get(graph_url, headers=headers, stream=True, verify=False)

        if response.status_code == 200:
            file_content = b''
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file_content += chunk
            return file_content

        # Si falla, intentar método alternativo
        logging.warning(f"Método 1 falló con status {response.status_code}. Intentando método alternativo...")
        logging.warning(f"Respuesta: {response.text}")

        # Método 2: Acceso directo por site/drive/path
        hostname, site_name, file_path = _parse_sharepoint_url(filename)

        # Primero obtener el site ID
        site_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_name}"
        logging.info(f"Método 2: Obteniendo site ID desde: {site_url}")

        site_response = requests.get(site_url, headers=headers, verify=False)

        if site_response.status_code != 200:
            logging.error(f"No se pudo obtener el site. Status: {site_response.status_code}")
            logging.error(f"Respuesta: {site_response.text}")
            raise ValueError(f"No se pudo acceder al sitio de SharePoint: {site_response.text}")

        site_data = site_response.json()
        site_id = site_data.get('id')
        logging.info(f"Site ID obtenido: {site_id}")

        # Obtener el drive (biblioteca de documentos)
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        logging.info(f"Obteniendo drives desde: {drives_url}")

        drives_response = requests.get(drives_url, headers=headers, verify=False)

        if drives_response.status_code != 200:
            logging.error(f"No se pudo obtener drives. Status: {drives_response.status_code}")
            raise ValueError(f"No se pudo obtener los drives del sitio")

        drives_data = drives_response.json()

        # Buscar el drive correcto (usualmente "Documentos compartidos" o similar)
        drive_id = None
        drives_list = drives_data.get('value', [])

        logging.info(f"Total de drives encontrados: {len(drives_list)}")

        for drive in drives_list:
            drive_name = drive.get('name', 'Sin nombre')
            drive_id_temp = drive.get('id')
            logging.info(f"Drive encontrado: '{drive_name}' - ID: {drive_id_temp}")

            # Buscar el drive que contiene la ruta del archivo
            # Normalmente es "Documentos" o "Documents"
            if 'Documentos' in file_path or 'Documents' in file_path:
                if 'Documentos' in drive_name or 'Documents' in drive_name or not drive_id:
                    drive_id = drive_id_temp
            else:
                drive_id = drive_id_temp

        if not drive_id:
            logging.error(f"Drives disponibles: {[d.get('name') for d in drives_list]}")
            raise ValueError(f"No se encontró ningún drive en el sitio. Drives disponibles: {len(drives_list)}")

        # Construir la ruta relativa del archivo
        # La ruta debe ser relativa al drive
        path_parts = file_path.split('/')
        # Encontrar donde empieza la ruta después del nombre del drive
        if 'Documentos' in file_path:
            doc_index = None
            for i, part in enumerate(path_parts):
                if 'Documentos' in part or 'Documents' in part:
                    doc_index = i
                    break
            if doc_index:
                relative_path = '/'.join(path_parts[doc_index + 1:])
            else:
                relative_path = '/'.join(path_parts[-3:])  # Últimos 3 componentes
        else:
            relative_path = '/'.join(path_parts[-3:])

        logging.info(f"Ruta relativa del archivo: {relative_path}")

        # Intentar acceder al archivo por ruta
        file_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{relative_path}:/content"
        logging.info(f"Accediendo al archivo en: {file_url}")

        file_response = requests.get(file_url, headers=headers, stream=True, verify=False)

        if file_response.status_code != 200:
            logging.error(f"No se pudo acceder al archivo. Status: {file_response.status_code}")
            logging.error(f"Respuesta: {file_response.text}")
            raise ValueError(f"No se pudo descargar el archivo: {file_response.text}")

        file_content = b''
        for chunk in file_response.iter_content(chunk_size=chunk_size):
            if chunk:
                file_content += chunk

        logging.info("Archivo descargado exitosamente usando método alternativo")
        return file_content

    except Exception as e:
        logging.error(f"Error en _download_sharepoint_file_chunked: {e}")
        raise

def _read_file_from_sharepoint(filename: str) -> pd.DataFrame:
    """Leer archivo Excel desde SharePoint"""
    file_content_bytes = _download_sharepoint_file_chunked(filename)
    return pd.read_excel(io.BytesIO(file_content_bytes))

def _upload_file_to_sharepoint(filename: str, file_path: str) -> bool:
    """Subir archivo a SharePoint usando método directo"""
    auth = get_sharepoint_authenticator()
    if not auth:
        raise ValueError("Autenticador SharePoint no disponible")

    access_token = auth.get_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        # Intentar primero con el método de sharing (actual)
        sharepoint_url_bytes = filename.encode('utf-8')
        encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')
        graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/root/content"

        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        logging.info(f"Upload Método 1: Intentando subir via sharing URL")

        with open(file_path, 'rb') as file:
            response = requests.put(graph_url, headers=upload_headers, data=file, verify=False)

        if response.status_code in [200, 201]:
            logging.info("Archivo subido exitosamente usando método de sharing")
            return True

        # Si falla, intentar método alternativo
        logging.warning(f"Upload Método 1 falló con status {response.status_code}. Intentando método alternativo...")
        logging.warning(f"Respuesta: {response.text}")

        # Método 2: Acceso directo por site/drive/path
        hostname, site_name, file_path_url = _parse_sharepoint_url(filename)

        # Obtener el site ID
        site_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_name}"
        logging.info(f"Upload Método 2: Obteniendo site ID desde: {site_url}")

        site_response = requests.get(site_url, headers=headers, verify=False)

        if site_response.status_code != 200:
            logging.error(f"No se pudo obtener el site. Status: {site_response.status_code}")
            raise ValueError(f"No se pudo acceder al sitio de SharePoint")

        site_data = site_response.json()
        site_id = site_data.get('id')

        # Obtener el drive
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        drives_response = requests.get(drives_url, headers=headers, verify=False)

        if drives_response.status_code != 200:
            raise ValueError(f"No se pudo obtener los drives del sitio")

        drives_data = drives_response.json()

        # Buscar el drive correcto
        drive_id = None
        drives_list = drives_data.get('value', [])

        logging.info(f"Upload: Total de drives encontrados: {len(drives_list)}")

        for drive in drives_list:
            drive_name = drive.get('name', 'Sin nombre')
            drive_id_temp = drive.get('id')
            logging.info(f"Upload: Drive encontrado: '{drive_name}' - ID: {drive_id_temp}")

            if 'Documentos' in file_path_url or 'Documents' in file_path_url:
                if 'Documentos' in drive_name or 'Documents' in drive_name or not drive_id:
                    drive_id = drive_id_temp
            else:
                drive_id = drive_id_temp

        if not drive_id:
            logging.error(f"Upload: Drives disponibles: {[d.get('name') for d in drives_list]}")
            raise ValueError(f"No se encontró ningún drive en el sitio. Drives disponibles: {len(drives_list)}")

        # Construir la ruta relativa del archivo
        path_parts = file_path_url.split('/')
        if 'Documentos' in file_path_url:
            doc_index = None
            for i, part in enumerate(path_parts):
                if 'Documentos' in part or 'Documents' in part:
                    doc_index = i
                    break
            if doc_index:
                relative_path = '/'.join(path_parts[doc_index + 1:])
            else:
                relative_path = '/'.join(path_parts[-3:])
        else:
            relative_path = '/'.join(path_parts[-3:])

        logging.info(f"Subiendo archivo a ruta relativa: {relative_path}")

        # Subir el archivo
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{relative_path}:/content"
        logging.info(f"Upload URL: {upload_url}")

        upload_headers_alt = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        with open(file_path, 'rb') as file:
            upload_response = requests.put(upload_url, headers=upload_headers_alt, data=file, verify=False)

        if upload_response.status_code not in [200, 201]:
            logging.error(f"No se pudo subir el archivo. Status: {upload_response.status_code}")
            logging.error(f"Respuesta: {upload_response.text}")
            raise ValueError(f"No se pudo subir el archivo: {upload_response.text}")

        logging.info("Archivo subido exitosamente usando método alternativo")
        return True

    except Exception as e:
        logging.error(f"Error en _upload_file_to_sharepoint: {e}")
        raise

def load_declaration_to_sharepoint(team_member: str, declaration_text: str) -> Dict[str, Any]:
    """Cargar una declaración al archivo Excel de SharePoint"""
    try:
        # Obtener la configuración del integrante
        if not config_parser.has_section('TeamMembers'):
            raise ValueError("Sección [TeamMembers] no encontrada en config.ini")

        if not config_parser.has_option('TeamMembers', team_member):
            raise ValueError(f"Integrante '{team_member}' no encontrado en la configuración")

        excel_url = config_parser.get('TeamMembers', team_member)
        logging.info(f"URL configurada para {team_member}: {excel_url}")

        # Autenticar con SharePoint
        auth = get_sharepoint_authenticator()
        if not auth:
            raise ValueError("Autenticador SharePoint no disponible")

        access_token = auth.get_token()

        # Leer el archivo Excel actual desde SharePoint
        logging.info(f"Leyendo archivo SharePoint para {team_member}: {excel_url}")
        df = _read_file_from_sharepoint(excel_url)
        logging.info(f"Archivo leído. Filas: {len(df)}, Columnas: {list(df.columns) if not df.empty else 'vacío'}")

        # Preparar la nueva declaración
        declaration_lines = [line.strip() for line in declaration_text.split('\n') if line.strip()]
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_user = team_member.replace('_', ' ').title()

        # Crear DataFrame con la nueva declaración
        declaration_data = {
            'EAN_HIJO': declaration_lines,
            'Fecha': [current_time] * len(declaration_lines),
            'Usuario': [current_user] * len(declaration_lines)
        }

        new_declaration_df = pd.DataFrame(declaration_data)

        # Si el archivo está vacío o no tiene la estructura esperada, crear uno nuevo
        if df.empty or 'EAN_HIJO' not in df.columns:
            df = new_declaration_df
        else:
            df = pd.concat([df, new_declaration_df], ignore_index=True)

        # Guardar archivo temporal
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"declaration_{team_member}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(temp_file, index=False)

        # Subir a SharePoint
        sharepoint_url_bytes = excel_url.encode('utf-8')
        encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')

        graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/root/content"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        with open(temp_file, 'rb') as file:
            response = requests.put(graph_url, headers=headers, data=file, verify=False)

        # Limpiar archivo temporal
        os.remove(temp_file)

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "message": f"Declaración cargada exitosamente para {team_member}"
            }
        else:
            return {
                "success": False,
                "message": f"Error al subir archivo: {response.status_code} - {response.text}"
            }

    except Exception as e:
        logging.error(f"Error cargando declaración: {e}")
        return {
            "success": False,
            "message": f"Error interno: {str(e)}"
        }

def load_rejection_to_sharepoint(team_member: str, rejection_text: str, rejection_obs: str) -> Dict[str, Any]:
    """Cargar un rechazo al archivo Excel de SharePoint"""
    try:
        # Obtener la configuración del integrante para rechazos
        if not config_parser.has_section('TeamMembersReject'):
            raise ValueError("Sección [TeamMembersReject] no encontrada en config.ini")

        if not config_parser.has_option('TeamMembersReject', team_member):
            raise ValueError(f"Integrante '{team_member}' no encontrado en la configuración de rechazos")

        excel_url = config_parser.get('TeamMembersReject', team_member)
        logging.info(f"URL configurada para rechazo {team_member}: {excel_url}")

        # Autenticar con SharePoint
        auth = get_sharepoint_authenticator()
        if not auth:
            raise ValueError("Autenticador SharePoint no disponible")

        access_token = auth.get_token()

        # Leer el archivo Excel actual desde SharePoint
        logging.info(f"Leyendo archivo SharePoint para rechazo {team_member}: {excel_url}")
        df = _read_file_from_sharepoint(excel_url)

        # Preparar el nuevo rechazo
        rejection_lines = [line.strip() for line in rejection_text.split('\n') if line.strip()]
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_user = team_member.replace('_', ' ').title()

        # Crear DataFrame con el nuevo rechazo
        rejection_data = {
            'EAN_HIJO': rejection_lines,
            'Observacion': [rejection_obs] * len(rejection_lines),
            'Fecha': [current_time] * len(rejection_lines),
            'Usuario': [current_user] * len(rejection_lines)
        }

        new_rejection_df = pd.DataFrame(rejection_data)

        # Si el archivo está vacío o no tiene la estructura esperada, crear uno nuevo
        if df.empty or 'EAN_HIJO' not in df.columns:
            df = new_rejection_df
        else:
            df = pd.concat([df, new_rejection_df], ignore_index=True)

        # Guardar archivo temporal
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"rejection_{team_member}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(temp_file, index=False)

        # Subir a SharePoint
        sharepoint_url_bytes = excel_url.encode('utf-8')
        encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')

        graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/root/content"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        with open(temp_file, 'rb') as file:
            response = requests.put(graph_url, headers=headers, data=file, verify=False)

        # Limpiar archivo temporal
        os.remove(temp_file)

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "message": f"Rechazo cargado exitosamente para {team_member}"
            }
        else:
            return {
                "success": False,
                "message": f"Error al subir archivo: {response.status_code} - {response.text}"
            }

    except Exception as e:
        logging.error(f"Error cargando rechazo: {e}")
        return {
            "success": False,
            "message": f"Error interno: {str(e)}"
        }

def load_pending_design_to_sharepoint(team_member: str, pending_design_text: str, country: str = 'chile') -> Dict[str, Any]:
    """Cargar un diseño pendiente usando S3 como backend de almacenamiento

    Args:
        team_member: ID del miembro del equipo
        pending_design_text: Texto con los EAN a declarar
        country: País ('chile' o 'peru'), default 'chile'
    """
    try:
        # Determinar la sección de configuración según el país
        config_section = 'TeamMembersPendingDesignPeru' if country.lower() == 'peru' else 'TeamMembersPendingDesign'

        # Obtener la configuración del integrante para diseño pendiente
        if not config_parser.has_section(config_section):
            raise ValueError(f"Sección [{config_section}] no encontrada en config.ini")

        if not config_parser.has_option(config_section, team_member):
            raise ValueError(f"Integrante '{team_member}' no encontrado en la configuración de diseño pendiente para {country.upper()}")

        # La URL ahora es una key de S3
        s3_key = config_parser.get(config_section, team_member)
        logging.info(f"S3 key configurada para diseño pendiente {country.upper()} {team_member}: {s3_key}")

        # Leer el archivo Excel actual desde S3
        logging.info(f"Leyendo archivo desde S3 para diseño pendiente {team_member}: {s3_key}")
        df = _read_file_from_s3(s3_key)

        # Obtener EANs existentes para verificar duplicados
        existing_eans = set()
        if not df.empty and 'EAN_HIJO' in df.columns:
            existing_eans = set(df['EAN_HIJO'].astype(str).tolist())

        # Preparar el nuevo diseño pendiente, filtrando duplicados
        pending_design_lines = [line.strip() for line in pending_design_text.split('\n') if line.strip()]
        # Filtrar solo los valores que NO existen en el archivo actual
        unique_pending_lines = [line for line in pending_design_lines if line not in existing_eans]

        # Solo procesar si hay valores únicos para agregar
        if unique_pending_lines:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_user = team_member.replace('_', ' ').title()

            # Crear DataFrame con el nuevo diseño pendiente (solo valores únicos)
            pending_design_data = {
                'EAN_HIJO': unique_pending_lines,
                'Fecha': [current_time] * len(unique_pending_lines),
                'Usuario': [current_user] * len(unique_pending_lines)
            }

            new_pending_design_df = pd.DataFrame(pending_design_data)

            # Si el archivo está vacío o no tiene la estructura esperada, crear uno nuevo
            if df.empty or 'EAN_HIJO' not in df.columns:
                df = new_pending_design_df
            else:
                df = pd.concat([df, new_pending_design_df], ignore_index=True)

            # Guardar archivo temporal
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"pending_design_{team_member}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            df.to_excel(temp_file, index=False)

            # Subir a S3
            _upload_file_to_s3(s3_key, temp_file)

            # Limpiar archivo temporal
            os.remove(temp_file)

        return {
            "success": True,
            "message": f"Diseño pendiente {country.upper()} cargado exitosamente para {team_member}"
        }

    except Exception as e:
        logging.error(f"Error cargando diseño pendiente: {e}")
        return {
            "success": False,
            "message": f"Error interno: {str(e)}"
        }

# Rutas principales

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Servir la página principal"""
    try:
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Página no encontrada")
    except Exception as e:
        logger.error("Error sirviendo index: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor") from e

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {
        "status": "ok",
        "service": "prod_peru",
        "message": "Producción PERÚ backend funcionando correctamente"
    }

# API Endpoints

@app.get("/api/users")
async def get_users():
    """Obtener lista de usuarios disponibles"""
    try:
        # Obtener usuarios desde configuración local
        team_members = get_team_members()

        # Filtrar solo usuarios que están en la lista de usuarios válidos
        available_users = [
            user for user in team_members
            if user['member_id'] in VALID_USERS
        ]

        return {"users": available_users}

    except Exception as e:
        logger.error("Error obteniendo usuarios: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo lista de usuarios") from e

@app.get("/api/auth/login")
async def auth_login_direct(request: Request):
    """
    Autentica un usuario usando MSAL interactivo sin requerir selección previa.
    Abre una ventana del navegador para autenticación de Microsoft y
    extrae el username del email autenticado.
    """
    try:
        # Obtener servicio de autenticación
        auth_svc = get_auth_service()
        if not auth_svc:
            raise HTTPException(status_code=500, detail="Servicio de autenticación no disponible")

        # Autenticar usuario (abre popup de Microsoft)
        result = auth_svc.authenticate()

        if not result.get('success'):
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error en autenticación: {error_msg}")
            # Redirigir al frontend con error
            return RedirectResponse(
                url=f"/prod_peru/?auth_error={error_msg}",
                status_code=302
            )

        # Obtener username del resultado
        username = result.get('username')

        # Validar que el usuario esté autorizado
        if username not in VALID_USERS:
            logger.warning(f"Usuario no autorizado intentó acceder: {username}")
            return RedirectResponse(
                url=f"/prod_peru/?auth_error=Usuario no autorizado para acceder a esta aplicación",
                status_code=302
            )

        # Autenticación exitosa - redirigir con token
        token = result.get('token')

        logger.info(f"Autenticación exitosa para: {username}")

        # Redirigir al frontend con el token
        return RedirectResponse(
            url=f"/prod_peru/?auth_token={token}&auth_user={username}",
            status_code=302
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error iniciando autenticación: %s", e)
        raise HTTPException(status_code=500, detail=f"Error en autenticación: {str(e)}") from e

@app.get("/api/auth/login/{username}")
async def auth_login(username: str, request: Request):
    """
    Autentica un usuario usando MSAL interactivo.
    Abre una ventana del navegador para autenticación de Microsoft.
    """
    try:
        # Validar que el usuario existe
        if username not in VALID_USERS:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Obtener servicio de autenticación
        auth_svc = get_auth_service()
        if not auth_svc:
            raise HTTPException(status_code=500, detail="Servicio de autenticación no disponible")

        # Autenticar usuario (abre popup de Microsoft)
        result = auth_svc.authenticate_user(username)

        if not result.get('success'):
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error en autenticación: {error_msg}")
            # Redirigir al frontend con error
            return RedirectResponse(
                url=f"/prod_peru/?auth_error={error_msg}",
                status_code=302
            )

        # Autenticación exitosa - redirigir con token
        token = result.get('token')

        logger.info(f"Autenticación exitosa para: {username}")

        # Redirigir al frontend con el token
        return RedirectResponse(
            url=f"/prod_peru/?auth_token={token}&auth_user={username}",
            status_code=302
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error iniciando autenticación: %s", e)
        raise HTTPException(status_code=500, detail=f"Error en autenticación: {str(e)}") from e


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """
    Obtiene la información del usuario autenticado actual.
    Requiere token JWT en el header Authorization.
    """
    try:
        username = get_current_user_from_token(request)

        # Obtener información del usuario desde configuración local
        team_members = get_team_members()
        user_info = next((user for user in team_members if user['member_id'] == username), None)

        if not user_info:
            raise HTTPException(status_code=404, detail="Usuario no encontrado en configuración")

        # Agregar nombre real y género al objeto user_info
        user_info_with_real_name = user_info.copy()
        user_data = USER_INFO.get(username, {})
        user_info_with_real_name["real_name"] = user_data.get('name', user_info.get('display_name', username))
        user_info_with_real_name["gender"] = user_data.get('gender', 'male')
        user_info_with_real_name["has_pending_design_access"] = has_pending_design_access(username)

        return {
            "success": True,
            "user": user_info_with_real_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo usuario actual: %s", e)
        raise HTTPException(status_code=500, detail="Error obteniendo información del usuario") from e


@app.post("/api/auth/logout")
async def logout(request: Request):
    """
    Cierra la sesión del usuario.
    Con JWT stateless, solo confirmamos que el token era válido.
    """
    try:
        username = get_current_user_from_token(request)
        logger.info(f"Logout para usuario: {username}")

        return {
            "success": True,
            "message": "Sesión cerrada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en logout: %s", e)
        raise HTTPException(status_code=500, detail="Error cerrando sesión") from e

@app.post("/api/load-declaration")
async def load_declaration(declaration_request: DeclarationRequest, request: Request):
    """Cargar declaración del usuario autenticado"""
    try:
        # Validar token JWT y obtener usuario
        authenticated_user = get_current_user_from_token(request)

        # Verificar que el usuario del token coincida con el request
        if declaration_request.team_member != authenticated_user:
            raise HTTPException(status_code=403, detail="No puedes cargar declaraciones para otro usuario")

        # Cargar declaración
        result = load_declaration_to_sharepoint(
            declaration_request.team_member,
            declaration_request.declaration_text
        )

        if result.get('success', False):
            logger.info("Declaración cargada para usuario: %s", declaration_request.team_member)
            return {
                "success": True,
                "message": result.get('message', 'Declaración cargada exitosamente')
            }

        return {
            "success": False,
            "message": result.get('message', 'Error al cargar la declaración')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cargando declaración: %s", e)
        raise HTTPException(status_code=500, detail="Error al procesar la declaración") from e

@app.post("/api/load-rejection")
async def load_rejection(rejection_request: RejectionRequest, request: Request):
    """Cargar rechazo del usuario autenticado"""
    try:
        # Validar token JWT y obtener usuario
        authenticated_user = get_current_user_from_token(request)

        # Verificar que el usuario del token coincida con el request
        if rejection_request.team_member != authenticated_user:
            raise HTTPException(status_code=403, detail="No puedes cargar rechazos para otro usuario")

        # Cargar rechazo
        result = load_rejection_to_sharepoint(
            rejection_request.team_member,
            rejection_request.rejection_text,
            rejection_request.rejection_obs
        )

        if result.get('success', False):
            logger.info("Rechazo cargado para usuario: %s", rejection_request.team_member)
            return {
                "success": True,
                "message": result.get('message', 'Rechazo cargado exitosamente')
            }

        return {
            "success": False,
            "message": result.get('message', 'Error al cargar el rechazo')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cargando rechazo: %s", e)
        raise HTTPException(status_code=500, detail="Error al procesar el rechazo") from e

@app.post("/api/load-pending-design")
async def load_pending_design(pending_design_request: PendingDesignRequest, request: Request):
    """Cargar diseño pendiente CHILE del usuario autenticado"""
    try:
        # Validar token JWT y obtener usuario
        authenticated_user = get_current_user_from_token(request)

        # Verificar que el usuario del token coincida con el request
        if pending_design_request.team_member != authenticated_user:
            raise HTTPException(status_code=403, detail="No puedes cargar diseño pendiente para otro usuario")

        # Verificar que el usuario tenga acceso a diseño pendiente
        if not has_pending_design_access(pending_design_request.team_member):
            raise HTTPException(status_code=403, detail="Usuario no tiene acceso a diseño pendiente")

        # Cargar diseño pendiente para Chile
        result = load_pending_design_to_sharepoint(
            pending_design_request.team_member,
            pending_design_request.pending_design_text,
            country='chile'
        )

        if result.get('success', False):
            logger.info("Diseño pendiente CHILE cargado para usuario: %s", pending_design_request.team_member)
            return {
                "success": True,
                "message": result.get('message', 'Diseño pendiente cargado exitosamente')
            }

        return {
            "success": False,
            "message": result.get('message', 'Error al cargar el diseño pendiente')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cargando diseño pendiente: %s", e)
        raise HTTPException(status_code=500, detail="Error al procesar el diseño pendiente") from e

@app.post("/api/load-pending-design-peru")
async def load_pending_design_peru(pending_design_request: PendingDesignRequest, request: Request):
    """Cargar diseño pendiente PERU del usuario autenticado"""
    try:
        # Validar token JWT y obtener usuario
        authenticated_user = get_current_user_from_token(request)

        # Verificar que el usuario del token coincida con el request
        if pending_design_request.team_member != authenticated_user:
            raise HTTPException(status_code=403, detail="No puedes cargar diseño pendiente para otro usuario")

        # Verificar que el usuario tenga acceso a diseño pendiente
        if not has_pending_design_access(pending_design_request.team_member):
            raise HTTPException(status_code=403, detail="Usuario no tiene acceso a diseño pendiente")

        # Cargar diseño pendiente para Peru
        result = load_pending_design_to_sharepoint(
            pending_design_request.team_member,
            pending_design_request.pending_design_text,
            country='peru'
        )

        if result.get('success', False):
            logger.info("Diseño pendiente PERU cargado para usuario: %s", pending_design_request.team_member)
            return {
                "success": True,
                "message": result.get('message', 'Diseño pendiente cargado exitosamente')
            }

        return {
            "success": False,
            "message": result.get('message', 'Error al cargar el diseño pendiente')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cargando diseño pendiente Peru: %s", e)
        raise HTTPException(status_code=500, detail="Error al procesar el diseño pendiente") from e

# Manejadores de errores

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Manejador de errores 404"""
    return {
        "error": "Endpoint no encontrado",
        "detail": exc.detail,
        "status_code": 404
    }

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Manejador de errores 500"""
    return {
        "error": "Error interno del servidor",
        "detail": exc.detail,
        "status_code": 500
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)