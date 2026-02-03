"""
Endpoints de autenticación (login, refresh, me, logout)
"""
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.auth import (
    AdminResetPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserResponse,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Rate limiting en memoria: IP -> lista de timestamps de intentos de login
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_RATE_LIMIT_WINDOW = 60  # segundos
_LOGIN_RATE_LIMIT_MAX = 5  # intentos por ventana


def _require_reset_secret(x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret")) -> None:
    """Exige que X-Admin-Secret coincida con RESET_PASSWORD_SECRET. Solo para uso interno."""
    if not settings.RESET_PASSWORD_SECRET or not settings.RESET_PASSWORD_SECRET.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Configure RESET_PASSWORD_SECRET en el servidor para usar este endpoint.",
        )
    if not x_admin_secret or x_admin_secret.strip() != settings.RESET_PASSWORD_SECRET.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secreto inválido",
        )


@router.post("/admin/reset-password")
def admin_reset_password(
    body: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_reset_secret),
):
    """
    Uso interno: restablece la contraseña del usuario con el email dado
    a la contraseña actual ADMIN_PASSWORD. Así puedes alinear el usuario en BD con Render
    sin tocar la base a mano. Requiere header X-Admin-Secret = RESET_PASSWORD_SECRET.
    """
    if not settings.ADMIN_PASSWORD or not settings.ADMIN_PASSWORD.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ADMIN_PASSWORD no está configurado en el servidor.",
        )
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario con ese email.",
        )
    user.password_hash = get_password_hash(settings.ADMIN_PASSWORD)
    db.commit()
    return {"message": "Contraseña actualizada. El usuario puede iniciar sesión con ADMIN_PASSWORD."}


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
        rol="administrador",
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login=now,
    )


def _get_client_ip(request: Request) -> str:
    """Obtiene la IP del cliente (respeta X-Forwarded-For si está detrás de proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(ip: str) -> None:
    """Lanza 429 si se supera el límite de intentos de login por IP."""
    now = time.time()
    attempts = _LOGIN_ATTEMPTS[ip]
    # Eliminar intentos fuera de la ventana
    attempts[:] = [t for t in attempts if now - t < _LOGIN_RATE_LIMIT_WINDOW]
    if len(attempts) >= _LOGIN_RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesión. Espere un minuto e intente de nuevo.",
        )
    attempts.append(now)


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login con email y contraseña. Primero busca usuario en BD; si no existe, usa admin desde env."""
    client_ip = _get_client_ip(request)
    _check_login_rate_limit(client_ip)

    email = credentials.email.lower().strip()

    # 1) Buscar usuario en BD
    u = db.query(User).filter(User.email == email).first()
    if u:
        if not u.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )
        if not verify_password(credentials.password, u.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )
        _LOGIN_ATTEMPTS[client_ip] = []
        u.last_login = datetime.utcnow()
        db.commit()
        db.refresh(u)
        user = user_to_response(u)
        access_token = create_access_token(subject=user.email, extra={"email": user.email})
        refresh_token = create_refresh_token(subject=user.email)
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
        )

    # 2) Fallback: admin desde env
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    admin_email_normalized = settings.ADMIN_EMAIL.lower().strip()
    hashed = get_password_hash(settings.ADMIN_PASSWORD)
    password_ok = verify_password(credentials.password, hashed)
    email_ok = email == admin_email_normalized

    if not (email_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    _LOGIN_ATTEMPTS[client_ip] = []
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


@router.post("/logout")
def logout():
    """Cierre de sesión. El cliente debe eliminar tokens localmente. Respuesta 200 para coherencia."""
    return {"message": "Sesión cerrada"}


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
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
    u = db.query(User).filter(User.email == email).first()
    if u and u.is_active:
        user = user_to_response(u)
    else:
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
def me(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """Devuelve el usuario actual a partir del Bearer token (desde BD o admin env)."""
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
    return _fake_user(email)
