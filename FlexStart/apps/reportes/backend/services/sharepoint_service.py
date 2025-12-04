"""
SharePoint authentication module - Re-export from shared services.

Este módulo re-exporta las funciones de autenticación SharePoint desde el módulo
compartido para mantener compatibilidad con el código existente en Reportes.
"""

import sys
from pathlib import Path

# Agregar el directorio shared/services al path
shared_services_dir = Path(__file__).parent.parent.parent.parent.parent / "shared" / "services"
if str(shared_services_dir) not in sys.path:
    sys.path.insert(0, str(shared_services_dir))

# Re-exportar desde el módulo compartido
from sharepoint_service import (
    SharePointAuth,
    get_valid_token,
    get_sharepoint_authenticator,
    _auth_instance
)

# Mantener compatibilidad con main()
def main() -> None:
    """Example usage."""
    auth = SharePointAuth()
    try:
        token = auth.get_token()
        print("Token adquirido con éxito!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
