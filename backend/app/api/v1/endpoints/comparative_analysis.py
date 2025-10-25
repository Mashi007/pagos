"""
Sistema Comparativo de Análisis Diferencial
Compara casos exitosos vs fallidos para identificar diferencias específicas
"""

import logging
import statistics
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA COMPARATIVO DE ANÁLISIS DIFERENCIAL
# ============================================


class ComparativeAnalysisSystem:
    """Sistema comparativo para análisis diferencial de casos exitosos \
    vs fallidos"""

    def __init__(self):
        self.successful_cases = deque(maxlen=5000)  # Casos exitosos
        self.failed_cases = deque(maxlen=5000)  # Casos fallidos
        self.comparison_results = {}  # Resultados de comparaciones
        self.lock = threading.Lock()

    def log_successful_case(self, case_data: Dict[str, Any]):
        """Registrar caso exitoso"""
        with self.lock:
            case = {
                "case_id": case_data.get(
                    "case_id", f"success_{len(self.successful_cases)}"
                ),
                "timestamp": datetime.now(),
                "case_type": case_data.get("case_type", "unknown"),
                "data": case_data.get("data", {}),
                "metrics": case_data.get("metrics", {}),
                "context": case_data.get("context", {}),
            }
            self.successful_cases.append(case)

            logger.debug(f"✅ Caso exitoso registrado: {case['case_id']}")

    def log_failed_case(self, case_data: Dict[str, Any]):
        """Registrar caso fallido"""
        with self.lock:
            case = {
                "case_id": case_data.get(
                    "case_id", f"failed_{len(self.failed_cases)}"
                ),
                "timestamp": datetime.now(),
                "case_type": case_data.get("case_type", "unknown"),
                "data": case_data.get("data", {}),
                "metrics": case_data.get("metrics", {}),
                "context": case_data.get("context", {}),
                "error_details": case_data.get("error_details", {}),
            }
            self.failed_cases.append(case)

            logger.debug(f"❌ Caso fallido registrado: {case['case_id']}")

    def perform_differential_analysis(
        self, analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Realizar análisis diferencial completo"""
        with self.lock:
            if not self.successful_cases or not self.failed_cases:
                return {
                    "error": "Datos insuficientes para análisis diferencial",
                    "successful_cases": len(self.successful_cases),
                    "failed_cases": len(self.failed_cases),
                }

            analysis_id = (
                f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            if analysis_type == "comprehensive":
                analysis = self._comprehensive_differential_analysis()
            elif analysis_type == "token_focused":
                analysis = self._token_focused_analysis()
            elif analysis_type == "user_focused":
                analysis = self._user_focused_analysis()
            elif analysis_type == "timing_focused":
                analysis = self._timing_focused_analysis()
            else:
                analysis = self._basic_differential_analysis()

            analysis["analysis_id"] = analysis_id
            analysis["timestamp"] = datetime.now().isoformat()
            analysis["analysis_type"] = analysis_type

            # Guardar resultado
            self.comparison_results[analysis_id] = analysis

            return analysis

    def _comprehensive_differential_analysis(self) -> Dict[str, Any]:
        """Análisis diferencial comprehensivo"""
        analysis = {
            "summary": self._analyze_basic_statistics(),
            "token_analysis": self._analyze_token_differences(),
            "user_analysis": self._analyze_user_differences(),
            "timing_analysis": self._analyze_timing_differences(),
            "context_analysis": self._analyze_context_differences(),
            "pattern_analysis": self._analyze_pattern_differences(),
            "root_cause_indicators": self._identify_root_cause_indicators(),
        }

        return analysis

    def _analyze_basic_statistics(self) -> Dict[str, Any]:
        """Análisis de estadísticas básicas"""
        successful_count = len(self.successful_cases)
        failed_count = len(self.failed_cases)
        total_count = successful_count + failed_count

        # Distribución por tipo de caso
        successful_types = defaultdict(int)
        failed_types = defaultdict(int)

        for case in self.successful_cases:
            successful_types[case["case_type"]] += 1

        for case in self.failed_cases:
            failed_types[case["case_type"]] += 1

        return {
            "total_cases": total_count,
            "successful_cases": successful_count,
            "failed_cases": failed_count,
            "success_rate": (
                (successful_count / total_count * 100)
                if total_count > 0
                else 0
            ),
            "failure_rate": (
                (failed_count / total_count * 100) if total_count > 0 else 0
            ),
            "successful_types_distribution": dict(successful_types),
            "failed_types_distribution": dict(failed_types),
        }

    def _analyze_token_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias en tokens"""
        successful_tokens = []
        failed_tokens = []

        # Extraer datos de tokens de casos exitosos
        for case in self.successful_cases:
            token_data = case["data"].get("token_data", {})
            if token_data:
                successful_tokens.append(token_data)

        # Extraer datos de tokens de casos fallidos
        for case in self.failed_cases:
            token_data = case["data"].get("token_data", {})
            if token_data:
                failed_tokens.append(token_data)

        if not successful_tokens or not failed_tokens:
            return {"error": "Datos de tokens insuficientes"}

        # Análisis de longitud de tokens
        successful_lengths = [
            t.get("token_length", 0) for t in successful_tokens
        ]
        failed_lengths = [t.get("token_length", 0) for t in failed_tokens]

        # Análisis de tiempo de expiración
        successful_exp_times = []
        failed_exp_times = []

        for token_data in successful_tokens:
            if "exp_timestamp" in token_data:
                exp_time = datetime.fromtimestamp(token_data["exp_timestamp"])
                time_to_expiry = (exp_time - datetime.now()).total_seconds()
                successful_exp_times.append(time_to_expiry)

        for token_data in failed_tokens:
            if "exp_timestamp" in token_data:
                exp_time = datetime.fromtimestamp(token_data["exp_timestamp"])
                time_to_expiry = (exp_time - datetime.now()).total_seconds()
                failed_exp_times.append(time_to_expiry)

        return {
            "token_length_analysis": {
                "successful_avg_length": (
                    statistics.mean(successful_lengths)
                    if successful_lengths
                    else 0
                ),
                "failed_avg_length": (
                    statistics.mean(failed_lengths) if failed_lengths else 0
                ),
                "length_difference": (
                    statistics.mean(successful_lengths)
                    - statistics.mean(failed_lengths)
                    if successful_lengths and failed_lengths
                    else 0
                ),
            },
            "expiration_analysis": {
                "successful_avg_time_to_expiry": (
                    statistics.mean(successful_exp_times)
                    if successful_exp_times
                    else 0
                ),
                "failed_avg_time_to_expiry": (
                    statistics.mean(failed_exp_times)
                    if failed_exp_times
                    else 0
                ),
                "expiry_difference": (
                    statistics.mean(successful_exp_times)
                    - statistics.mean(failed_exp_times)
                    if successful_exp_times and failed_exp_times
                    else 0
                ),
            },
            "token_type_analysis": {
                "successful_token_types": self._count_token_types(
                    successful_tokens
                ),
                "failed_token_types": self._count_token_types(failed_tokens),
            },
        }

    def _analyze_user_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias en usuarios"""
        successful_users = []
        failed_users = []

        # Extraer datos de usuarios de casos exitosos
        for case in self.successful_cases:
            user_data = case["data"].get("user_data", {})
            if user_data:
                successful_users.append(user_data)

        # Extraer datos de usuarios de casos fallidos
        for case in self.failed_cases:
            user_data = case["data"].get("user_data", {})
            if user_data:
                failed_users.append(user_data)

        if not successful_users or not failed_users:
            return {"error": "Datos de usuarios insuficientes"}

        # Análisis de estado de usuarios
        successful_active_count = len(
            [u for u in successful_users if u.get("is_active", False)]
        )
        failed_active_count = len(
            [u for u in failed_users if u.get("is_active", False)]
        )

        successful_admin_count = len(
            [u for u in successful_users if u.get("is_admin", False)]
        )
        failed_admin_count = len(
            [u for u in failed_users if u.get("is_admin", False)]
        )

        return {
            "user_status_analysis": {
                "successful_active_rate": (
                    (successful_active_count / len(successful_users) * 100)
                    if successful_users
                    else 0
                ),
                "failed_active_rate": (
                    (failed_active_count / len(failed_users) * 100)
                    if failed_users
                    else 0
                ),
                "active_rate_difference": (
                    (successful_active_count / len(successful_users) * 100)
                    - (failed_active_count / len(failed_users) * 100)
                    if successful_users and failed_users
                    else 0
                ),
            },
            "admin_status_analysis": {
                "successful_admin_rate": (
                    (successful_admin_count / len(successful_users) * 100)
                    if successful_users
                    else 0
                ),
                "failed_admin_rate": (
                    (failed_admin_count / len(failed_users) * 100)
                    if failed_users
                    else 0
                ),
                "admin_rate_difference": (
                    (successful_admin_count / len(successful_users) * 100)
                    - (failed_admin_count / len(failed_users) * 100)
                    if successful_users and failed_users
                    else 0
                ),
            },
            "user_pattern_analysis": {
                "successful_user_patterns": self._analyze_user_patterns(
                    successful_users
                ),
                "failed_user_patterns": self._analyze_user_patterns(
                    failed_users
                ),
            },
        }

    def _analyze_timing_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de timing"""
        successful_timings = []
        failed_timings = []

        # Extraer métricas de timing de casos exitosos
        for case in self.successful_cases:
            timing_data = case["metrics"].get("timing", {})
            if timing_data:
                successful_timings.append(timing_data)

        # Extraer métricas de timing de casos fallidos
        for case in self.failed_cases:
            timing_data = case["metrics"].get("timing", {})
            if timing_data:
                failed_timings.append(timing_data)

        if not successful_timings or not failed_timings:
            return {"error": "Datos de timing insuficientes"}

        # Análisis de tiempo de respuesta
        successful_response_times = [
            t.get("response_time_ms", 0) for t in successful_timings
        ]
        failed_response_times = [
            t.get("response_time_ms", 0) for t in failed_timings
        ]

        return {
            "response_time_analysis": {
                "successful_avg_response_time": (
                    statistics.mean(successful_response_times)
                    if successful_response_times
                    else 0
                ),
                "failed_avg_response_time": (
                    statistics.mean(failed_response_times)
                    if failed_response_times
                    else 0
                ),
                "response_time_difference": (
                    statistics.mean(successful_response_times)
                    - statistics.mean(failed_response_times)
                    if successful_response_times and failed_response_times
                    else 0
                ),
            },
            "timing_pattern_analysis": {
                "successful_timing_patterns": self._analyze_timing_patterns(
                    successful_timings
                ),
                "failed_timing_patterns": self._analyze_timing_patterns(
                    failed_timings
                ),
            },
        }

    def _analyze_context_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de contexto"""
        successful_contexts = []
        failed_contexts = []

        # Extraer contexto de casos exitosos
        for case in self.successful_cases:
            context = case.get("context", {})
            if context:
                successful_contexts.append(context)

        # Extraer contexto de casos fallidos
        for case in self.failed_cases:
            context = case.get("context", {})
            if context:
                failed_contexts.append(context)

        if not successful_contexts or not failed_contexts:
            return {"error": "Datos de contexto insuficientes"}

        # Análisis de endpoints
        successful_endpoints = [
            c.get("endpoint", "unknown") for c in successful_contexts
        ]
        failed_endpoints = [
            c.get("endpoint", "unknown") for c in failed_contexts
        ]

        # Análisis de métodos HTTP
        successful_methods = [
            c.get("method", "unknown") for c in successful_contexts
        ]
        failed_methods = [c.get("method", "unknown") for c in failed_contexts]

        return {
            "endpoint_analysis": {
                "successful_endpoints": self._count_patterns(
                    successful_endpoints
                ),
                "failed_endpoints": self._count_patterns(failed_endpoints),
                "endpoint_differences": self._find_pattern_differences(
                    successful_endpoints, failed_endpoints
                ),
            },
            "method_analysis": {
                "successful_methods": self._count_patterns(successful_methods),
                "failed_methods": self._count_patterns(failed_methods),
                "method_differences": self._find_pattern_differences(
                    successful_methods, failed_methods
                ),
            },
        }

    def _analyze_pattern_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de patrones"""
        # Identificar patrones únicos en casos exitosos
        successful_patterns = self._extract_patterns(self.successful_cases)
        failed_patterns = self._extract_patterns(self.failed_cases)

        # Patrones que solo aparecen en casos exitosos
        success_only_patterns = set(successful_patterns.keys()) - set(
            failed_patterns.keys()
        )

        # Patrones que solo aparecen en casos fallidos
        failure_only_patterns = set(failed_patterns.keys()) - set(
            successful_patterns.keys()
        )

        # Patrones comunes con diferentes frecuencias
        common_patterns = {}
        for pattern in set(successful_patterns.keys()) & set(
            failed_patterns.keys()
        ):
            success_freq = successful_patterns[pattern]
            failed_freq = failed_patterns[pattern]
            if success_freq != failed_freq:
                common_patterns[pattern] = {
                    "successful_frequency": success_freq,
                    "failed_frequency": failed_freq,
                    "frequency_difference": success_freq - failed_freq,
                }

        return {
            "success_only_patterns": list(success_only_patterns),
            "failure_only_patterns": list(failure_only_patterns),
            "common_patterns_with_differences": common_patterns,
            "pattern_significance": self._calculate_pattern_significance(
                successful_patterns, failed_patterns
            ),
        }

    def _identify_root_cause_indicators(self) -> Dict[str, Any]:
        """Identificar indicadores de causa raíz"""
        indicators = {
            "high_confidence_indicators": [],
            "medium_confidence_indicators": [],
            "low_confidence_indicators": [],
            "recommendations": [],
        }

        # Analizar diferencias significativas
        analysis_results = self._comprehensive_differential_analysis()

        # Indicadores de alta confianza
        if "token_analysis" in analysis_results:
            token_analysis = analysis_results["token_analysis"]

            # Diferencia significativa en tiempo de expiración
            if "expiration_analysis" in token_analysis:
                expiry_diff = token_analysis["expiration_analysis"].get(
                    "expiry_difference", 0
                )
                if abs(expiry_diff) > 300:  # Más de 5 minutos de diferencia
                    indicators["high_confidence_indicators"].append(
                        {
                            "indicator": "token_expiration_timing",
                            "description": (
                                f"Diferencia significativa en tiempo de expiración: {expiry_diff:.1f} segundos"
                            ),
                            "confidence": "high",
                        }
                    )

        # Indicadores de confianza media
        if "user_analysis" in analysis_results:
            user_analysis = analysis_results["user_analysis"]

            if "user_status_analysis" in user_analysis:
                active_rate_diff = user_analysis["user_status_analysis"].get(
                    "active_rate_difference", 0
                )
                if abs(active_rate_diff) > 20:  # Más del 20% de diferencia
                    indicators["medium_confidence_indicators"].append(
                        {
                            "indicator": "user_active_status",
                            "description": (
                                f"Diferencia significativa en tasa de usuarios activos: {active_rate_diff:.1f}%"
                            ),
                            "confidence": "medium",
                        }
                    )

        # Generar recomendaciones
        if indicators["high_confidence_indicators"]:
            indicators["recommendations"].append(
                "🔴 Revisar configuración de expiración de tokens"
            )

        if indicators["medium_confidence_indicators"]:
            indicators["recommendations"].append(
                "🟡 Verificar estado de usuarios en base de datos"
            )

        if not any(indicators.values()):
            indicators["recommendations"].append(
                "✅ No se encontraron diferencias significativas"
            )

        return indicators

    # Métodos auxiliares
    def _count_token_types(
        self, token_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Contar tipos de tokens"""
        token_types = defaultdict(int)
        for token_data in token_data_list:
            token_type = token_data.get("token_type", "unknown")
            token_types[token_type] += 1
        return dict(token_types)

    def _analyze_user_patterns(
        self, user_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analizar patrones de usuarios"""
        patterns = {
            "active_users": len(
                [u for u in user_data_list if u.get("is_active", False)]
            ),
            "admin_users": len(
                [u for u in user_data_list if u.get("is_admin", False)]
            ),
            "total_users": len(user_data_list),
        }
        return patterns

    def _analyze_timing_patterns(
        self, timing_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analizar patrones de timing"""
        response_times = [
            t.get("response_time_ms", 0) for t in timing_data_list
        ]
        return {
            "avg_response_time": (
                statistics.mean(response_times) if response_times else 0
            ),
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
        }

    def _count_patterns(self, pattern_list: List[str]) -> Dict[str, int]:
        """Contar patrones"""
        pattern_counts = defaultdict(int)
        for pattern in pattern_list:
            pattern_counts[pattern] += 1
        return dict(pattern_counts)

    def _find_pattern_differences(
        self, successful_patterns: List[str], failed_patterns: List[str]
    ) -> Dict[str, Any]:
        """Encontrar diferencias en patrones"""
        successful_counts = self._count_patterns(successful_patterns)
        failed_counts = self._count_patterns(failed_patterns)

        differences = {}
        all_patterns = set(successful_patterns) | set(failed_patterns)

        for pattern in all_patterns:
            success_count = successful_counts.get(pattern, 0)
            failed_count = failed_counts.get(pattern, 0)
            if success_count != failed_count:
                differences[pattern] = {
                    "successful_count": success_count,
                    "failed_count": failed_count,
                    "difference": success_count - failed_count,
                }

        return differences

    def _extract_patterns(self, cases: deque) -> Dict[str, int]:
        """Extraer patrones de casos"""
        patterns = defaultdict(int)
        for case in cases:
            # Extraer patrones del tipo de caso
            patterns[f"case_type_{case['case_type']}"] += 1

            # Extraer patrones de contexto
            context = case.get("context", {})
            if context.get("endpoint"):
                patterns[f"endpoint_{context['endpoint']}"] += 1
            if context.get("method"):
                patterns[f"method_{context['method']}"] += 1

        return dict(patterns)

    def _calculate_pattern_significance(
        self,
        successful_patterns: Dict[str, int],
        failed_patterns: Dict[str, int],
    ) -> Dict[str, float]:
        """Calcular significancia de patrones"""
        significance = {}
        all_patterns = set(successful_patterns.keys()) | set(
            failed_patterns.keys()
        )

        for pattern in all_patterns:
            success_count = successful_patterns.get(pattern, 0)
            failed_count = failed_patterns.get(pattern, 0)
            total_count = success_count + failed_count

            if total_count > 0:
                # Calcular significancia basada en diferencia proporcional
                significance[pattern] = (
                    abs(success_count - failed_count) / total_count
                )

        return significance

    def _token_focused_analysis(self) -> Dict[str, Any]:
        """Análisis enfocado en tokens"""
        return {
            "token_analysis": self._analyze_token_differences(),
            "summary": "Análisis enfocado en diferencias de tokens",
        }

    def _user_focused_analysis(self) -> Dict[str, Any]:
        """Análisis enfocado en usuarios"""
        return {
            "user_analysis": self._analyze_user_differences(),
            "summary": "Análisis enfocado en diferencias de usuarios",
        }

    def _timing_focused_analysis(self) -> Dict[str, Any]:
        """Análisis enfocado en timing"""
        return {
            "timing_analysis": self._analyze_timing_differences(),
            "summary": "Análisis enfocado en diferencias de timing",
        }

    def _basic_differential_analysis(self) -> Dict[str, Any]:
        """Análisis diferencial básico"""
        return {
            "summary": self._analyze_basic_statistics(),
            "pattern_analysis": self._analyze_pattern_differences(),
        }


# Instancia global del sistema comparativo
comparative_system = ComparativeAnalysisSystem()

# ============================================
# ENDPOINTS COMPARATIVOS
# ============================================


@router.post("/log-successful-case")
async def log_successful_case_endpoint(
    case_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ Registrar caso exitoso para análisis comparativo
    """
    try:
        comparative_system.log_successful_case(case_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "logged",
            "message": "Caso exitoso registrado",
        }

    except Exception as e:
        logger.error(f"Error registrando caso exitoso: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/log-failed-case")
async def log_failed_case_endpoint(
    case_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ❌ Registrar caso fallido para análisis comparativo
    """
    try:
        comparative_system.log_failed_case(case_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "logged",
            "message": "Caso fallido registrado",
        }

    except Exception as e:
        logger.error(f"Error registrando caso fallido: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/differential-analysis")
async def perform_differential_analysis_endpoint(
    analysis_request: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Realizar análisis diferencial completo
    """
    try:
        analysis_type = analysis_request.get("analysis_type", "comprehensive")
        analysis = comparative_system.perform_differential_analysis(
            analysis_type
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Error en análisis diferencial: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/comparative-summary")
async def get_comparative_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📈 Resumen comparativo general
    """
    try:
        with comparative_system.lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "successful_cases_count": len(
                        comparative_system.successful_cases
                    ),
                    "failed_cases_count": len(comparative_system.failed_cases),
                    "total_analyses_performed": len(
                        comparative_system.comparison_results
                    ),
                },
                "recent_analyses": (
                    list(comparative_system.comparison_results.values())[-5:]
                    if comparative_system.comparison_results
                    else []
                ),
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen comparativo: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }
