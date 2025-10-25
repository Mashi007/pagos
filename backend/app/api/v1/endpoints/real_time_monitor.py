"""
Sistema de Monitoreo en Tiempo Real para Autenticación
Análisis continuo de tokens, requests y patrones de error
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE MONITOREO EN TIEMPO REAL
# ============================================


class RealTimeAuthMonitor:
    """Monitor de autenticación en tiempo real"""

    def __init__(self):
        self.request_history = deque(maxlen=1000)  # Últimos 1000 requests
        self.token_analysis = defaultdict(list)  # Análisis por token
        self.error_patterns = defaultdict(int)  # Patrones de error
        self.performance_metrics = deque(maxlen=100)  # Métricas de rendimiento
        self.active_sessions = {}  # Sesiones activas
        self.lock = threading.Lock()

        # Iniciar monitoreo en background
        self._start_background_monitoring()

    def _start_background_monitoring(self):
        """Iniciar monitoreo en background"""

        def monitor_loop():
            while True:
                try:
                    self._analyze_patterns()
                    self._cleanup_expired_sessions()
                    time.sleep(30)  # Analizar cada 30 segundos
                except Exception as e:
                    logger.error(f"Error en monitoreo background: {e}")
                    time.sleep(60)  # Esperar más tiempo si hay error

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("🔍 Monitor de autenticación en tiempo real iniciado")

    def log_request(self, request_data: Dict[str, Any]):
        """Registrar request para análisis"""
        with self.lock:
            request_data["timestamp"] = datetime.now()
            self.request_history.append(request_data)

            # Analizar token si está presente
            if "token" in request_data:
                self._analyze_token(request_data["token"], request_data)

    def _analyze_token(self, token: str, request_data: Dict[str, Any]):
        """Analizar token específico"""
        try:
            payload = decode_token(token)
            token_id = f"{payload.get('sub')}_{payload.get('exp')}"

            analysis = {
                "token_id": token_id,
                "user_id": payload.get("sub"),
                "exp": payload.get("exp"),
                "type": payload.get("type"),
                "request_time": request_data["timestamp"],
                "endpoint": request_data.get("endpoint"),
                "success": request_data.get("success", True),
            }

            self.token_analysis[token_id].append(analysis)

            # Mantener solo últimos 50 análisis por token
            if len(self.token_analysis[token_id]) > 50:
                self.token_analysis[token_id] = self.token_analysis[token_id][-50:]

        except Exception as e:
            logger.error(f"Error analizando token: {e}")

    def _analyze_patterns(self):
        """Analizar patrones en tiempo real"""
        with self.lock:
            # Analizar últimos 5 minutos
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_requests = [req for req in self.request_history if req["timestamp"] > cutoff_time]

            # Contar errores por tipo
            error_counts = defaultdict(int)
            for req in recent_requests:
                if not req.get("success", True):
                    error_type = req.get("error_type", "unknown")
                    error_counts[error_type] += 1

            # Actualizar patrones de error
            for error_type, count in error_counts.items():
                self.error_patterns[error_type] += count

            # Limpiar patrones antiguos
            if len(self.error_patterns) > 100:
                # Mantener solo los más frecuentes
                sorted_patterns = sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)
                self.error_patterns = dict(sorted_patterns[:50])

    def _cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session_data in self.active_sessions.items():
            if session_data.get("expires_at", current_time) < current_time:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

    def get_real_time_status(self) -> Dict[str, Any]:
        """Obtener estado en tiempo real"""
        with self.lock:
            current_time = datetime.now()

            # Análisis de últimos 5 minutos
            cutoff_time = current_time - timedelta(minutes=5)
            recent_requests = [req for req in self.request_history if req["timestamp"] > cutoff_time]

            # Estadísticas básicas
            total_requests = len(recent_requests)
            failed_requests = len([req for req in recent_requests if not req.get("success", True)])
            success_rate = ((total_requests - failed_requests) / total_requests * 100) if total_requests > 0 else 100

            # Análisis de tokens
            active_tokens = len(self.token_analysis)
            expiring_tokens = 0

            for token_id, analyses in self.token_analysis.items():
                if analyses:
                    latest_analysis = analyses[-1]
                    exp_time = datetime.fromtimestamp(latest_analysis["exp"])
                    if exp_time < current_time + timedelta(minutes=5):  # Expira en 5 minutos
                        expiring_tokens += 1

            return {
                "timestamp": current_time.isoformat(),
                "status": "monitoring_active",
                "metrics": {
                    "total_requests_5min": total_requests,
                    "failed_requests_5min": failed_requests,
                    "success_rate_percent": round(success_rate, 2),
                    "active_tokens": active_tokens,
                    "expiring_tokens": expiring_tokens,
                    "active_sessions": len(self.active_sessions),
                    "error_patterns_count": len(self.error_patterns),
                },
                "recent_errors": dict(list(self.error_patterns.items())[:10]),
                "performance": {
                    "avg_response_time": self._calculate_avg_response_time(),
                    "peak_error_rate": self._calculate_peak_error_rate(),
                },
            }

    def _calculate_avg_response_time(self) -> float:
        """Calcular tiempo promedio de respuesta"""
        if not self.performance_metrics:
            return 0.0

        total_time = sum(metric.get("response_time", 0) for metric in self.performance_metrics)
        return round(total_time / len(self.performance_metrics), 2)

    def _calculate_peak_error_rate(self) -> float:
        """Calcular tasa máxima de errores"""
        if not self.performance_metrics:
            return 0.0

        error_count = sum(1 for metric in self.performance_metrics if not metric.get("success", True))
        return round((error_count / len(self.performance_metrics)) * 100, 2)


# Instancia global del monitor
auth_monitor = RealTimeAuthMonitor()

# ============================================
# ENDPOINTS DE MONITOREO
# ============================================


@router.get("/real-time-status")
async def get_real_time_status():
    """
    📊 Estado en tiempo real del sistema de autenticación
    """
    try:
        status = auth_monitor.get_real_time_status()
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "data": status,
        }
    except Exception as e:
        logger.error(f"Error obteniendo estado en tiempo real: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/token-analysis/{user_id}")
async def analyze_user_tokens(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Análisis detallado de tokens de un usuario específico
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Usuario no encontrado",
            }

        # Buscar análisis de tokens para este usuario
        user_token_analyses = []
        for token_id, analyses in auth_monitor.token_analysis.items():
            if analyses and str(analyses[0]["user_id"]) == str(user_id):
                user_token_analyses.extend(analyses)

        # Ordenar por tiempo más reciente
        user_token_analyses.sort(key=lambda x: x["request_time"], reverse=True)

        # Análisis estadístico
        total_requests = len(user_token_analyses)
        successful_requests = len([a for a in user_token_analyses if a.get("success", True)])
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

        # Endpoints más usados
        endpoint_usage = defaultdict(int)
        for analysis in user_token_analyses:
            endpoint_usage[analysis.get("endpoint", "unknown")] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
            },
            "analysis": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate_percent": round(success_rate, 2),
                "most_used_endpoints": dict(sorted(endpoint_usage.items(), key=lambda x: x[1], reverse=True)[:10]),
                "recent_requests": user_token_analyses[:20],  # Últimos 20 requests
            },
        }

    except Exception as e:
        logger.error(f"Error analizando tokens del usuario: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/log-request")
async def log_request_data(request: Request, request_data: Dict[str, Any]):
    """
    📝 Endpoint para registrar datos de request (usado por middleware)
    """
    try:
        # Agregar información adicional del request
        enhanced_data = {
            **request_data,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "endpoint": str(request.url.path),
            "method": request.method,
        }

        auth_monitor.log_request(enhanced_data)

        return {"timestamp": datetime.now().isoformat(), "status": "logged"}

    except Exception as e:
        logger.error(f"Error registrando request: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/error-patterns")
async def get_error_patterns():
    """
    🚨 Patrones de error detectados
    """
    try:
        with auth_monitor.lock:
            patterns = dict(auth_monitor.error_patterns)

        # Ordenar por frecuencia
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "patterns": sorted_patterns,
            "total_patterns": len(patterns),
            "most_common_error": sorted_patterns[0] if sorted_patterns else None,
        }

    except Exception as e:
        logger.error(f"Error obteniendo patrones de error: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/performance-metrics")
async def get_performance_metrics():
    """
    ⚡ Métricas de rendimiento del sistema
    """
    try:
        status = auth_monitor.get_real_time_status()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "metrics": status["metrics"],
            "performance": status["performance"],
            "recommendations": _generate_performance_recommendations(status),
        }

    except Exception as e:
        logger.error(f"Error obteniendo métricas de rendimiento: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


def _generate_performance_recommendations(status: Dict[str, Any]) -> List[str]:
    """Generar recomendaciones basadas en métricas"""
    recommendations = []
    metrics = status.get("metrics", {})

    success_rate = metrics.get("success_rate_percent", 100)
    if success_rate < 95:
        recommendations.append(f"⚠️ Tasa de éxito baja ({success_rate}%) - Revisar configuración de tokens")

    expiring_tokens = metrics.get("expiring_tokens", 0)
    if expiring_tokens > 0:
        recommendations.append(f"🔄 {expiring_tokens} tokens expirando pronto - Verificar auto-refresh")

    avg_response_time = status.get("performance", {}).get("avg_response_time", 0)
    if avg_response_time > 2.0:
        recommendations.append(f"🐌 Tiempo de respuesta alto ({avg_response_time}s) - Optimizar queries")

    if not recommendations:
        recommendations.append("✅ Sistema funcionando correctamente")

    return recommendations
