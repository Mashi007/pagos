# backend/app/api/v1/endpoints/auth.py
"""
Endpoints de autenticación - VERSIÓN SIMPLIFICADA SIN AUDITORÍA
Solución temporal para resolver error 503
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    Token,
    LoginResponse,
    RefreshTokenRequest,
    ChangePasswordRequest
)
from app.schemas.user import UserMeResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

def add_cors_headers(request: Request, response: Response) -> None:
    """
    Helper function para agregar headers CORS de forma consistente
    """
    from app.core.config import settings
    
    origin = request.headers.get("origin")
    logger.info(f"CORS Debug - Origin recibido: {origin}")
    logger.info(f"CORS Debug - Origins permitidos: {settings.CORS_ORIGINS}")
    
    if origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        logger.info(f"CORS Debug - Origin permitido: {origin}")
    else:
        logger.warning(f"CORS Debug - Origin NO permitido: {origin}")
    
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
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
                detail="Credenciales inválidas"
            )
        
        # Generar token
        access_token = AuthService.create_access_token(data={"sub": user.email})
        
        logger.info(f"Login exitoso para: {login_data.email}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserMeResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    👤 Obtener información del usuario actual
    """
    try:
        # Agregar headers CORS
        add_cors_headers(request, response)
        
        return UserMeResponse.model_validate(current_user)
        
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    🚪 Logout de usuario
    """
    try:
        # Agregar headers CORS
        add_cors_headers(request, response)
        
        logger.info(f"Logout exitoso para: {current_user.email}")
        
        return {"message": "Logout exitoso"}
        
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    🔄 Refrescar token de acceso
    """
    try:
        # Agregar headers CORS
        add_cors_headers(request, response)
        
        # Validar token de refresh
        user = AuthService.validate_refresh_token(db, refresh_data.refresh_token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido"
            )
        
        # Generar nuevo token
        access_token = AuthService.create_access_token(data={"sub": user.email})
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refrescando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    response: Response,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔑 Cambiar contraseña
    """
    try:
        # Agregar headers CORS
        add_cors_headers(request, response)
        
        # Verificar contraseña actual
        if not AuthService.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
        
        # Actualizar contraseña
        new_hashed_password = AuthService.get_password_hash(password_data.new_password)
        current_user.hashed_password = new_hashed_password
        
        db.commit()
        
        logger.info(f"Contraseña cambiada para: {current_user.email}")
        
        return {"message": "Contraseña cambiada exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.options("/{path:path}")
async def options_handler(request: Request, response: Response, path: str):
    """
    Manejar requests OPTIONS para CORS
    """
    add_cors_headers(request, response)
    return {"message": "OK"}