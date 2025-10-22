"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Decorator Específico para Análisis de Impacto por Endpoint
Implementa análisis específico para endpoints críticos
"""
from functools import wraps


from app.core.impact_monitoring import record_endpoint_performance
from app.core.error_impact_analysis import record_error, record_success

logger = logging.getLogger(__name__)

class EndpointSpecificAnalyzer:
    """
    Analizador específico para endpoints críticos
    """

    def __init__(self):
        self.endpoint_metrics = {}
        self.business_metrics = {}

    def record_business_metric(self, endpoint: str, metric_name: str, value: Any):
        """Registrar métrica de negocio específica"""
        if endpoint not in self.business_metrics:
            self.business_metrics[endpoint] = {}

        if metric_name not in self.business_metrics[endpoint]:
            self.business_metrics[endpoint][metric_name] = []

        self.business_metrics[endpoint][metric_name].append({
            "value": value,
            "timestamp": datetime.utcnow()
        })

    def get_endpoint_analysis(self, endpoint: str) -> Dict[str, Any]:
        """Obtener análisis específico del endpoint"""
        if endpoint not in self.business_metrics:
            return {"message": "No hay métricas específicas para este endpoint"}

        metrics = self.business_metrics[endpoint]
        analysis = {}

        for metric_name, values in metrics.items():
            if values:
                recent_values = values[-10:]  # Últimos 10 valores
                analysis[metric_name] = {
                    "current": recent_values[-1]["value"],
                    "average": sum(v["value"] for v in recent_values) / len(recent_values),
                    "max": max(v["value"] for v in recent_values),
                    "min": min(v["value"] for v in recent_values),
                    "trend": "increasing" if len(recent_values) > 1 and recent_values[-1]["value"] > recent_values[0]["value"] else "stable"
                }

        return analysis

# Instancia global
endpoint_analyzer = EndpointSpecificAnalyzer()

def endpoint_impact_analysis(endpoint_name: str, business_metrics: Optional[Dict[str, str]] = None):
    """
    Decorator para análisis de impacto específico por endpoint

    Args:
        endpoint_name: Nombre del endpoint para métricas
        business_metrics: Diccionario de métricas de negocio a capturar
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # Ejecutar función
                result = func(*args, **kwargs)

                # Calcular tiempo de respuesta
                response_time = (time.time() - start_time) * 1000

                # Registrar métricas genéricas
                record_endpoint_performance(endpoint_name, response_time)
                record_success(endpoint_name, response_time)

                # Registrar métricas específicas si se proporcionan
                if business_metrics and result:
                    for metric_name, metric_path in business_metrics.items():
                        try:
                            # Extraer valor de la métrica usando el path
                            value = _extract_metric_value(result, metric_path)
                            if value is not None:
                                endpoint_analyzer.record_business_metric(endpoint_name, metric_name, value)
                        except Exception as e:
                            logger.warning(f"Error extrayendo métrica {metric_name}: {e}")

                return result

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                record_error(e, endpoint_name, response_time)
                raise e

        return wrapper
    return decorator

def _extract_metric_value(data: Any, path: str) -> Any:
    """Extraer valor de métrica usando path (ej: 'data.total', 'count', etc.)"""
    try:
        if '.' in path:
            # Path con puntos (ej: 'data.total')
            parts = path.split('.')
            value = data
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value
        else:
            # Path simple
            if hasattr(data, path):
                return getattr(data, path)
            elif isinstance(data, dict) and path in data:
                return data[path]
            return None
    except Exception:
        return None

# Decorators específicos para endpoints críticos

def auth_endpoint_analysis(func: Callable):
    """Decorator específico para endpoints de autenticación"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # Métricas específicas de autenticación
            if result and hasattr(result, 'access_token'):
                endpoint_analyzer.record_business_metric("auth", "tokens_generated", 1)
                endpoint_analyzer.record_business_metric("auth", "auth_success", 1)

            record_endpoint_performance("auth", response_time)
            record_success("auth", response_time)

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Métricas de error de autenticación
            endpoint_analyzer.record_business_metric("auth", "auth_failed", 1)

            record_error(e, "auth", response_time)
            raise e

    return wrapper

def carga_masiva_endpoint_analysis(func: Callable):
    """Decorator específico para endpoints de carga masiva"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # Métricas específicas de carga masiva
            if result and isinstance(result, dict):
                if 'total_registros' in result:
                    endpoint_analyzer.record_business_metric("carga_masiva", "registros_procesados", result['total_registros'])
                if 'registros_exitosos' in result:
                    endpoint_analyzer.record_business_metric("carga_masiva", "registros_exitosos", result['registros_exitosos'])
                if 'registros_con_errores' in result:
                    endpoint_analyzer.record_business_metric("carga_masiva", "registros_con_errores", result['registros_con_errores'])

            record_endpoint_performance("carga_masiva", response_time)
            record_success("carga_masiva", response_time)

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Métricas de error de carga masiva
            endpoint_analyzer.record_business_metric("carga_masiva", "carga_failed", 1)

            record_error(e, "carga_masiva", response_time)
            raise e

    return wrapper

def clientes_endpoint_analysis(func: Callable):
    """Decorator específico para endpoints de clientes"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # Métricas específicas de clientes
            if result:
                if hasattr(result, '__len__'):
                    endpoint_analyzer.record_business_metric("clientes", "registros_devueltos", len(result))
                elif isinstance(result, dict) and 'total' in result:
                    endpoint_analyzer.record_business_metric("clientes", "registros_devueltos", result['total'])

            record_endpoint_performance("clientes", response_time)
            record_success("clientes", response_time)

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Métricas de error de clientes
            endpoint_analyzer.record_business_metric("clientes", "clientes_failed", 1)

            record_error(e, "clientes", response_time)
            raise e

    return wrapper

def pagos_endpoint_analysis(func: Callable):
    """Decorator específico para endpoints de pagos"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # Métricas específicas de pagos
            if result:
                if isinstance(result, dict) and 'monto_total' in result:
                    endpoint_analyzer.record_business_metric("pagos", "monto_procesado", result['monto_total'])
                elif hasattr(result, 'monto_pagado'):
                    endpoint_analyzer.record_business_metric("pagos", "monto_procesado", result.monto_pagado)

            record_endpoint_performance("pagos", response_time)
            record_success("pagos", response_time)

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Métricas de error de pagos
            endpoint_analyzer.record_business_metric("pagos", "pagos_failed", 1)

            record_error(e, "pagos", response_time)
            raise e

    return wrapper

def get_endpoint_analyzer() -> EndpointSpecificAnalyzer:
    """Obtener instancia del analizador específico"""
    return endpoint_analyzer

if __name__ == "__main__":
    # Ejemplo de uso
    @auth_endpoint_analysis
    def login_example():
        return {"access_token": "token123", "user": "test"}

    @carga_masiva_endpoint_analysis
    def carga_masiva_example():
        return {
            "total_registros": 100,
            "registros_exitosos": 95,
            "registros_con_errores": 5
        }

    # Ejecutar ejemplos
    login_result = login_example()
    carga_result = carga_masiva_example()

    # Obtener análisis
    analyzer = get_endpoint_analyzer()
    auth_analysis = analyzer.get_endpoint_analysis("auth")
    carga_analysis = analyzer.get_endpoint_analysis("carga_masiva")

    print("Análisis de auth:", auth_analysis)
    print("Análisis de carga masiva:", carga_analysis)
