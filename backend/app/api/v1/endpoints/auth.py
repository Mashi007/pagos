# backend/app/api/v1/endpoints/auth.py
"""Endpoints de autenticación - VERSIÓN SIMPLIFICADA SIN AUDITORÍA
Solución temporal para resolver error 503
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.auditoria import Auditoria
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
)
from app.schemas.user import UserMeResponse
from app.services.auth_service import AuthService
from app.utils.validators import validate_password_strength

logger = logging.getLogger(__name__)
router = APIRouter()


def add_cors_headers(request: Request, response: Response):
    """Agregar headers CORS manualmente"""
    origin = request.headers.get("origin")

    if origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        logger.info(f"CORS Debug - Origin permitido: {origin}")
    else:
        logger.warning(f"CORS Debug - Origin NO permitido: {origin}")
        # En caso de origin no permitido, usar el primer origin válido
        if settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = settings.CORS_ORIGINS[0]
            logger.info(f"CORS Debug - Usando origin por defecto: {settings.CORS_ORIGINS[0]}")

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"


def _obtener_info_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extrae IP y User-Agent de la request"""
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    return (ip, ua)


def _registrar_auditoria_login(
    db: Session, request: Request, usuario_id: int, exito: bool, entidad_id: Optional[int] = None
) -> None:
    """Registra auditoría de login sin bloquear el proceso"""
    try:
        ip, ua = _obtener_info_request(request)
        detalles = "Inicio de sesión" if exito else "Intento de login fallido"
        audit = Auditoria(
            usuario_id=usuario_id,
            accion="LOGIN",
            entidad="USUARIOS",
            entidad_id=entidad_id,
            detalles=detalles,
            ip_address=ip,
            user_agent=ua,
            exito=exito,
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        tipo = "LOGIN" if exito else "LOGIN FALLIDO"
        logger.warning(f"No se pudo registrar auditoría {tipo}: {e}")


def _generar_tokens_usuario(user_id: int) -> tuple[str, str]:
    """Genera access token y refresh token para el usuario"""
    access_token = create_access_token(subject=str(user_id))
    refresh_token = create_access_token(subject=str(user_id), expires_delta=timedelta(days=7))
    return (access_token, refresh_token)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    🔐 Login de usuario - VERSIÓN SIMPLIFICADA
    Características:
    - Sin auditoría (temporal)
    - Sin rate limiting (temporal)
    - Solo autenticación básica
    - Headers CORS
    """
    try:
        logger.info(f"Intento de login para: {login_data.email}")

        # Agregar headers CORS
        add_cors_headers(request, response)

        # Autenticar usuario
        user = AuthService.authenticate_user(db, login_data.email, login_data.password)

        if not user:
            logger.warning(f"Login fallido para: {login_data.email}")
            _registrar_auditoria_login(db, request, 0, False)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrecto")

        # Generar tokens
        user_id = int(user.id)
        access_token, refresh_token = _generar_tokens_usuario(user_id)

        logger.info(f"Login exitoso para: {login_data.email}")
        _registrar_auditoria_login(db, request, user_id, True, user_id)

        # Preparar información del usuario para la respuesta
        user_info = {
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "rol": user.rol,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
        }

        # Calcular tiempo de expiración en segundos (4 horas = 240 minutos)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 14400 segundos (4 horas)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_info,
            expires_in=expires_in,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: dict,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    🔄 Refresh token - VERSIÓN SIMPLIFICADA
    """
    try:
        refresh_token = refresh_data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token requerido",
            )

        # Agregar headers CORS
        add_cors_headers(request, response)

        # Validar refresh token (simplificado)
        user_id = AuthService.validate_refresh_token(refresh_token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )

        # Obtener usuario
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

        # Generar nuevo access token (4 horas)
        new_access_token = create_access_token(subject=str(user.id))
        # Generar nuevo refresh token (7 días) - usar create_refresh_token para tipo correcto
        from app.core.security import create_refresh_token

        new_refresh_token = create_refresh_token(subject=str(user.id))

        # Calcular tiempo de expiración en segundos (4 horas = 240 minutos)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 14400 segundos

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    👤 Obtener información del usuario actual
    """
    return UserMeResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    🔒 Cambiar contraseña del usuario actual
    """
    try:
        # Validar contraseña actual
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta",
            )

        # Validar nueva contraseña
        if not validate_password_strength(password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña no cumple con los requisitos de seguridad",
            )

        # Actualizar contraseña
        current_user.password_hash = get_password_hash(password_data.new_password)
        db.commit()

        logger.info(f"Contraseña cambiada para usuario: {current_user.email}")

        # ✅ IMPORTANTE: Indicar que se requiere reautenticación
        # Los tokens actuales siguen siendo válidos técnicamente, pero por seguridad
        # el frontend debe cerrar la sesión y pedir que el usuario se vuelva a autenticar
        return {
            "message": "Contraseña cambiada exitosamente",
            "requires_reauth": True  # Señal para que el frontend cierre la sesión
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )


@router.options("/login")
@router.options("/refresh")
@router.options("/me")
@router.options("/change-password")
async def options_handler(request: Request, response: Response):
    """
    Manejar requests OPTIONS para CORS
    """
    add_cors_headers(request, response)
    return {"message": "OK"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    🚪 Logout del usuario actual: registra evento de auditoría
    ✅ Tolerante: funciona incluso si el token expiró (para limpiar sesión del frontend)
    """
    try:
        add_cors_headers(request, response)

        # Si hay usuario autenticado, registrar auditoría
        if current_user:
            ip = request.client.host if request and request.client else None
            ua = request.headers.get("user-agent") if request else None

            audit = Auditoria(
                usuario_id=current_user.id,
                accion="LOGOUT",
                entidad="USUARIOS",
                entidad_id=current_user.id,
                detalles="Cierre de sesión",
                ip_address=ip,
                user_agent=ua,
                exito=True,
            )
            db.add(audit)
            try:
                db.commit()
            except Exception as e:
                try:
                    db.rollback()
                except Exception:
                    pass
                logging.getLogger(__name__).warning(f"No se pudo registrar auditoría LOGOUT: {e}")

        return {"message": "Sesión cerrada"}
    except Exception as e:
        logging.getLogger(__name__).warning(f"No se pudo registrar auditoría LOGOUT: {e}")
        return {"message": "Sesión cerrada"}
