# -*- coding: utf-8 -*-
"""Login admin solo desde variables de entorno (sin fila en usuarios)."""
from typing import Optional

from app.core.config import settings


def is_configured_env_admin_email(email: Optional[str]) -> bool:
    """
    True si ADMIN_EMAIL esta definido y coincide con el email del token (normalizado).
    Evita elevar a admin sintetico a cualquier JWT con sub desconocido.
    """
    ae = (getattr(settings, "ADMIN_EMAIL", None) or "").strip().lower()
    if not ae:
        return False
    em = (email or "").strip().lower()
    return bool(em) and em == ae
