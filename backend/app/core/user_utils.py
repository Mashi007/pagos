"""
Utilidades para usuario: convertir modelo User a UserResponse (auth/schemas).
Usado por auth, deps y endpoints de usuarios.
"""
from datetime import datetime, timezone
from typing import Optional

from app.models.user import User
from app.schemas.auth import UserResponse


def user_to_response(u: User) -> UserResponse:
    """Convierte modelo User a UserResponse (fechas en ISO)."""
    def _dt_iso(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if getattr(dt, "tzinfo", None):
            return dt.isoformat().replace("+00:00", "Z")
        return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    rol = getattr(u, "rol", None) or ("administrador" if getattr(u, "is_admin", False) else "operativo")
    return UserResponse(
        id=u.id,
        email=u.email,
        nombre=u.nombre or "",
        apellido=u.apellido or "",
        cargo=u.cargo,
        rol=rol,
        is_active=bool(u.is_active),
        created_at=_dt_iso(u.created_at) or "",
        updated_at=_dt_iso(u.updated_at),
        last_login=_dt_iso(u.last_login),
    )
