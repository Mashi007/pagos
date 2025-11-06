"""
🔍 HELPERS DE DEBUGGING Y ALERTAS RÁPIDAS
Sistema centralizado para identificar problemas rápidamente
"""

import logging
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ============================================
# ALERTAS Y DETECCIÓN DE PROBLEMAS COMUNES
# ============================================


class DebugAlert:
    """Sistema de alertas para problemas comunes"""

    @staticmethod
    def log_sql_error(error: Exception, query: str, params: Optional[Dict] = None):
        """Log detallado de errores SQL con contexto completo"""
        logger.error("=" * 80)
        logger.error("🚨 ERROR SQL DETECTADO")
        logger.error("=" * 80)
        logger.error(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.error(f"❌ Error: {type(error).__name__}: {str(error)}")
        logger.error(f"📝 Query: {query[:500]}...")  # Primeros 500 caracteres
        if params:
            logger.error("📋 Parámetros: %s", params)
        logger.error("📍 Stack trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)

    @staticmethod
    def log_slow_query(endpoint: str, duration_ms: float, threshold_ms: float = 5000):
        """Alerta cuando una query es lenta"""
        if duration_ms > threshold_ms:
            logger.warning("=" * 80)
            logger.warning("⚠️ QUERY LENTA DETECTADA")
            logger.warning("=" * 80)
            logger.warning(f"📍 Endpoint: {endpoint}")
            logger.warning(f"⏱️ Duración: {duration_ms:.2f}ms (Umbral: {threshold_ms}ms)")
            logger.warning(f"⏰ Timestamp: {datetime.now().isoformat()}")
            logger.warning("=" * 80)

    @staticmethod
    def log_missing_data(endpoint: str, expected_field: str, data: Any):
        """Alerta cuando faltan datos esperados"""
        logger.warning("=" * 80)
        logger.warning("⚠️ DATOS FALTANTES DETECTADOS")
        logger.warning("=" * 80)
        logger.warning(f"📍 Endpoint: {endpoint}")
        logger.warning(f"🔍 Campo esperado: {expected_field}")
        logger.warning(f"📊 Datos recibidos: {str(data)[:200]}...")
        logger.warning(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.warning("=" * 80)

    @staticmethod
    def log_graph_error(endpoint: str, error: Exception, data_sample: Optional[Any] = None):
        """Alerta específica para errores en gráficos"""
        logger.error("=" * 80)
        logger.error("🚨 ERROR EN GRÁFICO")
        logger.error("=" * 80)
        logger.error(f"📍 Endpoint: {endpoint}")
        logger.error(f"❌ Error: {type(error).__name__}: {str(error)}")
        if data_sample:
            logger.error("📊 Muestra de datos: %s...", str(data_sample)[:300])
        logger.error("📍 Stack trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)


# ============================================
# DECORADORES DE DEBUGGING
# ============================================


def debug_timing(threshold_ms: float = 5000):
    """Decorador para medir tiempo de ejecución y alertar si es lento"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    DebugAlert.log_slow_query(
                        endpoint=f"{func.__module__}.{func.__name__}", duration_ms=duration_ms, threshold_ms=threshold_ms
                    )

                logger.debug(f"⏱️ {func.__name__} ejecutado en {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"❌ {func.__name__} falló después de {duration_ms:.2f}ms: {e}")
                raise

        return wrapper

    return decorator


def debug_sql_errors(func: Callable) -> Callable:
    """Decorador para capturar y loggear errores SQL con contexto completo"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Detectar si es un error SQL
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["sql", "database", "query", "syntax", "column", "table"]):
                # Intentar extraer query y params si están disponibles
                query = kwargs.get("query", "N/A")
                params = kwargs.get("params", kwargs.get("bind_params", None))
                DebugAlert.log_sql_error(e, str(query), params)
            raise

    return wrapper


# ============================================
# HELPERS DE VALIDACIÓN RÁPIDA
# ============================================


def validate_graph_data(
    data: list, required_fields: list, non_numeric_fields: Optional[list] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida que los datos del gráfico tengan los campos requeridos

    Args:
        data: Lista de diccionarios con los datos
        required_fields: Lista de campos requeridos
        non_numeric_fields: Lista de campos que NO deben validarse como numéricos (ej: 'mes', 'fecha', 'label')

    Returns:
        (is_valid, error_message)
    """
    if not data:
        return False, "❌ Datos vacíos: No hay datos para mostrar en el gráfico"

    if not isinstance(data, list):
        return False, f"❌ Tipo incorrecto: Se esperaba lista, se recibió {type(data).__name__}"

    # Campos que por defecto no son numéricos
    default_non_numeric = ["mes", "fecha", "label", "periodo", "nombre", "descripcion"]
    if non_numeric_fields is None:
        non_numeric_fields = default_non_numeric
    else:
        # Combinar con los campos por defecto
        non_numeric_fields = list(set(non_numeric_fields + default_non_numeric))

    # Validar que todos los elementos tengan los campos requeridos
    missing_fields = []
    for i, item in enumerate(data[:5]):  # Revisar primeros 5 elementos
        if not isinstance(item, dict):
            return False, f"❌ Elemento {i} no es un diccionario: {type(item).__name__}"

        for field in required_fields:
            if field not in item:
                missing_fields.append(f"{field} (en elemento {i})")

    if missing_fields:
        return False, f"❌ Campos faltantes: {', '.join(set(missing_fields))}"

    # Validar que los valores numéricos sean válidos (excluyendo campos no numéricos)
    for i, item in enumerate(data[:5]):
        for field in required_fields:
            # Saltar validación numérica para campos que no deben ser numéricos
            if field in non_numeric_fields:
                continue

            value = item.get(field)
            if value is not None and not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    return False, f"❌ Valor inválido: {field} en elemento {i} = {value} (tipo: {type(value).__name__})"

    return True, None


def log_graph_debug_info(endpoint: str, data: list, y_axis_domain: Optional[list] = None):
    """Log información de debugging para gráficos"""
    logger.info("=" * 80)
    logger.info(f"📊 DEBUG INFO - {endpoint}")
    logger.info("=" * 80)
    logger.info(f"📈 Total de puntos de datos: {len(data)}")

    if data:
        logger.info(f"📋 Primer elemento: {data[0]}")
        logger.info(f"📋 Último elemento: {data[-1]}")

        # Calcular estadísticas de valores numéricos
        numeric_fields = ["monto_nuevos", "monto_cuotas_programadas", "monto_pagado", "morosidad_mensual"]
        for field in numeric_fields:
            values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
            if values:
                logger.info(f"📊 {field}: min={min(values):.2f}, max={max(values):.2f}, avg={sum(values)/len(values):.2f}")

    if y_axis_domain:
        logger.info(f"📏 Dominio del eje Y: {y_axis_domain}")

    logger.info("=" * 80)


# ============================================
# CHECKLIST DE DEBUGGING RÁPIDO
# ============================================


def run_debug_checklist(endpoint: str, data: Any, required_fields: Optional[list] = None):
    """
    Ejecuta un checklist rápido de debugging

    Returns:
        Dict con resultados del checklist
    """
    results = {"endpoint": endpoint, "timestamp": datetime.now().isoformat(), "checks": {}}

    # Check 1: Datos no vacíos
    if isinstance(data, list):
        results["checks"]["data_not_empty"] = len(data) > 0
        if not results["checks"]["data_not_empty"]:
            logger.warning(f"⚠️ {endpoint}: Datos vacíos")
    else:
        results["checks"]["data_not_empty"] = data is not None
        if not results["checks"]["data_not_empty"]:
            logger.warning(f"⚠️ {endpoint}: Datos es None")

    # Check 2: Campos requeridos
    if required_fields and isinstance(data, list) and data:
        missing = []
        for field in required_fields:
            if field not in data[0]:
                missing.append(field)
        results["checks"]["required_fields"] = len(missing) == 0
        if missing:
            logger.warning(f"⚠️ {endpoint}: Campos faltantes: {', '.join(missing)}")

    # Check 3: Valores numéricos válidos
    if isinstance(data, list) and data:
        invalid_values = []
        for i, item in enumerate(data[:10]):  # Revisar primeros 10
            if isinstance(item, dict):
                for key, value in item.items():
                    if "monto" in key.lower() or "morosidad" in key.lower():
                        if value is not None and not isinstance(value, (int, float)):
                            try:
                                float(value)
                            except (ValueError, TypeError):
                                invalid_values.append(f"{key}[{i}]={value}")
        results["checks"]["valid_numeric_values"] = len(invalid_values) == 0
        if invalid_values:
            logger.warning(f"⚠️ {endpoint}: Valores inválidos: {', '.join(invalid_values[:5])}")

    return results
