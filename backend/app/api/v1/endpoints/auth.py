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
from app.core.rate_limiter import RATE_LIMITS, get_rate_limiter
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
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
from app.utils.auditoria_table_helper import asegurar_tabla_auditoria
from app.utils.validators import validate_password_strength

logger = logging.getLogger(__name__)
router = APIRouter()

# Obtener limiter para aplicar rate limiting
limiter = get_rate_limiter()


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
        # Asegurar que la tabla existe antes de intentar insertar
        if not asegurar_tabla_auditoria(db):
            logger.debug("Tabla 'auditoria' no disponible, omitiendo registro de auditoría")
            return
        
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
        # Solo registrar como warning si es un error diferente a "tabla no existe"
        error_str = str(e).lower()
        if "does not exist" in error_str or "undefinedtable" in error_str:
            # Error de tabla no existe - intentar crear y silenciar el warning
            logger.debug(f"Tabla 'auditoria' no existe, omitiendo registro de auditoría: {e}")
        else:
            # Otro tipo de error - registrar como warning
            tipo = "LOGIN" if exito else "LOGIN FALLIDO"
            logger.warning(f"No se pudo registrar auditoría {tipo}: {e}")


def _generar_tokens_usuario(user_id: int) -> tuple[str, str]:
    """Genera access token y refresh token para el usuario"""
    access_token = create_access_token(subject=str(user_id))
    refresh_token = create_refresh_token(subject=str(user_id))
    return (access_token, refresh_token)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMITS["auth"])  # 5 intentos por minuto para proteger contra fuerza bruta
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    🔐 Login de usuario - VERSIÓN SIMPLIFICADA
    Características:
    - Rate limiting: 5 intentos por minuto por IP
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

        # ✅ Actualizar último acceso del usuario
        from datetime import datetime

        try:
            # Obtener fecha actual
            now = datetime.utcnow()
            logger.info(f"🔄 Actualizando last_login para usuario {user_id} a {now}")

            # Asegurar que el usuario esté en la sesión
            db.add(user)
            user.last_login = now

            # Flush para aplicar cambios antes del commit
            db.flush()
            logger.debug("✅ Flush exitoso para last_login")

            # Commit explícito
            db.commit()
            logger.info("✅ Commit exitoso para last_login")

            # Refresh para obtener el valor actualizado de la BD
            db.refresh(user)
            logger.info(f"✅ last_login actualizado correctamente para usuario {user_id}: {user.last_login}")

        except Exception as update_error:
            # Si falla la actualización de last_login, hacer rollback pero continuar con el login
            # No queremos que un error en last_login impida el login del usuario
            try:
                db.rollback()
                logger.warning("⚠️ Rollback realizado después de error en last_login")
            except Exception as rollback_error:
                logger.error(f"❌ Error al hacer rollback: {rollback_error}")
            logger.error(f"❌ No se pudo actualizar last_login para usuario {user_id}: {update_error}", exc_info=True)
            # Continuar con el login aunque last_login no se actualizó

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
            "last_login": user.last_login.isoformat() if user.last_login else None,
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
        if not verify_password(password_data.current_password, current_user.hashed_password):
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

        # Preservar el cargo antes de actualizar (por si acaso)
        cargo_original = current_user.cargo

        # Actualizar contraseña - usar merge para evitar problemas con el refresh
        user_id = current_user.id
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Actualizar solo el campo hashed_password
        user.hashed_password = get_password_hash(password_data.new_password)

        # ✅ Actualizar updated_at
        from datetime import datetime

        user.updated_at = datetime.utcnow()

        # Asegurar que el cargo se mantiene explícitamente
        if cargo_original is not None:
            user.cargo = cargo_original

        db.commit()
        db.refresh(user)  # ✅ Refrescar para asegurar que los cambios se reflejen

        # Verificar que el cargo se mantuvo después del refresh
        if cargo_original is not None and user.cargo != cargo_original:
            logger.warning(f"El cargo cambió después del refresh. Restaurando cargo original para usuario {user_id}")
            user.cargo = cargo_original
            db.commit()
            db.refresh(user)

        logger.info(f"Contraseña cambiada para usuario: {current_user.email}")

        # ✅ IMPORTANTE: Indicar que se requiere reautenticación
        # Por seguridad, después de cambiar la contraseña el usuario debe volver a iniciar sesión
        # El frontend cerrará la sesión automáticamente y redirigirá al login
        return {
            "message": "Contraseña cambiada exitosamente. Debes volver a iniciar sesión.",
            "requires_reauth": True,  # Señal para que el frontend cierre la sesión y redirija al login
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
