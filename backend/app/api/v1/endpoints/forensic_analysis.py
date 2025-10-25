"""
Sistema Forense de Análisis de Logs y Trazas
Reconstruye la secuencia exacta de eventos que llevan al error 401
"""

import logging
import threading
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA FORENSE DE TRAZAS
# ============================================


class ForensicTraceSystem:
    """Sistema forense para reconstruir eventos de autenticación"""

    def __init__(self):
        self.trace_sessions = {}  # Sesiones de trazado activas
        self.event_log = deque(maxlen=10000)  # Log de eventos
        self.failed_sequences = deque(maxlen=1000)  # Secuencias que fallaron
        self.lock = threading.Lock()

    def start_trace_session(
        self, session_id: str, user_id: str = None
    ) -> Dict[str, Any]:
        """Iniciar sesión de trazado"""
        with self.lock:
            trace_session = {
                "session_id": session_id,
                "user_id": user_id,
                "start_time": datetime.now(),
                "events": [],
                "status": "active",
                "metadata": {},
            }
            self.trace_sessions[session_id] = trace_session

            # Log evento de inicio
            self._log_event(
                "trace_session_started",
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "timestamp": trace_session["start_time"].isoformat(),
                },
            )

            return trace_session

    def log_auth_event(
        self, session_id: str, event_type: str, event_data: Dict[str, Any]
    ):
        """Registrar evento de autenticación"""
        with self.lock:
            if session_id not in self.trace_sessions:
                return

            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.now(),
                "data": event_data,
                "sequence_number": len(
                    self.trace_sessions[session_id]["events"]
                ),
            }

            self.trace_sessions[session_id]["events"].append(event)

            # Log global
            self._log_event(
                event_type,
                {
                    "session_id": session_id,
                    "event_id": event["event_id"],
                    "data": event_data,
                },
            )

            # Si es un evento de fallo, marcar secuencia como fallida
            if event_type in [
                "auth_failure",
                "token_expired",
                "validation_failed",
            ]:
                self._mark_sequence_as_failed(session_id, event)

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log global de eventos"""
        event_log = {
            "event_type": event_type,
            "timestamp": datetime.now(),
            "data": data,
        }
        self.event_log.append(event_log)

    def _mark_sequence_as_failed(
        self, session_id: str, failure_event: Dict[str, Any]
    ):
        """Marcar secuencia como fallida para análisis"""
        if session_id in self.trace_sessions:
            failed_sequence = {
                "session_id": session_id,
                "failure_event": failure_event,
                "full_sequence": self.trace_sessions[session_id][
                    "events"
                ].copy(),
                "failure_time": datetime.now(),
                "user_id": self.trace_sessions[session_id].get("user_id"),
            }
            self.failed_sequences.append(failed_sequence)

    def end_trace_session(self, session_id: str, success: bool = True):
        """Finalizar sesión de trazado"""
        with self.lock:
            if session_id in self.trace_sessions:
                self.trace_sessions[session_id]["status"] = (
                    "completed" if success else "failed"
                )
                self.trace_sessions[session_id]["end_time"] = datetime.now()

                self._log_event(
                    "trace_session_ended",
                    {
                        "session_id": session_id,
                        "success": success,
                        "duration_seconds": (
                            (
                                self.trace_sessions[session_id]["end_time"]
                                - self.trace_sessions[session_id]["start_time"]
                            ).total_seconds()
                        ),
                    },
                )

    def analyze_failed_sequence(self, session_id: str) -> Dict[str, Any]:
        """Analizar secuencia fallida específica"""
        with self.lock:
            # Buscar en secuencias fallidas
            failed_seq = None
            for seq in self.failed_sequences:
                if seq["session_id"] == session_id:
                    failed_seq = seq
                    break

            if not failed_seq:
                return {"error": "Secuencia no encontrada o no falló"}

            # Análisis forense
            analysis = {
                "session_id": session_id,
                "failure_analysis": self._analyze_failure_pattern(failed_seq),
                "timeline": self._build_timeline(failed_seq),
                "root_cause_hypothesis": self._generate_root_cause_hypothesis(
                    failed_seq
                ),
                "evidence": self._extract_evidence(failed_seq),
            }

            return analysis

    def _analyze_failure_pattern(
        self, failed_seq: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar patrón de fallo"""
        events = failed_seq["full_sequence"]
        failure_event = failed_seq["failure_event"]

        # Análisis temporal
        if len(events) >= 2:
            time_to_failure = (
                failure_event["timestamp"] - events[0]["timestamp"]
            ).total_seconds()
        else:
            time_to_failure = 0

        # Contar tipos de eventos
        event_types = defaultdict(int)
        for event in events:
            event_types[event["event_type"]] += 1

        # Identificar eventos sospechosos
        suspicious_events = []
        for event in events:
            if event["event_type"] in [
                "token_validation",
                "user_lookup",
                "permission_check",
            ]:
                if "error" in event.get("data", {}):
                    suspicious_events.append(event)

        return {
            "time_to_failure_seconds": time_to_failure,
            "total_events": len(events),
            "event_type_counts": dict(event_types),
            "suspicious_events_count": len(suspicious_events),
            "failure_event_type": failure_event["event_type"],
            "failure_data": failure_event["data"],
        }

    def _build_timeline(
        self, failed_seq: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Construir timeline de eventos"""
        timeline = []
        events = failed_seq["full_sequence"]

        for i, event in enumerate(events):
            timeline_entry = {
                "sequence": i + 1,
                "timestamp": event["timestamp"].isoformat(),
                "event_type": event["event_type"],
                "event_id": event["event_id"],
                "summary": self._summarize_event(event),
                "is_failure": event["event_id"]
                == failed_seq["failure_event"]["event_id"],
            }
            timeline.append(timeline_entry)

        return timeline

    def _summarize_event(self, event: Dict[str, Any]) -> str:
        """Resumir evento para timeline"""
        event_type = event["event_type"]
        data = event.get("data", {})

        summaries = {
            "token_received": f"Token recibido: {data.get('token_length', 'unknown')} chars",
            "token_validation": f"Validación token: {data.get('status', 'unknown')}",
            "user_lookup": f"Búsqueda usuario: {data.get('user_id', 'unknown')}",
            "permission_check": f"Verificación permisos: {data.get('permission', 'unknown')}",
            "auth_failure": f"Fallo autenticación: {data.get('reason', 'unknown')}",
            "token_expired": f"Token expirado: {data.get('exp_time', 'unknown')}",
        }

        return summaries.get(event_type, f"Evento {event_type}")

    def _generate_root_cause_hypothesis(
        self, failed_seq: Dict[str, Any]
    ) -> List[str]:
        """Generar hipótesis de causa raíz"""
        hypotheses = []
        failure_event = failed_seq["failure_event"]
        events = failed_seq["full_sequence"]

        # Hipótesis basadas en el tipo de fallo
        if failure_event["event_type"] == "token_expired":
            hypotheses.append(
                "Token JWT expirado - problema de sincronización de tiempo"
            )
            hypotheses.append(
                "Token JWT expirado - configuración de expiración incorrecta"
            )

        elif failure_event["event_type"] == "auth_failure":
            hypotheses.append(
                "Credenciales inválidas - usuario no existe o inactivo"
            )
            hypotheses.append(
                "Problema de base de datos - usuario no encontrado"
            )
            hypotheses.append(
                "Token malformado - problema de codificación JWT"
            )

        elif failure_event["event_type"] == "validation_failed":
            hypotheses.append("Validación JWT fallida - secret key incorrecta")
            hypotheses.append("Validación JWT fallida - algoritmo incorrecto")
            hypotheses.append("Token corrupto - problema de transmisión")

        # Hipótesis basadas en patrones de eventos
        event_types = [e["event_type"] for e in events]
        if (
            "token_received" in event_types
            and "token_validation" not in event_types
        ):
            hypotheses.append(
                "Token recibido pero no validado - problema en middleware"
            )

        if len(events) == 1:
            hypotheses.append(
                "Fallo inmediato - problema en configuración inicial"
            )

        return hypotheses

    def _extract_evidence(self, failed_seq: Dict[str, Any]) -> Dict[str, Any]:
        """Extraer evidencia específica"""
        evidence = {
            "token_evidence": {},
            "user_evidence": {},
            "timing_evidence": {},
            "system_evidence": {},
        }

        events = failed_seq["full_sequence"]
        failure_event = failed_seq["failure_event"]

        # Evidencia de token
        for event in events:
            if event["event_type"] == "token_received":
                evidence["token_evidence"] = event["data"]
            elif event["event_type"] == "token_validation":
                evidence["token_evidence"].update(event["data"])

        # Evidencia de usuario
        for event in events:
            if event["event_type"] == "user_lookup":
                evidence["user_evidence"] = event["data"]

        # Evidencia de timing
        if len(events) >= 2:
            evidence["timing_evidence"] = {
                "first_event_time": events[0]["timestamp"].isoformat(),
                "failure_time": failure_event["timestamp"].isoformat(),
                "total_duration_ms": (
                    (
                        failure_event["timestamp"] - events[0]["timestamp"]
                    ).total_seconds()
                    * 1000
                ),
            }

        # Evidencia del sistema
        evidence["system_evidence"] = {
            "failure_event_data": failure_event["data"],
            "total_events_before_failure": len(events) - 1,
            "session_user_id": failed_seq.get("user_id"),
        }

        return evidence

    def get_forensic_summary(self) -> Dict[str, Any]:
        """Obtener resumen forense general"""
        with self.lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(
                hours=24
            )  # Últimas 24 horas

            # Filtrar eventos recientes
            recent_events = [
                event
                for event in self.event_log
                if event["timestamp"] > cutoff_time
            ]

            # Contar tipos de eventos
            event_type_counts = defaultdict(int)
            for event in recent_events:
                event_type_counts[event["event_type"]] += 1

            # Análisis de secuencias fallidas
            recent_failures = [
                seq
                for seq in self.failed_sequences
                if seq["failure_time"] > cutoff_time
            ]

            # Patrones de fallo más comunes
            failure_patterns = defaultdict(int)
            for failure in recent_failures:
                failure_patterns[failure["failure_event"]["event_type"]] += 1

            return {
                "timestamp": current_time.isoformat(),
                "summary": {
                    "total_events_24h": len(recent_events),
                    "total_failures_24h": len(recent_failures),
                    "active_trace_sessions": len(
                        [
                            s
                            for s in self.trace_sessions.values()
                            if s["status"] == "active"
                        ]
                    ),
                    "event_type_distribution": dict(event_type_counts),
                    "failure_pattern_distribution": dict(failure_patterns),
                },
                "recent_failures": (
                    recent_failures[-10:] if recent_failures else []
                ),
                "recommendations": self._generate_forensic_recommendations(
                    recent_failures
                ),
            }

    def _generate_forensic_recommendations(
        self, recent_failures: List[Dict[str, Any]]
    ) -> List[str]:
        """Generar recomendaciones basadas en evidencia forense"""
        recommendations = []

        if not recent_failures:
            recommendations.append(
                "✅ No hay fallos recientes - sistema estable"
            )
            return recommendations

        # Analizar patrones de fallo
        failure_types = [
            f["failure_event"]["event_type"] for f in recent_failures
        ]

        if failure_types.count("token_expired") > len(failure_types) * 0.5:
            recommendations.append(
                "🔴 Más del 50% de fallos son por tokens expirados - revisar ...
            )

        if failure_types.count("auth_failure") > len(failure_types) * 0.3:
            recommendations.append(
                "🟡 Más del 30% de fallos son de autenticación - revisar vali...
            )

        if failure_types.count("validation_failed") > len(failure_types) * 0.2:
            recommendations.append(
                "🟡 Más del 20% de fallos son de validación - revisar configu...
            )

        # Recomendaciones de timing
        avg_time_to_failure = sum(
            (
                f["failure_time"] - f["full_sequence"][0]["timestamp"]
            ).total_seconds()
            for f in recent_failures
            if f["full_sequence"]
        ) / len(recent_failures)

        if avg_time_to_failure < 1:
            recommendations.append(
                "⚡ Fallos muy rápidos - posible problema de configuración in...
            )

        return recommendations


# Instancia global del sistema forense
forensic_system = ForensicTraceSystem()

# ============================================
# ENDPOINTS FORENSES
# ============================================


@router.post("/start-trace")
async def start_forensic_trace(
    trace_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Iniciar sesión de trazado forense
    """
    try:
        session_id = trace_data.get("session_id", str(uuid.uuid4()))
        user_id = trace_data.get("user_id")

        trace_session = forensic_system.start_trace_session(
            session_id, user_id
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "trace_session": trace_session,
        }

    except Exception as e:
        logger.error(f"Error iniciando trazado forense: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/log-auth-event")
async def log_auth_event_endpoint(
    event_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📝 Registrar evento de autenticación para análisis forense
    """
    try:
        session_id = event_data.get("session_id")
        event_type = event_data.get("event_type")
        event_data_dict = event_data.get("data", {})

        if not session_id or not event_type:
            raise HTTPException(
                status_code=400, detail="session_id y event_type requeridos"
            )

        forensic_system.log_auth_event(session_id, event_type, event_data_dict)

        return {"timestamp": datetime.now().isoformat(), "status": "logged"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registrando evento de autenticación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/analyze-failure/{session_id}")
async def analyze_failure_sequence(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Analizar secuencia fallida específica
    """
    try:
        analysis = forensic_system.analyze_failed_sequence(session_id)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Error analizando secuencia fallida: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/forensic-summary")
async def get_forensic_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Resumen forense general
    """
    try:
        summary = forensic_system.get_forensic_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen forense: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/end-trace/{session_id}")
async def end_forensic_trace(
    session_id: str,
    success_data: Dict[str, bool],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ Finalizar sesión de trazado forense
    """
    try:
        success = success_data.get("success", True)
        forensic_system.end_trace_session(session_id, success)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "message": f"Sesión {session_id} finalizada",
        }

    except Exception as e:
        logger.error(f"Error finalizando trazado forense: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }
