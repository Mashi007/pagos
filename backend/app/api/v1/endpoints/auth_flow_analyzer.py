from collections import deque
"""Sistema de Análisis de Flujo de Autenticación
Tracing avanzado y análisis de causa raíz para problemas de autenticación
"""

import hashlib
import json
import logging
import uuid
from collections import defaultdict, deque
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
timing_stats = defaultdict(list)  # Estadísticas de timing


class AuthFlowTracer:


    def __init__(self):
        self.trace_id = str(uuid.uuid4())
        self.steps = []
        self.metadata = {}


    def add_step
        """Agregar paso al trace"""
        step = 
            "details": details or {},
        self.steps.append(step)

        # Log específico para debugging
        logger.info(f"🔍 AUTH_TRACE [{self.trace_id}] {step_name}: {status}")
        if details:
            logger.info(f"   Details: {json.dumps(details, default=str)}")


    def finalize(self, overall_status: str, error: str = None):
        """Finalizar el trace"""
        trace_data = 

        # Agregar al almacenamiento
        auth_flow_traces.append(trace_data)

        # Actualizar estadísticas
        timing_stats[overall_status].append(total_duration)

        # Detectar anomalías
        self._detect_anomalies(trace_data)

        logger.info
            f"{overall_status} ({total_duration:.2f}ms)"


    def _detect_anomalies(self, trace_data: Dict):
        # Anomalía 1: Duración excesiva
            anomaly_patterns["slow_auth_flow"] += 1

        failed_steps = len
        if failed_steps > 2:
            anomaly_patterns["multiple_failures"] += 1

        # Anomalía 3: Token inválido repetido
        token_errors = len
                if "token" in s["step"].lower() and s["status"] == "failed"
        if token_errors > 0:
            anomaly_patterns["token_validation_failure"] += 1


class CorrelationAnalyzer:
    """Analizador de correlación entre requests"""

    @staticmethod
    def analyze_request_correlation(request: Request) -> Dict[str, Any]:
        """Analizar correlación del request"""
        # Extraer información del request
        user_agent = request.headers.get("user-agent", "")
        auth_header = request.headers.get("authorization", "")

        # Generar fingerprint del cliente
        client_fingerprint = hashlib.md5
            f"{ip}_{user_agent}".encode()
        ).hexdigest()[:8]

        # Analizar token si existe
        token_analysis = {}
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decodificar sin verificar para análisis
                payload = jwt.decode
                token_analysis = 
            except Exception:
                token_analysis = {"error": "Invalid token format"}

        return 


def _analizar_request_info(request: Request) -> dict:
    """Analizar información del request"""
    auth_header = request.headers.get("authorization")
    user_agent = request.headers.get("user-agent", "unknown")

    return 


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
        unverified_payload = jwt.decode
        return True, "", unverified_payload
    except Exception as e:
        return False, f"Token decoding failed: {str(e)}", {}


def _verificar_expiracion_token(unverified_payload: dict) -> tuple[bool, str]:
    """Verificar si el token ha expirado"""
        return True, "No expiration found in token"


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


def _verificar_usuario_en_bd
) -> tuple[bool, str, any]:
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


async def trace_authentication_flow
    request: Request, db: Session = Depends(get_db)
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
            tracer.add_step
            tracer.finalize("failed", error_msg)
            return 

        tracer.add_step
                    len(auth_header.split(" ")[1]) if " " in auth_header else 0
            },

        # Paso 3: Extracción y análisis del token
        tracer.add_step("token_extraction", "started")
        is_valid, error_msg, token = _extraer_y_analizar_token(auth_header)
        if not is_valid:
            tracer.add_step("token_extraction", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return 

        tracer.add_step
            {"token_parts": 3, "token_length": len(token)},

        # Paso 4: Decodificación del token
        tracer.add_step("token_decoding", "started")
        is_valid, error_msg, unverified_payload = _decodificar_token(token)
        if not is_valid:
            tracer.add_step("token_decoding", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return 

        tracer.add_step
                "payload_keys": list(unverified_payload.keys()),
                "user_id": unverified_payload.get("sub"),
                "token_type": unverified_payload.get("type"),
                "exp": unverified_payload.get("exp"),
                "iat": unverified_payload.get("iat"),
            },

        # Paso 5: Verificación de expiración
        tracer.add_step("expiration_check", "started")
        is_valid, error_msg = _verificar_expiracion_token(unverified_payload)
        if not is_valid:
            tracer.add_step("expiration_check", "failed", {"error": error_msg})
            tracer.finalize("failed", error_msg)
            return 

            tracer.add_step

        # Paso 6: Verificación con SECRET_KEY
        tracer.add_step("signature_verification", "started")
        is_valid, error_msg, verified_payload = _verificar_firma_token(token)
        if not is_valid:
            tracer.add_step
            tracer.finalize("failed", error_msg)
            return 

        tracer.add_step
            {"verified": True, "user_id": verified_payload.get("sub")},

        # Paso 7: Verificación de usuario en BD
        tracer.add_step("user_verification", "started")
        user_id = verified_payload.get("sub")
        is_valid, error_msg, user = _verificar_usuario_en_bd(user_id, db)
        if not is_valid:
            tracer.add_step
            tracer.finalize("failed", error_msg)
            return 

        tracer.add_step

        # Éxito completo
        tracer.finalize("success")
        return 
            },
            "steps": tracer.steps,
            "total_duration_ms": 
    except Exception as e:
        tracer.finalize("error", str(e))
        logger.error(f"Error en trace de autenticación: {e}")
        return 


def _obtener_traces_recientes(minutes: int) -> list:
    return [
        trace
        for trace in auth_flow_traces


def _analizar_correlacion_basica(recent_traces: list, minutes: int) -> dict:
    """Análisis básico de correlación"""
    return 


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
            intervals = [
            avg_interval = sum(intervals) / len(intervals) if intervals else 0

            temporal_patterns[error_type] = 
    return temporal_patterns


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
            timing_analysis[status] = 
    return timing_analysis

@router.get("/analyze-correlation")
async def analyze_request_correlation(request: Request, minutes: int = 60):
    """
    🔗 Análisis de correlación entre requests (VERSIÓN REFACTORIZADA)
    """
    try:
        # 1. Obtener traces recientes
        recent_traces = _obtener_traces_recientes(minutes)

        # 2. Análisis de correlación básico
        correlation_analysis = _analizar_correlacion_basica

        # 3. Agrupar por tipo de error
        error_groups = _agrupar_errores_por_tipo(recent_traces)

        # 4. Análisis de patrones temporales
        temporal_patterns = _analizar_patrones_temporales(error_groups)


        # 6. Estadísticas de timing
        timing_analysis = _analizar_timing_por_estado()

        return 
            },
            "recommendations": _generate_correlation_recommendations
    except Exception as e:
        logger.error(f"Error en análisis de correlación: {e}")
        return 


def _detectar_anomalia_tasa_error(recent_traces: list) -> list:
    """Detectar anomalías de tasa de error alta"""
    anomalies = []
    total_traces = len(recent_traces)
    failed_traces = len
    error_rate = 
        (failed_traces / total_traces * 100) if total_traces > 0 else 0

    if error_rate > 50:
        anomalies.append
                f"(>{total_traces} traces analyzed)",
                "recommendation": "Investigate authentication configuration "
                "and token generation",
    elif error_rate > 20:
        anomalies.append
                f"(>{total_traces} traces analyzed)",

    return anomalies


def _detectar_anomalia_duracion_excesiva(recent_traces: list) -> list:
    """Detectar anomalías de duración excesiva"""
    anomalies = []
    slow_traces = [t for t in recent_traces if t["total_duration_ms"] > 3000]
    if slow_traces:
        avg_slow_duration = sum
        ) / len(slow_traces)
        anomalies.append
                "description": f"{len(slow_traces)} traces took >3s "
                f"(avg: {avg_slow_duration:.0f}ms)",
                "recommendation": "Check database performance and network \
                latency",
    return anomalies


    anomalies = []
    error_patterns_count = defaultdict(int)
    for trace in recent_traces:
        if trace["overall_status"] == "failed":
            error_patterns_count[trace["error"]] += 1

    for error, count in error_patterns_count.items():
        if count > 5:  # Más de 5 ocurrencias del mismo error
            anomalies.append
    return anomalies


    anomalies = []
    success_durations = timing_stats.get("success", [])
    if success_durations:
        avg_success_duration = sum(success_durations) / len(success_durations)
        if avg_success_duration > 1000:  # Más de 1 segundo para éxito
            anomalies.append
    return anomalies

@router.get("/detect-anomalies")
async def detect_authentication_anomalies():
    """
    """
    try:
        # Obtener traces de la última hora
        recent_traces = [
            trace
            for trace in auth_flow_traces

        anomalies = []

        anomalies.extend(_detectar_anomalia_tasa_error(recent_traces))
        anomalies.extend(_detectar_anomalia_duracion_excesiva(recent_traces))
        anomalies.extend

        total_traces = len(recent_traces)

        return 
            },
            "analysis_period": "last_hour",
            "total_traces_analyzed": total_traces,
    except Exception as e:
        logger.error(f"Error detectando anomalías: {e}")
        return 

    """
    """
    try:
        recent_traces = [
            trace
            for trace in auth_flow_traces

        # Ordenar por tiempo

        if limit:
            recent_traces = recent_traces[-limit:]

        for trace in recent_traces:
                "trace_id": trace["trace_id"],
                "status": trace["overall_status"],
                "duration_ms": trace["total_duration_ms"],
                "error": trace.get("error"),
                "steps_count": len(trace["steps"]),
                "failed_steps": len

        return 
            },
    except Exception as e:
        return 


def _generate_correlation_recommendations
) -> List[str]:
    """Generar recomendaciones basadas en análisis de correlación"""
    recommendations = []

    # Recomendaciones basadas en errores más comunes
    if step_failures:
        recommendations.append

    # Recomendaciones basadas en patrones temporales
    for error_type, pattern in temporal_patterns.items():
        if pattern["count"] > 3 and pattern["avg_interval_seconds"] < 60:
            recommendations.append
                f"(cada {pattern['avg_interval_seconds']:.0f}s)"

    # Recomendaciones generales
    if not recommendations:
        recommendations.append

    return recommendations

# Nota: Middleware removido - APIRouter no soporta middleware directamente
# El middleware debe ser agregado a la aplicación principal en main.py

"""
"""