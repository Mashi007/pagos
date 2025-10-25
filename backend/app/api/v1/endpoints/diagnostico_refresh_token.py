"""Endpoint de diagnóstico específico para problemas de refresh token
"""

import logging
from datetime import datetime
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from jwt import PyJWTError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/diagnosticar-refresh-token")
async def diagnosticar_refresh_token(
    request: Request, 
    db: Session = Depends(get_db)
):
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
                "recomendacion": (
                    "Verificar que el frontend esté enviando el refresh_token "
                    "correctamente"
                ),
            }
        
        logger.info(f"🔍 Refresh token recibido: {refresh_token[:20]}...")
        
        # 1. Verificar formato del token
        try:
            # Decodificar sin verificar para obtener información básica
            payload_unverified = jwt.decode(
                refresh_token, options={"verify_signature": False}
            )
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
                token_info["time_until_expiry"] = (
                    str(exp_datetime - now)
                    if not token_info["expired"]
                    else "EXPIRED"
                )
                
        except Exception as e:
            token_info = {
                "formato_valido": False,
                "error": str(e),
            }
        
        # 2. Verificar con la función decode_token del sistema
        try:
            decoded_payload = decode_token(refresh_token)
            system_validation = {
                "valido_segun_sistema": True,
                "payload": decoded_payload,
            }
        except Exception as e:
            system_validation = {
                "valido_segun_sistema": False,
                "error": str(e),
            }
        
        # 3. Verificar configuración JWT
        config_check = {
            "secret_key_configurado": bool(settings.SECRET_KEY),
            "algorithm_configurado": bool(settings.ALGORITHM),
            "algorithm": settings.ALGORITHM,
        }
        
        # 4. Generar recomendaciones
        recomendaciones = []
        
        if not token_info.get("formato_valido"):
            recomendaciones.append("Token malformado - verificar formato JWT")
        
        if token_info.get("expired"):
            recomendaciones.append("Token expirado - solicitar nuevo refresh token")
        
        if not system_validation.get("valido_segun_sistema"):
            recomendaciones.append("Token inválido según sistema - verificar configuración")
        
        if not config_check["secret_key_configurado"]:
            recomendaciones.append("SECRET_KEY no configurado")
        
        if not config_check["algorithm_configurado"]:
            recomendaciones.append("ALGORITHM no configurado")
        
        if not recomendaciones:
            recomendaciones.append("Token parece válido - revisar otros aspectos del sistema")
        
        # 5. Resultado del diagnóstico
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "token_info": token_info,
            "system_validation": system_validation,
            "config_check": config_check,
            "recomendaciones": recomendaciones,
            "diagnostico_completo": True,
        }
        
        logger.info("🔍 Diagnóstico de refresh token completado")
        
        return {
            "success": True,
            "diagnostico": resultado
        }
        
    except Exception as e:
        logger.error(f"🔍 Error en diagnóstico de refresh token: {e}")
        return {
            "success": False,
            "error": str(e),
            "diagnostico": {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "recomendacion": "Revisar logs del servidor para más detalles"
            }
        }

@router.post("/test-refresh-token")
async def test_refresh_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """🧪 Probar generación y validación de refresh token"""
    try:
        logger.info("🧪 Iniciando test de refresh token")
        
        # Generar nuevo refresh token
        nuevo_refresh_token = create_refresh_token(data={"sub": current_user.id})
        
        # Intentar decodificarlo
        try:
            decoded = decode_token(nuevo_refresh_token)
            validation_success = True
            validation_error = None
        except Exception as e:
            validation_success = False
            validation_error = str(e)
        
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "nuevo_token_generado": True,
            "token_preview": nuevo_refresh_token[:50] + "...",
            "validacion_exitosa": validation_success,
            "validation_error": validation_error,
            "user_id": current_user.id,
            "configuracion": {
                "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
                "algorithm": settings.ALGORITHM,
            }
        }
        
        logger.info("🧪 Test de refresh token completado")
        
        return {
            "success": True,
            "test_result": resultado
        }
        
    except Exception as e:
        logger.error(f"🧪 Error en test de refresh token: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/refresh-token-config")
async def get_refresh_token_config(
    current_user: User = Depends(get_current_user)
):
    """⚙️ Obtener configuración de refresh token"""
    try:
        config = {
            "timestamp": datetime.now().isoformat(),
            "secret_key_configured": bool(settings.SECRET_KEY),
            "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
            "algorithm": settings.ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "recommendations": []
        }
        
        # Generar recomendaciones
        if not settings.SECRET_KEY:
            config["recommendations"].append("Configurar SECRET_KEY")
        
        if not settings.ALGORITHM:
            config["recommendations"].append("Configurar ALGORITHM")
        
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES < 15:
            config["recommendations"].append("Considerar aumentar tiempo de expiración del token")
        
        if not config["recommendations"]:
            config["recommendations"].append("Configuración parece correcta")
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"⚙️ Error obteniendo configuración: {e}")
        return {
            "success": False,
            "error": str(e)
        }