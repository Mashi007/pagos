from collections import deque
﻿"""Sistema Forense de Análisis de Logs y Trazas
"""

import logging
import threading
import uuid
from collections import defaultdict, deque
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
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "request_context": request_context
        }

        with self.lock:
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
    ) -> Dict[str, Any]:
        reconstruction = {
            "error_event_id": error_event_id,
            "user_id": user_id,
            "events_sequence": [],
            "analysis": {},
            "recommendations": []
        }

        try:
            with self.lock:
                # Encontrar el evento de error
                error_event = None
                    if event["event_id"] == error_event_id:
                        error_event = event
                        break

                if not error_event:
                    reconstruction["error"] = "Evento de error no encontrado"
                    return reconstruction

                # Obtener ventana de tiempo

                user_events = [
                    event for event in self.user_sessions[user_id]
                ]


                reconstruction["events_sequence"] = user_events
                    {
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
        analysis = {
            "total_events": len(events),
            "error_patterns": [],
            "suspicious_activities": [],
            "user_behavior_changes": [],
            "security_indicators": []
        }

        # Analizar patrones de error
        error_events = [e for e in events if "error" in e["event_type"].lower()]
        analysis["error_patterns"] = [
            {
                "event_type": e["event_type"],
                "details": e["details"]
            }
            for e in error_events
        ]

        suspicious_events = []
        for event in events:
            event_type = event["event_type"].lower()
            if any(keyword in event_type for keyword in ["unauthorized", "forbidden", "suspicious"]):
                suspicious_events.append(event)

        analysis["suspicious_activities"] = [
            {
                "event_type": e["event_type"],
                "details": e["details"]
            }
            for e in suspicious_events
        ]

        # Detectar anomalías en la línea de tiempo
        if len(events) > 1:
            for i in range(1, len(events)):
                        "gap_seconds": gap.total_seconds(),
                        "between_events": [events[i-1]["event_type"], events[i]["event_type"]]
                    })


        return analysis


    def _generate_forensic_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones forenses"""
        recommendations = []

        # Recomendaciones basadas en patrones de error
        if analysis["error_patterns"]:
            recommendations.append("Revisar configuración de autenticación")
            recommendations.append("Verificar logs del sistema de autenticación")

        if analysis["suspicious_activities"]:
            recommendations.append("Implementar monitoreo adicional de seguridad")
            recommendations.append("Revisar políticas de acceso")

        # Recomendaciones basadas en anomalías temporales

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

            # Duración de sesión (desde el primer evento hasta el último)
            if len(user_events) > 1:
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
                    }
                ]
            }

# Instancia global del analizador forense
forensic_analyzer = ForensicAnalyzer()

# ============================================
# ENDPOINTS FORENSES
# ============================================

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
        }

    except Exception as e:
        logger.error(f"Error registrando evento forense: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

async def reconstruct_error_sequence_endpoint(
    reconstruction_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    try:
        user_id = reconstruction_data.get("user_id")
        error_event_id = reconstruction_data.get("error_event_id")

        if not user_id or not error_event_id:
            raise HTTPException(
                status_code=400,
            )

        # Reconstruir secuencia
        reconstruction = forensic_analyzer.reconstruct_error_sequence(
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

    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Obtener línea de tiempo forense"""
    try:
        with forensic_analyzer.lock:

            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "user_id": event["user_id"],
                "details": event["details"]
            }
            for event in recent_events
        ]

        return {
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error obteniendo línea de tiempo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
