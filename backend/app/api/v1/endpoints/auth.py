"""
Endpoints de autenticación (login, refresh, me)
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserResponse,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.get("/status")
def auth_status():
    """Diagnóstico: indica si auth está configurado (sin revelar datos)."""
    configured = bool(settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD)
    return {
        "auth_configured": configured,
        "message": "Auth configurado. Use POST /api/v1/auth/login." if configured else "Configure ADMIN_EMAIL y ADMIN_PASSWORD en el servidor.",
    }


def _fake_user(email: str) -> UserResponse:
    """Usuario mínimo para auth sin tabla users (admin desde env)."""
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


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """Login con email y contraseña (usuario admin desde env)."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticación no configurada. Configure ADMIN_EMAIL y ADMIN_PASSWORD en el servidor.",
        )
    email = credentials.email.lower().strip()
    if email != settings.ADMIN_EMAIL.lower().strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    hashed = get_password_hash(settings.ADMIN_PASSWORD)
    if not verify_password(credentials.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    user = _fake_user(settings.ADMIN_EMAIL)
    access_token = create_access_token(subject=user.email, extra={"email": user.email})
    refresh_token = create_refresh_token(subject=user.email)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.post("/refresh")
def refresh(body: RefreshRequest):
    """Obtener nuevo access_token desde refresh_token."""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido o expirado",
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    email = sub if "@" in sub else f"{sub}@admin.local"
    user = _fake_user(email)
    access_token = create_access_token(subject=user.email, extra={"email": user.email})
    new_refresh = create_refresh_token(subject=user.email)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Devuelve el usuario actual a partir del Bearer token."""
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
    return _fake_user(email)
