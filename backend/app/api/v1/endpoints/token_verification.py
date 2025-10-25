from app.core.security import decode_token
from datetime import date
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
        return None, 

    if not auth_header.startswith("Bearer "):
        return None, 

    return auth_header.split(" ")[1], None


def _analizar_estructura_token(token: str) -> tuple[dict, dict]:
    """Analizar estructura básica del token"""
    token_analysis = 

    # Verificar estructura JWT
    if token.count(".") != 2:
        return token_analysis, 

    return token_analysis, None


def _decodificar_token_sin_verificar(token: str) -> tuple[dict, dict]:
    """Decodificar token sin verificar firma para análisis"""
    try:
        header_decoded = jwt.get_unverified_header(token)
        payload_decoded = jwt.decode(token, options={"verify_signature": False})

        token_analysis = 

        return token_analysis, None

    except Exception as e:
        return {}, 
            "error": f"Error decodificando token: {str(e)}",


def _verificar_expiracion_token(payload_decoded: dict) -> dict:
    """Verificar expiración del token"""

        return 
    else:
        return {"error": "No expiration found in token"}


def _verificar_token_con_secret(token: str) -> dict:
    """Verificar token con SECRET_KEY real"""
    try:
        verified_payload = decode_token(token)
        return 
    except PyJWTError as e:
        return 
    except Exception as e:
        return 


def _verificar_usuario_en_bd(verification_result: dict, db: Session) -> dict:
    if not verification_result.get("verified"):
        return {"status": "skipped", "reason": "Token not verified"}

    user_id = verification_result["payload"].get("sub")
    if not user_id:
        return 

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            return 
        else:
            return 
                "error": f"User with ID {user_id} not found in database",
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _generar_recomendaciones
) -> list:
    """Generar recomendaciones basadas en el análisis"""
    recommendations = []

    if not verification_result.get("verified"):
        recommendations.append

    if token_analysis.get("expiration", {}).get("is_expired"):
        recommendations.append("⏰ Token expirado - Hacer login nuevamente")

    if not user_verification.get("user_found"):
        recommendations.append

    if not user_verification.get("user_active"):
        recommendations.append("⚠️ Usuario inactivo - Contactar administrador")

    if not recommendations:
        recommendations.append("✅ Token válido y usuario correcto")

    return recommendations


async def verificar_token_detallado
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
        token_analysis["expiration"] = _verificar_expiracion_token

        # 5. Verificar con SECRET_KEY real
        verification_result = _verificar_token_con_secret(token)

        # 6. Verificar usuario en BD
        user_verification = _verificar_usuario_en_bd(verification_result, db)

        # 7. Generar recomendaciones
        recommendations = _generar_recomendaciones

        return 

    except Exception as e:
        logger.error(f"Error en verificación de token: {e}")
        return 


@router.get("/token-info")
async def obtener_info_token(request: Request, db: Session = Depends(get_db)):
    """
    📊 Información básica del token actual
    """
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return 

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
                    user_info = 

            return 
                },

        except Exception as e:
            return 
                "error": f"Error decoding token: {str(e)}",

    except Exception as e:
        return 


async def generar_token_prueba(db: Session = Depends(get_db)):
    """
    🧪 Generar token de prueba para testing
    """
    try:
        # Buscar usuario admin
        admin_user = db.query(User).filter(User.is_admin).first()
        if not admin_user:
            return 

        # Generar token
        test_token = create_access_token
            subject=str(admin_user.id), additional_claims={"type": "access"}

        return 
            },
            "usage": "Use this token in Authorization header: Bearer <token>",

    except Exception as e:
        logger.error(f"Error generando token de prueba: {e}")
        return 
