"""Sistema de AnÃ¡lisis Predictivo para Tokens JWTPredice problemas de autenticaciÃ³n antes de que ocurran"""
import logging
import statistics
from collections 
import defaultdict, deque
from datetime 
import datetime
from typing 
import Any, Dict, List
from fastapi 
import APIRouter, Depends, HTTPException
from sqlalchemy.orm 
import Session
from app.api.deps 
import get_current_user, get_db
from app.core.security 
import decode_token
from app.models.user 
import Userlogger = logging.getLogger(__name__)router = APIRouter()# ============================================# SISTEMA DE ANÃLISIS PREDICTIVO# ============================================
class TokenPredictiveAnalyzer:
    """Analizador predictivo de tokens JWT"""    
def __init__(self):
        self.token_history = defaultdict(list)  # Historial por token        self.user_patterns = defaultdict(dict)  # Patrones por usuario        self.system_metrics = deque(maxlen=1000)  # MÃ©tricas del sistema        self.prediction_cache = {}  # Cache de predicciones    
def analyze_token_lifecycle(self, token:
 str) -> Dict[str, Any]:
        """Analizar ciclo de vida completo de un token"""        try:
            payload = decode_token(token)            token_id = f"{payload.get('sub')}_{payload.get('exp')}"            # InformaciÃ³n bÃ¡sica del token            token_info = {                "token_id":
 token_id,                "user_id":
 payload.get("sub"),                "issued_at":
 datetime.fromtimestamp(payload.get("iat", 0)),                "expires_at":
 datetime.fromtimestamp(payload.get("exp", 0)),                "type":
 payload.get("type"),                "time_to_expiry":
 self._calculate_time_to_expiry(                    payload.get("exp", 0)                ),                "usage_pattern":
 self._analyze_usage_pattern(token_id),                "risk_factors":
 self._identify_risk_factors(token_id, payload),            }            # Predicciones            predictions = self._generate_predictions(token_info)            token_info["predictions"] = predictions            return token_info        except Exception as e:
            logger.error(f"Error analizando token:
 {e}")            return {"error":
 str(e), "status":
 "invalid_token"}    
def _calculate_time_to_expiry(self, exp_timestamp:
 int) -> Dict[str, Any]:
        """Calcular tiempo hasta expiraciÃ³n"""        current_time = datetime.now()        exp_time = datetime.fromtimestamp(exp_timestamp)        time_diff = exp_time - current_time        return {            "total_seconds":
 int(time_diff.total_seconds()),            "minutes":
 int(time_diff.total_seconds() / 60),            "hours":
 int(time_diff.total_seconds() / 3600),            "is_expired":
 time_diff.total_seconds() < 0,            "is_expiring_soon":
 0            < time_diff.total_seconds()            < 300,  # 5 minutos        }    
def _analyze_usage_pattern(self, token_id:
 str) -> Dict[str, Any]:
        """Analizar patrÃ³n de uso del token"""        if token_id not in self.token_history:
            return {"status":
 "no_history"}        history = self.token_history[token_id]        if not history:
            return {"status":
 "no_history"}        # AnÃ¡lisis temporal        timestamps = [entry["timestamp"] for entry in history]        intervals = []        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()            intervals.append(interval)        # EstadÃ­sticas de uso        usage_stats = {            "total_uses":
 len(history),            "avg_interval_minutes":
 (                statistics.mean(intervals) / 60 if intervals else 0            ),            "min_interval_minutes":
 min(intervals) / 60 if intervals else 0,            "max_interval_minutes":
 max(intervals) / 60 if intervals else 0,            "usage_frequency":
 self._calculate_usage_frequency(intervals),            "peak_usage_hours":
 self._identify_peak_usage_hours(history),        }        return usage_stats    
def _calculate_usage_frequency(self, intervals:
 List[float]) -> str:
        """Calcular frecuencia de uso"""        if not intervals:
            return "unknown"        avg_interval = statistics.mean(intervals)        if avg_interval < 60:
  # Menos de 1 minuto            return "very_high"        elif avg_interval < 300:
  # Menos de 5 minutos            return "high"        elif avg_interval < 1800:
  # Menos de 30 minutos            return "medium"        elif avg_interval < 3600:
  # Menos de 1 hora            return "low"        else:
            return "very_low"    
def _identify_peak_usage_hours(self, history:
 List[Dict]) -> List[int]:
        """Identificar horas pico de uso"""        hour_counts = defaultdict(int)        for entry in history:
            hour = entry["timestamp"].hour            hour_counts[hour] += 1        # Retornar las 3 horas con mÃ¡s uso        sorted_hours = sorted(            hour_counts.items(), key=lambda x:
 x[1], reverse=True        )        return [hour for hour, count in sorted_hours[:
3]]    
def _identify_risk_factors(        self, token_id:
 str, payload:
 Dict    ) -> List[str]:
        """Identificar factores de riesgo"""        risk_factors = []        # Verificar tiempo de expiraciÃ³n        exp_time = datetime.fromtimestamp(payload.get("exp", 0))        time_to_expiry = (exp_time - datetime.now()).total_seconds()        if time_to_expiry < 300:
  # Menos de 5 minutos            risk_factors.append("expiring_soon")        if time_to_expiry < 0:
  # Ya expirado            risk_factors.append("already_expired")        # Verificar patrÃ³n de uso        if token_id in self.token_history:
            history = self.token_history[token_id]            if len(history) > 50:
  # Mucho uso                risk_factors.append("high_usage")            # Verificar errores recientes            recent_errors = [                h for h in history[-10:
] if not h.get("success", True)            ]            if len(recent_errors) > 3:
                risk_factors.append("recent_errors")        # Verificar tipo de token        if payload.get("type") != "access":
            risk_factors.append("wrong_token_type")        return risk_factors    
def _generate_predictions(        self, token_info:
 Dict[str, Any]    ) -> Dict[str, Any]:
        """Generar predicciones basadas en anÃ¡lisis"""        predictions = {            "will_expire_soon":
 False,            "likely_to_fail":
 False,            "recommended_action":
 "none",            "confidence_score":
 0.0,            "predicted_failure_time":
 None,            "risk_level":
 "low",        }        # AnÃ¡lisis de tiempo de expiraciÃ³n        time_to_expiry = token_info.get("time_to_expiry", {})        if time_to_expiry.get("is_expiring_soon", False):
            predictions["will_expire_soon"] = True            predictions["recommended_action"] = "refresh_token"            predictions["confidence_score"] += 0.8        # AnÃ¡lisis de factores de riesgo        risk_factors = token_info.get("risk_factors", [])        risk_score = len(risk_factors) * 0.2        if "already_expired" in risk_factors:
            predictions["likely_to_fail"] = True            predictions["recommended_action"] = "immediate_refresh"            predictions["confidence_score"] += 0.9            predictions["risk_level"] = "critical"        elif "expiring_soon" in risk_factors:
            predictions["likely_to_fail"] = True            predictions["recommended_action"] = "refresh_token"            predictions["confidence_score"] += 0.7            predictions["risk_level"] = "high"        elif risk_score > 0.6:
            predictions["likely_to_fail"] = True            predictions["recommended_action"] = "monitor_closely"            predictions["confidence_score"] += risk_score            predictions["risk_level"] = "medium"        # PredicciÃ³n de tiempo de falla        if predictions["will_expire_soon"]:
            exp_time = token_info.get("expires_at")            if exp_time:
                predictions["predicted_failure_time"] = exp_time.isoformat()        # Normalizar score de confianza        predictions["confidence_score"] = min(            predictions["confidence_score"], 1.0        )        return predictions    
def predict_system_failures(self) -> Dict[str, Any]:
        """Predecir fallas del sistema"""        predictions = {            "timestamp":
 datetime.now().isoformat(),            "predicted_failures":
 [],            "system_health":
 "good",            "recommendations":
 [],        }        # Analizar mÃ©tricas del sistema        if len(self.system_metrics) < 10:
            predictions["system_health"] = "insufficient_data"            return predictions        recent_metrics = list(self.system_metrics)[            -50:
        ]  # Ãšltimos 50 registros        # Calcular tasa de error promedio        error_rate = sum(            1 for m in recent_metrics if not m.get("success", True)        ) / len(recent_metrics)        if error_rate > 0.1:
  # MÃ¡s del 10% de errores            predictions["predicted_failures"].append(                {                    "type":
 "high_error_rate",                    "probability":
 error_rate,                    "description":
 f"Tasa de error alta:
 {error_rate:
.2%}",                }            )            predictions["system_health"] = "degraded"            predictions["recommendations"].append(                "Revisar configuraciÃ³n de autenticaciÃ³n"            )        # Predecir sobrecarga        avg_response_time = statistics.mean(            [m.get("response_time", 0) for m in recent_metrics]        )        if avg_response_time > 2.0:
            predictions["predicted_failures"].append(                {                    "type":
 "performance_degradation",                    "probability":
 min(avg_response_time / 5.0, 1.0),                    "description":
 f"Tiempo de respuesta alto:
    {avg_reresponse_time:
.2f}s",                }            )            predictions["system_health"] = "degraded"            predictions["recommendations"].append(                "Optimizar queries de base de datos"            )        return predictions# Instancia global del analizadorpredictive_analyzer = TokenPredictiveAnalyzer()# ============================================# ENDPOINTS DE ANÃLISIS PREDICTIVO# ============================================@router.post("/analyze-token")async 
def analyze_token_predictive(    token_data:
 Dict[str, str],    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ”® AnÃ¡lisis predictivo completo de un token    """    try:
        token = token_data.get("token")        if not token:
            raise HTTPException(status_code=400, detail="Token requerido")        analysis = predictive_analyzer.analyze_token_lifecycle(token)        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "analysis":
 analysis,        }    except HTTPException:
        raise    except Exception as e:
        logger.error(f"Error en anÃ¡lisis predictivo:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/predict-system-failures")async 
def predict_system_failures_endpoint(    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ”® PredicciÃ³n de fallas del sistema    """    try:
        predictions = predictive_analyzer.predict_system_failures()        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "predictions":
 predictions,        }    except Exception as e:
        logger.error(f"Error prediciendo fallas del sistema:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/user-patterns/{user_id}")async 
def analyze_user_patterns(    user_id:
 int,    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ‘¤ AnÃ¡lisis de patrones de uso de un usuario especÃ­fico    """    try:
        # Verificar que el usuario existe        user = db.query(User).filter(User.id == user_id).first()        if not user:
            raise HTTPException(                status_code=404, detail="Usuario no encontrado"            )        # Buscar patrones del usuario        user_patterns = predictive_analyzer.user_patterns.get(str(user_id), {})        # Generar anÃ¡lisis predictivo        analysis = {            "user_id":
 user_id,            "email":
 user.email,            "patterns":
 user_patterns,            "predictions":
 {                "likely_usage_times":
 _predict_usage_times(user_patterns),                "risk_factors":
 _identify_user_risk_factors(user_patterns),                "recommendations":
 _generate_user_recommendations(                    user_patterns                ),            },        }        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "analysis":
 analysis,        }    except HTTPException:
        raise    except Exception as e:
        logger.error(f"Error analizando patrones del usuario:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/token-health-check")async 
def token_health_check():
    """    ðŸ¥ VerificaciÃ³n de salud de tokens en el sistema    """    try:
        health_status = {            "timestamp":
 datetime.now().isoformat(),            "overall_health":
 "good",            "token_statistics":
 {},            "warnings":
 [],            "recommendations":
 [],        }        # Analizar todos los tokens conocidos        total_tokens = len(predictive_analyzer.token_history)        if total_tokens == 0:
            health_status["overall_health"] = "no_data"            health_status["warnings"].append(                "No hay datos de tokens para analizar"            )            return health_status        # EstadÃ­sticas generales        expiring_soon = 0        expired = 0        high_risk = 0        for token_id, history in predictive_analyzer.token_history.items():
            if history:
                history[-1]                # AquÃ­ podrÃ­as agregar mÃ¡s anÃ¡lisis especÃ­fico        health_status["token_statistics"] = {            "total_tokens":
 total_tokens,            "expiring_soon":
 expiring_soon,            "expired":
 expired,            "high_risk":
 high_risk,        }        # Generar recomendaciones        if expiring_soon > total_tokens * 0.1:
  # MÃ¡s del 10% expirando pronto            health_status["warnings"].append(                f"{expiring_soon} tokens expirando pronto"            )            health_status["recommendations"].append(                "Implementar renovaciÃ³n automÃ¡tica mÃ¡s agresiva"            )        if expired > 0:
            health_status["warnings"].append(f"{expired} tokens expirados")            health_status["recommendations"].append(                "Limpiar tokens expirados del sistema"            )        return health_status    except Exception as e:
        logger.error(f"Error en verificaciÃ³n de salud:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }# Funciones auxiliares
def _predict_usage_times(user_patterns:
 Dict) -> List[int]:
    """Predecir horarios de uso mÃ¡s probables"""    # ImplementaciÃ³n simplificada    return [9, 14, 18]  # Horarios tÃ­picos de uso
def _identify_user_risk_factors(user_patterns:
 Dict) -> List[str]:
    """Identificar factores de riesgo del usuario"""    risk_factors = []    # ImplementaciÃ³n simplificada    if user_patterns.get("error_rate", 0) > 0.1:
        risk_factors.append("high_error_rate")    return risk_factors
def _generate_user_recommendations(user_patterns:
 Dict) -> List[str]:
    """Generar recomendaciones para el usuario"""    recommendations = []    # ImplementaciÃ³n simplificada    if user_patterns.get("error_rate", 0) > 0.1:
        recommendations.append("Revisar configuraciÃ³n de tokens")    if not recommendations:
        recommendations.append("PatrÃ³n de uso normal")    return recommendations





