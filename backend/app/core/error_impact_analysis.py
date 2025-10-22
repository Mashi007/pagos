"""
Sistema de Manejo de Errores con Análisis de Impacto en Performance
Implementa manejo robusto de errores con métricas de impacto
"""
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import psutil
import threading
from collections import defaultdict, deque

# Constantes de configuración
ERROR_RETENTION_HOURS = 24
MAX_ERROR_HISTORY = 1000
ERROR_RATE_THRESHOLD = 0.05  # 5% de tasa de error
MAX_CONSECUTIVE_ERRORS = 5
CIRCUIT_BREAKER_TIMEOUT = 60  # segundos

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
    timestamp: datetime
    response_time_ms: float
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
    avg_response_time_ms: float
    system_impact_level: str
    consecutive_errors: int
    circuit_breaker_status: str
    recommendations: list


class CircuitBreaker:
    """
    Circuit Breaker para prevenir cascadas de errores
    """

    def __init__(self, failure_threshold: int = MAX_CONSECUTIVE_ERRORS, 
                 timeout: int = CIRCUIT_BREAKER_TIMEOUT):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """Ejecutar función con circuit breaker"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
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
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorImpactAnalyzer:
    """
    Analizador de impacto de errores en el sistema
    """

    def __init__(self):
        self.error_history: deque = deque(maxlen=MAX_ERROR_HISTORY)
        self.endpoint_errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests = 0
        self.lock = threading.Lock()

    def record_error(self, error: Exception, endpoint: str, response_time_ms: float,
                    user_id: Optional[str] = None, request_id: Optional[str] = None):
        """Registrar un error con métricas de impacto"""
        with self.lock:
            # Obtener métricas del sistema
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent

            # Determinar severidad
            severity = self._determine_severity(error, response_time_ms)

            # Crear métricas de error
            error_metrics = ErrorMetrics(
                error_type=type(error).__name__,
                error_message=str(error),
                endpoint=endpoint,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms,
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                severity=severity,
                stack_trace=traceback.format_exc(),
                user_id=user_id,
                request_id=request_id
            )

            # Registrar error
            self.error_history.append(error_metrics)
            self.endpoint_errors[endpoint].append(error_metrics)
            self.error_counts[type(error).__name__] += 1
            self.total_requests += 1

            # Actualizar circuit breaker
            self._update_circuit_breaker(endpoint, error)

            logger.error(f"Error registrado: {error_metrics.error_type} en {endpoint} - {severity.value}")

    def record_success(self, endpoint: str, response_time_ms: float):
        """Registrar request exitoso"""
        with self.lock:
            self.total_requests += 1

            # Actualizar circuit breaker
            if endpoint in self.circuit_breakers:
                self.circuit_breakers[endpoint]._on_success()

    def _determine_severity(self, error: Exception, response_time_ms: float) -> ErrorSeverity:
        """Determinar severidad del error"""
        error_type = type(error).__name__

        # Errores críticos del sistema
        if error_type in ["DatabaseError", "ConnectionError", "TimeoutError"]:
            return ErrorSeverity.CRITICAL

        # Errores de autenticación/autorización
        if error_type in ["AuthenticationError", "AuthorizationError"]:
            return ErrorSeverity.HIGH

        # Errores de validación
        if error_type in ["ValidationError", "ValueError"]:
            return ErrorSeverity.MEDIUM

        # Errores de tiempo de respuesta
        if response_time_ms > 5000:  # 5 segundos
            return ErrorSeverity.HIGH
        elif response_time_ms > 2000:  # 2 segundos
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
                return ErrorImpactAnalysis(
                    error_rate=0,
                    avg_response_time_ms=0,
                    system_impact_level="UNKNOWN",
                    consecutive_errors=0,
                    circuit_breaker_status="NO_DATA",
                    recommendations=["No hay datos de errores disponibles"]
                )

            # Calcular tasa de error
            error_rate = len(self.error_history) / max(self.total_requests, 1)

            # Calcular tiempo promedio de respuesta
            response_times = [e.response_time_ms for e in self.error_history]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            # Determinar nivel de impacto del sistema
            system_impact_level = "LOW"
            if error_rate > ERROR_RATE_THRESHOLD:
                system_impact_level = "HIGH"
            elif error_rate > ERROR_RATE_THRESHOLD / 2:
                system_impact_level = "MEDIUM"

            # Contar errores consecutivos
            consecutive_errors = 0
            if self.error_history:
                last_error_time = self.error_history[-1].timestamp
                for error in reversed(self.error_history):
                    if (last_error_time - error.timestamp).total_seconds() < 60:  # Último minuto
                        consecutive_errors += 1
                    else:
                        break

            # Estado de circuit breakers
            open_circuits = sum(1 for cb in self.circuit_breakers.values() if cb.state == "OPEN")
            circuit_breaker_status = f"{open_circuits} circuitos abiertos de {len(self.circuit_breakers)}"

            # Generar recomendaciones
            recommendations = self._generate_recommendations(error_rate, avg_response_time, consecutive_errors)

            return ErrorImpactAnalysis(
                error_rate=error_rate,
                avg_response_time_ms=avg_response_time,
                system_impact_level=system_impact_level,
                consecutive_errors=consecutive_errors,
                circuit_breaker_status=circuit_breaker_status,
                recommendations=recommendations
            )

    def _generate_recommendations(self, error_rate: float, avg_response_time: float, 
                                consecutive_errors: int) -> list:
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []

        if error_rate > ERROR_RATE_THRESHOLD:
            recommendations.append("Implementar retry logic con exponential backoff")
            recommendations.append("Revisar configuración de recursos del sistema")

        if avg_response_time > 2000:
            recommendations.append("Optimizar queries de base de datos")
            recommendations.append("Implementar caching para endpoints lentos")

        if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
            recommendations.append("Activar circuit breakers para endpoints problemáticos")
            recommendations.append("Implementar graceful degradation")

        if not recommendations:
            recommendations.append("Sistema funcionando dentro de parámetros normales")

        return recommendations

    def get_endpoint_error_summary(self) -> Dict[str, Any]:
        """Obtener resumen de errores por endpoint"""
        with self.lock:
            summary = {}

            for endpoint, errors in self.endpoint_errors.items():
                if not errors:
                    continue

                error_types = [e.error_type for e in errors]
                error_counts = {error_type: error_types.count(error_type) for error_type in set(error_types)}

                avg_response_time = sum(e.response_time_ms for e in errors) / len(errors)

                summary[endpoint] = {
                    "total_errors": len(errors),
                    "error_types": error_counts,
                    "avg_response_time_ms": avg_response_time,
                    "circuit_breaker_state": self.circuit_breakers.get(endpoint, {}).get("state", "N/A"),
                    "last_error": errors[-1].timestamp.isoformat() if errors else None
                }

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
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000
                error_analyzer.record_success(endpoint, response_time)
                return result
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                error_analyzer.record_error(e, endpoint, response_time)
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


def record_error(error: Exception, endpoint: str, response_time_ms: float,
                user_id: Optional[str] = None, request_id: Optional[str] = None):
    """Registrar un error"""
    error_analyzer.record_error(error, endpoint, response_time_ms, user_id, request_id)


def record_success(endpoint: str, response_time_ms: float):
    """Registrar request exitoso"""
    error_analyzer.record_success(endpoint, response_time_ms)


if __name__ == "__main__":
    # Ejemplo de uso
    analyzer = ErrorImpactAnalyzer()

    # Simular algunos errores
    try:
        raise ValueError("Error de validación")
    except Exception as e:
        analyzer.record_error(e, "/api/v1/clientes", 150)

    try:
        raise ConnectionError("Error de conexión a BD")
    except Exception as e:
        analyzer.record_error(e, "/api/v1/pagos", 5000)

    # Registrar algunos éxitos
    analyzer.record_success("/api/v1/health", 50)
    analyzer.record_success("/api/v1/auth/login", 200)

    # Obtener análisis
    analysis = analyzer.get_error_impact_analysis()
    summary = analyzer.get_endpoint_error_summary()

    print("Análisis de impacto de errores:", asdict(analysis))
    print("\nResumen por endpoint:", summary)
