from collections import deque
"""Sistema Comparativo de Análisis Diferencial
"""

import logging
import statistics
import threading
from collections import defaultdict, deque
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


    def __init__(self):
        self.lock = threading.Lock()


    def log_successful_case(self, case_data: Dict[str, Any]):
        with self.lock:
            case = 
                    "case_id", f"success_{len(self.successful_cases)}"
                ),
                "case_type": case_data.get("case_type", "unknown"),
                "data": case_data.get("data", {}),
                "metrics": case_data.get("metrics", {}),
                "context": case_data.get("context", {}),
            }
            self.successful_cases.append(case)


    def log_failed_case(self, case_data: Dict[str, Any]):
        """Registrar caso fallido"""
        with self.lock:
            case = 
                    "case_id", f"failed_{len(self.failed_cases)}"
                ),
                "case_type": case_data.get("case_type", "unknown"),
                "data": case_data.get("data", {}),
                "metrics": case_data.get("metrics", {}),
                "context": case_data.get("context", {}),
                "error_details": case_data.get("error_details", {}),
            }
            self.failed_cases.append(case)
            logger.debug(f"❌ Caso fallido registrado: {case['case_id']}")


    def perform_differential_analysis
    ) -> Dict[str, Any]:
        """Realizar análisis diferencial completo"""
        with self.lock:
            if not self.successful_cases or not self.failed_cases:
                return 
                }

            analysis_id = 
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
            analysis["analysis_type"] = analysis_type

            # Guardar resultado
            self.comparison_results[analysis_id] = analysis

            return analysis


    def _comprehensive_differential_analysis(self) -> Dict[str, Any]:
        """Análisis diferencial comprehensivo"""
        analysis = 
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

        return 
        }


    def _analyze_token_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias en tokens"""
        successful_tokens = []
        failed_tokens = []

        for case in self.successful_cases:
            token_data = case["data"].get("token_data", {})
            if token_data:
                successful_tokens.append(token_data)

        for case in self.failed_cases:
            token_data = case["data"].get("token_data", {})
            if token_data:
                failed_tokens.append(token_data)

        if not successful_tokens or not failed_tokens:

        # Análisis de longitud de tokens
        successful_lengths = [
            t.get("token_length", 0) for t in successful_tokens
        ]
        failed_lengths = [t.get("token_length", 0) for t in failed_tokens]

        # Análisis de tiempo de expiración

        for token_data in successful_tokens:

        for token_data in failed_tokens:

        return 
            },
            "expiration_analysis": 
            },
            "token_type_analysis": 
            },
        }


    def _analyze_user_differences(self) -> Dict[str, Any]:
        successful_users = []
        failed_users = []

        for case in self.successful_cases:
            user_data = case["data"].get("user_data", {})
            if user_data:
                successful_users.append(user_data)

        for case in self.failed_cases:
            user_data = case["data"].get("user_data", {})
            if user_data:
                failed_users.append(user_data)

        if not successful_users or not failed_users:

        successful_active_count = len
            [u for u in successful_users if u.get("is_active", False)]
        )
        failed_active_count = len
            [u for u in failed_users if u.get("is_active", False)]
        )

        successful_admin_count = len
            [u for u in successful_users if u.get("is_admin", False)]
        )
        failed_admin_count = len
            [u for u in failed_users if u.get("is_admin", False)]
        )

        return 
            },
            "admin_status_analysis": 
            },
            "user_pattern_analysis": 
            },
        }


    def _analyze_timing_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de timing"""
        successful_timings = []
        failed_timings = []

        for case in self.successful_cases:
            timing_data = case["metrics"].get("timing", {})
            if timing_data:
                successful_timings.append(timing_data)

        for case in self.failed_cases:
            timing_data = case["metrics"].get("timing", {})
            if timing_data:
                failed_timings.append(timing_data)

        if not successful_timings or not failed_timings:

        # Análisis de tiempo de respuesta
        ]
        ]

        return 
            },
            "timing_pattern_analysis": 
            },
        }


    def _analyze_context_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de contexto"""
        successful_contexts = []
        failed_contexts = []

        for case in self.successful_cases:
            context = case.get("context", {})
            if context:
                successful_contexts.append(context)

        for case in self.failed_cases:
            context = case.get("context", {})
            if context:
                failed_contexts.append(context)

        if not successful_contexts or not failed_contexts:

        # Análisis de endpoints
        successful_endpoints = [
            c.get("endpoint", "unknown") for c in successful_contexts
        ]
        failed_endpoints = [
            c.get("endpoint", "unknown") for c in failed_contexts
        ]

        successful_methods = [
            c.get("method", "unknown") for c in successful_contexts
        ]
        failed_methods = [c.get("method", "unknown") for c in failed_contexts]

        return 
            },
            "method_analysis": 
            },
        }


    def _analyze_pattern_differences(self) -> Dict[str, Any]:
        """Análisis de diferencias de patrones"""
        successful_patterns = self._extract_patterns(self.successful_cases)
        failed_patterns = self._extract_patterns(self.failed_cases)

        success_only_patterns = set(successful_patterns.keys()) - set
            failed_patterns.keys()
        )

        failure_only_patterns = set(failed_patterns.keys()) - set
            successful_patterns.keys()
        )

        # Patrones comunes con diferentes frecuencias
        common_patterns = {}
        for pattern in set(successful_patterns.keys()) & set
            failed_patterns.keys()
        ):
            success_freq = successful_patterns[pattern]
            failed_freq = failed_patterns[pattern]
            if success_freq != failed_freq:
                common_patterns[pattern] = 
                }

        return 
        }


    def _identify_root_cause_indicators(self) -> Dict[str, Any]:
        """Identificar indicadores de causa raíz"""
        indicators = 
        }

        # Analizar diferencias significativas
        analysis_results = self._comprehensive_differential_analysis()

        # Indicadores de alta confianza
        if "token_analysis" in analysis_results:
            token_analysis = analysis_results["token_analysis"]
            # Diferencia significativa en tiempo de expiración
            if "expiration_analysis" in token_analysis:
                expiry_diff = token_analysis["expiration_analysis"].get
                )
                    indicators["high_confidence_indicators"].append
                            ),
                            "confidence": "high",
                        }
                    )

        # Indicadores de confianza media
        if "user_analysis" in analysis_results:
            user_analysis = analysis_results["user_analysis"]
            if "user_status_analysis" in user_analysis:
                active_rate_diff = user_analysis["user_status_analysis"].get
                )
                if abs(active_rate_diff) > 20:  # Más del 20% de diferencia
                    indicators["medium_confidence_indicators"].append
                            ),
                            "confidence": "medium",
                        }
                    )

        # Generar recomendaciones
        if indicators["high_confidence_indicators"]:
            indicators["recommendations"].append
            )
        if indicators["medium_confidence_indicators"]:
            indicators["recommendations"].append
            )
        if not any(indicators.values()):
            indicators["recommendations"].append
            )

        return indicators



    def _count_token_types
    ) -> Dict[str, int]:
        token_types = defaultdict(int)
        for token_data in token_data_list:
            token_type = token_data.get("token_type", "unknown")
            token_types[token_type] += 1
        return dict(token_types)


    def _analyze_user_patterns
    ) -> Dict[str, Any]:
        patterns = 
        }
        return patterns


    def _analyze_timing_patterns
    ) -> Dict[str, Any]:
        """Analizar patrones de timing"""
        ]
        return 
        }


    def _count_patterns(self, pattern_list: List[str]) -> Dict[str, int]:
        """Contar patrones"""
        pattern_counts = defaultdict(int)
        for pattern in pattern_list:
            pattern_counts[pattern] += 1
        return dict(pattern_counts)


    def _find_pattern_differences
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
                differences[pattern] = 
                }

        return differences


    def _extract_patterns(self, cases: deque) -> Dict[str, int]:
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


    def _calculate_pattern_significance
    ) -> Dict[str, float]:
        """Calcular significancia de patrones"""
        significance = {}
        all_patterns = set(successful_patterns.keys()) | set
            failed_patterns.keys()
        )

        for pattern in all_patterns:
            success_count = successful_patterns.get(pattern, 0)
            failed_count = failed_patterns.get(pattern, 0)
            total_count = success_count + failed_count

            if total_count > 0:
                # Calcular significancia basada en diferencia proporcional
                significance[pattern] = 
                    abs(success_count - failed_count) / total_count
                )

        return significance


    def _token_focused_analysis(self) -> Dict[str, Any]:
        """Análisis enfocado en tokens"""
        return 
        }


    def _user_focused_analysis(self) -> Dict[str, Any]:
        return 
        }


    def _timing_focused_analysis(self) -> Dict[str, Any]:
        """Análisis enfocado en timing"""
        return 
        }


    def _basic_differential_analysis(self) -> Dict[str, Any]:
        """Análisis diferencial básico"""
        return 
        }

# Instancia global del sistema comparativo
comparative_system = ComparativeAnalysisSystem()

# ============================================
# ENDPOINTS COMPARATIVOS
# ============================================

async def log_successful_case_endpoint
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    try:
        comparative_system.log_successful_case(case_data)
        return 
        }
    except Exception as e:
        return 
        }

async def log_failed_case_endpoint
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ❌ Registrar caso fallido para análisis comparativo
    """
    try:
        comparative_system.log_failed_case(case_data)
        return 
        }
    except Exception as e:
        logger.error(f"Error registrando caso fallido: {e}")
        return 
        }

async def perform_differential_analysis_endpoint
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Realizar análisis diferencial completo
    """
    try:
        analysis_type = analysis_request.get("analysis_type", "comprehensive")
        analysis = comparative_system.perform_differential_analysis
        )
        return 
        }
    except Exception as e:
        logger.error(f"Error en análisis diferencial: {e}")
        return 
        }

@router.get("/comparative-summary")
async def get_comparative_summary_endpoint
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📈 Resumen comparativo general
    """
    try:
        with comparative_system.lock:
            summary = 
                },
                "recent_analyses": 
                    list(comparative_system.comparison_results.values())[-5:]
                    if comparative_system.comparison_results
                    else []
                ),
            }

        return 
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen comparativo: {e}")
        return 
        }
