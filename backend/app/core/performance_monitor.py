"""
Sistema de Monitoreo de Performance
Almacena métricas de endpoints para análisis y alertas
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EndpointMetric:
    """Métrica de un endpoint individual"""
    path: str
    method: str
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    error_count: int = 0
    last_request: Optional[datetime] = None
    response_sizes: List[int] = field(default_factory=list)
    
    def update(self, response_time_ms: float, status_code: int, response_bytes: int):
        """Actualizar métrica con una nueva petición"""
        self.count += 1
        self.total_time_ms += response_time_ms
        self.min_time_ms = min(self.min_time_ms, response_time_ms)
        self.max_time_ms = max(self.max_time_ms, response_time_ms)
        self.avg_time_ms = self.total_time_ms / self.count
        
        if status_code >= 400:
            self.error_count += 1
        
        self.last_request = datetime.now()
        
        # Mantener solo últimos 100 tamaños para calcular percentiles
        if len(self.response_sizes) < 100:
            self.response_sizes.append(response_bytes)
        else:
            self.response_sizes.pop(0)
            self.response_sizes.append(response_bytes)


class PerformanceMonitor:
    """
    Monitor de performance que almacena métricas de endpoints en memoria
    """
    
    def __init__(self, max_entries: int = 1000, retention_hours: int = 24):
        """
        Args:
            max_entries: Máximo número de métricas individuales a mantener
            retention_hours: Horas que se mantienen las métricas en memoria
        """
        self.max_entries = max_entries
        self.retention_hours = retention_hours
        self.metrics: Dict[str, EndpointMetric] = {}
        self.request_history: List[Dict] = []  # Historial de últimas peticiones
        self.max_history = 500  # Mantener últimas 500 peticiones
        
    def record_request(
        self, 
        method: str, 
        path: str, 
        response_time_ms: float, 
        status_code: int,
        response_bytes: int = 0
    ):
        """Registrar una petición en las métricas"""
        try:
            # Crear clave única para el endpoint
            key = f"{method}:{path}"
            
            # Obtener o crear métrica
            if key not in self.metrics:
                if len(self.metrics) >= self.max_entries:
                    # Limpiar métricas antiguas
                    self._cleanup_old_metrics()
                self.metrics[key] = EndpointMetric(path=path, method=method)
            
            # Actualizar métrica
            metric = self.metrics[key]
            metric.update(response_time_ms, status_code, response_bytes)
            
            # Registrar en historial
            self.request_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "path": path,
                "response_time_ms": response_time_ms,
                "status_code": status_code,
                "response_bytes": response_bytes,
            })
            
            # Limitar tamaño del historial
            if len(self.request_history) > self.max_history:
                self.request_history.pop(0)
                
        except Exception as e:
            logger.error(f"Error registrando métrica: {e}")
    
    def _cleanup_old_metrics(self):
        """Limpiar métricas antiguas que no se han usado recientemente"""
        now = datetime.now()
        cutoff = now - timedelta(hours=self.retention_hours)
        
        keys_to_remove = [
            key for key, metric in self.metrics.items()
            if metric.last_request and metric.last_request < cutoff
        ]
        
        for key in keys_to_remove[:100]:  # Limpiar máximo 100 a la vez
            del self.metrics[key]
    
    def get_slow_endpoints(
        self, 
        threshold_ms: float = 1000, 
        limit: int = 20
    ) -> List[Dict]:
        """
        Obtener endpoints lentos ordenados por tiempo promedio
        
        Args:
            threshold_ms: Umbral mínimo de tiempo en ms para considerar lento
            limit: Número máximo de resultados
            
        Returns:
            Lista de diccionarios con información de endpoints lentos
        """
        slow_endpoints = []
        
        for key, metric in self.metrics.items():
            if metric.avg_time_ms >= threshold_ms and metric.count > 0:
                slow_endpoints.append({
                    "endpoint": f"{metric.method} {metric.path}",
                    "method": metric.method,
                    "path": metric.path,
                    "count": metric.count,
                    "avg_time_ms": round(metric.avg_time_ms, 2),
                    "min_time_ms": round(metric.min_time_ms, 2),
                    "max_time_ms": round(metric.max_time_ms, 2),
                    "total_time_ms": round(metric.total_time_ms, 2),
                    "error_rate": round((metric.error_count / metric.count) * 100, 2) if metric.count > 0 else 0,
                    "last_request": metric.last_request.isoformat() if metric.last_request else None,
                })
        
        # Ordenar por tiempo promedio descendente
        slow_endpoints.sort(key=lambda x: x["avg_time_ms"], reverse=True)
        
        return slow_endpoints[:limit]
    
    def get_endpoint_stats(self, method: str, path: str) -> Optional[Dict]:
        """Obtener estadísticas de un endpoint específico"""
        key = f"{method}:{path}"
        metric = self.metrics.get(key)
        
        if not metric or metric.count == 0:
            return None
        
        # Calcular percentiles de tamaño de respuesta
        response_sizes_sorted = sorted(metric.response_sizes)
        percentile_50 = response_sizes_sorted[len(response_sizes_sorted) // 2] if response_sizes_sorted else 0
        percentile_95 = response_sizes_sorted[int(len(response_sizes_sorted) * 0.95)] if response_sizes_sorted else 0
        
        return {
            "endpoint": f"{method} {path}",
            "method": method,
            "path": path,
            "count": metric.count,
            "avg_time_ms": round(metric.avg_time_ms, 2),
            "min_time_ms": round(metric.min_time_ms, 2),
            "max_time_ms": round(metric.max_time_ms, 2),
            "total_time_ms": round(metric.total_time_ms, 2),
            "error_count": metric.error_count,
            "error_rate": round((metric.error_count / metric.count) * 100, 2) if metric.count > 0 else 0,
            "avg_response_bytes": round(sum(metric.response_sizes) / len(metric.response_sizes), 2) if metric.response_sizes else 0,
            "percentile_50_bytes": percentile_50,
            "percentile_95_bytes": percentile_95,
            "last_request": metric.last_request.isoformat() if metric.last_request else None,
        }
    
    def get_summary(self) -> Dict:
        """Obtener resumen general de todas las métricas"""
        if not self.metrics:
            return {
                "total_endpoints": 0,
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "total_errors": 0,
            }
        
        total_requests = sum(m.count for m in self.metrics.values())
        total_time = sum(m.total_time_ms for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        
        return {
            "total_endpoints": len(self.metrics),
            "total_requests": total_requests,
            "avg_response_time_ms": round(total_time / total_requests, 2) if total_requests > 0 else 0,
            "total_errors": total_errors,
            "error_rate": round((total_errors / total_requests) * 100, 2) if total_requests > 0 else 0,
            "monitoring_since": min(
                (m.last_request for m in self.metrics.values() if m.last_request),
                default=datetime.now()
            ).isoformat(),
        }
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict]:
        """Obtener peticiones recientes"""
        return self.request_history[-limit:]
    
    def clear_metrics(self):
        """Limpiar todas las métricas (útil para testing o reset)"""
        self.metrics.clear()
        self.request_history.clear()
        logger.info("Métricas de performance limpiadas")


# Instancia global del monitor
performance_monitor = PerformanceMonitor()

