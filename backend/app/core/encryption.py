"""
Módulo de encriptación para datos sensibles
Usa Fernet (cryptography) para encriptación simétrica
"""

import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)

# Variable global para la instancia de Fernet
_fernet_instance: Optional[Fernet] = None


def _get_encryption_key() -> bytes:
    """
    Obtiene o genera la clave de encriptación.
    Usa ENCRYPTION_KEY de settings si está disponible, o genera una desde SECRET_KEY.
    """
    # Si hay una ENCRYPTION_KEY configurada, usarla directamente
    if hasattr(settings, "ENCRYPTION_KEY") and settings.ENCRYPTION_KEY:
        encryption_key_str = settings.ENCRYPTION_KEY
        # Si es una cadena, convertirla a bytes
        if isinstance(encryption_key_str, str):
            # Si ya está en formato base64, decodificarla
            try:
                return base64.urlsafe_b64decode(encryption_key_str.encode())
            except Exception:
                # Si no es base64, generar una clave desde SECRET_KEY
                pass

    # Si no hay ENCRYPTION_KEY, generar una desde SECRET_KEY
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY no está configurada. No se puede generar clave de encriptación.")

    # Generar clave desde SECRET_KEY usando PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"rapicredit_encryption_salt",  # Salt fijo para consistencia
        iterations=100000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key


def _get_fernet() -> Fernet:
    """
    Obtiene la instancia de Fernet (singleton).
    """
    global _fernet_instance
    if _fernet_instance is None:
        encryption_key = _get_encryption_key()
        _fernet_instance = Fernet(encryption_key)
    return _fernet_instance


def encrypt_value(value: str) -> str:
    """
    Encripta un valor usando Fernet.

    Args:
        value: Valor en texto plano a encriptar

    Returns:
        Valor encriptado en formato base64 (string)

    Raises:
        ValueError: Si el valor está vacío o None
    """
    if not value or not isinstance(value, str):
        raise ValueError("El valor a encriptar debe ser una cadena no vacía")

    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(value.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        logger.error(f"Error encriptando valor: {e}", exc_info=True)
        raise ValueError(f"Error al encriptar valor: {str(e)}")


def decrypt_value(encrypted_value: str) -> str:
    """
    Desencripta un valor usando Fernet.

    Args:
        encrypted_value: Valor encriptado en formato base64 (string)

    Returns:
        Valor desencriptado (texto plano)

    Raises:
        ValueError: Si el valor no se puede desencriptar (formato inválido o clave incorrecta)
    """
    if not encrypted_value or not isinstance(encrypted_value, str):
        raise ValueError("El valor encriptado debe ser una cadena no vacía")

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        # Si falla la desencriptación, puede ser que el valor no esté encriptado
        # (compatibilidad con valores antiguos)
        logger.warning("No se pudo desencriptar el valor. Puede ser un valor antiguo sin encriptar.")
        # Retornar el valor original (para compatibilidad con datos antiguos)
        return encrypted_value
    except Exception as e:
        logger.error(f"Error desencriptando valor: {e}", exc_info=True)
        # Intentar retornar el valor original si falla (compatibilidad)
        return encrypted_value


def is_encrypted(value: str) -> bool:
    """
    Verifica si un valor está encriptado.

    Args:
        value: Valor a verificar

    Returns:
        True si parece estar encriptado, False en caso contrario
    """
    if not value or not isinstance(value, str):
        return False

    # Los valores encriptados con Fernet empiezan con 'gAAAAAB' (base64)
    # y tienen una longitud mínima
    try:
        # Intentar decodificar como base64
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
        # Si tiene el formato correcto de Fernet (32 bytes de token + datos)
        return len(decoded) > 32 and value.startswith("gAAAAAB")
    except Exception:
        return False


def encrypt_api_key(api_key: str) -> str:
    """
    Encripta una API Key de OpenAI.

    Args:
        api_key: API Key en texto plano

    Returns:
        API Key encriptada
    """
    return encrypt_value(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Desencripta una API Key de OpenAI.
    Si el valor no está encriptado (compatibilidad con datos antiguos), lo retorna tal cual.

    Args:
        encrypted_api_key: API Key encriptada o en texto plano

    Returns:
        API Key desencriptada o en texto plano
    """
    # Si no parece estar encriptado, retornar tal cual (compatibilidad)
    if not is_encrypted(encrypted_api_key):
        return encrypted_api_key

    return decrypt_value(encrypted_api_key)
