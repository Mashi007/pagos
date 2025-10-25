from app.core.security import decode_token
"""Endpoint de Verificación de Tokens JWT
"""

import logging

import jwt
from fastapi import APIRouter, Depends, Request
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import create_access_token, decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _extraer_token_del_header(request: Request) -> tuple[str, dict]:
    """Extraer token del header Authorization"""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None, {
            "status": "error",
            "error": "No Authorization header found",
            "recommendation": "Verificar que el frontend esté enviando el header Authorization",
        }

    if not auth_header.startswith("Bearer "):
        return None, {
            "status": "error",
            "error": "Invalid Authorization header format",
            "expected_format": "Bearer <token>",
            "received": (
                auth_header[:20] + "..." if len(auth_header) > 20 else auth_header
            ),
        }

    return auth_header.split(" ")[1], None


def _analizar_estructura_token(token: str) -> tuple[dict, dict]:
    """Analizar estructura básica del token"""
    token_analysis = {
        "token_length": len(token),
        "token_preview": token[:20] + "..." if len(token) > 20 else token,
        "has_dots": "." in token,
        "dot_count": token.count("."),
    }

    # Verificar estructura JWT
    if token.count(".") != 2:
        return token_analysis, {
            "status": "error",
            "error": "Invalid JWT structure",
            "expected_dots": 2,
            "actual_dots": token.count("."),
            "token_analysis": token_analysis,
        }

    return token_analysis, None


def _decodificar_token_sin_verificar(token: str) -> tuple[dict, dict]:
    """Decodificar token sin verificar firma para análisis"""
    try:
        header_decoded = jwt.get_unverified_header(token)
        payload_decoded = jwt.decode(token, options={"verify_signature": False})

        token_analysis = {
            "header": header_decoded,
            "payload": payload_decoded,
            "payload_keys": list(payload_decoded.keys()),
            "user_id": payload_decoded.get("sub"),
            "token_type": payload_decoded.get("type"),
            "exp": payload_decoded.get("exp"),
            "iat": payload_decoded.get("iat"),
        }

        return token_analysis, None

    except Exception as e:
        return {}, {
            "status": "error",
            "error": f"Error decodificando token: {str(e)}",
        }


def _verificar_expiracion_token(payload_decoded: dict) -> dict:
    """Verificar expiración del token"""

        return {
            "is_expired": is_expired,
            ),
        }
    else:
        return {"error": "No expiration found in token"}


def _verificar_token_con_secret(token: str) -> dict:
    """Verificar token con SECRET_KEY real"""
    try:
        verified_payload = decode_token(token)
        return {
            "status": "success",
            "verified": True,
            "payload": verified_payload,
        }
    except PyJWTError as e:
        return {
            "status": "error",
            "verified": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
    except Exception as e:
        return {
            "status": "error",
            "verified": False,
            "error": str(e),
            "error_type": "Unknown",
        }


def _verificar_usuario_en_bd(verification_result: dict, db: Session) -> dict:
    if not verification_result.get("verified"):
        return {"status": "skipped", "reason": "Token not verified"}

    user_id = verification_result["payload"].get("sub")
    if not user_id:
        return {
            "status": "error",
            "error": "No user_id in token payload",
        }

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            return {
                "status": "success",
                "user_found": True,
                "user_email": user.email,
                "user_active": user.is_active,
                "user_admin": user.is_admin,
            }
        else:
            return {
                "status": "error",
                "user_found": False,
                "error": f"User with ID {user_id} not found in database",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _generar_recomendaciones(
    verification_result: dict, token_analysis: dict, user_verification: dict
) -> list:
    """Generar recomendaciones basadas en el análisis"""
    recommendations = []

    if not verification_result.get("verified"):
        recommendations.append(
            "🔐 Token no válido - Verificar SECRET_KEY o regenerar token"
        )

    if token_analysis.get("expiration", {}).get("is_expired"):
        recommendations.append("⏰ Token expirado - Hacer login nuevamente")

    if not user_verification.get("user_found"):
        recommendations.append(
        )

    if not user_verification.get("user_active"):
        recommendations.append("⚠️ Usuario inactivo - Contactar administrador")

    if not recommendations:
        recommendations.append("✅ Token válido y usuario correcto")

    return recommendations


async def verificar_token_detallado(
    request: Request, db: Session = Depends(get_db)
):
    """
    🔍 Verificación detallada de token JWT (VERSIÓN REFACTORIZADA)
    Analiza token sin requerir autenticación previa
    """
    try:
        # 1. Extraer token del header
        token, error_response = _extraer_token_del_header(request)
        if error_response:
            return error_response

        # 2. Analizar estructura del token
        token_analysis, error_response = _analizar_estructura_token(token)
        if error_response:
            return error_response

        # 3. Decodificar token sin verificar
        decoded_analysis, error_response = _decodificar_token_sin_verificar(token)
        if error_response:
            return error_response

        token_analysis.update(decoded_analysis)

        # 4. Verificar expiración
        token_analysis["expiration"] = _verificar_expiracion_token(
            token_analysis["payload"]
        )

        # 5. Verificar con SECRET_KEY real
        verification_result = _verificar_token_con_secret(token)

        # 6. Verificar usuario en BD
        user_verification = _verificar_usuario_en_bd(verification_result, db)

        # 7. Generar recomendaciones
        recommendations = _generar_recomendaciones(
            verification_result, token_analysis, user_verification
        )

        return {
            "status": "analysis_complete",
            "token_analysis": token_analysis,
            "verification": verification_result,
            "user_verification": user_verification,
            "recommendations": recommendations,
            "overall_status": (
                "valid"
                if verification_result.get("verified") and user_verification.get("user_found")
                else "invalid"
            ),
        }

    except Exception as e:
        logger.error(f"Error en verificación de token: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/token-info")
async def obtener_info_token(request: Request, db: Session = Depends(get_db)):
    """
    📊 Información básica del token actual
    """
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "status": "no_token",
                "message": "No valid token provided",
            }

        token = auth_header.split(" ")[1]

        # Decodificar sin verificar
        try:
            payload = jwt.decode(token, options={"verify_signature": False})

            # Información básica
            user_id = payload.get("sub")
            user_info = {}
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user:
                    user_info = {
                        "email": user.email,
                        "active": user.is_active,
                        "admin": user.is_admin,
                    }

            return {
                "status": "success",
                "token_info": {
                    "user_id": user_id,
                    "token_type": payload.get("type"),
                    "exp": payload.get("exp"),
                    "iat": payload.get("iat"),
                    "user_info": user_info,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Error decoding token: {str(e)}",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


async def generar_token_prueba(db: Session = Depends(get_db)):
    """
    🧪 Generar token de prueba para testing
    """
    try:
        # Buscar usuario admin
        admin_user = db.query(User).filter(User.is_admin).first()
        if not admin_user:
            return {
                "status": "error",
                "error": "No admin user found",
            }

        # Generar token
        test_token = create_access_token(
            subject=str(admin_user.id), additional_claims={"type": "access"}
        )

        return {
            "status": "success",
            "test_token": test_token,
            "user_info": {
                "id": admin_user.id,
                "email": admin_user.email,
                "active": admin_user.is_active,
                "admin": admin_user.is_admin,
            },
            "usage": "Use this token in Authorization header: Bearer <token>",
        }

    except Exception as e:
        logger.error(f"Error generando token de prueba: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
