"""
Dependencias reutilizables para la API (autenticación, BD).
get_current_user: exige Bearer token válido; se usa en routers protegidos.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.core.user_utils import user_to_response
from app.models.finiquito import FiniquitoUsuarioAcceso
from app.models.user import User
from app.schemas.auth import UserResponse

security = HTTPBearer(auto_error=True)
security_optional_bearer = HTTPBearer(auto_error=False)


def _fake_user_response(email: str) -> UserResponse:
    """Usuario mínimo cuando no existe en BD (admin desde env)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return UserResponse(
        id=1,
        email=email.lower(),
        nombre="Admin",
        apellido="Sistema",
        cargo="Administrador",
        rol="administrador",
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login=now,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Obtiene el usuario actual a partir del Bearer token (desde BD o admin env).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token",
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    if payload.get("scope") == "finiquito":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Use el token solo en el portal Finiquito",
        )
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)


def require_administrador(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Solo rol administrador (portal interno)."""
    if (current.rol or "").lower() != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden acceder a este recurso.",
        )
    return current


def get_finiquito_usuario_acceso(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional_bearer),
    db: Session = Depends(get_db),
) -> FiniquitoUsuarioAcceso:
    """
    Usuario del portal Finiquito (JWT con scope=finiquito, sub=id en finiquito_usuario_acceso).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token",
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    if payload.get("scope") != "finiquito":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido para el portal Finiquito",
        )
    sub = payload.get("sub")
    if sub is None or str(sub).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    u = (
        db.query(FiniquitoUsuarioAcceso)
        .filter(
            FiniquitoUsuarioAcceso.id == uid,
            FiniquitoUsuarioAcceso.is_active.is_(True),
        )
        .first()
    )
    if not u:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario Finiquito inactivo o inexistente",
        )
    return u


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[UserResponse]:
    """
    Usuario actual si hay Bearer token válido; None en caso contrario.
    """
    if not credentials or not credentials.credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    if payload.get("scope") == "finiquito":
        return None
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        return None
    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)
