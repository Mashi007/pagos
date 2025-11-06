"""
Sistema de Monitoreo de Queries SQL
Detecta queries lentas, errores y problemas de rendimiento
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Umbrales de alerta (en milisegundos)
SLOW_QUERY_THRESHOLD_MS = 1000  # 1 segundo
CRITICAL_QUERY_THRESHOLD_MS = 5000  # 5 segundos
VERY_SLOW_QUERY_THRESHOLD_MS = 10000  # 10 segundos


@dataclass
class QueryMetric:
    """Métrica de una query individual"""
    query_name: str
    query_type: str  # 'SELECT', 'INSERT', 'UPDATE', etc.
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    error_count: int = 0
    slow_query_count: int = 0  # Queries > 1 segundo
    critical_query_count: int = 0  # Queries > 5 segundos
    last_execution: Optional[datetime] = None
    last_error: Optional[str] = None

    def update(self, execution_time_ms: float, error: Optional[Exception] = None):
        """Actualizar métrica con una nueva ejecución"""
        self.count += 1
        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.avg_time_ms = self.total_time_ms / self.count
        self.last_execution = datetime.now()

        if error:
            self.error_count += 1
            self.last_error = str(error)

        # Contar queries lentas
        if execution_time_ms >= CRITICAL_QUERY_THRESHOLD_MS:
            self.critical_query_count += 1
        elif execution_time_ms >= SLOW_QUERY_THRESHOLD_MS:
            self.slow_query_count += 1


class QueryMonitor:
    """
    Monitor de queries SQL para detectar problemas de rendimiento
    """
    def __init__(self):
        self.metrics: Dict[str, QueryMetric] = {}
        self.query_history: List[Dict] = []
        self.max_history = 200  # Mantener últimas 200 queries
        self.alerts: List[Dict] = []  # Alertas activas
        self.max_alerts = 100  # Máximo de alertas en memoria

    def record_query(
        self,
        query_name: str,
        execution_time_ms: float,
        query_type: str = "SELECT",
        error: Optional[Exception] = None,
        query_sql: Optional[str] = None,
        params: Optional[Dict] = None,
        tables: Optional[List[str]] = None,
        columns: Optional[List[str]] = None
    ):
        """
        Registrar una ejecución de query
        
        Args:
            query_name: Nombre identificador de la query (ej: "obtener_kpis_principales")
            execution_time_ms: Tiempo de ejecución en milisegundos
            query_type: Tipo de query (SELECT, INSERT, etc.)
            error: Excepción si hubo error
            query_sql: SQL de la query (opcional, para debugging)
            params: Parámetros de la query (opcional)
        """
        try:
            # Obtener o crear métrica
            if query_name not in self.metrics:
                self.metrics[query_name] = QueryMetric(
                    query_name=query_name,
                    query_type=query_type
                )

            metric = self.metrics[query_name]
            metric.update(execution_time_ms, error)

            # Registrar en historial
            query_record = {
                "timestamp": datetime.now().isoformat(),
                "query_name": query_name,
                "execution_time_ms": execution_time_ms,
                "query_type": query_type,
                "error": str(error) if error else None,
                "query_sql": query_sql[:500] if query_sql else None,  # Limitar tamaño
                "tables": tables or [],
                "columns": columns or [],
            }
            self.query_history.append(query_record)

            # Limitar tamaño del historial
            if len(self.query_history) > self.max_history:
                self.query_history.pop(0)

            # Generar alertas si es necesario
            self._check_alerts(query_name, execution_time_ms, error, query_sql, tables, columns)

        except Exception as e:
            logger.error(f"Error registrando métrica de query: {e}")

    def _check_alerts(
        self,
        query_name: str,
        execution_time_ms: float,
        error: Optional[Exception],
        query_sql: Optional[str],
        tables: Optional[List[str]] = None,
        columns: Optional[List[str]] = None
    ):
        """Verificar y generar alertas si es necesario"""
        alert = None

        # Alerta por query muy lenta (crítica)
        if execution_time_ms >= VERY_SLOW_QUERY_THRESHOLD_MS:
            alert = {
                "type": "very_slow_query",
                "severity": "CRITICAL",
                "query_name": query_name,
                "execution_time_ms": execution_time_ms,
                "threshold_ms": VERY_SLOW_QUERY_THRESHOLD_MS,
                "message": f"Query {query_name} tomó {execution_time_ms:.0f}ms (umbral: {VERY_SLOW_QUERY_THRESHOLD_MS}ms)",
                "timestamp": datetime.now().isoformat(),
                "query_sql": query_sql[:200] if query_sql else None,
                "tables_used": tables or [],
                "columns_used": columns or [],
            }
            logger.error(
                f"🚨 [QUERY CRÍTICA] {query_name}: {execution_time_ms:.0f}ms "
                f"(umbral: {VERY_SLOW_QUERY_THRESHOLD_MS}ms)"
            )

        # Alerta por query crítica
        elif execution_time_ms >= CRITICAL_QUERY_THRESHOLD_MS:
            alert = {
                "type": "critical_query",
                "severity": "HIGH",
                "query_name": query_name,
                "execution_time_ms": execution_time_ms,
                "threshold_ms": CRITICAL_QUERY_THRESHOLD_MS,
                "message": f"Query {query_name} tomó {execution_time_ms:.0f}ms (umbral: {CRITICAL_QUERY_THRESHOLD_MS}ms)",
                "timestamp": datetime.now().isoformat(),
                "query_sql": query_sql[:200] if query_sql else None,
                "tables_used": tables or [],
                "columns_used": columns or [],
            }
            logger.warning(
                f"⚠️ [QUERY LENTA] {query_name}: {execution_time_ms:.0f}ms "
                f"(umbral: {CRITICAL_QUERY_THRESHOLD_MS}ms)"
            )

        # Alerta por query lenta
        elif execution_time_ms >= SLOW_QUERY_THRESHOLD_MS:
            alert = {
                "type": "slow_query",
                "severity": "MEDIUM",
                "query_name": query_name,
                "execution_time_ms": execution_time_ms,
                "threshold_ms": SLOW_QUERY_THRESHOLD_MS,
                "message": f"Query {query_name} tomó {execution_time_ms:.0f}ms (umbral: {SLOW_QUERY_THRESHOLD_MS}ms)",
                "timestamp": datetime.now().isoformat(),
            }
            logger.info(
                f"⏱️ [QUERY LENTA] {query_name}: {execution_time_ms:.0f}ms "
                f"(umbral: {SLOW_QUERY_THRESHOLD_MS}ms)"
            )

        # Alerta por error
        if error:
            alert = {
                "type": "query_error",
                "severity": "HIGH",
                "query_name": query_name,
                "error": str(error),
                "message": f"Error en query {query_name}: {str(error)}",
                "timestamp": datetime.now().isoformat(),
                "query_sql": query_sql[:200] if query_sql else None,
                "tables_used": tables or [],
                "columns_used": columns or [],
            }
            logger.error(f"❌ [ERROR QUERY] {query_name}: {str(error)}")

        # Agregar alerta si existe
        if alert:
            self.alerts.append(alert)
            # Limitar tamaño de alertas
            if len(self.alerts) > self.max_alerts:
                self.alerts.pop(0)

    @contextmanager
    def monitor_query(self, query_name: str, query_type: str = "SELECT", query_sql: Optional[str] = None):
        """
        Context manager para monitorear una query automáticamente
        
        Uso:
            with query_monitor.monitor_query("obtener_kpis_principales"):
                # código de la query
                result = db.query(...).all()
        """
        start_time = time.time()
        error = None
        try:
            yield
        except Exception as e:
            error = e
            raise
        finally:
            execution_time_ms = (time.time() - start_time) * 1000
            self.record_query(query_name, execution_time_ms, query_type, error, query_sql)

    def get_slow_queries(self, threshold_ms: float = SLOW_QUERY_THRESHOLD_MS, limit: int = 20) -> List[Dict]:
        """Obtener queries lentas ordenadas por tiempo promedio"""
        slow_queries = []
        for metric in self.metrics.values():
            if metric.avg_time_ms >= threshold_ms and metric.count > 0:
                slow_queries.append({
                    "query_name": metric.query_name,
                    "query_type": metric.query_type,
                    "count": metric.count,
                    "avg_time_ms": round(metric.avg_time_ms, 2),
                    "min_time_ms": round(metric.min_time_ms, 2),
                    "max_time_ms": round(metric.max_time_ms, 2),
                    "slow_query_count": metric.slow_query_count,
                    "critical_query_count": metric.critical_query_count,
                    "error_count": metric.error_count,
                    "error_rate": round((metric.error_count / metric.count) * 100, 2) if metric.count > 0 else 0,
                    "last_execution": metric.last_execution.isoformat() if metric.last_execution else None,
                })
        slow_queries.sort(key=lambda x: x["avg_time_ms"], reverse=True)
        return slow_queries[:limit]

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Obtener alertas recientes"""
        return self.alerts[-limit:]

    def get_query_stats(self, query_name: str) -> Optional[Dict]:
        """Obtener estadísticas de una query específica"""
        metric = self.metrics.get(query_name)
        if not metric or metric.count == 0:
            return None

        return {
            "query_name": query_name,
            "query_type": metric.query_type,
            "count": metric.count,
            "avg_time_ms": round(metric.avg_time_ms, 2),
            "min_time_ms": round(metric.min_time_ms, 2),
            "max_time_ms": round(metric.max_time_ms, 2),
            "slow_query_count": metric.slow_query_count,
            "critical_query_count": metric.critical_query_count,
            "error_count": metric.error_count,
            "error_rate": round((metric.error_count / metric.count) * 100, 2) if metric.count > 0 else 0,
            "last_execution": metric.last_execution.isoformat() if metric.last_execution else None,
            "last_error": metric.last_error,
        }

    def get_summary(self) -> Dict:
        """Obtener resumen general de todas las queries"""
        if not self.metrics:
            return {
                "total_queries": 0,
                "total_executions": 0,
                "avg_execution_time_ms": 0,
                "total_errors": 0,
                "total_slow_queries": 0,
            }

        total_executions = sum(m.count for m in self.metrics.values())
        total_time = sum(m.total_time_ms for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        total_slow = sum(m.slow_query_count for m in self.metrics.values())
        total_critical = sum(m.critical_query_count for m in self.metrics.values())

        return {
            "total_queries": len(self.metrics),
            "total_executions": total_executions,
            "avg_execution_time_ms": round(total_time / total_executions, 2) if total_executions > 0 else 0,
            "total_errors": total_errors,
            "total_slow_queries": total_slow,
            "total_critical_queries": total_critical,
            "error_rate": round((total_errors / total_executions) * 100, 2) if total_executions > 0 else 0,
            "slow_query_rate": round((total_slow / total_executions) * 100, 2) if total_executions > 0 else 0,
        }

    def clear_metrics(self):
        """Limpiar todas las métricas"""
        self.metrics.clear()
        self.query_history.clear()
        self.alerts.clear()
        logger.info("Métricas de queries limpiadas")


# Instancia global del monitor
query_monitor = QueryMonitor()

