"""Sistema de Monitoreo en Tiempo Real para Autenticación
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

class RealTimeMonitor:
    """Monitor en tiempo real para autenticación"""
    
def __init__(self):
        self.request_logs = deque(maxlen=10000)  # Logs de requests
        self.token_analytics = deque(maxlen=5000)  # Análisis de tokens
        self.error_patterns = defaultdict(int)  # Patrones de error
        self.success_patterns = defaultdict(int)  # Patrones de éxito
        self.lock = threading.Lock()
        
        # Iniciar monitoreo en background
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Iniciar monitoreo en background"""        
        def monitoring_loop():
            while True:
                try:
                    self._analyze_recent_activity()
                    self._detect_anomalies()
                    time.sleep(60)  # Monitorear cada minuto
                except Exception as e:
                    logger.error(f"Error en monitoreo tiempo real: {e}")
                    time.sleep(120)
        
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🔍 Monitor tiempo real iniciado")
    
    def _analyze_recent_activity(self):
        """Analizar actividad reciente"""
        with self.lock:
            # Analizar requests de los últimos 5 minutos
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_requests = [
                req for req in self.request_logs
                if req["timestamp"] >= cutoff_time
            ]
            
            # Analizar patrones de éxito y error
            for request in recent_requests:
                if request["status_code"] >= 400:
                    self.error_patterns[request["endpoint"]] += 1
                else:
                    self.success_patterns[request["endpoint"]] += 1
    
    def _detect_anomalies(self):
        """Detectar anomalías en tiempo real"""
        with self.lock:
            # Detectar endpoints con alta tasa de error
            total_requests = sum(self.error_patterns.values()) + sum(self.success_patterns.values())
            
            if total_requests > 0:
                for endpoint, error_count in self.error_patterns.items():
                    success_count = self.success_patterns.get(endpoint, 0)
                    total_endpoint_requests = error_count + success_count
                    
                    if total_endpoint_requests > 10:  # Solo analizar endpoints con suficiente tráfico
                        error_rate = error_count / total_endpoint_requests
                        
                        if error_rate > 0.5:  # Más del 50% de errores
                            logger.warning(
                                f"⚠️ Alta tasa de error detectada en {endpoint}: "
                                f"{error_rate:.2%} ({error_count}/{total_endpoint_requests})"
                            )
    
    def log_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: str = None,
        response_time_ms: float = None,
        details: Dict[str, Any] = None
    ):
        """Registrar un request"""
        with self.lock:
            request_log = {
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "user_id": user_id,
                "response_time_ms": response_time_ms,
                "details": details or {},
            }
            self.request_logs.append(request_log)
    
    def analyze_token(self, token: str) -> Dict[str, Any]:
        """Analizar un token"""
        try:
            payload = decode_token(token)
            current_time = datetime.now().timestamp()
            
            analysis = {
                "token_valid": True,
                "user_id": payload.get("sub"),
                "token_type": payload.get("type"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "time_to_expiry": payload.get("exp", 0) - current_time,
                "analysis_timestamp": datetime.now().isoformat(),
            }
            
            # Agregar al análisis de tokens
            with self.lock:
                self.token_analytics.append(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando token: {e}")
            return {
                "token_valid": False,
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
            }
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas en tiempo real"""
        with self.lock:
            return {
                "total_requests": len(self.request_logs),
                "total_token_analyses": len(self.token_analytics),
                "error_patterns": dict(self.error_patterns),
                "success_patterns": dict(self.success_patterns),
                "last_update": datetime.now().isoformat(),
            }

# Instancia global del monitor tiempo real
realtime_monitor = RealTimeMonitor()

# ============================================
# ENDPOINTS DEL MONITOR TIEMPO REAL
# ============================================

@router.post("/realtime/log-request", status_code=201)
async def log_request(
    endpoint: str,
    method: str,
    status_code: int,
    user_id: str = None,
    response_time_ms: float = None,
    details: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
):
    """Registrar un request"""
    realtime_monitor.log_request(
        endpoint, method, status_code, user_id, response_time_ms, details
    )
    return {"message": "Request registrado"}

@router.post("/realtime/analyze-token", response_model=Dict[str, Any])
async def analyze_token(
    token: str,
    current_user: User = Depends(get_current_user),
):
    """Analizar un token"""
    return realtime_monitor.analyze_token(token)

@router.get("/realtime/stats", response_model=Dict[str, Any])
async def get_realtime_stats(
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas en tiempo real"""
    return realtime_monitor.get_realtime_stats()