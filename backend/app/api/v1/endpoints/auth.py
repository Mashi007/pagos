# backend/app/api/v1/endpoints/auth.py
"""Endpoints de autenticación - VERSIÓN SIMPLIFICADA SIN AUDITORÍA
Solución temporal para resolver error 503
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, TokenResponse
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
            logger.info(
                f"CORS Debug - Usando origin por defecto: {settings.CORS_ORIGINS[0]}"
            )

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"


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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        # Generar tokens
        access_token = create_access_token(subject=str(user.id))

        # Generar refresh token nuevo
        refresh_token = create_access_token(
            subject=str(user.id), expires_delta=timedelta(minutes=1440)
        )

        logger.info(f"Login exitoso para: {login_data.email}")

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

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_info,
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado"
            )

        # Generar nuevo access token
        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_access_token(
            subject=str(user.id), expires_delta=timedelta(minutes=1440)
        )

        # Calcular tiempo de expiración en segundos (30 minutos por defecto)
        expires_in = 30 * 60  # 1800 segundos

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
        if not verify_password(
            password_data.current_password, current_user.password_hash
        ):
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

        return {"message": "Contraseña cambiada exitosamente"}

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
