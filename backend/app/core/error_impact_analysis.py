from collections import deque
from datetime import date
﻿"""Sistema de Manejo de Errores con Análisis de Impacto en Performance
Implementa manejo robusto de errores con métricas de impacto
"""

import logging
import threading
import traceback
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Constantes de configuración
ERROR_RETENTION_HOURS = 24
MAX_ERROR_HISTORY = 1000
ERROR_RATE_THRESHOLD = 0.05  # 5% de tasa de error
MAX_CONSECUTIVE_ERRORS = 5

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severidad de errores"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ErrorMetrics:
    """Métricas de un error"""
    error_type: str
    error_message: str
    endpoint: str
    cpu_usage_percent: float
    memory_usage_percent: float
    severity: ErrorSeverity
    stack_trace: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None

@dataclass
class ErrorImpactAnalysis:
    """Análisis de impacto de errores"""
    error_rate: float
    system_impact_level: str
    consecutive_errors: int
    circuit_breaker_status: str
    recommendations: list


class CircuitBreaker:
    """
    Circuit Breaker para prevenir cascadas de errores
    """


    def __init__
    ):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN


    def call(self, func: Callable, *args, **kwargs):
        """Ejecutar función con circuit breaker"""
        if self.state == "OPEN":
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e


    def _on_success(self):
        """Manejar éxito"""
        self.failure_count = 0
        self.state = "CLOSED"


    def _on_failure(self):
        """Manejar fallo"""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorImpactAnalyzer:
    """
    Analizador de impacto de errores en el sistema
    """


    def __init__(self):
        self.error_history: deque = deque(maxlen=MAX_ERROR_HISTORY)
        self.endpoint_errors: Dict[str, deque] = defaultdict
            lambda: deque(maxlen=100)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests = 0
        self.lock = threading.Lock()


    def record_error
    ):
        """Registrar un error con métricas de impacto"""
        with self.lock:
            # Obtener métricas del sistema
            cpu_usage = psutil.cpu_percent() if PSUTIL_AVAILABLE else 0.0
            memory_usage = psutil.virtual_memory().percent if PSUTIL_AVAILABLE else 0.0

            # Determinar severidad

            # Crear métricas de error
            error_metrics = ErrorMetrics
                error_type=type(error).__name__,
                error_message=str(error),
                endpoint=endpoint,
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                severity=severity,
                stack_trace=traceback.format_exc(),
                user_id=user_id,
                request_id=request_id,

            # Registrar error
            self.error_history.append(error_metrics)
            self.endpoint_errors[endpoint].append(error_metrics)
            self.error_counts[type(error).__name__] += 1
            self.total_requests += 1

            # Actualizar circuit breaker
            self._update_circuit_breaker(endpoint, error)

            logger.error


        with self.lock:
            self.total_requests += 1
            # Actualizar circuit breaker
            if endpoint in self.circuit_breakers:
                self.circuit_breakers[endpoint]._on_success()


    def _determine_severity
    ) -> ErrorSeverity:
        """Determinar severidad del error"""
        error_type = type(error).__name__

        if error_type in ["DatabaseError", "ConnectionError", "TimeoutError"]:
            return ErrorSeverity.CRITICAL

        # Errores de autenticación/autorización
        if error_type in ["AuthenticationError", "AuthorizationError"]:
            return ErrorSeverity.HIGH

        # Errores de validación
        if error_type in ["ValidationError", "ValueError"]:
            return ErrorSeverity.MEDIUM

        # Errores de tiempo de respuesta
            return ErrorSeverity.HIGH
            return ErrorSeverity.MEDIUM

        return ErrorSeverity.LOW


    def _update_circuit_breaker(self, endpoint: str, error: Exception):
        """Actualizar circuit breaker para el endpoint"""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker()

        circuit_breaker = self.circuit_breakers[endpoint]
        circuit_breaker._on_failure()


    def get_error_impact_analysis(self) -> ErrorImpactAnalysis:
        """Obtener análisis de impacto de errores"""
        with self.lock:
            if not self.error_history:
                return ErrorImpactAnalysis

            # Calcular tasa de error
            error_rate = len(self.error_history) / max(self.total_requests, 1)

            # Calcular tiempo promedio de respuesta
                else 0

            # Determinar nivel de impacto del sistema
            system_impact_level = "LOW"
            if error_rate > ERROR_RATE_THRESHOLD:
                system_impact_level = "HIGH"
            elif error_rate > ERROR_RATE_THRESHOLD / 2:
                system_impact_level = "MEDIUM"

            consecutive_errors = 0
            if self.error_history:
                for error in reversed(self.error_history):
                    if 
                    ).total_seconds() < 60:  # Último minuto
                        consecutive_errors += 1
                    else:
                        break

            # Estado de circuit breakers
            open_circuits = sum
                for cb in self.circuit_breakers.values()
                if cb.state == "OPEN"

            # Generar recomendaciones
            recommendations = self._generate_recommendations

            return ErrorImpactAnalysis


    def _generate_recommendations
    ) -> list:
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []

        if error_rate > ERROR_RATE_THRESHOLD:
            recommendations.append
            recommendations.append


        if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
            recommendations.append
            recommendations.append("Implementar graceful degradation")

        if not recommendations:
            recommendations.append

        return recommendations


    def get_endpoint_error_summary(self) -> Dict[str, Any]:
        """Obtener resumen de errores por endpoint"""
        with self.lock:
            summary = {}
            for endpoint, errors in self.endpoint_errors.items():
                if not errors:
                    continue

                error_types = [e.error_type for e in errors]
                error_counts = 

                ) / len(errors)

                summary[endpoint] = 
                        self.circuit_breakers.get(endpoint, {}).get
                    ),
                    "last_error": 
                    ),

            return summary


    def get_recent_errors(self, limit: int = 10) -> list:
        """Obtener errores recientes"""
        with self.lock:
            recent_errors = list(self.error_history)[-limit:]
            return [asdict(error) for error in recent_errors]

# Instancia global del analizador
error_analyzer = ErrorImpactAnalyzer()


def error_handler(endpoint: str):
    """
    Decorator para manejo de errores con análisis de impacto
    """


    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                raise e
        return wrapper
    return decorator


def circuit_breaker_call(endpoint: str, func: Callable, *args, **kwargs):
    """
    Ejecutar función con circuit breaker
    """
    if endpoint not in error_analyzer.circuit_breakers:
        error_analyzer.circuit_breakers[endpoint] = CircuitBreaker()

    circuit_breaker = error_analyzer.circuit_breakers[endpoint]
    return circuit_breaker.call(func, *args, **kwargs)


def get_error_analyzer() -> ErrorImpactAnalyzer:
    """Obtener instancia del analizador de errores"""
    return error_analyzer


def record_error
):
    """Registrar un error"""
    error_analyzer.record_error



"""
"""