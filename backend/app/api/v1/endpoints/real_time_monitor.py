from collections import deque
﻿"""Sistema de Monitoreo en Tiempo Real para Autenticación
Análisis continuo de tokens, requests y patrones de error
"""

import logging
import threading
from collections import defaultdict, deque
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request
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
                except Exception as e:
                    logger.error(f"Error en monitoreo tiempo real: {e}")

        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🔍 Monitor tiempo real iniciado")


    def _analyze_recent_activity(self):
        """Analizar actividad reciente"""
        with self.lock:
            recent_requests = [
                req for req in self.request_logs
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
                            logger.warning
                                f"{error_rate:.2%} ({error_count}/{total_endpoint_requests})"
                            )


    def log_request
    ):
        """Registrar un request"""
        with self.lock:
            request_log = 
                "details": details or {},
            }
            self.request_logs.append(request_log)


    def analyze_token(self, token: str) -> Dict[str, Any]:
        """Analizar un token"""
        try:
            payload = decode_token(token)

            analysis = 
            }

            # Agregar al análisis de tokens
            with self.lock:
                self.token_analytics.append(analysis)

            return analysis

        except Exception as e:
            logger.error(f"Error analizando token: {e}")
            return 
            }


        """Obtener estadísticas en tiempo real"""
        with self.lock:
            return 
            }

# Instancia global del monitor tiempo real

# ============================================
# ENDPOINTS DEL MONITOR TIEMPO REAL
# ============================================

async def log_request
    current_user: User = Depends(get_current_user),
):
    """Registrar un request"""
    )
    return {"message": "Request registrado"}

async def analyze_token
    current_user: User = Depends(get_current_user),
):
    """Analizar un token"""

    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas en tiempo real"""
