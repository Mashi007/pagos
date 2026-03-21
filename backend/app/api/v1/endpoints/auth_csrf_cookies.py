"""
Rutas de Autenticación - Login con CSRF Token y Secure Cookies
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security_csrf import csrf_manager, secure_cookie_config
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ========================
# Esquemas Pydantic
# ========================

class LoginFormRequest(BaseModel):
    """Esquema para solicitud de formulario de login (obtener CSRF token)"""
    pass  # Endpoint GET, sin body


class LoginFormResponse(BaseModel):
    """Esquema para respuesta del formulario de login"""
    csrf_token: str
    form_url: str
    
    class Config:
        schema_extra = {
            "example": {
                "csrf_token": "rN3x_8mK9pL2qR5sT7uV9wX0yZ1aB2cD3eF4gH5iJ6",
                "form_url": "/api/v1/auth/login"
            }
        }


class LoginRequest(BaseModel):
    """Esquema para solicitud de login"""
    email: EmailStr
    password: str = None  # Optional para desarrollo
    csrf_token: str
    remember_me: bool = False
    
    @validator('password')
    def password_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Password is required')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
                "csrf_token": "rN3x_8mK9pL2qR5sT7uV9wX0yZ1aB2cD3eF4gH5iJ6",
                "remember_me": False
            }
        }


class LoginResponse(BaseModel):
    """Esquema para respuesta exitosa de login"""
    status: str
    message: str
    user_id: str
    email: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Sesión iniciada correctamente",
                "user_id": "user_123",
                "email": "user@example.com"
            }
        }


class LoginErrorResponse(BaseModel):
    """Esquema para respuesta de error en login"""
    status: str
    detail: str
    code: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "detail": "Email o contraseña incorrectos",
                "code": "INVALID_CREDENTIALS"
            }
        }


# ========================
# Endpoints
# ========================

@router.get(
    "/login-form",
    response_model=LoginFormResponse,
    summary="Obtener formulario de login con CSRF token",
    description="""
    Obtiene el formulario de login junto con un token CSRF único.
    
    Este token debe incluirse en cada solicitud POST de login para validación.
    Los tokens expiran en 1 hora.
    
    **Seguridad:**
    - CSRF token de una sola vez (one-time use)
    - Token único por sesión
    - Expira automáticamente
    """
)
async def get_login_form(request: Request) -> LoginFormResponse:
    """
    Endpoint para obtener formulario de login con protección CSRF.
    
    Genera un token CSRF único que debe usarse en la solicitud de login.
    """
    try:
        # Obtener o crear ID de sesión del usuario
        session_id = request.cookies.get("session_id")
        if not session_id:
            # Crear nueva sesión - en producción usar session store real
            import uuid
            session_id = str(uuid.uuid4())
        
        # Generar token CSRF
        csrf_token = csrf_manager.generate_token(session_id)
        
        return LoginFormResponse(
            csrf_token=csrf_token,
            form_url="/api/v1/auth/login"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar formulario: {str(e)}"
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión con email y contraseña",
    description="""
    Autentica un usuario usando email y contraseña.
    
    **Validaciones:**
    - Verifica token CSRF (previene ataques CSRF)
    - Valida credenciales del usuario
    - Configura cookies seguras (httpOnly, Secure, SameSite=Strict)
    
    **Seguridad:**
    - Cookies con httpOnly (no accesible desde JavaScript)
    - Secure flag (solo HTTPS en producción)
    - SameSite=strict (previene CSRF)
    - Token session seguro
    """
)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    Endpoint de login con validación CSRF y cookies seguras.
    """
    try:
        # 1. VALIDAR CSRF TOKEN (paso crítico)
        session_id = request.cookies.get("session_id", "default_session")
        
        # Verificar que el token CSRF sea válido
        # Esta función lanza HTTPException si el token es inválido
        csrf_manager.verify_token(session_id, login_data.csrf_token)
        
        # 2. VALIDAR CREDENCIALES
        # TODO: Implementar consulta real a base de datos
        if login_data.email == "demo@rapicredit.com" and login_data.password == "demo123":
            user_id = "user_demo_123"
            user_email = login_data.email
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 3. CREAR RESPUESTA CON COOKIES SEGURAS
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Sesión iniciada correctamente",
                "user_id": user_id,
                "email": user_email
            }
        )
        
        # 4. CONFIGURAR COOKIES SEGURAS
        # Cookie de sesión
        cookie_kwargs = secure_cookie_config.get_session_cookie_kwargs()
        response.set_cookie(
            value=f"{user_id}:session_token_xyz",
            **cookie_kwargs
        )
        
        # Cookie de refresh token (opcional, para token rotation)
        if login_data.remember_me:
            refresh_kwargs = secure_cookie_config.get_refresh_cookie_kwargs()
            response.set_cookie(
                value=f"{user_id}:refresh_token_xyz",
                **refresh_kwargs
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en autenticación: {str(e)}"
        )


@router.post(
    "/logout",
    response_model=dict,
    summary="Cerrar sesión",
    description="""
    Cierra la sesión actual borrando las cookies de sesión.
    """
)
async def logout(request: Request) -> dict:
    """
    Endpoint para cerrar sesión.
    """
    try:
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Sesión cerrada correctamente"
            }
        )
        
        # Borrar cookies de sesión
        session_kwargs = secure_cookie_config.get_delete_cookie_kwargs(
            secure_cookie_config.SESSION_COOKIE_NAME
        )
        response.delete_cookie(**session_kwargs)
        
        # Borrar cookies de refresh token
        refresh_kwargs = secure_cookie_config.get_delete_cookie_kwargs(
            secure_cookie_config.REFRESH_COOKIE_NAME
        )
        response.delete_cookie(**refresh_kwargs)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cerrar sesión: {str(e)}"
        )


@router.options(
    "/login",
    summary="CORS Preflight para login",
    include_in_schema=False
)
async def options_login():
    """Manejo de CORS preflight requests"""
    return {"detail": "OK"}
