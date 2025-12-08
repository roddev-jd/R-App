"""
Script de diagnóstico para probar el parsing de URLs de SharePoint.
"""
import re
from urllib.parse import unquote

def _parse_sharepoint_url(full_url: str) -> tuple:
    """
    Parsea una URL completa de SharePoint para extraer la URL base del sitio y la carpeta.
    """
    # Decodificar URL
    decoded_url = unquote(full_url)
    print(f"URL original: {full_url}")
    print(f"URL decodificada: {decoded_url}")

    # Extraer hostname y site path
    match = re.match(r'(https://[^/]+/sites/[^/]+)(?:/(.+))?', decoded_url)
    if not match:
        raise ValueError(f"URL de SharePoint inválida: {full_url}")

    site_base_url = match.group(1)
    folder_path = match.group(2) if match.group(2) else 'root'

    # Limpiar slashes finales que pueden causar problemas con Microsoft Graph API
    if folder_path != 'root':
        folder_path = folder_path.rstrip('/')

    print(f"Site base URL: {site_base_url}")
    print(f"Folder path (limpiado): {folder_path}")

    return site_base_url, folder_path

# URLs de prueba desde config.ini
urls_to_test = [
    # C1 PERU
    "https://ripleycorp.sharepoint.com/sites/Equipopyc/Documentos%20compartidos/mantenedor/PROYECTO/ARCHIVOS_PRODUCCI%C3%93N/DATA/formato_ppias/",
    # UNIVERSO PERU
    "https://ripleycorp.sharepoint.com/sites/Equipopyc/Documentos%20compartidos/mantenedor/PROYECTO/ARCHIVOS_PRODUCCI%C3%93N/DATA/sabana/",
]

print("=" * 80)
print("DIAGNÓSTICO DE PARSING DE URLs DE SHAREPOINT")
print("=" * 80)

for i, url in enumerate(urls_to_test, 1):
    print(f"\n--- Test {i} ---")
    try:
        site, folder = _parse_sharepoint_url(url)
        print(f"[OK] Parsing exitoso")
        print(f"   Site: {site}")
        print(f"   Folder: {folder}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    print("-" * 80)
