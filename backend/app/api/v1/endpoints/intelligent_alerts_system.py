"""Sistema de Alertas Inteligentes para Autenticación
Detecta y alerta sobre problemas de autenticación en tiempo real
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE ALERTAS INTELIGENTES
# ============================================

class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Tipos de alertas"""
    TOKEN_EXPIRY = "token_expiry"
    AUTH_FAILURE = "auth_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SYSTEM_OVERLOAD = "system_overload"
    SECURITY_BREACH = "security_breach"
    PERFORMANCE_DEGRADATION = "performance_degradation"

class IntelligentAlertSystem:
    """Sistema de alertas inteligentes"""    
    
def __init__(self):
        self.active_alerts = {}  # Alertas activas
        self.alert_history = deque(maxlen=1000)  # Historial de alertas
        self.alert_rules = {}  # Reglas de alerta
        self.metrics_buffer = deque(maxlen=100)  # Buffer de métricas
        self.notification_handlers = []  # Manejadores de notificaciones
        self.lock = threading.Lock()
        
        # Inicializar reglas por defecto
        self._initialize_default_rules()
        
        # Iniciar monitoreo en background
        self._start_background_monitoring()
    
def _initialize_default_rules(self):
        """Inicializar reglas de alerta por defecto"""
        self.alert_rules = {
            AlertType.TOKEN_EXPIRY: {
                "threshold": 5,  # minutos antes de expirar
                "severity": AlertSeverity.MEDIUM,
                "enabled": True,
                "cooldown": 300,  # 5 minutos entre alertas
            },
            AlertType.AUTH_FAILURE: {
                "threshold": 10,  # fallos por minuto
                "severity": AlertSeverity.HIGH,
                "enabled": True,
                "cooldown": 60,  # 1 minuto entre alertas
            },
            AlertType.SUSPICIOUS_ACTIVITY: {
                "threshold": 5,  # actividades sospechosas por minuto
                "severity": AlertSeverity.MEDIUM,
                "enabled": True,
                "cooldown": 180,  # 3 minutos entre alertas
            },
            AlertType.SYSTEM_OVERLOAD: {
                "threshold": 80,  # porcentaje de uso de recursos
                "severity": AlertSeverity.HIGH,
                "enabled": True,
                "cooldown": 120,  # 2 minutos entre alertas
            },
            AlertType.SECURITY_BREACH: {
                "threshold": 1,  # cualquier intento de brecha
                "severity": AlertSeverity.CRITICAL,
                "enabled": True,
                "cooldown": 0,  # sin cooldown para críticos
            },
            AlertType.PERFORMANCE_DEGRADATION: {
                "threshold": 5000,  # ms de tiempo de respuesta
                "severity": AlertSeverity.MEDIUM,
                "enabled": True,
                "cooldown": 300,  # 5 minutos entre alertas
            },
        }
    
def _start_background_monitoring(self):
        """Iniciar monitoreo en background"""        
        def monitor():
            while True:
                try:
                    self._check_alert_conditions()
                    time.sleep(30)  # Verificar cada 30 segundos
                except Exception as e:
                    logger.error(f"Error en monitoreo de alertas: {e}")
                    time.sleep(60)  # Esperar más tiempo en caso de error
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info("Monitoreo de alertas iniciado")
    
def _check_alert_conditions(self):
        """Verificar condiciones de alerta"""
        with self.lock:
            current_time = datetime.now()
            
            # Verificar cada tipo de alerta
            for alert_type, rule in self.alert_rules.items():
                if not rule["enabled"]:
                    continue
                
                # Verificar cooldown
                last_alert = self._get_last_alert_time(alert_type)
                if last_alert and (current_time - last_alert).seconds < rule["cooldown"]:
                    continue
                
                # Verificar condición específica
                if self._check_alert_condition(alert_type, rule):
                    self._trigger_alert(alert_type, rule)
    
    def _get_last_alert_time(self, alert_type: AlertType) -> Optional[datetime]:
        """Obtener tiempo de la última alerta de este tipo"""
        for alert in reversed(self.alert_history):
            if alert["type"] == alert_type.value:
                return datetime.fromisoformat(alert["timestamp"])
        return None
    
    def _check_alert_condition(self, alert_type: AlertType, rule: Dict[str, Any]) -> bool:
        """Verificar condición específica de alerta"""
        threshold = rule["threshold"]
        
        if alert_type == AlertType.AUTH_FAILURE:
            # Contar fallos de autenticación en los últimos minutos
            recent_failures = self._count_recent_auth_failures(5)
            return recent_failures >= threshold
        
        elif alert_type == AlertType.PERFORMANCE_DEGRADATION:
            # Verificar tiempo de respuesta promedio
            avg_response_time = self._get_average_response_time()
            return avg_response_time >= threshold
        
        elif alert_type == AlertType.SYSTEM_OVERLOAD:
            # Verificar uso de recursos (simulado)
            resource_usage = self._get_resource_usage()
            return resource_usage >= threshold
        
        return False
    
    def _count_recent_auth_failures(self, minutes: int) -> int:
        """Contar fallos de autenticación recientes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        count = 0
        
        for metric in self.metrics_buffer:
            if (metric.get("type") == "auth_failure" and 
                datetime.fromisoformat(metric["timestamp"]) > cutoff):
                count += 1
        
        return count
    
    def _get_average_response_time(self) -> float:
        """Obtener tiempo de respuesta promedio"""
        response_times = [
            metric["response_time"] for metric in self.metrics_buffer
            if "response_time" in metric
        ]
        
        if not response_times:
            return 0.0
        
        return sum(response_times) / len(response_times)
    
    def _get_resource_usage(self) -> float:
        """Obtener uso de recursos (simulado)"""
        # En un sistema real, esto obtendría métricas reales del sistema
        return 45.0  # Simulado al 45%
    
    def _trigger_alert(self, alert_type: AlertType, rule: Dict[str, Any]):
        """Disparar una alerta"""
        alert = {
            "id": f"alert_{int(time.time())}_{alert_type.value}",
            "type": alert_type.value,
            "severity": rule["severity"].value,
            "message": self._generate_alert_message(alert_type),
            "timestamp": datetime.now().isoformat(),
            "threshold": rule["threshold"],
            "resolved": False,
        }
        
        with self.lock:
            self.active_alerts[alert["id"]] = alert
            self.alert_history.append(alert)
        
        logger.warning(f"🚨 Alerta disparada: {alert_type.value} - {alert['message']}")
        
        # Notificar a los manejadores
        self._notify_handlers(alert)
    
    def _generate_alert_message(self, alert_type: AlertType) -> str:
        """Generar mensaje de alerta"""
        messages = {
            AlertType.TOKEN_EXPIRY: "Token próximo a expirar",
            AlertType.AUTH_FAILURE: "Alto número de fallos de autenticación",
            AlertType.SUSPICIOUS_ACTIVITY: "Actividad sospechosa detectada",
            AlertType.SYSTEM_OVERLOAD: "Sistema sobrecargado",
            AlertType.SECURITY_BREACH: "Posible brecha de seguridad",
            AlertType.PERFORMANCE_DEGRADATION: "Degradación de performance",
        }
        
        return messages.get(alert_type, "Alerta desconocida")
    
    def _notify_handlers(self, alert: Dict[str, Any]):
        """Notificar a los manejadores de alertas"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error notificando handler: {e}")
    
    def add_metric(self, metric_data: Dict[str, Any]):
        """Agregar métrica al buffer"""
        with self.lock:
            metric_data["timestamp"] = datetime.now().isoformat()
            self.metrics_buffer.append(metric_data)
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Obtener alertas activas"""
        with self.lock:
            return list(self.active_alerts.values())
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolver una alerta"""
        with self.lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id]["resolved"] = True
                self.active_alerts[alert_id]["resolved_at"] = datetime.now().isoformat()
                del self.active_alerts[alert_id]
                logger.info(f"✅ Alerta resuelta: {alert_id}")
                return True
            return False
    
def get_alert_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de alertas"""
        with self.lock:
            total_alerts = len(self.alert_history)
            active_alerts = len(self.active_alerts)
            resolved_alerts = total_alerts - active_alerts
            
            # Distribución por severidad
            severity_dist = defaultdict(int)
            for alert in self.alert_history:
                severity_dist[alert["severity"]] += 1
            
            # Distribución por tipo
            type_dist = defaultdict(int)
            for alert in self.alert_history:
                type_dist[alert["type"]] += 1
            
            return {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "resolved_alerts": resolved_alerts,
                "severity_distribution": dict(severity_dist),
                "type_distribution": dict(type_dist),
                "resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0,
            }

# Instancia global del sistema de alertas
alert_system = IntelligentAlertSystem()

# ============================================
# ENDPOINTS DE ALERTAS INTELIGENTES
# ============================================

@router.post("/add-metric")
async def add_metric(
    metric_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Agregar métrica al sistema de alertas"""
    try:
        alert_system.add_metric(metric_data)
        
        return {
            "success": True,
            "message": "Métrica agregada exitosamente"
        }
        
    except Exception as e:
        logger.error(f"Error agregando métrica: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/active-alerts")
async def get_active_alerts(
    current_user: User = Depends(get_current_user),
):
    """Obtener alertas activas"""
    try:
        alerts = alert_system.get_active_alerts()
        
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas activas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.post("/resolve-alert/{alert_id}")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resolver una alerta"""
    try:
        success = alert_system.resolve_alert(alert_id)
        
        if success:
            return {
                "success": True,
                "message": f"Alerta {alert_id} resuelta exitosamente"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Alerta {alert_id} no encontrada"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolviendo alerta: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/alert-statistics")
async def get_alert_statistics(
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas de alertas"""
    try:
        statistics = alert_system.get_alert_statistics()
        
        return {
            "success": True,
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/alert-history")
async def get_alert_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de alertas"""
    try:
        with alert_system.lock:
            history = list(alert_system.alert_history)[-limit:]
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )