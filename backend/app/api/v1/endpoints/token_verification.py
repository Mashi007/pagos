import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/verify-token")
def verificar_token(
    token: str,
    db: Session = Depends(get_db),
):
    # Verificar si un token es válido
    try:
        # Decodificar token
        payload = decode_token(token)

        if not payload:
            return {"valid": False, "message": "Token inválido o expirado"}

        # Obtener usuario
        user_id = payload.get("sub")
        if not user_id:
            return {"valid": False, "message": "Token malformado"}

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return {"valid": False, "message": "Usuario no encontrado"}

        return {
            "valid": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "activo": user.activo,
            },
            "expires_at": datetime.fromtimestamp(payload.get("exp", 0)).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        return {"valid": False, "message": f"Error interno: {str(e)}"}


@router.post("/refresh-token")
def renovar_token(
    current_user: User = Depends(get_current_user),
):
    # Renovar token de acceso
    try:
        # Generar nuevo token
        new_token = create_access_token(
            subject=str(current_user.id), additional_claims={"type": "access"}
        )

        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hora
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin,
            },
        }

    except Exception as e:
        logger.error(f"Error renovando token: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/token-info")
def obtener_info_token(
    current_user: User = Depends(get_current_user),
):
    # Obtener información del token actual
    try:
        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin,
                "activo": current_user.activo,
            },
            "token_type": "bearer",
            "authenticated": True,
        }

    except Exception as e:
        logger.error(f"Error obteniendo info del token: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/generar-token-prueba")
async def generar_token_prueba(db: Session = Depends(get_db)):
    # Generar token de prueba para testing
    try:
        # Buscar usuario admin
        admin_user = db.query(User).filter(User.is_admin).first()
        if not admin_user:
            return {"error": "No se encontró usuario administrador"}

        # Generar token
        test_token = create_access_token(
            subject=str(admin_user.id), additional_claims={"type": "access"}
        )

        return {
            "token": test_token,
            "user": {
                "id": admin_user.id,
                "email": admin_user.email,
                "is_admin": admin_user.is_admin,
            },
            "usage": "Use this token in Authorization header: Bearer <token>",
            "expires_in": "1 hour",
        }

    except Exception as e:
        logger.error(f"Error generando token de prueba: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
