"""
Endpoint de Verificación de Tokens JWT
Sistema avanzado para diagnosticar problemas de autenticación
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
import jwt
from jwt import JWTError

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.core.security import create_access_token, decode_token

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/verify-token")
async def verificar_token_detallado(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔍 Verificación detallada de token JWT
    Analiza token sin requerir autenticación previa
    """
    try:
        # Obtener token del header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "No Authorization header found",
                "recommendation": "Verificar que el frontend esté enviando el header Authorization"
            }

        # Extraer token
        if not auth_header.startswith("Bearer "):
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Invalid Authorization header format",
                "expected_format": "Bearer <token>",
                "received": auth_header[:20] + "..." if len(auth_header) > 20 else auth_header
            }

        token = auth_header.split(" ")[1]

        # Análisis del token
        token_analysis = {
            "token_length": len(token),
            "token_preview": token[:20] + "..." if len(token) > 20 else token,
            "has_dots": "." in token,
            "dot_count": token.count(".")
        }

        # Verificar estructura JWT
        if token.count(".") != 2:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Invalid JWT structure",
                "expected_dots": 2,
                "actual_dots": token.count("."),
                "token_analysis": token_analysis
            }

        # Decodificar sin verificar firma (para análisis)
        try:
            # Decodificar header
            header_encoded = token.split(".")[0]
            header_decoded = jwt.get_unverified_header(token)

            # Decodificar payload sin verificar
            payload_encoded = token.split(".")[1]
            payload_decoded = jwt.decode(token, options={"verify_signature": False})

            token_analysis.update({
                "header": header_decoded,
                "payload": payload_decoded,
                "payload_keys": list(payload_decoded.keys()),
                "user_id": payload_decoded.get("sub"),
                "token_type": payload_decoded.get("type"),
                "exp": payload_decoded.get("exp"),
                "iat": payload_decoded.get("iat")
            })

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Error decodificando token: {str(e)}",
                "token_analysis": token_analysis
            }

        # Verificar expiración
        exp_timestamp = payload_decoded.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            is_expired = datetime.now() > exp_datetime
            token_analysis["expiration"] = {
                "exp_datetime": exp_datetime.isoformat(),
                "is_expired": is_expired,
                "time_until_expiry": str(exp_datetime - datetime.now()) if not is_expired else "EXPIRED"
            }
        else:
            token_analysis["expiration"] = {
                "error": "No expiration found in token"
            }

        # Verificar con SECRET_KEY real
        verification_result = {}
        try:
            # Intentar decodificar con SECRET_KEY
            verified_payload = decode_token(token)
            verification_result = {
                "status": "success",
                "verified": True,
                "payload": verified_payload
            }
        except JWTError as e:
            verification_result = {
                "status": "error",
                "verified": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        except Exception as e:
            verification_result = {
                "status": "error",
                "verified": False,
                "error": str(e),
                "error_type": "Unknown"
            }

        # Verificar usuario en BD
        user_verification = {}
        if verification_result.get("verified"):
            user_id = verification_result["payload"].get("sub")
            if user_id:
                try:
                    user = db.query(User).filter(User.id == int(user_id)).first()
                    if user:
                        user_verification = {
                            "status": "success",
                            "user_found": True,
                            "user_email": user.email,
                            "user_active": user.is_active,
                            "user_admin": user.is_admin
                        }
                    else:
                        user_verification = {
                            "status": "error",
                            "user_found": False,
                            "error": f"User with ID {user_id} not found in database"
                        }
                except Exception as e:
                    user_verification = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                user_verification = {
                    "status": "error",
                    "error": "No user_id in token payload"
                }

        # Generar recomendaciones
        recommendations = []
        if not verification_result.get("verified"):
            recommendations.append("🔐 Token no válido - Verificar SECRET_KEY o regenerar token")

        if token_analysis.get("expiration", {}).get("is_expired"):
            recommendations.append("⏰ Token expirado - Hacer login nuevamente")

        if not user_verification.get("user_found"):
            recommendations.append("👤 Usuario no encontrado en BD - Verificar datos de usuario")

        if not user_verification.get("user_active"):
            recommendations.append("⚠️ Usuario inactivo - Contactar administrador")

        if not recommendations:
            recommendations.append("✅ Token válido y usuario correcto")

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "analysis_complete",
            "token_analysis": token_analysis,
            "verification": verification_result,
            "user_verification": user_verification,
            "recommendations": recommendations,
            "overall_status": "valid" if verification_result.get("verified") and user_verification.get("user_found") else "invalid"
        }

    except Exception as e:
        logger.error(f"Error en verificación de token: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/token-info")
async def obtener_info_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    📊 Información básica del token actual
    """
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "no_token",
                "message": "No valid token provided"
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
                        "admin": user.is_admin
                    }

            return {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "token_info": {
                    "user_id": user_id,
                    "token_type": payload.get("type"),
                    "exp": payload.get("exp"),
                    "iat": payload.get("iat"),
                    "user_info": user_info
                }
            }

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Error decoding token: {str(e)}"
            }

    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/generate-test-token")
async def generar_token_prueba(
    db: Session = Depends(get_db)
):
    """
    🧪 Generar token de prueba para testing
    """
    try:
        # Buscar usuario admin
        admin_user = db.query(User).filter(User.is_admin).first()
        if not admin_user:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "No admin user found"
            }

        # Generar token
        test_token = create_access_token(
            subject=str(admin_user.id),
            additional_claims={"type": "access"}
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "test_token": test_token,
            "user_info": {
                "id": admin_user.id,
                "email": admin_user.email,
                "active": admin_user.is_active,
                "admin": admin_user.is_admin
            },
            "usage": "Use this token in Authorization header: Bearer <token>"
        }

    except Exception as e:
        logger.error(f"Error generando token de prueba: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
