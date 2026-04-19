"""Identificador de usuario para auditoría en registros de pago."""

from typing import Any, Optional

from .constants import _USUARIO_REGISTRO_FALLBACK


def _usuario_registro_desde_current_user(current_user: Optional[Any]) -> str:
    """
    Email del usuario o identificador estable para auditoría.

    No devuelve cadena vacía (los lotes MER/BNC quedan trazables).
    """
    if current_user is None:
        return _USUARIO_REGISTRO_FALLBACK

    email = getattr(current_user, "email", None)
    if email is None and isinstance(current_user, dict):
        email = current_user.get("email")

    if isinstance(email, str) and email.strip():
        return email.strip()[:255]

    uid = getattr(current_user, "id", None)
    if uid is None and isinstance(current_user, dict):
        uid = current_user.get("id")

    if uid is not None:
        return f"user_id:{uid}@{_USUARIO_REGISTRO_FALLBACK}"[:255]

    return _USUARIO_REGISTRO_FALLBACK
