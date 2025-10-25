from app.core.security import decode_token
﻿"""Endpoint de diagnóstico específico para problemas de refresh token
"""

import logging
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import 
)
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Funcion compleja - considerar refactoring


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
            return 
            }

        logger.info(f"🔍 Refresh token recibido: {refresh_token[:20]}...")

        # 1. Verificar formato del token
        try:
            # Decodificar sin verificar para obtener información básica
            payload_unverified = jwt.decode
            )
            token_info = 
            }

            # Verificar si está expirado
            if payload_unverified.get("exp"):
                    if not token_info["expired"]
                    else "EXPIRED"
                )

        except Exception as e:
            token_info = 
            }

        # 2. Verificar con la función decode_token del sistema
        try:
            decoded_payload = decode_token(refresh_token)
            system_validation = 
            }
        except Exception as e:
            system_validation = 
            }

        # 3. Verificar configuración JWT
        config_check = 
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

        # 5. Resultado del diagnóstico
        resultado = 
        }

        logger.info("🔍 Diagnóstico de refresh token completado")

        return 
        }

    except Exception as e:
        logger.error(f"🔍 Error en diagnóstico de refresh token: {e}")
        return 
            }
        }

async def test_refresh_token
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
#             decoded = decode_token(nuevo_refresh_token)  # Variable no usada
            validation_success = True
            validation_error = None
        except Exception as e:
            validation_success = False
            validation_error = str(e)

        resultado = 
            }
        }

        logger.info("🧪 Test de refresh token completado")

        return 
        }

    except Exception as e:
        logger.error(f"🧪 Error en test de refresh token: {e}")
        return 
        }

@router.get("/refresh-token-config")
async def get_refresh_token_config
    current_user: User = Depends(get_current_user)
):
    """⚙️ Obtener configuración de refresh token"""
    try:
        config = 
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

        return 
        }

    except Exception as e:
        logger.error(f"⚙️ Error obteniendo configuración: {e}")
        return 
        }
