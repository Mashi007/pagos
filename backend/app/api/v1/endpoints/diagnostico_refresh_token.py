"""
Endpoint de diagnóstico específico para problemas de refresh token
"""

import logging
from datetime import datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/diagnosticar-refresh-token")
async def diagnosticar_refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    🔍 Diagnóstico específico para problemas de refresh token
    """
    try:
        logger.info("🔍 Iniciando diagnóstico de refresh token")

        # Obtener refresh token del body
        body = await request.json()
        refresh_token = body.get("refresh_token")

        if not refresh_token:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "No refresh token provided",
                "recomendacion": "Verificar que el frontend esté enviando el refresh_token correctamente",
            }

        logger.info(f"🔍 Refresh token recibido: {refresh_token[:20]}...")

        # 1. Verificar formato del token
        try:
            # Decodificar sin verificar para obtener información básica
            payload_unverified = jwt.decode(refresh_token, options={"verify_signature": False})

            token_info = {
                "formato_valido": True,
                "payload_keys": list(payload_unverified.keys()),
                "user_id": payload_unverified.get("sub"),
                "token_type": payload_unverified.get("type"),
                "exp": payload_unverified.get("exp"),
                "iat": payload_unverified.get("iat"),
            }

            # Verificar si está expirado
            if payload_unverified.get("exp"):
                exp_timestamp = payload_unverified["exp"]
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                now = datetime.now()

                token_info["expired"] = now > exp_datetime
                token_info["expires_at"] = exp_datetime.isoformat()
                token_info["time_until_expiry"] = str(exp_datetime - now) if not token_info["expired"] else "EXPIRED"

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Token format invalid: {str(e)}",
                "recomendacion": "El refresh token tiene un formato inválido",
            }

        # 2. Verificar con decode_token (con verificación)
        try:
            payload_verified = decode_token(refresh_token)
            token_info["verificacion_firma"] = "SUCCESS"
            token_info["payload_verificado"] = payload_verified
        except PyJWTError as e:
            token_info["verificacion_firma"] = "FAILED"
            token_info["error_verificacion"] = str(e)

            if "expired" in str(e).lower():
                return {
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": "Refresh token expired",
                    "token_info": token_info,
                    "recomendacion": "El refresh token ha expirado. El usuario debe hacer login nuevamente.",
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": f"Token verification failed: {str(e)}",
                    "token_info": token_info,
                    "recomendacion": "El refresh token es inválido o corrupto.",
                }

        # 3. Verificar tipo de token
        if payload_verified.get("type") != "refresh":
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Token type is not 'refresh'",
                "token_info": token_info,
                "recomendacion": "El token enviado no es un refresh token válido.",
            }

        # 4. Verificar usuario en BD
        user_id = payload_verified.get("sub")
        if not user_id:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "No user ID in token",
                "token_info": token_info,
                "recomendacion": "El refresh token no contiene un user_id válido.",
            }

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "User not found",
                "token_info": token_info,
                "recomendacion": f"Usuario con ID {user_id} no existe en la base de datos.",
            }

        if not user.is_active:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "User inactive",
                "token_info": token_info,
                "user_info": {
                    "email": user.email,
                    "active": user.is_active,
                    "admin": user.is_admin,
                },
                "recomendacion": "El usuario está inactivo. Contactar administrador.",
            }

        # 5. Intentar generar nuevos tokens
        try:
            new_access_token = create_access_token(
                subject=user.id,
                additional_claims={"is_admin": user.is_admin, "email": user.email},
            )

            new_refresh_token = create_refresh_token(subject=user.id)

            token_info["nuevos_tokens_generados"] = True
            token_info["usuario_valido"] = True

            return {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "message": "Refresh token válido y nuevos tokens generados",
                "token_info": token_info,
                "user_info": {
                    "email": user.email,
                    "active": user.is_active,
                    "admin": user.is_admin,
                },
                "nuevos_tokens": {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                },
                "recomendacion": "El refresh token es válido. El problema puede estar en el frontend.",
            }

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Error generating new tokens: {str(e)}",
                "token_info": token_info,
                "recomendacion": "Error interno al generar nuevos tokens.",
            }

    except Exception as e:
        logger.error(f"❌ Error en diagnóstico de refresh token: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": f"Error interno: {str(e)}",
            "recomendacion": "Error interno del servidor.",
        }


@router.get("/estado-refresh-tokens")
async def estado_refresh_tokens(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    📊 Estado general de los refresh tokens en el sistema
    """
    try:
        logger.info(f"📊 Verificando estado de refresh tokens - Usuario: {current_user.email}")

        # Información del usuario actual
        user_info = {
            "id": current_user.id,
            "email": current_user.email,
            "active": current_user.is_active,
            "admin": current_user.is_admin,
        }

        # Generar tokens de prueba para el usuario actual
        test_access_token = create_access_token(
            subject=current_user.id,
            additional_claims={
                "is_admin": current_user.is_admin,
                "email": current_user.email,
            },
        )

        test_refresh_token = create_refresh_token(subject=current_user.id)

        return {
            "timestamp": datetime.now().isoformat(),
            "usuario": user_info,
            "tokens_generados": {
                "access_token": test_access_token,
                "refresh_token": test_refresh_token,
            },
            "configuracion": {
                "jwt_secret_key": ("CONFIGURED" if settings.SECRET_KEY else "NOT_CONFIGURED"),
                "jwt_algorithm": "HS256",
                "access_token_expire_minutes": 30,
                "refresh_token_expire_days": 7,
            },
            "recomendacion": "Tokens generados correctamente. Verificar configuración del frontend.",
        }

    except Exception as e:
        logger.error(f"❌ Error verificando estado de refresh tokens: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando estado de refresh tokens: {str(e)}",
        )
