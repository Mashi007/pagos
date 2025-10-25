"""Sistema de Alertas Inteligentes para Autenticación
Sistema avanzado de monitoreo y alertas basado en patrones y umbrales
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# ENUMS Y DATACLASSES
# ============================================

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    AUTHENTICATION_FAILURE = "authentication_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    UNUSUAL_LOCATION = "unusual_location"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"

@dataclass
class Alert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    user_id: Optional[str]
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None

# ============================================
# SISTEMA DE ALERTAS INTELIGENTES
# ============================================

class IntelligentAlertSystem:
    """Sistema inteligente de alertas"""    
    
def __init__(self):
        self.alerts = deque(maxlen=1000)
        self.alert_rules = {}
        self.user_metrics = defaultdict(lambda: {
            "failed_attempts": deque(maxlen=100),
            "successful_logins": deque(maxlen=100),
            "ip_addresses": set(),
            "user_agents": set(),
            "last_activity": None
        })
        self.system_metrics = {
            "error_rate": deque(maxlen=100),
            "response_time": deque(maxlen=100),
            "active_users": deque(maxlen=100)
        }
        
    def add_alert(
        self, 
        alert_type: AlertType, 
        severity: AlertSeverity,
        title: str, 
        description: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Agregar una nueva alerta"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.alerts)}"
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            timestamp=datetime.now(),
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        logger.warning(f"Alerta generada: {alert_type.value} - {title}")
        return alert_id
    
    def analyze_authentication_event(
        self, 
        user_id: str, 
        success: bool,
        request_context: Dict[str, Any]
    ) -> List[str]:
        """Analizar evento de autenticación y generar alertas"""
        generated_alerts = []
        
        try:
            # Actualizar métricas del usuario
            user_metrics = self.user_metrics[user_id]
            
            if success:
                user_metrics["successful_logins"].append(datetime.now())
            else:
                user_metrics["failed_attempts"].append(datetime.now())
            
            # Actualizar información de contexto
            client_ip = request_context.get("client_ip")
            if client_ip:
                user_metrics["ip_addresses"].add(client_ip)
            
            user_agent = request_context.get("user_agent")
            if user_agent:
                user_metrics["user_agents"].add(user_agent)
            
            user_metrics["last_activity"] = datetime.now()
            
            # Analizar patrones y generar alertas
            alerts = self._check_authentication_patterns(user_id, success, request_context)
            generated_alerts.extend(alerts)
            
        except Exception as e:
            logger.error(f"Error analizando evento de autenticación: {e}")
        
        return generated_alerts
    
    def _check_authentication_patterns(
        self, 
        user_id: str, 
        success: bool,
        request_context: Dict[str, Any]
    ) -> List[str]:
        """Verificar patrones de autenticación y generar alertas"""
        alerts = []
        user_metrics = self.user_metrics[user_id]
        
        # Verificar intentos de fuerza bruta
        if not success:
            recent_failures = [
                attempt for attempt in user_metrics["failed_attempts"]
                if datetime.now() - attempt < timedelta(minutes=15)
            ]
            
            if len(recent_failures) >= 5:
                alert_id = self.add_alert(
                    AlertType.BRUTE_FORCE_ATTACK,
                    AlertSeverity.HIGH,
                    "Posible ataque de fuerza bruta",
                    f"Usuario {user_id} ha tenido {len(recent_failures)} intentos fallidos en 15 minutos",
                    user_id=user_id,
                    metadata={
                        "failed_attempts": len(recent_failures),
                        "time_window": "15 minutes",
                        "client_ip": request_context.get("client_ip")
                    }
                )
                alerts.append(alert_id)
        
        # Verificar ubicación inusual
        client_ip = request_context.get("client_ip")
        if client_ip and len(user_metrics["ip_addresses"]) > 1:
            if client_ip not in user_metrics["ip_addresses"]:
                alert_id = self.add_alert(
                    AlertType.UNUSUAL_LOCATION,
                    AlertSeverity.MEDIUM,
                    "Acceso desde ubicación inusual",
                    f"Usuario {user_id} accediendo desde nueva IP: {client_ip}",
                    user_id=user_id,
                    metadata={
                        "new_ip": client_ip,
                        "known_ips": list(user_metrics["ip_addresses"])
                    }
                )
                alerts.append(alert_id)
        
        # Verificar actividad sospechosa
        if len(user_metrics["user_agents"]) > 3:
            alert_id = self.add_alert(
                AlertType.SUSPICIOUS_ACTIVITY,
                AlertSeverity.MEDIUM,
                "Actividad sospechosa detectada",
                f"Usuario {user_id} usando múltiples user agents",
                user_id=user_id,
                metadata={
                    "user_agents": list(user_metrics["user_agents"]),
                    "count": len(user_metrics["user_agents"])
                }
            )
            alerts.append(alert_id)
        
        return alerts
    
    def get_active_alerts(
        self, 
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        user_id: Optional[str] = None
    ) -> List[Alert]:
        """Obtener alertas activas con filtros opcionales"""
        filtered_alerts = []
        
        for alert in self.alerts:
            if alert.resolved:
                continue
            
            if severity and alert.severity != severity:
                continue
            
            if alert_type and alert.alert_type != alert_type:
                continue
            
            if user_id and alert.user_id != user_id:
                continue
            
            filtered_alerts.append(alert)
        
        return sorted(filtered_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolver una alerta"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alerta resuelta: {alert_id}")
                return True
        
        return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de alertas"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts if not a.resolved])
        resolved_alerts = total_alerts - active_alerts
        
        # Distribución por severidad
        severity_distribution = defaultdict(int)
        for alert in self.alerts:
            severity_distribution[alert.severity.value] += 1
        
        # Distribución por tipo
        type_distribution = defaultdict(int)
        for alert in self.alerts:
            type_distribution[alert.alert_type.value] += 1
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": resolved_alerts,
            "severity_distribution": dict(severity_distribution),
            "type_distribution": dict(type_distribution),
            "resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
        }

# Instancia global del sistema de alertas
alert_system = IntelligentAlertSystem()

# ============================================
# ENDPOINTS DE ALERTAS
# ============================================

@router.post("/analyze-auth-event")
async def analyze_authentication_event(
    event_data: Dict[str, Any],
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Analizar evento de autenticación"""
    try:
        user_id = event_data.get("user_id", current_user.id)
        success = event_data.get("success", False)
        
        # Obtener contexto de la petición
        request_context = {
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Analizar evento
        generated_alerts = alert_system.analyze_authentication_event(
            user_id, success, request_context
        )
        
        return {
            "success": True,
            "generated_alerts": generated_alerts,
            "message": f"Evento analizado, {len(generated_alerts)} alertas generadas"
        }
        
    except Exception as e:
        logger.error(f"Error analizando evento de autenticación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/active-alerts")
async def get_active_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Obtener alertas activas"""
    try:
        # Convertir strings a enums si se proporcionan
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Severidad inválida: {severity}"
                )
        
        type_enum = None
        if alert_type:
            try:
                type_enum = AlertType(alert_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de alerta inválido: {alert_type}"
                )
        
        # Obtener alertas filtradas
        alerts = alert_system.get_active_alerts(severity_enum, type_enum, user_id)
        
        # Convertir a formato serializable
        alerts_data = [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "timestamp": alert.timestamp.isoformat(),
                "user_id": alert.user_id,
                "metadata": alert.metadata
            }
            for alert in alerts
        ]
        
        return {
            "success": True,
            "alerts": alerts_data,
            "total_count": len(alerts_data)
        }
        
    except HTTPException:
        raise
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

@router.get("/user-metrics/{user_id}")
async def get_user_metrics(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener métricas de usuario"""
    try:
        user_metrics = alert_system.user_metrics.get(user_id, {})
        
        # Convertir sets a listas para serialización
        metrics_data = {
            "user_id": user_id,
            "failed_attempts_count": len(user_metrics.get("failed_attempts", [])),
            "successful_logins_count": len(user_metrics.get("successful_logins", [])),
            "ip_addresses": list(user_metrics.get("ip_addresses", set())),
            "user_agents": list(user_metrics.get("user_agents", set())),
            "last_activity": user_metrics.get("last_activity").isoformat() if user_metrics.get("last_activity") else None
        }
        
        return {
            "success": True,
            "metrics": metrics_data
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de usuario: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )