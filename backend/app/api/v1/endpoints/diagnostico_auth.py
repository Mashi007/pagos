"""
🔍 Endpoint de Diagnóstico Avanzado de Autenticación
Sistema de auditoría para encontrar causa raíz de problemas 401
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import jwt
import json
from jose import JWTError

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.security import decode_token, create_access_token
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache para requests fallidos
failed_requests_cache = []

@router.get("/auth-debug")
async def debug_autenticacion(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔍 Diagnóstico completo de autenticación
    Analiza tokens, headers, y configuración
    """
    try:
        # 1. Analizar headers de la request
        headers_analysis = {}
        auth_header = request.headers.get("authorization")

        if auth_header:
            headers_analysis["authorization_present"] = True
            headers_analysis["authorization_type"] = auth_header.split(" ")[0] if " " in auth_header else "unknown"
            headers_analysis["token_length"] = len(auth_header.split(" ")[1]) if " " in auth_header else 0
        else:
            headers_analysis["authorization_present"] = False

        # 2. Verificar configuración JWT
        jwt_config = {
            "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
            "algorithm": settings.ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS
        }

        # 3. Verificar usuarios en BD
        users_analysis = {}
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            admin_users = db.query(User).filter(User.is_admin == True).count()

            users_analysis = {
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "status": "ok"
            }
        except Exception as e:
            users_analysis = {
                "status": "error",
                "error": str(e)
            }

        # 4. Verificar tokens recientes (simulado)
        recent_tokens_analysis = {
            "failed_requests_last_hour": len([r for r in failed_requests_cache if r.get("timestamp", datetime.min) > datetime.now() - timedelta(hours=1)]),
            "total_failed_requests": len(failed_requests_cache),
            "last_failed_request": failed_requests_cache[-1] if failed_requests_cache else None
        }

        # 5. Test de creación de token
        token_test = {}
        try:
            # Buscar usuario admin para test
            admin_user = db.query(User).filter(User.is_admin == True).first()
            if admin_user:
                test_token = create_access_token(
                    subject=str(admin_user.id),
                    additional_claims={"type": "access"}
                )
                token_test = {
                    "status": "success",
                    "token_created": True,
                    "token_length": len(test_token),
                    "test_user_id": admin_user.id,
                    "test_user_email": admin_user.email
                }
            else:
                token_test = {
                    "status": "error",
                    "error": "No admin user found"
                }
        except Exception as e:
            token_test = {
                "status": "error",
                "error": str(e)
            }

        # 6. Verificar CORS y headers de seguridad
        cors_analysis = {
            "cors_origins": settings.CORS_ORIGINS,
            "cors_origins_count": len(settings.CORS_ORIGINS),
            "environment": settings.ENVIRONMENT
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "diagnostic_complete",
            "analysis": {
                "headers": headers_analysis,
                "jwt_config": jwt_config,
                "users": users_analysis,
                "recent_tokens": recent_tokens_analysis,
                "token_test": token_test,
                "cors": cors_analysis
            },
            "recommendations": _generate_recommendations(headers_analysis, jwt_config, users_analysis)
        }

    except Exception as e:
        logger.error(f"Error en diagnóstico de autenticación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/auth-test")
async def test_autenticacion(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🧪 Test completo de autenticación
    Prueba login, token creation, y validación
    """
    try:
        # 1. Test de login
        login_test = {}
        try:
            admin_user = db.query(User).filter(User.is_admin == True).first()
            if admin_user:
                # Simular login
                test_token = create_access_token(
                    subject=str(admin_user.id),
                    additional_claims={"type": "access"}
                )
                login_test = {
                    "status": "success",
                    "user_found": True,
                    "user_email": admin_user.email,
                    "user_active": admin_user.is_active,
                    "token_generated": True,
                    "token_length": len(test_token)
                }
            else:
                login_test = {
                    "status": "error",
                    "error": "No admin user found"
                }
        except Exception as e:
            login_test = {
                "status": "error",
                "error": str(e)
            }

        # 2. Test de validación de token
        validation_test = {}
        try:
            if login_test.get("status") == "success":
                # Decodificar el token creado
                decoded = decode_token(test_token)
                validation_test = {
                    "status": "success",
                    "token_decoded": True,
                    "user_id_from_token": decoded.get("sub"),
                    "token_type": decoded.get("type"),
                    "exp": decoded.get("exp")
                }
            else:
                validation_test = {
                    "status": "skipped",
                    "reason": "Login test failed"
                }
        except Exception as e:
            validation_test = {
                "status": "error",
                "error": str(e)
            }

        # 3. Test de endpoint protegido
        protected_test = {}
        try:
            if validation_test.get("status") == "success":
                # Simular request con token
                user_id = validation_test.get("user_id_from_token")
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user:
                    protected_test = {
                        "status": "success",
                        "user_found_in_db": True,
                        "user_email": user.email,
                        "user_active": user.is_active
                    }
                else:
                    protected_test = {
                        "status": "error",
                        "error": "User not found in DB"
                    }
            else:
                protected_test = {
                    "status": "skipped",
                    "reason": "Validation test failed"
                }
        except Exception as e:
            protected_test = {
                "status": "error",
                "error": str(e)
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "test_complete",
            "tests": {
                "login": login_test,
                "validation": validation_test,
                "protected_endpoint": protected_test
            },
            "overall_status": "success" if all(t.get("status") == "success" for t in [login_test, validation_test, protected_test]) else "failed"
        }

    except Exception as e:
        logger.error(f"Error en test de autenticación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/auth-logs")
async def obtener_logs_autenticacion():
    """
    📝 Obtener logs de autenticación recientes
    """
    try:
        # Filtrar logs de la última hora
        recent_logs = [
            log for log in failed_requests_cache 
            if log.get("timestamp", datetime.min) > datetime.now() - timedelta(hours=1)
        ]

        # Agrupar por tipo de error
        error_summary = {}
        for log in recent_logs:
            error_type = log.get("error_type", "unknown")
            error_summary[error_type] = error_summary.get(error_type, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "logs": {
                "total_recent_logs": len(recent_logs),
                "error_summary": error_summary,
                "recent_requests": recent_logs[-10:] if recent_logs else []  # Últimos 10
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo logs de autenticación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/auth-fix")
async def aplicar_fix_autenticacion(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔧 Aplicar fixes automáticos de autenticación
    """
    try:
        fixes_applied = []

        # 1. Verificar y recrear usuario admin si es necesario
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if not admin_user:
            # Crear usuario admin
            from app.core.security import get_password_hash
            new_admin = User(
                email=settings.ADMIN_EMAIL,
                password=get_password_hash(settings.ADMIN_PASSWORD),
                nombre="Admin",
                apellido="Sistema",
                is_admin=True,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            fixes_applied.append("admin_user_created")
        else:
            # Asegurar que esté activo
            if not admin_user.is_active:
                admin_user.is_active = True
                db.commit()
                fixes_applied.append("admin_user_activated")

        # 2. Limpiar cache de requests fallidos
        failed_requests_cache.clear()
        fixes_applied.append("failed_requests_cache_cleared")

        # 3. Verificar configuración JWT
        if not settings.SECRET_KEY:
            fixes_applied.append("jwt_secret_key_missing")

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "fixes_applied",
            "fixes": fixes_applied,
            "message": f"Aplicados {len(fixes_applied)} fixes"
        }

    except Exception as e:
        logger.error(f"Error aplicando fixes: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

def _generate_recommendations(headers_analysis: Dict, jwt_config: Dict, users_analysis: Dict) -> List[str]:
    """Generar recomendaciones basadas en el análisis"""
    recommendations = []

    if not headers_analysis.get("authorization_present"):
        recommendations.append("🔑 No se encontró header Authorization - Verificar que el frontend esté enviando el token")

    if jwt_config.get("secret_key_length", 0) < 32:
        recommendations.append("🔐 SECRET_KEY muy corta - Debe tener al menos 32 caracteres")

    if users_analysis.get("admin_users", 0) == 0:
        recommendations.append("👤 No hay usuarios administradores - Crear usuario admin")

    if users_analysis.get("active_users", 0) == 0:
        recommendations.append("⚠️ No hay usuarios activos - Verificar estado de usuarios")

    if not recommendations:
        recommendations.append("✅ Configuración parece correcta - Revisar logs de aplicación")

    return recommendations

# Nota: Middleware removido - APIRouter no soporta middleware directamente
# El middleware debe ser agregado a la aplicación principal en main.py
