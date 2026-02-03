"""
Dependencias reutilizables para la API (autenticación, BD).
get_current_user: exige Bearer token válido; se usa en routers protegidos.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.auth import UserResponse

security = HTTPBearer(auto_error=True)


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
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    email = sub if "@" in sub else f"{sub}@admin.local"
    u = db.query(User).filter(User.email == email).first()
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)


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
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        return None
    email = sub if "@" in sub else f"{sub}@admin.local"
    u = db.query(User).filter(User.email == email).first()
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)
