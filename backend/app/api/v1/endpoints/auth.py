# backend/app/api/v1/endpoints/auth.py
"""
Endpoints de autenticación
Login, logout, refresh token, cambio de contraseña
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

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
from app.utils.auditoria_helper import registrar_login_exitoso, registrar_logout, registrar_error

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

# Security Audit Logging
from app.core.security_audit import log_login_attempt, log_password_change

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

def add_cors_headers(request: Request, response: Response) -> None:
    """
    Helper function para agregar headers CORS de forma consistente
    
    Args:
        request: Request object con origin header
        response: Response object donde agregar headers
    """
    from app.core.config import settings
    import logging
    logger = logging.getLogger(__name__)
    
    origin = request.headers.get("origin")
    logger.info(f"🌐 CORS Debug - Origin recibido: {origin}")
    logger.info(f"🌐 CORS Debug - Origins permitidos: {settings.CORS_ORIGINS}")
    
    if origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        logger.info(f"✅ CORS Headers agregados para origin: {origin}")
    else:
        logger.warning(f"❌ CORS Origin no permitido: {origin}")
        # FALLBACK: Permitir origin específico del frontend
        if origin == "https://rapicredit.onrender.com":
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
            logger.info(f"✅ CORS Headers agregados (FALLBACK) para origin: {origin}")


@router.options("/login")
async def options_login():
    """Endpoint OPTIONS explícito para preflight CORS"""
    return {"message": "OK"}

@router.get("/cors-test")
async def cors_test(request: Request):
    """
    Endpoint de prueba CORS - SOLUCIÓN DEFINITIVA
    """
    origin = request.headers.get("origin", "No origin")
    return {
        "message": "CORS Test OK",
        "origin": origin,
        "headers": dict(request.headers),
        "cors_working": True
    }


@router.post("/login", response_model=LoginResponse, summary="Login de usuario")
@limiter.limit("5/minute")  # ✅ Rate limiting: 5 intentos por minuto
def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login de usuario con email y contraseña
    
    Retorna access_token, refresh_token e información del usuario
    
    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    
    **Rate Limit:** 5 intentos por minuto por IP
    """
    # CORS MANEJADO POR MIDDLEWARE - SIN CONFLICTOS
    
    try:
        token, user = AuthService.login(db, login_data)
        
        # ✅ Log de login exitoso
        log_login_attempt(
            email=login_data.email,
            ip_address=request.client.host if request.client else "unknown",
            success=True
        )
        
        # Registrar auditoría de login exitoso
        try:
            registrar_login_exitoso(
                db=db,
                usuario=user,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        except Exception as e:
            logger.warning(f"Error registrando auditoría de login: {e}")
        
    except HTTPException as e:
        # ❌ Log de login fallido
        log_login_attempt(
            email=login_data.email,
            ip_address=request.client.host if request.client else "unknown",
            success=False,
            reason=str(e.detail)
        )
        
        # Registrar auditoría de login fallido
        try:
            registrar_error(
                db=db,
                usuario=None,  # Usuario no encontrado
                accion="LOGIN",
                modulo="AUTH",
                tabla="usuarios",
                descripcion=f"Intento de login fallido para {login_data.email}",
                mensaje_error=str(e.detail),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        except Exception as audit_error:
            logger.warning(f"Error registrando auditoría de login fallido: {audit_error}")
        
        raise
    
    # Crear respuesta con tokens y usuario
    login_response = LoginResponse(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        token_type=token.token_type,
        user={
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "rol": "ADMIN" if user.is_admin else "USER",
            "is_active": user.is_active
        }
    )
    
    return login_response


@router.post("/refresh", response_model=Token, summary="Refresh token")
@limiter.limit("10/minute")  # ✅ Rate limiting: 10 intentos por minuto
def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un nuevo access token usando un refresh token válido
    
    - **refresh_token**: Refresh token válido
    
    **Rate Limit:** 10 intentos por minuto por IP
    """
    token = AuthService.refresh_access_token(db, refresh_data.refresh_token)
    
    return token


@router.get("/me", response_model=UserMeResponse, summary="Usuario actual")
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la información del usuario actualmente autenticado
    
    Incluye permisos basados en el rol del usuario
    """
    # Obtener permisos del usuario
    permissions = AuthService.get_user_permissions(current_user)
    
    # Crear respuesta
    user_response = UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        is_admin=current_user.is_admin,  # CRÍTICO: Incluir is_admin
        cargo=current_user.cargo,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        permissions=permissions
    )
    
    return user_response


@router.post("/change-password", summary="Cambiar contraseña")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambia la contraseña del usuario actual
    
    - **current_password**: Contraseña actual
    - **new_password**: Nueva contraseña
    - **confirm_password**: Confirmación de nueva contraseña
    """
    # Verificar que las contraseñas coincidan
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    # Cambiar contraseña
    AuthService.change_password(
        db,
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    
    return {
        "message": "Contraseña actualizada exitosamente"
    }


@router.post("/logout", summary="Logout de usuario")
def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout de usuario
    
    Nota: En esta implementación, el logout es del lado del cliente
    (eliminar tokens del almacenamiento local).
    
    Para invalidar tokens del lado del servidor, se requeriría
    implementar una blacklist de tokens en Redis o similar.
    """
    return {
        "message": f"Usuario {current_user.email} cerró sesión exitosamente"
    }


@router.get("/verify", summary="Verificar token")
def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verifica si el token actual es válido
    
    Útil para verificar la sesión desde el frontend
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "rol": "ADMIN" if current_user.is_admin else "USER"
    }


@router.post("/create-test-user", summary="Crear usuario de prueba")
def create_test_user(db: Session = Depends(get_db)):
    """
    ENDPOINT TEMPORAL PARA CREAR USUARIO CON CONTRASEÑA CONOCIDA
    
    CREDENCIALES:
    - Email: admin@rapicredit.com
    - Password: admin123
    - Rol: ADMIN
    """
    import bcrypt
    
    try:
        # Eliminar usuario existente si existe
        existing_user = db.query(User).filter(User.email == "admin@rapicredit.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
        
        # Crear hash de contraseña desde settings
        from app.core.config import settings
        password_hash = get_password_hash(settings.ADMIN_PASSWORD)
        
        # Crear usuario nuevo
        new_user = User(
            email="admin@rapicredit.com",
            hashed_password=password_hash,
            nombre="Admin",
            apellido="Sistema",
            is_admin=True,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "Usuario de prueba creado exitosamente",
            "credentials": {
                "email": "admin@rapicredit.com",
                "password": "admin123",
                "is_admin": True
            },
            "user_id": new_user.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando usuario de prueba: {str(e)}"
        )
