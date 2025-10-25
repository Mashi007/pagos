"""
Sistema de Alertas Inteligentes para Autenticación
Sistema avanzado de monitoreo y alertas basado en patrones y umbrales
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertSeverity(Enum):
    """Severidad de alertas"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Estado de alertas"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Regla de alerta"""

    name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    cooldown_minutes: int = 15
    enabled: bool = True


@dataclass
class Alert:
    """Alerta generada"""

    id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# Almacenamiento de alertas
active_alerts = deque(maxlen=500)  # Alertas activas
alert_history = deque(maxlen=2000)  # Historial de alertas
alert_rules = {}  # Reglas de alerta configuradas
alert_cooldowns = {}  # Cooldowns de alertas


class IntelligentAlertSystem:
    """Sistema inteligente de alertas"""

    def __init__(self):
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Inicializar reglas de alerta por defecto"""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                condition="error_rate > threshold",
                threshold=0.3,  # 30%
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=10,
            ),
            AlertRule(
                name="slow_response_time",
                condition="avg_response_time > threshold",
                threshold=3000,  # 3 segundos
                severity=AlertSeverity.WARNING,
                cooldown_minutes=15,
            ),
            AlertRule(
                name="token_expiry_spike",
                condition="token_expiry_rate > threshold",
                threshold=0.2,  # 20%
                severity=AlertSeverity.WARNING,
                cooldown_minutes=20,
            ),
            AlertRule(
                name="authentication_failure_spike",
                condition="auth_failures_per_minute > threshold",
                threshold=10,  # 10 fallos por minuto
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
            ),
            AlertRule(
                name="database_connection_issues",
                condition="db_connection_failures > threshold",
                threshold=3,  # 3 fallos de conexión
                severity=AlertSeverity.EMERGENCY,
                cooldown_minutes=5,
            ),
            AlertRule(
                name="unusual_user_patterns",
                condition="unusual_user_activity > threshold",
                threshold=0.5,  # 50% de actividad inusual
                severity=AlertSeverity.WARNING,
                cooldown_minutes=30,
            ),
        ]

        for rule in default_rules:
            alert_rules[rule.name] = rule

    def evaluate_conditions(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Evaluar condiciones y generar alertas"""
        new_alerts = []
        current_time = datetime.now()

        for rule_name, rule in alert_rules.items():
            if not rule.enabled:
                continue

            # Verificar cooldown
            if rule_name in alert_cooldowns:
                last_alert_time = alert_cooldowns[rule_name]
                if current_time - last_alert_time < timedelta(
                    minutes=rule.cooldown_minutes
                ):
                    continue

            # Evaluar condición
            if self._evaluate_condition(rule, metrics):
                alert = self._create_alert(rule, metrics)
                new_alerts.append(alert)

                # Actualizar cooldown
                alert_cooldowns[rule_name] = current_time

        return new_alerts

    def _evaluate_condition(
        self, rule: AlertRule, metrics: Dict[str, Any]
    ) -> bool:
        """Evaluar condición específica de la regla"""
        try:
            if rule.name == "high_error_rate":
                error_rate = metrics.get("error_rate", 0)
                return error_rate > rule.threshold

            elif rule.name == "slow_response_time":
                avg_response_time = metrics.get("avg_response_time", 0)
                return avg_response_time > rule.threshold

            elif rule.name == "token_expiry_spike":
                token_expiry_rate = metrics.get("token_expiry_rate", 0)
                return token_expiry_rate > rule.threshold

            elif rule.name == "authentication_failure_spike":
                auth_failures = metrics.get("auth_failures_per_minute", 0)
                return auth_failures > rule.threshold

            elif rule.name == "database_connection_issues":
                db_failures = metrics.get("db_connection_failures", 0)
                return db_failures > rule.threshold

            elif rule.name == "unusual_user_patterns":
                unusual_activity = metrics.get("unusual_user_activity", 0)
                return unusual_activity > rule.threshold

            return False

        except Exception as e:
            logger.error(f"Error evaluando condición {rule.name}: {e}")
            return False

    def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> Alert:
        """Crear nueva alerta"""
        import uuid

        alert_id = str(uuid.uuid4())

        # Generar mensaje específico
        message = self._generate_alert_message(rule, metrics)

        # Crear detalles
        details = {
            "rule_name": rule.name,
            "threshold": rule.threshold,
            "current_value": self._get_current_value(rule.name, metrics),
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            details=details,
            timestamp=datetime.now(),
            status=AlertStatus.ACTIVE,
        )

        # Agregar a almacenamiento
        active_alerts.append(alert)
        alert_history.append(alert)

        # Log de alerta
        logger.warning(
            f"🚨 ALERT [{rule.severity.value.upper()}] {rule.name}: {message}"
        )

        return alert

    def _generate_alert_message(
        self, rule: AlertRule, metrics: Dict[str, Any]
    ) -> str:
        """Generar mensaje específico para la alerta"""
        current_value = self._get_current_value(rule.name, metrics)

        messages = {
            "high_error_rate": (
                f"Tasa de error alta: {current_value:.1%} (umbral: {rule.threshold:.1%})"
            ),
            "slow_response_time": (
                f"Tiempo de respuesta lento: {current_value:.0f}ms (umbral: {rule.threshold:.0f}ms)"
            ),
            "token_expiry_spike": (
                f"Pico de tokens expirados: {current_value:.1%} (umbral: {rule.threshold:.1%})"
            ),
            "authentication_failure_spike": (
                f"Pico de fallos de autenticación: {current_value:.0f}/min (...
            ),
            "database_connection_issues": (
                f"Problemas de conexión a BD: {current_value:.0f} fallos (um...
            ),
            "unusual_user_patterns": (
                f"Patrones de usuario inusuales: {current_value:.1%} (umbral: {rule.threshold:.1%})"
            ),
        }

        return messages.get(
            rule.name,
            f"Alerta {rule.name}: {current_value} > {rule.threshold}",
        )

    def _get_current_value(
        self, rule_name: str, metrics: Dict[str, Any]
    ) -> float:
        """Obtener valor actual para la regla"""
        value_map = {
            "high_error_rate": metrics.get("error_rate", 0),
            "slow_response_time": metrics.get("avg_response_time", 0),
            "token_expiry_spike": metrics.get("token_expiry_rate", 0),
            "authentication_failure_spike": metrics.get(
                "auth_failures_per_minute", 0
            ),
            "database_connection_issues": metrics.get(
                "db_connection_failures", 0
            ),
            "unusual_user_patterns": metrics.get("unusual_user_activity", 0),
        }

        return value_map.get(rule_name, 0)


# Instancia global del sistema de alertas
alert_system = IntelligentAlertSystem()


@router.post("/evaluate-alerts")
async def evaluate_alerts(db: Session = Depends(get_db)):
    """
    🚨 Evaluar condiciones y generar alertas
    """
    try:
        # Recolectar métricas actuales
        current_time = datetime.now()

        # Simular recolección de métricas (en producción vendría de
        # logs/monitoring)
        metrics = {
            "error_rate": 0.15,  # Simulado
            "avg_response_time": 1200,  # Simulado
            "token_expiry_rate": 0.05,  # Simulado
            "auth_failures_per_minute": 3,  # Simulado
            "db_connection_failures": 0,  # Simulado
            "unusual_user_activity": 0.1,  # Simulado
            "timestamp": current_time.isoformat(),
        }

        # Evaluar condiciones
        new_alerts = alert_system.evaluate_conditions(metrics)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "evaluation": {
                "metrics": metrics,
                "rules_evaluated": len(alert_rules),
                "new_alerts": len(new_alerts),
                "active_alerts_count": len(active_alerts),
            },
            "new_alerts": [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in new_alerts
            ],
        }

    except Exception as e:
        logger.error(f"Error evaluando alertas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/active-alerts")
async def get_active_alerts():
    """
    📋 Obtener alertas activas
    """
    try:
        # Filtrar alertas activas
        current_alerts = [
            alert
            for alert in active_alerts
            if alert.status == AlertStatus.ACTIVE
        ]

        # Agrupar por severidad
        alerts_by_severity = defaultdict(list)
        for alert in current_alerts:
            alerts_by_severity[alert.severity.value].append(
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "details": alert.details,
                }
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "alerts": {
                "total_active": len(current_alerts),
                "by_severity": dict(alerts_by_severity),
                "all_alerts": [
                    {
                        "id": alert.id,
                        "rule_name": alert.rule_name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat(),
                        "status": alert.status.value,
                    }
                    for alert in current_alerts
                ],
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo alertas activas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/acknowledge-alert/{alert_id}")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "system"):
    """
    ✅ Reconocer alerta
    """
    try:
        # Buscar alerta
        alert_found = False
        for alert in active_alerts:
            if alert.id == alert_id and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                alert_found = True
                break

        if not alert_found:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Alert not found or already acknowledged",
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": f"Alert {alert_id} acknowledged by {acknowledged_by}",
        }

    except Exception as e:
        logger.error(f"Error reconociendo alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/resolve-alert/{alert_id}")
async def resolve_alert(alert_id: str, resolved_by: str = "system"):
    """
    ✅ Resolver alerta
    """
    try:
        # Buscar alerta
        alert_found = False
        for alert in active_alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                alert_found = True
                break

        if not alert_found:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Alert not found",
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": f"Alert {alert_id} resolved by {resolved_by}",
        }

    except Exception as e:
        logger.error(f"Error resolviendo alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/alert-rules")
async def get_alert_rules():
    """
    ⚙️ Obtener reglas de alerta configuradas
    """
    try:
        rules_data = {}
        for rule_name, rule in alert_rules.items():
            rules_data[rule_name] = {
                "name": rule.name,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity.value,
                "cooldown_minutes": rule.cooldown_minutes,
                "enabled": rule.enabled,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "rules": rules_data,
            "total_rules": len(alert_rules),
        }

    except Exception as e:
        logger.error(f"Error obteniendo reglas de alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/update-alert-rule")
async def update_alert_rule(
    rule_name: str,
    threshold: float = None,
    enabled: bool = None,
    cooldown_minutes: int = None,
):
    """
    ⚙️ Actualizar regla de alerta
    """
    try:
        if rule_name not in alert_rules:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Rule '{rule_name}' not found",
            }

        rule = alert_rules[rule_name]

        if threshold is not None:
            rule.threshold = threshold
        if enabled is not None:
            rule.enabled = enabled
        if cooldown_minutes is not None:
            rule.cooldown_minutes = cooldown_minutes

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": f"Rule '{rule_name}' updated successfully",
            "rule": {
                "name": rule.name,
                "threshold": rule.threshold,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
            },
        }

    except Exception as e:
        logger.error(f"Error actualizando regla de alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/alert-summary")
async def get_alert_summary():
    """
    📊 Resumen de alertas
    """
    try:
        # Estadísticas de alertas activas
        active_count = len(
            [a for a in active_alerts if a.status == AlertStatus.ACTIVE]
        )
        acknowledged_count = len(
            [a for a in active_alerts if a.status == AlertStatus.ACKNOWLEDGED]
        )
        resolved_count = len(
            [a for a in alert_history if a.status == AlertStatus.RESOLVED]
        )

        # Estadísticas por severidad
        severity_stats = defaultdict(int)
        for alert in active_alerts:
            if alert.status == AlertStatus.ACTIVE:
                severity_stats[alert.severity.value] += 1

        # Alertas más frecuentes
        rule_frequency = defaultdict(int)
        for alert in alert_history:
            rule_frequency[alert.rule_name] += 1

        most_frequent = sorted(
            rule_frequency.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "summary": {
                "active_alerts": active_count,
                "acknowledged_alerts": acknowledged_count,
                "resolved_alerts": resolved_count,
                "by_severity": dict(severity_stats),
                "most_frequent_rules": most_frequent,
                "total_rules": len(alert_rules),
                "enabled_rules": len(
                    [r for r in alert_rules.values() if r.enabled]
                ),
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de alertas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }
