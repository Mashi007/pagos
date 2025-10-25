"""Sistema Forense de Análisis de Logs y Trazas
Reconstruye la secuencia exacta de eventos que llevan al error 401
"""

import logging
import threading
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request, HTTPException
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA FORENSE DE ANÁLISIS
# ============================================


class ForensicAnalyzer:
    """Analizador forense de logs y trazas"""


    def __init__(self):
        self.event_timeline = deque(maxlen=10000)
        self.user_sessions = defaultdict(list)
        self.error_sequences = defaultdict(list)
        self.lock = threading.Lock()


    def log_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        request_context: Dict[str, Any]
    ) -> str:
        """Registrar un evento en la línea de tiempo"""
        event_id = str(uuid.uuid4())

        event = {
            "event_id": event_id,
            "timestamp": datetime.now(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "request_context": request_context
        }

        with self.lock:
            self.event_timeline.append(event)
            self.user_sessions[user_id].append(event)

            # Si es un error, agregarlo a la secuencia de errores
            if "error" in event_type.lower() or "fail" in event_type.lower():
                self.error_sequences[user_id].append(event)

        logger.info(f"Evento registrado: {event_type} para usuario {user_id}")
        return event_id


    def reconstruct_error_sequence(
        self,
        user_id: str,
        error_event_id: str,
        time_window_minutes: int = 30
    ) -> Dict[str, Any]:
        """Reconstruir secuencia de eventos que llevaron al error"""
        reconstruction = {
            "error_event_id": error_event_id,
            "user_id": user_id,
            "time_window_minutes": time_window_minutes,
            "events_sequence": [],
            "analysis": {},
            "timeline": [],
            "recommendations": []
        }

        try:
            with self.lock:
                # Encontrar el evento de error
                error_event = None
                for event in self.event_timeline:
                    if event["event_id"] == error_event_id:
                        error_event = event
                        break

                if not error_event:
                    reconstruction["error"] = "Evento de error no encontrado"
                    return reconstruction

                # Obtener ventana de tiempo
                start_time = error_event["timestamp"] - timedelta(minutes=time_window_minutes)

                # Filtrar eventos del usuario en la ventana de tiempo
                user_events = [
                    event for event in self.user_sessions[user_id]
                    if start_time <= event["timestamp"] <= error_event["timestamp"]
                ]

                # Ordenar por timestamp
                user_events.sort(key=lambda x: x["timestamp"])

                reconstruction["events_sequence"] = user_events
                reconstruction["timeline"] = [
                    {
                        "timestamp": event["timestamp"].isoformat(),
                        "event_type": event["event_type"],
                        "details": event["details"]
                    }
                    for event in user_events
                ]

                # Analizar la secuencia
                analysis = self._analyze_event_sequence(user_events, error_event)
                reconstruction["analysis"] = analysis

                # Generar recomendaciones
                recommendations = self._generate_forensic_recommendations(analysis)
                reconstruction["recommendations"] = recommendations

        except Exception as e:
            logger.error(f"Error reconstruyendo secuencia: {e}")
            reconstruction["error"] = str(e)

        return reconstruction


    def _analyze_event_sequence(
        self,
        events: List[Dict[str, Any]],
        error_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar secuencia de eventos"""
        analysis = {
            "total_events": len(events),
            "error_patterns": [],
            "suspicious_activities": [],
            "timeline_anomalies": [],
            "user_behavior_changes": [],
            "security_indicators": []
        }

        # Analizar patrones de error
        error_events = [e for e in events if "error" in e["event_type"].lower()]
        analysis["error_patterns"] = [
            {
                "event_type": e["event_type"],
                "timestamp": e["timestamp"].isoformat(),
                "details": e["details"]
            }
            for e in error_events
        ]

        # Detectar actividades sospechosas
        suspicious_events = []
        for event in events:
            event_type = event["event_type"].lower()
            if any(keyword in event_type for keyword in ["unauthorized", "forbidden", "suspicious"]):
                suspicious_events.append(event)

        analysis["suspicious_activities"] = [
            {
                "event_type": e["event_type"],
                "timestamp": e["timestamp"].isoformat(),
                "details": e["details"]
            }
            for e in suspicious_events
        ]

        # Detectar anomalías en la línea de tiempo
        if len(events) > 1:
            time_gaps = []
            for i in range(1, len(events)):
                gap = events[i]["timestamp"] - events[i-1]["timestamp"]
                if gap.total_seconds() > 300:  # Más de 5 minutos
                    time_gaps.append({
                        "gap_seconds": gap.total_seconds(),
                        "between_events": [events[i-1]["event_type"], events[i]["event_type"]]
                    })

            analysis["timeline_anomalies"] = time_gaps

        return analysis


    def _generate_forensic_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones forenses"""
        recommendations = []

        # Recomendaciones basadas en patrones de error
        if analysis["error_patterns"]:
            recommendations.append("Revisar configuración de autenticación")
            recommendations.append("Verificar logs del sistema de autenticación")

        # Recomendaciones basadas en actividades sospechosas
        if analysis["suspicious_activities"]:
            recommendations.append("Implementar monitoreo adicional de seguridad")
            recommendations.append("Revisar políticas de acceso")

        # Recomendaciones basadas en anomalías temporales
        if analysis["timeline_anomalies"]:
            recommendations.append("Investigar períodos de inactividad inusuales")
            recommendations.append("Verificar integridad de los logs")

        # Recomendaciones generales
        if not recommendations:
            recommendations.append("Continuar monitoreo de la actividad del usuario")
            recommendations.append("Revisar políticas de seguridad")

        return recommendations


    def get_user_session_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtener resumen de sesión del usuario"""
        with self.lock:
            user_events = self.user_sessions.get(user_id, [])

            if not user_events:
                return {
                    "user_id": user_id,
                    "total_events": 0,
                    "last_activity": None,
                    "error_count": 0,
                    "session_duration": 0
                }

            # Calcular métricas
            total_events = len(user_events)
            error_count = len(self.error_sequences.get(user_id, []))
            last_activity = max(event["timestamp"] for event in user_events)

            # Duración de sesión (desde el primer evento hasta el último)
            if len(user_events) > 1:
                session_start = min(event["timestamp"] for event in user_events)
                session_end = max(event["timestamp"] for event in user_events)
                session_duration = (session_end - session_start).total_seconds()
            else:
                session_duration = 0

            return {
                "user_id": user_id,
                "total_events": total_events,
                "last_activity": last_activity.isoformat(),
                "error_count": error_count,
                "session_duration": session_duration,
                "recent_events": [
                    {
                        "event_type": event["event_type"],
                        "timestamp": event["timestamp"].isoformat()
                    }
                    for event in user_events[-10:]  # Últimos 10 eventos
                ]
            }

# Instancia global del analizador forense
forensic_analyzer = ForensicAnalyzer()

# ============================================
# ENDPOINTS FORENSES
# ============================================

@router.post("/log-event")
async def log_forensic_event(
    event_data: Dict[str, Any],
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Registrar un evento forense"""
    try:
        event_type = event_data.get("event_type", "unknown")
        user_id = event_data.get("user_id", current_user.id)
        details = event_data.get("details", {})

        # Obtener contexto de la petición
        request_context = {
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "endpoint": str(request.url),
            "method": request.method
        }

        # Registrar evento
        event_id = forensic_analyzer.log_event(
            event_type, user_id, details, request_context
        )

        return {
            "success": True,
            "event_id": event_id,
            "message": "Evento registrado exitosamente"
        }

    except Exception as e:
        logger.error(f"Error registrando evento forense: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.post("/reconstruct-error-sequence")
async def reconstruct_error_sequence_endpoint(
    reconstruction_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Reconstruir secuencia de eventos de error"""
    try:
        user_id = reconstruction_data.get("user_id")
        error_event_id = reconstruction_data.get("error_event_id")
        time_window = reconstruction_data.get("time_window_minutes", 30)

        if not user_id or not error_event_id:
            raise HTTPException(
                status_code=400,
                detail="user_id y error_event_id son requeridos"
            )

        # Reconstruir secuencia
        reconstruction = forensic_analyzer.reconstruct_error_sequence(
            user_id, error_event_id, time_window
        )

        return {
            "success": True,
            "reconstruction": reconstruction
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconstruyendo secuencia: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/user-session/{user_id}")
async def get_user_session_summary(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener resumen de sesión del usuario"""
    try:
        summary = forensic_analyzer.get_user_session_summary(user_id)

        return {
            "success": True,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de sesión: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/forensic-timeline")
async def get_forensic_timeline(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Obtener línea de tiempo forense"""
    try:
        with forensic_analyzer.lock:
            recent_events = list(forensic_analyzer.event_timeline)[-limit:]

        timeline = [
            {
                "event_id": event["event_id"],
                "timestamp": event["timestamp"].isoformat(),
                "event_type": event["event_type"],
                "user_id": event["user_id"],
                "details": event["details"]
            }
            for event in recent_events
        ]

        return {
            "success": True,
            "timeline": timeline,
            "total_events": len(timeline)
        }

    except Exception as e:
        logger.error(f"Error obteniendo línea de tiempo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
