"""
Sistema de Alertas Inteligentes para Autenticación
Detecta y alerta sobre problemas de autenticación en tiempo real
"""

import logging
import threading
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from collections import deque, defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
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
                'threshold': 5,  # minutos antes de expirar
                'severity': AlertSeverity.MEDIUM,
                'enabled': True,
                'cooldown': 300  # 5 minutos entre alertas
            },
            AlertType.AUTH_FAILURE: {
                'threshold': 10,  # fallos por minuto
                'severity': AlertSeverity.HIGH,
                'enabled': True,
                'cooldown': 60  # 1 minuto entre alertas
            },
            AlertType.SUSPICIOUS_ACTIVITY: {
                'threshold': 3,  # actividades sospechosas por minuto
                'severity': AlertSeverity.HIGH,
                'enabled': True,
                'cooldown': 180  # 3 minutos entre alertas
            },
            AlertType.SYSTEM_OVERLOAD: {
                'threshold': 80,  # porcentaje de CPU/memoria
                'severity': AlertSeverity.CRITICAL,
                'enabled': True,
                'cooldown': 120  # 2 minutos entre alertas
            },
            AlertType.PERFORMANCE_DEGRADATION: {
                'threshold': 5.0,  # segundos de tiempo de respuesta
                'severity': AlertSeverity.MEDIUM,
                'enabled': True,
                'cooldown': 300  # 5 minutos entre alertas
            }
        }

    def _start_background_monitoring(self):
        """Iniciar monitoreo en background"""
        def monitoring_loop():
            while True:
                try:
                    self._check_alert_conditions()
                    self._cleanup_expired_alerts()
                    time.sleep(30)  # Verificar cada 30 segundos
                except Exception as e:
                    logger.error(f"Error en monitoreo de alertas: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🚨 Sistema de alertas inteligentes iniciado")

    def add_metric(self, metric_type: str, value: float, metadata: Dict[str, Any] = None):
        """Agregar métrica para análisis"""
        with self.lock:
            metric = {
                'type': metric_type,
                'value': value,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }
            self.metrics_buffer.append(metric)

    def _check_alert_conditions(self):
        """Verificar condiciones de alerta"""
        with self.lock:
            current_time = datetime.now()

            # Verificar cada tipo de alerta
            for alert_type, rule in self.alert_rules.items():
                if not rule['enabled']:
                    continue

                # Verificar cooldown
                last_alert = self._get_last_alert_time(alert_type)
                if last_alert and (current_time - last_alert).total_seconds() < rule['cooldown']:
                    continue

                # Verificar condición específica
                if self._check_alert_condition(alert_type, rule):
                    self._trigger_alert(alert_type, rule, current_time)

    def _check_alert_condition(self, alert_type: AlertType, rule: Dict[str, Any]) -> bool:
        """Verificar condición específica de alerta"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=5)  # Últimos 5 minutos

        # Filtrar métricas recientes
        recent_metrics = [
            m for m in self.metrics_buffer 
            if m['timestamp'] > cutoff_time
        ]

        if alert_type == AlertType.AUTH_FAILURE:
            # Contar fallos de autenticación
            auth_failures = [
                m for m in recent_metrics 
                if m['type'] == 'auth_failure'
            ]
            return len(auth_failures) >= rule['threshold']

        elif alert_type == AlertType.TOKEN_EXPIRY:
            # Contar tokens expirando pronto
            expiring_tokens = [
                m for m in recent_metrics 
                if m['type'] == 'token_expiry' and m['value'] <= rule['threshold']
            ]
            return len(expiring_tokens) >= 1

        elif alert_type == AlertType.SUSPICIOUS_ACTIVITY:
            # Contar actividades sospechosas
            suspicious_activities = [
                m for m in recent_metrics 
                if m['type'] == 'suspicious_activity'
            ]
            return len(suspicious_activities) >= rule['threshold']

        elif alert_type == AlertType.PERFORMANCE_DEGRADATION:
            # Verificar tiempo de respuesta promedio
            response_times = [
                m['value'] for m in recent_metrics 
                if m['type'] == 'response_time'
            ]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                return avg_response_time >= rule['threshold']

        return False

    def _trigger_alert(self, alert_type: AlertType, rule: Dict[str, Any], timestamp: datetime):
        """Disparar alerta"""
        alert_id = f"{alert_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        alert = {
            'id': alert_id,
            'type': alert_type.value,
            'severity': rule['severity'].value,
            'timestamp': timestamp.isoformat(),
            'message': self._generate_alert_message(alert_type, rule),
            'details': self._generate_alert_details(alert_type),
            'status': 'active',
            'resolved_at': None
        }

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Enviar notificaciones
        self._send_notifications(alert)

        logger.warning(f"🚨 Alerta disparada: {alert_type.value} - {alert['message']}")

    def _generate_alert_message(self, alert_type: AlertType, rule: Dict[str, Any]) -> str:
        """Generar mensaje de alerta"""
        messages = {
            AlertType.TOKEN_EXPIRY: f"Token expirando en menos de {rule['threshold']} minutos",
            AlertType.AUTH_FAILURE: f"Más de {rule['threshold']} fallos de autenticación en los últimos minutos",
            AlertType.SUSPICIOUS_ACTIVITY: f"Actividad sospechosa detectada ({rule['threshold']}+ eventos)",
            AlertType.SYSTEM_OVERLOAD: f"Sistema sobrecargado ({rule['threshold']}%+ de recursos)",
            AlertType.PERFORMANCE_DEGRADATION: f"Degradación de rendimiento ({rule['threshold']}s+ tiempo de respuesta)"
        }
        return messages.get(alert_type, "Alerta desconocida")

    def _generate_alert_details(self, alert_type: AlertType) -> Dict[str, Any]:
        """Generar detalles de alerta"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=5)

        recent_metrics = [
            m for m in self.metrics_buffer 
            if m['timestamp'] > cutoff_time
        ]

        details = {
            'timestamp': current_time.isoformat(),
            'metrics_count': len(recent_metrics),
            'active_alerts_count': len(self.active_alerts)
        }

        if alert_type == AlertType.AUTH_FAILURE:
            auth_failures = [m for m in recent_metrics if m['type'] == 'auth_failure']
            details['auth_failures'] = len(auth_failures)
            details['failure_details'] = [m['metadata'] for m in auth_failures]

        elif alert_type == AlertType.TOKEN_EXPIRY:
            expiring_tokens = [m for m in recent_metrics if m['type'] == 'token_expiry']
            details['expiring_tokens'] = len(expiring_tokens)
            details['token_details'] = [m['metadata'] for m in expiring_tokens]

        return details

    def _send_notifications(self, alert: Dict[str, Any]):
        """Enviar notificaciones de alerta"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")

    def _get_last_alert_time(self, alert_type: AlertType) -> Optional[datetime]:
        """Obtener tiempo de la última alerta de este tipo"""
        for alert in reversed(self.alert_history):
            if alert['type'] == alert_type.value:
                return datetime.fromisoformat(alert['timestamp'])
        return None

    def _cleanup_expired_alerts(self):
        """Limpiar alertas expiradas"""
        current_time = datetime.now()
        expired_alerts = []

        for alert_id, alert in self.active_alerts.items():
            alert_time = datetime.fromisoformat(alert['timestamp'])
            # Alertas expiran después de 1 hora
            if (current_time - alert_time).total_seconds() > 3600:
                expired_alerts.append(alert_id)

        for alert_id in expired_alerts:
            self.active_alerts[alert_id]['status'] = 'expired'
            self.active_alerts[alert_id]['resolved_at'] = current_time.isoformat()
            del self.active_alerts[alert_id]

    def resolve_alert(self, alert_id: str, resolution_notes: str = ""):
        """Resolver alerta manualmente"""
        with self.lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id]['status'] = 'resolved'
                self.active_alerts[alert_id]['resolved_at'] = datetime.now().isoformat()
                self.active_alerts[alert_id]['resolution_notes'] = resolution_notes

                # Actualizar en historial también
                for alert in self.alert_history:
                    if alert['id'] == alert_id:
                        alert['status'] = 'resolved'
                        alert['resolved_at'] = datetime.now().isoformat()
                        alert['resolution_notes'] = resolution_notes
                        break

                logger.info(f"✅ Alerta resuelta: {alert_id}")
                return True
            return False

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Obtener alertas activas"""
        with self.lock:
            return list(self.active_alerts.values())

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de alertas"""
        with self.lock:
            total_alerts = len(self.alert_history)
            active_alerts = len(self.active_alerts)
            resolved_alerts = total_alerts - active_alerts

            # Contar por severidad
            severity_counts = defaultdict(int)
            for alert in self.alert_history:
                severity_counts[alert['severity']] += 1

            # Contar por tipo
            type_counts = defaultdict(int)
            for alert in self.alert_history:
                type_counts[alert['type']] += 1

            return {
                'total_alerts': total_alerts,
                'active_alerts': active_alerts,
                'resolved_alerts': resolved_alerts,
                'severity_distribution': dict(severity_counts),
                'type_distribution': dict(type_counts),
                'last_alert_time': self.alert_history[-1]['timestamp'] if self.alert_history else None
            }

# Instancia global del sistema de alertas
alert_system = IntelligentAlertSystem()

# ============================================
# ENDPOINTS DE ALERTAS INTELIGENTES
# ============================================

@router.get("/active-alerts")
async def get_active_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚨 Obtener alertas activas
    """
    try:
        alerts = alert_system.get_active_alerts()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "alerts": alerts,
            "count": len(alerts)
        }

    except Exception as e:
        logger.error(f"Error obteniendo alertas activas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/alert-statistics")
async def get_alert_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Estadísticas de alertas
    """
    try:
        stats = alert_system.get_alert_statistics()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de alertas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/resolve-alert/{alert_id}")
async def resolve_alert_endpoint(
    alert_id: str,
    resolution_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✅ Resolver alerta manualmente
    """
    try:
        resolution_notes = resolution_data.get('notes', '')
        success = alert_system.resolve_alert(alert_id, resolution_notes)

        if success:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "message": f"Alerta {alert_id} resuelta exitosamente"
            }
        else:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolviendo alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/add-metric")
async def add_metric_endpoint(
    metric_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📈 Agregar métrica para análisis de alertas
    """
    try:
        metric_type = metric_data.get('type')
        value = metric_data.get('value')
        metadata = metric_data.get('metadata', {})

        if not metric_type or value is None:
            raise HTTPException(status_code=400, detail="Tipo y valor de métrica requeridos")

        alert_system.add_metric(metric_type, value, metadata)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": "Métrica agregada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando métrica: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/alert-history")
async def get_alert_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📜 Historial de alertas
    """
    try:
        with alert_system.lock:
            history = list(alert_system.alert_history)[-limit:]

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "history": history,
            "count": len(history)
        }

    except Exception as e:
        logger.error(f"Error obteniendo historial de alertas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/configure-alert-rule")
async def configure_alert_rule(
    rule_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ Configurar regla de alerta
    """
    try:
        alert_type = rule_data.get('type')
        threshold = rule_data.get('threshold')
        severity = rule_data.get('severity')
        enabled = rule_data.get('enabled', True)
        cooldown = rule_data.get('cooldown', 300)

        if not alert_type or threshold is None:
            raise HTTPException(status_code=400, detail="Tipo y umbral requeridos")

        # Validar tipo de alerta
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Tipo de alerta inválido")

        # Validar severidad
        try:
            severity_enum = AlertSeverity(severity) if severity else AlertSeverity.MEDIUM
        except ValueError:
            raise HTTPException(status_code=400, detail="Severidad inválida")

        # Actualizar regla
        with alert_system.lock:
            alert_system.alert_rules[alert_type_enum] = {
                'threshold': threshold,
                'severity': severity_enum,
                'enabled': enabled,
                'cooldown': cooldown
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": f"Regla de alerta {alert_type} configurada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configurando regla de alerta: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
