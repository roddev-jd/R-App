"""
Servicio de autenticación para Prod Peru usando Microsoft Azure AD.
Implementa autenticación interactiva con MSAL y validación de correo corporativo.

Uses in-memory token caching to avoid multiple authentication prompts during
a session, while ensuring tokens are not persisted to disk.
"""

import logging
import secrets
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import msal
import jwt
import requests

logger = logging.getLogger(__name__)

# Constantes de configuración MSAL
# Usamos el mismo Client ID público de Azure CLI que ya funciona en sharepoint_service
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/.default"]


class AuthService:
    """Servicio de autenticación con Microsoft Azure AD."""

    def __init__(self, config_parser):
        """
        Inicializa el servicio de autenticación.

        Args:
            config_parser: ConfigParser con la configuración de la aplicación
        """
        self.config = config_parser
        self._load_auth_config()
        self._pending_auth: Dict[str, Dict[str, Any]] = {}

        # Configurar caché de tokens en memoria (no persistente)
        self._token_cache = msal.SerializableTokenCache()
        self._auth_lock = threading.Lock()  # Prevent concurrent interactive auth

    def _load_auth_config(self):
        """Carga la configuración de autenticación desde config.ini."""
        self.jwt_secret = self.config.get('Auth', 'jwt_secret', fallback=secrets.token_hex(32))
        self.token_expiry_hours = self.config.getint('Auth', 'token_expiry_hours', fallback=8)
        self.domain = self.config.get('Auth', 'domain', fallback='ripley.com')

        logger.info(f"Configuración de auth cargada. Domain: {self.domain}, Expiry: {self.token_expiry_hours}h")

    def _create_msal_app(self) -> msal.PublicClientApplication:
        """Create MSAL public client application with in-memory cache."""
        return msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=self._token_cache,
            verify=False
        )

    def authenticate(self) -> Dict[str, Any]:
        """
        Autentica un usuario usando MSAL interactivo sin requerir username previo.
        Abre una ventana del navegador para autenticación de Microsoft y extrae
        el username del email autenticado.

        Returns:
            Dict con 'success', 'token' (JWT), 'username', 'email' o 'error'
        """
        try:
            app = self._create_msal_app()

            # Try to get token silently from any cached account
            accounts = app.get_accounts()
            result = None

            if accounts:
                # Try silent acquisition with the first account
                result = app.acquire_token_silent(
                    scopes=SCOPES,
                    account=accounts[0]
                )
                if result and "access_token" in result:
                    logger.debug("Token obtenido silenciosamente desde caché")

            # If no cached token, need interactive auth with lock
            if not result or "access_token" not in result:
                with self._auth_lock:
                    # Double-check after acquiring lock
                    accounts = app.get_accounts()
                    if accounts:
                        result = app.acquire_token_silent(
                            scopes=SCOPES,
                            account=accounts[0]
                        )
                        if result and "access_token" in result:
                            logger.debug("Token obtenido silenciosamente después de lock")

                    # Still no token, do interactive auth
                    if not result or "access_token" not in result:
                        logger.info("Iniciando autenticación interactiva...")
                        result = app.acquire_token_interactive(
                            scopes=SCOPES,
                            prompt="login"  # Forces full credential entry
                        )

            if 'error' in result:
                logger.error(f"Error en MSAL: {result.get('error_description', result.get('error'))}")
                return {
                    'success': False,
                    'error': f"Error de autenticación: {result.get('error_description', 'Error desconocido')}"
                }

            if 'access_token' not in result:
                logger.error("No se recibió access_token de Microsoft")
                return {
                    'success': False,
                    'error': 'No se pudo obtener el token de acceso de Microsoft'
                }

            # Obtener información del usuario desde Microsoft Graph
            user_info = self._get_user_info(result['access_token'])

            if not user_info:
                return {
                    'success': False,
                    'error': 'No se pudo obtener la información del usuario'
                }

            # Extraer email del usuario
            user_email = user_info.get('mail') or user_info.get('userPrincipalName', '')
            user_email = user_email.lower()

            # Validar dominio corporativo
            if '@' not in user_email:
                return {
                    'success': False,
                    'error': 'No se pudo obtener el email del usuario'
                }

            email_domain = user_email.split('@')[1]
            if email_domain != self.domain:
                logger.warning(f"Dominio incorrecto. Esperado: {self.domain}, Recibido: {email_domain}")
                return {
                    'success': False,
                    'error': f'Solo se permiten correos corporativos (@{self.domain})'
                }

            # Extraer el username del email autenticado
            username = user_email.split('@')[0]

            # Generar JWT para la sesión
            jwt_token = self._generate_jwt(username, user_email)

            logger.info(f"Autenticación exitosa para: {username} ({user_email})")

            return {
                'success': True,
                'token': jwt_token,
                'username': username,
                'email': user_email,
                'display_name': user_info.get('displayName', username)
            }

        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return {
                'success': False,
                'error': f'Error de autenticación: {str(e)}'
            }

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del usuario desde Microsoft Graph API.

        Args:
            access_token: Token de acceso de Microsoft

        Returns:
            Dict con información del usuario o None si hay error
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers,
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error obteniendo user info: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error en Graph API: {e}")
            return None

    def _generate_jwt(self, username: str, email: str) -> str:
        """
        Genera un token JWT para la sesión del usuario.

        Args:
            username: Nombre de usuario
            email: Email del usuario

        Returns:
            Token JWT codificado
        """
        expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)

        payload = {
            'sub': username,
            'email': email,
            'iat': datetime.utcnow(),
            'exp': expiry,
            'iss': 'prod_peru'
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida un token JWT y retorna los datos del usuario.

        Args:
            token: Token JWT a validar

        Returns:
            Dict con datos del usuario o None si el token es inválido
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=['HS256'],
                issuer='prod_peru'
            )

            return {
                'username': payload.get('sub'),
                'email': payload.get('email'),
                'exp': payload.get('exp')
            }

        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {e}")
            return None

    def invalidate_token(self, token: str) -> bool:
        """
        Invalida un token (para logout).
        Nota: Con JWT stateless, solo podemos validar que el token era válido.
        Para invalidación real, se necesitaría una blacklist.

        Args:
            token: Token a invalidar

        Returns:
            True si el token era válido, False si no
        """
        return self.validate_token(token) is not None

    def _cleanup_old_states(self):
        """Limpia states de autenticación que tienen más de 10 minutos."""
        current_time = time.time()
        expired_states = [
            state for state, data in self._pending_auth.items()
            if current_time - data.get('created_at', 0) > 600  # 10 minutos
        ]

        for state in expired_states:
            del self._pending_auth[state]

        if expired_states:
            logger.debug(f"Limpiados {len(expired_states)} states expirados")


# Instancia global del servicio (se inicializa en app.py)
_auth_service: Optional[AuthService] = None


def get_auth_service() -> Optional[AuthService]:
    """Obtiene la instancia global del servicio de autenticación."""
    return _auth_service


def init_auth_service(config_parser) -> AuthService:
    """
    Inicializa el servicio de autenticación global.

    Args:
        config_parser: ConfigParser con la configuración

    Returns:
        Instancia del AuthService
    """
    global _auth_service
    _auth_service = AuthService(config_parser)
    return _auth_service
