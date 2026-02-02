"""
Dependencias reutilizables para la API (autenticación, BD).
get_current_user: exige Bearer token válido; se usa en routers protegidos.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.schemas.auth import UserResponse

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    """
    Obtiene el usuario actual a partir del Bearer token.
    Usar como dependencia en routers que requieran autenticación.
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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return UserResponse(
        id=1,
        email=email.lower(),
        nombre="Admin",
        apellido="Sistema",
        cargo="Administrador",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login=now,
    )


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[UserResponse]:
    """
    Usuario actual si hay Bearer token válido; None en caso contrario.
    Útil para endpoints que cambian comportamiento según si hay sesión.
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
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return UserResponse(
        id=1,
        email=email.lower(),
        nombre="Admin",
        apellido="Sistema",
        cargo="Administrador",
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login=now,
    )
