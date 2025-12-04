"""SharePoint authentication module using MSAL."""

# Standard library
import logging
import threading
from typing import Optional

# Third-party
import msal

class SharePointAuth:
    """Handles SharePoint authentication using Microsoft Authentication Library (MSAL).

    Uses in-memory token caching to avoid multiple authentication prompts during
    a session, while ensuring tokens are not persisted to disk.
    """

    # Azure CLI public client ID
    CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
    AUTHORITY = "https://login.microsoftonline.com/common"
    SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(self) -> None:
        """Initialize SharePoint authentication with in-memory token caching."""
        self._token_cache = msal.SerializableTokenCache()  # In-memory only, not persisted
        self._auth_lock = threading.Lock()  # Prevent concurrent interactive auth
        self.app = self._create_msal_app()

    def _create_msal_app(self) -> msal.PublicClientApplication:
        """Create MSAL public client application with in-memory cache."""
        return msal.PublicClientApplication(
            self.CLIENT_ID,
            authority=self.AUTHORITY,
            token_cache=self._token_cache,  # Use in-memory cache
            verify=False
        )

    def get_token(self) -> str:
        """Get access token, trying silent acquisition first.

        Returns cached token if available and valid, otherwise prompts
        for interactive authentication (opens browser once per session).
        """
        # First, try to get token silently from cache
        accounts = self.app.get_accounts()
        if accounts:
            # Try silent acquisition with the first account
            result = self.app.acquire_token_silent(
                self.SCOPES,
                account=accounts[0]
            )
            if result and "access_token" in result:
                logging.debug("Token obtenido silenciosamente desde caché")
                return result["access_token"]

        # No cached token available, need interactive auth
        # Use lock to prevent multiple browser tabs
        with self._auth_lock:
            # Double-check after acquiring lock (another thread might have authenticated)
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(
                    self.SCOPES,
                    account=accounts[0]
                )
                if result and "access_token" in result:
                    logging.debug("Token obtenido silenciosamente después de lock")
                    return result["access_token"]

            # Perform interactive authentication
            logging.info("Iniciando autenticación interactiva de SharePoint...")
            result = self._try_interactive_acquisition()
            return self._extract_token(result)

    def _try_interactive_acquisition(self) -> dict:
        """Perform interactive token acquisition."""
        # prompt="login" forces full credential entry, ignoring browser sessions
        result = self.app.acquire_token_interactive(
            self.SCOPES,
            prompt="login"
        )
        return result

    def _extract_token(self, result: dict) -> str:
        """Extract access token from MSAL result."""
        if "access_token" in result:
            return result["access_token"]

        error_msg = result.get("error_description", "No se pudo adquirir un token.")
        raise Exception(error_msg)

# Instancia global para usar en toda la aplicación
_auth_instance = None

def get_valid_token() -> Optional[dict]:
    """
    Función compatible con el código existente del backend.
    Retorna información del token en formato dict.
    """
    global _auth_instance

    if _auth_instance is None:
        _auth_instance = SharePointAuth()

    try:
        access_token = _auth_instance.get_token()
        return {
            'access_token': access_token,
            'token_type': 'Bearer'
        }
    except Exception as e:
        logging.warning(f"Error obteniendo token de SharePoint: {e}")
        return None


def get_sharepoint_authenticator() -> SharePointAuth:
    """
    Obtiene la instancia única de SharePointAuth (patrón Singleton).
    Reutiliza la misma instancia para mantener la sesión token viva.

    Esta función es utilizada por los módulos async (main_logic_async.py,
    async_sharepoint_service.py) y el código síncrono legacy.

    Returns:
        SharePointAuth: Instancia única del autenticador
    """
    global _auth_instance

    if _auth_instance is None:
        _auth_instance = SharePointAuth()

    return _auth_instance


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
