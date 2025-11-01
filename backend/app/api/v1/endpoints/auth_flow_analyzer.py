# Sistema de Análisis de Flujo de Autenticación
# Tracing avanzado y análisis de causa raíz para problemas de autenticación

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacenamiento en memoria para análisis
auth_flow_cache = defaultdict(list)
failed_attempts = defaultdict(list)
successful_logins = defaultdict(list)


class AuthFlowAnalyzer:
    """Analizador de flujo de autenticación"""

    def __init__(self):
        self.max_cache_size = 1000
        self.analysis_window = timedelta(hours=24)

    def log_auth_attempt(self, user_email: str, success: bool, details: Dict[str, Any]):
        """Registrar intento de autenticación"""
        timestamp = datetime.now()
        attempt = {
            "timestamp": timestamp,
            "success": success,
            "details": details,
            "session_id": str(uuid.uuid4()),
        }

        if success:
            successful_logins[user_email].append(attempt)
        else:
            failed_attempts[user_email].append(attempt)

        # Limpiar cache antiguo
        self._cleanup_old_entries()

    def _cleanup_old_entries(self):
        """Limpiar entradas antiguas"""
        cutoff = datetime.now() - self.analysis_window

        for user_email in list(failed_attempts.keys()):
            failed_attempts[user_email] = [attempt for attempt in failed_attempts[user_email] if attempt["timestamp"] > cutoff]
            if not failed_attempts[user_email]:
                del failed_attempts[user_email]

        for user_email in list(successful_logins.keys()):
            successful_logins[user_email] = [
                attempt for attempt in successful_logins[user_email] if attempt["timestamp"] > cutoff
            ]
            if not successful_logins[user_email]:
                del successful_logins[user_email]

    def analyze_user_patterns(self, user_email: str) -> Dict[str, Any]:
        """Analizar patrones de un usuario específico"""
        failed = failed_attempts.get(user_email, [])
        successful = successful_logins.get(user_email, [])

        if not failed and not successful:
            return {"message": "No hay datos de autenticación para este usuario"}

        # Análisis de patrones
        analysis = {
            "user_email": user_email,
            "total_failed_attempts": len(failed),
            "total_successful_logins": len(successful),
            "success_rate": (len(successful) / (len(failed) + len(successful)) * 100 if (failed or successful) else 0),
            "last_failed_attempt": (failed[-1]["timestamp"].isoformat() if failed else None),
            "last_successful_login": (successful[-1]["timestamp"].isoformat() if successful else None),
        }

        # Detectar patrones sospechosos
        if len(failed) > 5:
            analysis["risk_level"] = "HIGH"
            analysis["recommendation"] = "Considerar bloqueo temporal o verificación adicional"
        elif len(failed) > 2:
            analysis["risk_level"] = "MEDIUM"
            analysis["recommendation"] = "Monitorear actividad"
        else:
            analysis["risk_level"] = "LOW"
            analysis["recommendation"] = "Actividad normal"

        return analysis

    def get_system_overview(self) -> Dict[str, Any]:
        """Obtener resumen del sistema"""
        total_failed = sum(len(attempts) for attempts in failed_attempts.values())
        total_successful = sum(len(attempts) for attempts in successful_logins.values())

        # Usuarios con más intentos fallidos
        top_failed_users = sorted(
            [(email, len(attempts)) for email, attempts in failed_attempts.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return {
            "total_failed_attempts": total_failed,
            "total_successful_logins": total_successful,
            "unique_users_with_failed_attempts": len(failed_attempts),
            "unique_users_with_successful_logins": len(successful_logins),
            "top_failed_users": top_failed_users,
            "analysis_window_hours": self.analysis_window.total_seconds() / 3600,
        }


# Instancia global del analizador
analyzer = AuthFlowAnalyzer()


@router.get("/auth-analysis/overview")
def get_auth_overview(
    current_user: User = Depends(get_current_user),
):
    # Obtener resumen del análisis de autenticación
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden acceder a este análisis",
        )

    try:
        overview = analyzer.get_system_overview()
        return overview

    except Exception as e:
        logger.error(f"Error obteniendo resumen de autenticación: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/auth-analysis/user/{user_email}")
def analyze_user_auth_patterns(
    user_email: str,
    current_user: User = Depends(get_current_user),
):
    # Analizar patrones de autenticación de un usuario específico
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden acceder a este análisis",
        )

    try:
        analysis = analyzer.analyze_user_patterns(user_email)
        return analysis

    except Exception as e:
        logger.error(f"Error analizando patrones de usuario {user_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/auth-analysis/log-attempt")
def log_auth_attempt(
    user_email: str,
    success: bool,
    details: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    # Registrar intento de autenticación para análisis
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden registrar intentos")

    try:
        analyzer.log_auth_attempt(user_email, success, details)
        return {"message": "Intento registrado exitosamente"}

    except Exception as e:
        logger.error(f"Error registrando intento: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/auth-analysis/risky-users")
def get_risky_users(
    current_user: User = Depends(get_current_user),
):
    # Obtener lista de usuarios con actividad sospechosa
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden acceder a esta información",
        )

    try:
        risky_users = []

        for user_email, attempts in failed_attempts.items():
            if len(attempts) > 3:  # Más de 3 intentos fallidos
                analysis = analyzer.analyze_user_patterns(user_email)
                risky_users.append(analysis)

        # Ordenar por número de intentos fallidos
        risky_users.sort(key=lambda x: x["total_failed_attempts"], reverse=True)

        return {"risky_users": risky_users, "total_risky_users": len(risky_users)}

    except Exception as e:
        logger.error(f"Error obteniendo usuarios de riesgo: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
