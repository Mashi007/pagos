from collections import deque
import statistics
﻿"""Sistema de Alertas Inteligentes para Autenticación
Sistema avanzado de monitoreo y alertas basado en patrones y umbrales
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException
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
    user_id: Optional[str]
    metadata: Dict[str, Any]
    resolved: bool = False

# ============================================
# SISTEMA DE ALERTAS INTELIGENTES
# ============================================


class IntelligentAlertSystem:
    """Sistema inteligente de alertas"""


    def __init__(self):
        self.alerts = deque(maxlen=1000)
        self.alert_rules = {}
        self.user_metrics = defaultdict
            "failed_attempts": deque(maxlen=100),
            "successful_logins": deque(maxlen=100),
            "ip_addresses": set(),
            "user_agents": set(),
            "last_activity": None
        })
        self.system_metrics = 
        }


    def add_alert
    ) -> str:
        """Agregar una nueva alerta"""

        alert = Alert
        )

        self.alerts.append(alert)

        logger.warning(f"Alerta generada: {alert_type.value} - {title}")
        return alert_id


    def analyze_authentication_event
    ) -> List[str]:
        """Analizar evento de autenticación y generar alertas"""
        generated_alerts = []

        try:
            # Actualizar métricas del usuario
            user_metrics = self.user_metrics[user_id]

            if success:
            else:

            # Actualizar información de contexto
            client_ip = request_context.get("client_ip")
            if client_ip:
                user_metrics["ip_addresses"].add(client_ip)

            user_agent = request_context.get("user_agent")
            if user_agent:
                user_metrics["user_agents"].add(user_agent)


            # Analizar patrones y generar alertas
            alerts = self._check_authentication_patterns(user_id, success, request_context)
            generated_alerts.extend(alerts)

        except Exception as e:
            logger.error(f"Error analizando evento de autenticación: {e}")

        return generated_alerts


    def _check_authentication_patterns
    ) -> List[str]:
        """Verificar patrones de autenticación y generar alertas"""
        alerts = []
        user_metrics = self.user_metrics[user_id]

        if not success:
            recent_failures = [
                attempt for attempt in user_metrics["failed_attempts"]
            ]

            if len(recent_failures) >= 5:
                alert_id = self.add_alert
                        "failed_attempts": len(recent_failures),
                        "client_ip": request_context.get("client_ip")
                    }
                )
                alerts.append(alert_id)

        # Verificar ubicación inusual
        client_ip = request_context.get("client_ip")
        if client_ip and len(user_metrics["ip_addresses"]) > 1:
            if client_ip not in user_metrics["ip_addresses"]:
                alert_id = self.add_alert
                        "known_ips": list(user_metrics["ip_addresses"])
                    }
                )
                alerts.append(alert_id)

        if len(user_metrics["user_agents"]) > 3:
            alert_id = self.add_alert
                    "user_agents": list(user_metrics["user_agents"]),
                    "count": len(user_metrics["user_agents"])
                }
            )
            alerts.append(alert_id)

        return alerts


    def get_active_alerts
    ) -> List[Alert]:
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



    def resolve_alert(self, alert_id: str) -> bool:
        """Resolver una alerta"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
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

        return 
        }

# Instancia global del sistema de alertas
alert_system = IntelligentAlertSystem()

# ============================================
# ENDPOINTS DE ALERTAS
# ============================================

async def analyze_authentication_event
    current_user: User = Depends(get_current_user),
):
    """Analizar evento de autenticación"""
    try:
        user_id = event_data.get("user_id", current_user.id)
        success = event_data.get("success", False)

        # Obtener contexto de la petición
        request_context = 
        }

        # Analizar evento
        generated_alerts = alert_system.analyze_authentication_event
        )

        return 
            "message": f"Evento analizado, {len(generated_alerts)} alertas generadas"
        }

    except Exception as e:
        logger.error(f"Error analizando evento de autenticación: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/active-alerts")
async def get_active_alerts
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
                raise HTTPException
                )

        type_enum = None
        if alert_type:
            try:
                type_enum = AlertType(alert_type)
            except ValueError:
                raise HTTPException
                )

        # Obtener alertas filtradas
        alerts = alert_system.get_active_alerts(severity_enum, type_enum, user_id)

        # Convertir a formato serializable
        alerts_data = [
            
            }
            for alert in alerts
        ]

        return 
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo alertas activas: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

async def resolve_alert
    current_user: User = Depends(get_current_user),
):
    """Resolver una alerta"""
    try:
        success = alert_system.resolve_alert(alert_id)

        if success:
            return 
            }
        else:
            raise HTTPException
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolviendo alerta: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/alert-statistics")
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas de alertas"""
    try:
        statistics = alert_system.get_alert_statistics()

        return 
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/user-metrics/{user_id}")
async def get_user_metrics
    current_user: User = Depends(get_current_user),
):
    """Obtener métricas de usuario"""
    try:
        user_metrics = alert_system.user_metrics.get(user_id, {})

        # Convertir sets a listas para serialización
        metrics_data = 
        }

        return 
        }

    except Exception as e:
        logger.error(f"Error obteniendo métricas de usuario: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

"""