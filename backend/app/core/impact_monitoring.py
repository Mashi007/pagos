""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Sistema de Monitoreo con Análisis de Impacto en Performance
Implementa monitoreo avanzado con métricas de impacto en recursos del sistema
""

from typing import List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Constantes de configuración
MONITORING_INTERVAL_SECONDS = 30
METRICS_RETENTION_HOURS = 24
ALERT_THRESHOLD_CPU = 80
ALERT_THRESHOLD_MEMORY = 85
ALERT_THRESHOLD_DISK = 90
ALERT_THRESHOLD_RESPONSE_TIME_MS = 1000
MAX_METRICS_HISTORY = 1000

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Severidad de alertas"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

dataclass
class SystemMetrics:
    """Métricas del sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: int
    disk_percent: float
    disk_free_gb: int
    process_count: int
    load_average: List[float]
    network_bytes_sent: int
    network_bytes_recv: int

dataclass
class PerformanceImpact:
    """Análisis de impacto en performance"""
    endpoint: str
    response_time_ms: float
    cpu_usage_percent: float
    memory_usage_mb: int
    impact_level: str
    timestamp: datetime

dataclass
class Alert:
    """Estructura de alerta"""
    id: str
    type: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metrics: Dict[str, Any]
    resolved: bool = False

class ImpactAnalyzer:
    """
    Analizador de impacto en performance del sistema
    """

    def __init__(self):
        self.metrics_history: deque = deque(maxlen=MAX_METRICS_HISTORY)
        self.performance_history: deque = deque(maxlen=MAX_METRICS_HISTORY)
        self.alerts: List[Alert] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self):
        """Iniciar monitoreo continuo del sistema"""
        if self.monitoring_active:
            logger.warning("Monitoreo ya está activo")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoreo de impacto iniciado")

    def stop_monitoring(self):
        """Detener monitoreo del sistema"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoreo de impacto detenido")

    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._analyze_impact()
                self._check_alerts()
                time.sleep(MONITORING_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(5)  # Esperar antes de reintentar

    def _collect_metrics(self):
        """Recolectar métricas del sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()

            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_mb=memory.available // (1024 * 1024),
                disk_percent=disk.percent,
                disk_free_gb=disk.free // (1024 * 1024 * 1024),
                process_count=len(psutil.pids()),
                load_average=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv
            )

            self.metrics_history.append(metrics)
            logger.debug(f"Métricas recolectadas: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%")

        except Exception as e:
            logger.error(f"Error recolectando métricas: {e}")

    def _analyze_impact(self):
        """Analizar impacto en performance basado en métricas históricas"""
        if len(self.metrics_history) < 2:
            return

        current = self.metrics_history[-1]
        previous = self.metrics_history[-2]

        # Calcular deltas
        cpu_delta = current.cpu_percent - previous.cpu_percent
        memory_delta = current.memory_percent - previous.memory_percent
        memory_mb_delta = previous.memory_available_mb - current.memory_available_mb

        # Determinar nivel de impacto
        impact_level = "LOW"
        if abs(cpu_delta) > 10 or memory_mb_delta > 50:
            impact_level = "HIGH"
        elif abs(cpu_delta) > 5 or memory_mb_delta > 20:
            impact_level = "MEDIUM"

        # Crear análisis de impacto
        impact = PerformanceImpact(
            endpoint="system_monitoring",
            response_time_ms=0,  # No aplicable para monitoreo del sistema
            cpu_usage_percent=cpu_delta,
            memory_usage_mb=memory_mb_delta,
            impact_level=impact_level,
            timestamp=current.timestamp
        )

        self.performance_history.append(impact)
        logger.debug(f"Análisis de impacto: {impact_level}, CPU delta: {cpu_delta:.1f}%")

    def _check_alerts(self):
        """Verificar condiciones de alerta"""
        if not self.metrics_history:
            return

        current = self.metrics_history[-1]

        # Verificar CPU
        if current.cpu_percent > ALERT_THRESHOLD_CPU:
            self._create_alert(
                alert_type="CPU_HIGH",
                severity=AlertSeverity.WARNING,
                message=f"CPU usage {current.cpu_percent:.1f}% exceeds threshold {ALERT_THRESHOLD_CPU}%",
                metrics={"cpu_percent": current.cpu_percent}
            )

        # Verificar memoria
        if current.memory_percent > ALERT_THRESHOLD_MEMORY:
            self._create_alert(
                alert_type="MEMORY_HIGH",
                severity=AlertSeverity.WARNING,
                message=f"Memory usage {current.memory_percent:.1f}% exceeds threshold {ALERT_THRESHOLD_MEMORY}%",
                metrics={"memory_percent": current.memory_percent}
            )

        # Verificar disco
        if current.disk_percent > ALERT_THRESHOLD_DISK:
            self._create_alert(
                alert_type="DISK_HIGH",
                severity=AlertSeverity.CRITICAL,
                message=f"Disk usage {current.disk_percent:.1f}% exceeds threshold {ALERT_THRESHOLD_DISK}%",
                metrics={"disk_percent": current.disk_percent}
            )

    def _create_alert(self, alert_type: str, severity: AlertSeverity, message: str, metrics: Dict[str, Any]):
        """Crear nueva alerta"""
        alert_id = f"{alert_type}_{int(time.time())}"

        # Verificar si ya existe una alerta similar no resuelta
        existing_alert = next(
            (a for a in self.alerts if a.type == alert_type and not a.resolved),
            None
        )

        if existing_alert:
            return  # No crear alertas duplicadas

        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metrics=metrics
        )

        self.alerts.append(alert)
        logger.warning(f"Alerta creada: {alert_type} - {message}")

    def record_endpoint_performance(self, endpoint: str, response_time_ms: float):
        """Registrar performance de un endpoint específico"""
        if not self.metrics_history:
            return

        current_metrics = self.metrics_history[-1]

        # Determinar nivel de impacto basado en tiempo de respuesta
        impact_level = "LOW"
        if response_time_ms > ALERT_THRESHOLD_RESPONSE_TIME_MS:
            impact_level = "HIGH"
        elif response_time_ms > ALERT_THRESHOLD_RESPONSE_TIME_MS / 2:
            impact_level = "MEDIUM"

        # Crear análisis de impacto para el endpoint
        impact = PerformanceImpact(
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            cpu_usage_percent=current_metrics.cpu_percent,
            memory_usage_mb=current_metrics.memory_available_mb,
            impact_level=impact_level,
            timestamp=datetime.utcnow()
        )

        self.performance_history.append(impact)

        # Crear alerta si el tiempo de respuesta es muy alto
        if response_time_ms > ALERT_THRESHOLD_RESPONSE_TIME_MS:
            self._create_alert(
                alert_type="SLOW_RESPONSE",
                severity=AlertSeverity.WARNING,
                message=f"Endpoint {endpoint} response time {response_time_ms:.2f}ms exceeds threshold",
                metrics={"endpoint": endpoint, "response_time_ms": response_time_ms}
            )

    def get_current_status(self) -> Dict[str, Any]:
        """Obtener estado actual del sistema"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "No hay métricas disponibles"}

        current = self.metrics_history[-1]

        # Calcular tendencias
        cpu_trend = self._calculate_trend("cpu_percent")
        memory_trend = self._calculate_trend("memory_percent")

        # Obtener alertas activas
        active_alerts = [a for a in self.alerts if not a.resolved]

        return {
            "status": "healthy" if not active_alerts else "degraded",
            "timestamp": current.timestamp.isoformat(),
            "current_metrics": asdict(current),
            "trends": {
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend
            },
            "active_alerts": len(active_alerts),
            "alerts": [asdict(alert) for alert in active_alerts[-5:]],  # Últimas 5 alertas
            "monitoring_active": self.monitoring_active
        }

    def _calculate_trend(self, metric_name: str) -> str:
        """Calcular tendencia de una métrica"""
        if len(self.metrics_history) < 5:
            return "insufficient_data"

        recent_metrics = list(self.metrics_history)[-5:]
        values = [getattr(m, metric_name) for m in recent_metrics]

        # Calcular pendiente simple
        x = list(range(len(values)))
        y = values

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        if n * sum_x2 - sum_x ** 2 == 0:
            return "stable"

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

        if slope > 0.5:
            return "increasing"
        elif slope < -0.5:
            return "decreasing"
        else:
            return "stable"

    def get_performance_report(self) -> Dict[str, Any]:
        """Obtener reporte de performance"""
        if not self.performance_history:
            return {"message": "No hay datos de performance disponibles"}

        recent_performance = list(self.performance_history)[-10:]  # Últimos 10 registros

        # Calcular estadísticas
        response_times = [p.response_time_ms for p in recent_performance if p.response_time_ms > 0]
        impact_levels = [p.impact_level for p in recent_performance]

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        impact_counts = {
            "LOW": impact_levels.count("LOW"),
            "MEDIUM": impact_levels.count("MEDIUM"),
            "HIGH": impact_levels.count("HIGH")
        }

        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "performance_summary": {
                "avg_response_time_ms": avg_response_time,
                "max_response_time_ms": max_response_time,
                "total_requests": len(recent_performance),
                "impact_distribution": impact_counts
            },
            "recent_performance": [asdict(p) for p in recent_performance[-5:]],
            "recommendations": self._generate_recommendations(impact_counts, avg_response_time)
        }

    def _generate_recommendations(self, impact_counts: Dict[str, int], avg_response_time: float) -> List[str]:
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []

        if impact_counts["HIGH"] > impact_counts["LOW"]:
            recommendations.append("Considerar optimización de endpoints con alto impacto")

        if avg_response_time > 500:
            recommendations.append("Implementar caching para reducir tiempos de respuesta")

        if impact_counts["MEDIUM"] + impact_counts["HIGH"] > impact_counts["LOW"]:
            recommendations.append("Revisar configuración de recursos del sistema")

        if not recommendations:
            recommendations.append("Sistema funcionando dentro de parámetros normales")

        return recommendations

# Instancia global del analizador
impact_analyzer = ImpactAnalyzer()

def get_impact_analyzer() -> ImpactAnalyzer:
    """Obtener instancia del analizador de impacto"""
    return impact_analyzer

def start_monitoring():
    """Iniciar monitoreo del sistema"""
    impact_analyzer.start_monitoring()

def stop_monitoring():
    """Detener monitoreo del sistema"""
    impact_analyzer.stop_monitoring()

def record_endpoint_performance(endpoint: str, response_time_ms: float):
    """Registrar performance de un endpoint"""
    impact_analyzer.record_endpoint_performance(endpoint, response_time_ms)

if __name__ == "__main__":
    # Ejemplo de uso
    analyzer = ImpactAnalyzer()
    analyzer.start_monitoring()

    try:
        # Simular algunos endpoints
        analyzer.record_endpoint_performance("/api/v1/health", 50)
        analyzer.record_endpoint_performance("/api/v1/clientes", 200)
        analyzer.record_endpoint_performance("/api/v1/auth/login", 150)

        # Esperar un poco para que se recopilen métricas
        time.sleep(35)

        # Obtener reportes
        status = analyzer.get_current_status()
        report = analyzer.get_performance_report()

        print("Estado actual:", json.dumps(status, indent=2, default=str))
        print("\nReporte de performance:", json.dumps(report, indent=2, default=str))

    finally:
        analyzer.stop_monitoring()
