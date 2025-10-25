"""Sistema de Análisis de Flujo de Autenticación
Tracing avanzado y análisis de causa raíz para problemas de autenticación
"""

import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

import jwt
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacenamiento para tracing
auth_flow_traces = deque(maxlen=2000)  # Mantener últimos 2000 traces
correlation_map = defaultdict(list)  # Mapear requests relacionados
anomaly_patterns = defaultdict(int)  # Patrones anómalos detectados
timing_stats = defaultdict(list)  # Estadísticas de timing

class AuthFlowTracer:
    """Sistema avanzado de tracing para flujos de autenticación"""
    
    def __init__(self):
        self.trace_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.steps = []
        self.metadata = {}
    
    def add_step(
        self,
        step_name: str,
        status: str,
        details: Dict = None,
        duration_ms: float = None,
    ):
        """Agregar paso al trace"""
        step = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms
            or (time.time() - self.start_time) * 1000,
            "details": details or {},
        }
        self.steps.append(step)
        
        # Log específico para debugging
        logger.info(f"🔍 AUTH_TRACE [{self.trace_id}] {step_name}: {status}")
        if details:
            logger.info(f"   Details: {json.dumps(details, default=str)}")
    
    def finalize(self, overall_status: str, error: str = None):
        """Finalizar el trace"""
        total_duration = (time.time() - self.start_time) * 1000
        trace_data = {
            "trace_id": self.trace_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration_ms": total_duration,
            "overall_status": overall_status,
            "error": error,
            "steps": self.steps,
            "metadata": self.metadata,
        }
        
        # Agregar al almacenamiento
        auth_flow_traces.append(trace_data)
        
        # Actualizar estadísticas
        timing_stats[overall_status].append(total_duration)
        
        # Detectar anomalías
        self._detect_anomalies(trace_data)
        
        logger.info(
            f"🏁 AUTH_TRACE [{self.trace_id}] COMPLETED: "
            f"{overall_status} ({total_duration:.2f}ms)"
        )
    
    def _detect_anomalies(self, trace_data: Dict):
        """Detectar patrones anómalos en el trace"""
        # Anomalía 1: Duración excesiva
        if trace_data["total_duration_ms"] > 5000:  # Más de 5 segundos
            anomaly_patterns["slow_auth_flow"] += 1
        
        # Anomalía 2: Muchos pasos fallidos
        failed_steps = len(
            [s for s in trace_data["steps"] if s["status"] == "failed"]
        )
        if failed_steps > 2:
            anomaly_patterns["multiple_failures"] += 1
        
        # Anomalía 3: Token inválido repetido
        token_errors = len(
            [
                s
                for s in trace_data["steps"]
                if "token" in s["step"].lower() and s["status"] == "failed"
            ]
        )
        if token_errors > 0:
            anomaly_patterns["token_validation_failure"] += 1

class CorrelationAnalyzer:
    """Analizador de correlación entre requests"""
    
    @staticmethod
    def analyze_request_correlation(request: Request) -> Dict[str, Any]:
        """Analizar correlación del request"""
        # Extraer información del request
        user_agent = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else "unknown"
        auth_header = request.headers.get("authorization", "")
        
        # Generar fingerprint del cliente
        client_fingerprint = hashlib.md5(
            f"{ip}_{user_agent}".encode()
        ).hexdigest()[:8]
        
        # Analizar token si existe
        token_analysis = {}
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decodificar sin verificar para análisis
                payload = jwt.decode(
                    token, options={"verify_signature": False}
                )
                token_analysis = {
                    "user_id": payload.get("sub"),
                    "token_type": payload.get("type"),
                    "exp": payload.get("exp"),
                    "is_expired": (
                        datetime.now().timestamp() > payload.get("exp", 0)
                        if payload.get("exp")
                        else False
                    ),
                }
            except Exception:
                token_analysis = {"error": "Invalid token format"}
        
        return {
            "client_fingerprint": client_fingerprint,
            "ip": ip,
            "user_agent": user_agent,
            "token_analysis": token_analysis,
            "timestamp": datetime.now().isoformat(),
        }

def _analizar_request_info(request: Request) -> dict:
    """Analizar información del request"""
    auth_header = request.headers.get("authorization")
    user_agent = request.headers.get("user-agent", "unknown")
    ip = request.client.host if request.client else "unknown"
    
    return {
        "has_auth_header": bool(auth_header),
        "auth_header_type": auth_header.split(" ")[0] if auth_header else None,
        "user_agent": (
            user_agent[:50] + "..." if len(user_agent) > 50 else user_agent
        ),
        "client_ip": ip,
    }

def _validar_headers_auth(auth_header: str) -> tuple[bool, str]:
    """Validar headers de autorización"""
    if not auth_header:
        return False, "Missing Authorization header"
    if not auth_header.startswith("Bearer "):
        return False, "Invalid Authorization format"
    return True, ""

def _extraer_y_analizar_token(auth_header: str) -> tuple[bool, str, str]:
    """Extraer y analizar estructura del token"""
    token = auth_header.split(" ")[1]
    token_parts = token.split(".")
    if len(token_parts) != 3:
        return False, "Invalid JWT structure", ""
    return True, "", token

def _decodificar_token(token: str) -> tuple[bool, str, dict]:
    """Decodificar token JWT sin verificar"""
    try:
        unverified_payload = jwt.decode(
            token, options={"verify_signature": False}
        )
        return True, "", unverified_payload
    except Exception as e:
        return False, f"Token decoding failed: {str(e)}", {}

def _verificar_expiracion_token(unverified_payload: dict) -> tuple[bool, str]:
    """Verificar si el token ha expirado"""
    exp_timestamp = unverified_payload.get("exp")
    if not exp_timestamp:
        return True, "No expiration found in token"
    
    exp_datetime = datetime.fromtimestamp(exp_timestamp)
    is_expired = datetime.now() > exp_datetime
    
    if is_expired:
        return False, "Token expired"
    return True, ""

def _verificar_firma_token(token: str) -> tuple[bool, str, dict]:
    """Verificar firma del token con SECRET_KEY"""
    try:
        verified_payload = decode_token(token)
        return True, "", verified_payload
    except Exception as e:
        return False, f"Signature verification failed: {str(e)}", {}

def _verificar_usuario_en_bd(
    user_id: str, db: Session
) -> tuple[bool, str, any]:
    """Verificar que el usuario existe en la base de datos"""
    try:
        if not user_id:
            return False, "No user_id in token", None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return False, f"User {user_id} not found", None
        
        if not user.is_active:
            return False, "User inactive", None
        
        return True, "", user
    except Exception as e:
        return False, f"User verification failed: {str(e)}", None

async def trace_authentication_flow(
    request: Request, db: Session = Depends(get_db)
):
    """
    🔬 Trace completo del flujo de autenticación
    Analiza cada paso del proceso de autenticación
    """
    tracer = AuthFlowTracer()
    
    try:
        # Paso 1: Análisis del request
        tracer.add_step("request_analysis", "started")
        request_info = _analizar_request_info(request)
        tracer.add_step("request_analysis", "completed", request_info)
        
        # Paso 2: Validación de headers
        tracer.add_step("header_validation", "started")
        auth_header = request.headers.get("authorization")
        is_valid, error_msg = _validar_headers_auth(auth_header)
        if not is_valid:
            tracer.add_step(
                "header_validation", "failed", {"error": error_msg}
            )
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        tracer.add_step(
            "header_validation",
            "completed",
            {
                "header_format": "Bearer",
                "token_length": (
                    len(auth_header.split(" ")[1]) if " " in auth_header else 0
                ),
            },
        )
        
        # Paso 3: Extracción y análisis del token
        tracer.add_step("token_extraction", "started")
        is_valid, error_msg, token = _extraer_y_analizar_token(auth_header)
        if not is_valid:
            tracer.add_step("token_extraction", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        tracer.add_step(
            "token_extraction",
            "completed",
            {"token_parts": 3, "token_length": len(token)},
        )
        
        # Paso 4: Decodificación del token
        tracer.add_step("token_decoding", "started")
        is_valid, error_msg, unverified_payload = _decodificar_token(token)
        if not is_valid:
            tracer.add_step("token_decoding", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        tracer.add_step(
            "token_decoding",
            "completed",
            {
                "payload_keys": list(unverified_payload.keys()),
                "user_id": unverified_payload.get("sub"),
                "token_type": unverified_payload.get("type"),
                "exp": unverified_payload.get("exp"),
                "iat": unverified_payload.get("iat"),
            },
        )
        
        # Paso 5: Verificación de expiración
        tracer.add_step("expiration_check", "started")
        is_valid, error_msg = _verificar_expiracion_token(unverified_payload)
        if not is_valid:
            tracer.add_step("expiration_check", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        exp_timestamp = unverified_payload.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            tracer.add_step(
                "expiration_check",
                "completed",
                {
                    "exp_datetime": exp_datetime.isoformat(),
                    "is_expired": False,
                    "time_until_expiry": str(exp_datetime - datetime.now()),
                },
            )
        
        # Paso 6: Verificación con SECRET_KEY
        tracer.add_step("signature_verification", "started")
        is_valid, error_msg, verified_payload = _verificar_firma_token(token)
        if not is_valid:
            tracer.add_step(
                "signature_verification", "failed", {"error": error_msg}
            )
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        tracer.add_step(
            "signature_verification",
            "completed",
            {"verified": True, "user_id": verified_payload.get("sub")},
        )
        
        # Paso 7: Verificación de usuario en BD
        tracer.add_step("user_verification", "started")
        user_id = verified_payload.get("sub")
        is_valid, error_msg, user = _verificar_usuario_en_bd(user_id, db)
        if not is_valid:
            tracer.add_step(
                "user_verification", "failed", {"error": error_msg}
            )
            tracer.finalize("failed", error_msg)
            return {
                "trace_id": tracer.trace_id,
                "status": "failed",
                "error": error_msg,
                "steps": tracer.steps,
            }
        
        tracer.add_step(
            "user_verification",
            "completed",
            {
                "user_id": user.id,
                "user_email": user.email,
                "user_active": user.is_active,
                "user_admin": user.is_admin,
            },
        )
        
        # Éxito completo
        tracer.finalize("success")
        return {
            "trace_id": tracer.trace_id,
            "status": "success",
            "user_info": {
                "id": user.id,
                "email": user.email,
                "active": user.is_active,
                "admin": user.is_admin,
            },
            "steps": tracer.steps,
            "total_duration_ms": (
                tracer.steps[-1]["duration_ms"] if tracer.steps else 0
            ),
        }
    except Exception as e:
        tracer.finalize("error", str(e))
        logger.error(f"Error en trace de autenticación: {e}")
        return {
            "trace_id": tracer.trace_id,
            "status": "error",
            "error": str(e),
            "steps": tracer.steps,
        }

def _obtener_traces_recientes(minutes: int) -> list:
    """Obtener traces recientes basados en el tiempo"""
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    return [
        trace
        for trace in auth_flow_traces
        if datetime.fromisoformat(trace["start_time"]) > cutoff_time
    ]

def _analizar_correlacion_basica(recent_traces: list, minutes: int) -> dict:
    """Análisis básico de correlación"""
    return {
        "time_range_minutes": minutes,
        "total_traces": len(recent_traces),
        "successful_traces": len(
            [t for t in recent_traces if t["overall_status"] == "success"]
        ),
        "failed_traces": len(
            [t for t in recent_traces if t["overall_status"] == "failed"]
        ),
        "error_traces": len(
            [t for t in recent_traces if t["overall_status"] == "error"]
        ),
    }

def _agrupar_errores_por_tipo(recent_traces: list) -> dict:
    """Agrupar traces por tipo de error"""
    error_groups = defaultdict(list)
    for trace in recent_traces:
        if trace["overall_status"] != "success":
            error_groups[trace["error"]].append(trace)
    return error_groups

def _analizar_patrones_temporales(error_groups: dict) -> dict:
    """Analizar patrones temporales de errores"""
    temporal_patterns = {}
    for error_type, traces in error_groups.items():
        if len(traces) > 1:
            # Calcular intervalo promedio entre errores
            timestamps = [
                datetime.fromisoformat(t["start_time"]) for t in traces
            ]
            intervals = [
                (timestamps[i + 1] - timestamps[i]).total_seconds()
                for i in range(len(timestamps) - 1)
            ]
            avg_interval = sum(intervals) / len(intervals) if intervals else 0
            
            temporal_patterns[error_type] = {
                "count": len(traces),
                "avg_interval_seconds": avg_interval,
                "first_occurrence": min(timestamps).isoformat(),
                "last_occurrence": max(timestamps).isoformat(),
            }
    return temporal_patterns

def _analizar_fallos_por_paso(recent_traces: list) -> dict:
    """Analizar fallos por paso"""
    step_failures = defaultdict(int)
    for trace in recent_traces:
        for step in trace["steps"]:
            if step["status"] == "failed":
                step_failures[step["step"]] += 1
    return step_failures

def _analizar_timing_por_estado() -> dict:
    """Analizar estadísticas de timing por estado"""
    timing_analysis = {}
    for status in ["success", "failed", "error"]:
        durations = timing_stats.get(status, [])
        if durations:
            timing_analysis[status] = {
                "count": len(durations),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": (
                    sorted(durations)[int(len(durations) * 0.95)]
                    if durations
                    else 0
                ),
            }
    return timing_analysis

@router.get("/analyze-correlation")
async def analyze_request_correlation(request: Request, minutes: int = 60):
    """
    🔗 Análisis de correlación entre requests (VERSIÓN REFACTORIZADA)
    Identifica patrones y relaciones entre requests fallidos
    """
    try:
        # 1. Obtener traces recientes
        recent_traces = _obtener_traces_recientes(minutes)
        
        # 2. Análisis de correlación básico
        correlation_analysis = _analizar_correlacion_basica(
            recent_traces, minutes
        )
        
        # 3. Agrupar por tipo de error
        error_groups = _agrupar_errores_por_tipo(recent_traces)
        
        # 4. Análisis de patrones temporales
        temporal_patterns = _analizar_patrones_temporales(error_groups)
        
        # 5. Análisis de pasos más problemáticos
        step_failures = _analizar_fallos_por_paso(recent_traces)
        
        # 6. Estadísticas de timing
        timing_analysis = _analizar_timing_por_estado()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": {
                "correlation": correlation_analysis,
                "error_groups": dict(error_groups),
                "temporal_patterns": temporal_patterns,
                "step_failures": dict(step_failures),
                "timing_analysis": timing_analysis,
                "anomaly_patterns": dict(anomaly_patterns),
            },
            "recommendations": _generate_correlation_recommendations(
                error_groups, temporal_patterns, step_failures
            ),
        }
    except Exception as e:
        logger.error(f"Error en análisis de correlación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }

def _detectar_anomalia_tasa_error(recent_traces: list) -> list:
    """Detectar anomalías de tasa de error alta"""
    anomalies = []
    total_traces = len(recent_traces)
    failed_traces = len(
        [t for t in recent_traces if t["overall_status"] == "failed"]
    )
    error_rate = (
        (failed_traces / total_traces * 100) if total_traces > 0 else 0
    )
    
    if error_rate > 50:
        anomalies.append(
            {
                "type": "high_error_rate",
                "severity": "critical",
                "description": f"Error rate is {error_rate:.1f}% "
                f"(>{total_traces} traces analyzed)",
                "recommendation": "Investigate authentication configuration "
                "and token generation",
            }
        )
    elif error_rate > 20:
        anomalies.append(
            {
                "type": "elevated_error_rate",
                "severity": "warning",
                "description": f"Error rate is {error_rate:.1f}% "
                f"(>{total_traces} traces analyzed)",
                "recommendation": "Monitor authentication patterns closely",
            }
        )
    
    return anomalies

def _detectar_anomalia_duracion_excesiva(recent_traces: list) -> list:
    """Detectar anomalías de duración excesiva"""
    anomalies = []
    slow_traces = [t for t in recent_traces if t["total_duration_ms"] > 3000]
    if slow_traces:
        avg_slow_duration = sum(
            t["total_duration_ms"] for t in slow_traces
        ) / len(slow_traces)
        anomalies.append(
            {
                "type": "slow_authentication",
                "severity": "warning",
                "description": f"{len(slow_traces)} traces took >3s "
                f"(avg: {avg_slow_duration:.0f}ms)",
                "recommendation": "Check database performance and network \
                latency",
            }
        )
    return anomalies

def _detectar_anomalia_patrones_repetitivos(recent_traces: list) -> list:
    """Detectar anomalías de patrones repetitivos de error"""
    anomalies = []
    error_patterns_count = defaultdict(int)
    for trace in recent_traces:
        if trace["overall_status"] == "failed":
            error_patterns_count[trace["error"]] += 1
    
    for error, count in error_patterns_count.items():
        if count > 5:  # Más de 5 ocurrencias del mismo error
            anomalies.append(
                {
                    "type": "repetitive_error",
                    "severity": "warning",
                    "description": f"Error '{error}' occurred {count} times",
                    "recommendation": f"Investigate root cause of: {error}",
                }
            )
    return anomalies

def _detectar_anomalia_timing_exitoso() -> list:
    """Detectar anomalías de timing en autenticaciones exitosas"""
    anomalies = []
    success_durations = timing_stats.get("success", [])
    if success_durations:
        avg_success_duration = sum(success_durations) / len(success_durations)
        if avg_success_duration > 1000:  # Más de 1 segundo para éxito
            anomalies.append(
                {
                    "type": "slow_successful_auth",
                    "severity": "info",
                    "description": f"Successful authentications average "
                    f"{avg_success_duration:.0f}ms",
                    "recommendation": "Consider optimizing authentication \
                    flow",
                }
            )
    return anomalies

@router.get("/detect-anomalies")
async def detect_authentication_anomalies():
    """
    🚨 Detección de patrones anómalos en autenticación (VERSIÓN REFACTORIZADA)
    """
    try:
        # Obtener traces de la última hora
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_traces = [
            trace
            for trace in auth_flow_traces
            if datetime.fromisoformat(trace["start_time"]) > cutoff_time
        ]
        
        anomalies = []
        
        # Detectar diferentes tipos de anomalías
        anomalies.extend(_detectar_anomalia_tasa_error(recent_traces))
        anomalies.extend(_detectar_anomalia_duracion_excesiva(recent_traces))
        anomalies.extend(
            _detectar_anomalia_patrones_repetitivos(recent_traces)
        )
        anomalies.extend(_detectar_anomalia_timing_exitoso())
        
        total_traces = len(recent_traces)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "anomalies": anomalies,
            "summary": {
                "total_anomalies": len(anomalies),
                "critical": len(
                    [a for a in anomalies if a["severity"] == "critical"]
                ),
                "warning": len(
                    [a for a in anomalies if a["severity"] == "warning"]
                ),
                "info": len([a for a in anomalies if a["severity"] == "info"]),
            },
            "analysis_period": "last_hour",
            "total_traces_analyzed": total_traces,
        }
    except Exception as e:
        logger.error(f"Error detectando anomalías: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }

@router.get("/flow-timeline")
async def get_authentication_timeline(minutes: int = 30, limit: int = 50):
    """
    📈 Timeline de flujos de autenticación
    """
    try:
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_traces = [
            trace
            for trace in auth_flow_traces
            if datetime.fromisoformat(trace["start_time"]) > cutoff_time
        ]
        
        # Ordenar por tiempo
        recent_traces.sort(key=lambda x: x["start_time"])
        
        # Limitar resultados
        if limit:
            recent_traces = recent_traces[-limit:]
        
        # Crear timeline
        timeline = []
        for trace in recent_traces:
            timeline_entry = {
                "trace_id": trace["trace_id"],
                "timestamp": trace["start_time"],
                "status": trace["overall_status"],
                "duration_ms": trace["total_duration_ms"],
                "error": trace.get("error"),
                "steps_count": len(trace["steps"]),
                "failed_steps": len(
                    [s for s in trace["steps"] if s["status"] == "failed"]
                ),
            }
            timeline.append(timeline_entry)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "timeline": {
                "period_minutes": minutes,
                "total_traces": len(timeline),
                "entries": timeline,
            },
        }
    except Exception as e:
        logger.error(f"Error obteniendo timeline: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }

def _generate_correlation_recommendations(
    error_groups: Dict, temporal_patterns: Dict, step_failures: Dict
) -> List[str]:
    """Generar recomendaciones basadas en análisis de correlación"""
    recommendations = []
    
    # Recomendaciones basadas en errores más comunes
    if step_failures:
        most_failed_step = max(step_failures.items(), key=lambda x: x[1])
        recommendations.append(
            f"🔧 Paso más problemático: '{most_failed_step[0]}' "
            f"({most_failed_step[1]} fallos)"
        )
    
    # Recomendaciones basadas en patrones temporales
    for error_type, pattern in temporal_patterns.items():
        if pattern["count"] > 3 and pattern["avg_interval_seconds"] < 60:
            recommendations.append(
                f"⚠️ Error '{error_type}' ocurre frecuentemente "
                f"(cada {pattern['avg_interval_seconds']:.0f}s)"
            )
    
    # Recomendaciones generales
    if not recommendations:
        recommendations.append(
            "✅ No se detectaron patrones problemáticos significativos"
        )
    
    return recommendations

# Nota: Middleware removido - APIRouter no soporta middleware directamente
# El middleware debe ser agregado a la aplicación principal en main.py