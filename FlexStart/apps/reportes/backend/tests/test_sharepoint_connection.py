"""
Script de diagnóstico para probar la conexión a SharePoint y listar archivos particionados.
"""
import sys
import os

# Añadir el directorio backend al path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_sharepoint_partitioned_connection():
    """Prueba la conexión a SharePoint y listado de archivos particionados."""

    print("=" * 80)
    print("TEST DE CONEXIÓN SHAREPOINT PARTICIONADO")
    print("=" * 80)

    try:
        # Importar funciones necesarias
        from main_logic import get_sharepoint_authenticator
        from services.storage_utils import list_sharepoint_directory_files, _parse_sharepoint_url

        print("\n1. Autenticación...")
        auth = get_sharepoint_authenticator()
        access_token = auth.get_token()
        print("   [OK] Token obtenido")

        # URLs de prueba desde config.ini
        test_cases = [
            {
                'name': 'C1 PERU',
                'url': 'https://ripleycorp.sharepoint.com/sites/Equipopyc/Documentos%20compartidos/mantenedor/PROYECTO/ARCHIVOS_PRODUCCI%C3%93N/DATA/formato_ppias/',
                'pattern': 'formato_ppias_part*.csv'
            },
            {
                'name': 'UNIVERSO PERU',
                'url': 'https://ripleycorp.sharepoint.com/sites/Equipopyc/Documentos%20compartidos/mantenedor/PROYECTO/ARCHIVOS_PRODUCCI%C3%93N/DATA/sabana/',
                'pattern': 'SABANA_part*.csv'
            }
        ]

        for test_case in test_cases:
            print(f"\n{'='*80}")
            print(f"2. Probando: {test_case['name']}")
            print(f"{'='*80}")

            print(f"   URL: {test_case['url']}")
            print(f"   Patrón: {test_case['pattern']}")

            # Parsear URL
            print("\n   2.1. Parseando URL...")
            site_base, folder_path = _parse_sharepoint_url(test_case['url'])
            print(f"        Site base: {site_base}")
            print(f"        Folder path: {folder_path}")

            # Listar archivos
            print("\n   2.2. Listando archivos...")
            try:
                files = list_sharepoint_directory_files(
                    sharepoint_folder_url=test_case['url'],
                    file_pattern=test_case['pattern'],
                    access_token=access_token
                )

                print(f"        [OK] {len(files)} archivos encontrados:")
                for i, file_info in enumerate(files, 1):
                    size_kb = file_info['size'] / 1024
                    print(f"             {i}. {file_info['name']} ({size_kb:.1f} KB)")

            except Exception as e:
                print(f"        [ERROR] Error listando archivos: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"\n[ERROR FATAL] {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("TEST COMPLETADO")
    print("=" * 80)
    return True

if __name__ == "__main__":
    test_sharepoint_partitioned_connection()
