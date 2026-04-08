"""
Utilidades para usuario: convertir modelo User a UserResponse (auth/schemas).
Usado por auth, deps y endpoints de usuarios.
"""
from datetime import datetime, timezone
from typing import Optional

from app.core.rol_normalization import canonical_rol
from app.models.user import User
from app.schemas.auth import UserResponse


def split_nombre_completo_para_api(full: Optional[str]) -> tuple[str, str]:
    """
    Parte nombre completo almacenado en usuarios.nombre (post-migración 041) en
    nombre + apellido para la API (último token = apellido).
    """
    s = (full or "").strip()
    if not s:
        return "", ""
    parts = s.rsplit(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def user_to_response(u: User) -> UserResponse:
    """Convierte modelo User a UserResponse (fechas en ISO)."""
    def _dt_iso(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if getattr(dt, "tzinfo", None):
            return dt.isoformat().replace("+00:00", "Z")
        return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    raw_rol = getattr(u, "rol", None) or (
        "admin" if getattr(u, "is_admin", False) else "viewer"
    )
    rol = canonical_rol(raw_rol)
    nombre_api, apellido_api = split_nombre_completo_para_api(getattr(u, "nombre", None))
    return UserResponse(
        id=u.id,
        email=u.email,
        nombre=nombre_api,
        apellido=apellido_api,
        cargo=u.cargo,
        rol=rol,
        is_active=bool(u.is_active),
        created_at=_dt_iso(u.created_at) or "",
        updated_at=_dt_iso(u.updated_at),
        last_login=_dt_iso(u.last_login),
    )


def user_is_administrator(user: UserResponse) -> bool:
    """True si el usuario tiene rol admin."""
    return canonical_rol(user.rol) == "admin"

