"""Sistema de Análisis Predictivo de Autenticación
Machine Learning y análisis estadístico para predecir problemas de autenticación
"""

import logging
import statistics
from collections import deque, defaultdict, Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, Request, HTTPException
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# DATACLASSES Y MODELOS
# ============================================

@dataclass
class PredictionResult:
    prediction_id: str
    user_id: str
    prediction_type: str
    confidence_score: float
    predicted_value: Any
    factors: List[str]

@dataclass
class UserBehaviorPattern:
    user_id: str
    login_frequency: float
    failure_rate: float
    location_patterns: Dict[str, int]
    device_patterns: Dict[str, int]
    risk_score: float

# ============================================
# SISTEMA DE ANÁLISIS PREDICTIVO
# ============================================


class PredictiveAnalyzer:
    """Analizador predictivo de autenticación"""


    def __init__(self):
        self.user_data = defaultdict(lambda: {
            "login_attempts": deque(maxlen=1000),
            "successful_logins": deque(maxlen=1000),
            "failed_logins": deque(maxlen=1000),
            "ip_addresses": deque(maxlen=100),
            "user_agents": deque(maxlen=100),
            "session_durations": deque(maxlen=1000)
        })
        self.predictions = deque(maxlen=1000)
        self.model_accuracy = {}


    def record_authentication_event(
        self,
        user_id: str,
        success: bool,
        request_context: Dict[str, Any],
        session_duration: Optional[float] = None
    ) -> None:
        """Registrar evento de autenticación para análisis"""
        user_data = self.user_data[user_id]

        # Registrar intento de login
        user_data["login_attempts"].append({
            "success": success,
            "ip": request_context.get("client_ip"),
            "user_agent": request_context.get("user_agent")
        })

        if success:
            if session_duration:
                user_data["session_durations"].append(session_duration)
        else:

        # Registrar información de contexto
        client_ip = request_context.get("client_ip")
        if client_ip:
            user_data["ip_addresses"].append(client_ip)

        user_agent = request_context.get("user_agent")
        if user_agent:
            user_data["user_agents"].append(user_agent)


        logger.debug(f"Evento de autenticación registrado para usuario {user_id}")


    def predict_authentication_failure(
        self,
        user_id: str,
    ) -> PredictionResult:
        """Predecir probabilidad de fallo de autenticación"""

        try:
            user_data = self.user_data[user_id]

            # Calcular métricas históricas
            location_risk = self._analyze_location_patterns(user_data)
            device_risk = self._analyze_device_patterns(user_data)

            # Calcular score de confianza y predicción
            predicted_failure_probability = self._calculate_failure_probability(
            )

            # Identificar factores de riesgo
            risk_factors = self._identify_risk_factors(
            )

            prediction = PredictionResult(
                prediction_id=prediction_id,
                user_id=user_id,
                prediction_type="authentication_failure",
                confidence_score=confidence_score,
                predicted_value=predicted_failure_probability,
                factors=risk_factors,
            )

            self.predictions.append(prediction)
            return prediction

        except Exception as e:
            logger.error(f"Error prediciendo fallo de autenticación: {e}")
            # Retornar predicción por defecto en caso de error
            return PredictionResult(
                prediction_id=prediction_id,
                user_id=user_id,
                prediction_type="authentication_failure",
                confidence_score=0.0,
                predicted_value=0.5,  # Probabilidad neutral
                factors=["Error en análisis"],
            )


        else:  # long

        recent_failures = [
            attempt for attempt in user_data["login_attempts"]
        ]

        return len(recent_failures)


        """Calcular tasa de fallo"""
        total_attempts = len([
            attempt for attempt in user_data["login_attempts"]
        ])

        if total_attempts == 0:
            return 0.0

        return recent_attempts / total_attempts


        """Analizar patrones temporales de riesgo"""
            return 0.0

        # Calcular desviación estándar de horas de login
        try:
            return min(std_dev / 12.0, 1.0)  # Normalizar a 0-1
        except statistics.StatisticsError:
            return 0.0


    def _analyze_location_patterns(self, user_data: Dict) -> float:
        """Analizar patrones de ubicación"""
        ip_addresses = list(user_data["ip_addresses"])
        if not ip_addresses:
            return 0.0

        # Calcular diversidad de IPs
        unique_ips = len(set(ip_addresses))
        total_ips = len(ip_addresses)

        if total_ips == 0:
            return 0.0

        # Mayor diversidad = mayor riesgo
        diversity_ratio = unique_ips / total_ips
        return diversity_ratio


    def _analyze_device_patterns(self, user_data: Dict) -> float:
        user_agents = list(user_data["user_agents"])
        if not user_agents:
            return 0.0

        # Calcular diversidad de user agents
        unique_agents = len(set(user_agents))
        total_agents = len(user_agents)

        if total_agents == 0:
            return 0.0

        # Mayor diversidad = mayor riesgo
        diversity_ratio = unique_agents / total_agents
        return diversity_ratio


        """Calcular score de confianza de la predicción"""
        total_attempts = len(user_data["login_attempts"])

        if total_attempts < 10:
            return 0.3
        elif total_attempts < 50:
            return 0.6
        elif total_attempts < 100:
            return 0.8
        else:
            return 0.9


    def _calculate_failure_probability(
        self,
        failure_rate: float,
        location_risk: float,
        device_risk: float
    ) -> float:
        """Calcular probabilidad de fallo"""
        weights = {
            "failure_rate": 0.4,
            "location_risk": 0.2,
            "device_risk": 0.2
        }

        probability = (
            failure_rate * weights["failure_rate"] +
            location_risk * weights["location_risk"] +
            device_risk * weights["device_risk"]
        )

        return min(max(probability, 0.0), 1.0)  # Clamp entre 0 y 1


    def _identify_risk_factors(
        self,
        failure_rate: float,
        location_risk: float,
        device_risk: float
    ) -> List[str]:
        """Identificar factores de riesgo"""
        factors = []

        if failure_rate > 0.3:

            factors.append("Patrones temporales irregulares")

        if location_risk > 0.7:
            factors.append("Múltiples ubicaciones de acceso")

        if device_risk > 0.7:

        if not factors:
            factors.append("Patrones normales de acceso")

        return factors


    def get_user_behavior_pattern(self, user_id: str) -> UserBehaviorPattern:
        """Obtener patrón de comportamiento del usuario"""
        user_data = self.user_data[user_id]

        # Calcular métricas de comportamiento
        login_frequency = self._calculate_login_frequency(user_data)
        failure_rate = self._calculate_failure_rate(user_data, "medium")
        location_patterns = dict(Counter(user_data["ip_addresses"]))
        device_patterns = dict(Counter(user_data["user_agents"]))

        # Calcular score de riesgo general
        risk_score = self._calculate_failure_probability(
            len(set(user_data["ip_addresses"])) / max(len(user_data["ip_addresses"]), 1),
            len(set(user_data["user_agents"])) / max(len(user_data["user_agents"]), 1)
        )

        return UserBehaviorPattern(
            user_id=user_id,
            login_frequency=login_frequency,
            failure_rate=failure_rate,
            location_patterns=location_patterns,
            device_patterns=device_patterns,
            risk_score=risk_score
        )


    def _calculate_login_frequency(self, user_data: Dict) -> float:
        """Calcular frecuencia de login (logins por día)"""
        successful_logins = list(user_data["successful_logins"])
        if not successful_logins:
            return 0.0

        # Calcular días entre primer y último login
        if len(successful_logins) == 1:
            return 1.0

        first_login = min(successful_logins)
        last_login = max(successful_logins)
        days = (last_login - first_login).days + 1

        return len(successful_logins) / days

# Instancia global del analizador predictivo
predictive_analyzer = PredictiveAnalyzer()

# ============================================
# ENDPOINTS DE ANÁLISIS PREDICTIVO
# ============================================

async def record_authentication_event(
    event_data: Dict[str, Any],
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Registrar evento de autenticación"""
    try:
        user_id = event_data.get("user_id", current_user.id)
        success = event_data.get("success", False)
        session_duration = event_data.get("session_duration")

        # Obtener contexto de la petición
        request_context = {
            "user_agent": request.headers.get("User-Agent"),
        }

        # Registrar evento
        predictive_analyzer.record_authentication_event(
            user_id, success, request_context, session_duration
        )

        return {
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error registrando evento de autenticación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

async def predict_authentication_failure(
    prediction_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Predecir fallo de autenticación"""
    try:
        user_id = prediction_data.get("user_id", current_user.id)

        # Validar horizonte temporal
            raise HTTPException(
                status_code=400,
            )

        # Realizar predicción
        prediction = predictive_analyzer.predict_authentication_failure(
        )

        # Convertir a formato serializable
        prediction_data = {
            "prediction_id": prediction.prediction_id,
            "user_id": prediction.user_id,
            "prediction_type": prediction.prediction_type,
            "confidence_score": prediction.confidence_score,
            "predicted_value": prediction.predicted_value,
            "factors": prediction.factors,
        }

        return {
            "success": True,
            "prediction": prediction_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error prediciendo fallo de autenticación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/user-behavior/{user_id}")
async def get_user_behavior_pattern(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener patrón de comportamiento del usuario"""
    try:
        behavior_pattern = predictive_analyzer.get_user_behavior_pattern(user_id)

        # Convertir a formato serializable
        behavior_data = {
            "user_id": behavior_pattern.user_id,
            "login_frequency": behavior_pattern.login_frequency,
            "failure_rate": behavior_pattern.failure_rate,
            "location_patterns": behavior_pattern.location_patterns,
            "device_patterns": behavior_pattern.device_patterns,
            "risk_score": behavior_pattern.risk_score
        }

        return {
            "success": True,
            "behavior_pattern": behavior_data
        }

    except Exception as e:
        logger.error(f"Error obteniendo patrón de comportamiento: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/prediction-history")
async def get_prediction_history(
    user_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de predicciones"""
    try:
        predictions = list(predictive_analyzer.predictions)

        # Filtrar por usuario si se especifica
        if user_id:
            predictions = [p for p in predictions if p.user_id == user_id]

        predictions = predictions[-limit:]

        # Convertir a formato serializable
        predictions_data = [
            {
                "prediction_id": p.prediction_id,
                "user_id": p.user_id,
                "prediction_type": p.prediction_type,
                "confidence_score": p.confidence_score,
                "predicted_value": p.predicted_value,
                "factors": p.factors,
            }
            for p in predictions
        ]

        return {
            "success": True,
            "predictions": predictions_data,
            "total_count": len(predictions_data)
        }

    except Exception as e:
        logger.error(f"Error obteniendo historial de predicciones: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/model-accuracy")
async def get_model_accuracy(
    current_user: User = Depends(get_current_user),
):
    """Obtener precisión del modelo predictivo"""
    try:
        # Calcular precisión básica basada en predicciones recientes
        recent_predictions = list(predictive_analyzer.predictions)[-100:]

        if not recent_predictions:
            return {
                "success": True,
                "accuracy": {
                    "overall_accuracy": 0.0,
                    "sample_size": 0,
                    "confidence_distribution": {}
                }
            }

        # Calcular distribución de confianza
        confidence_scores = [p.confidence_score for p in recent_predictions]
        avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0

        return {
            "success": True,
            "accuracy": {
                "overall_accuracy": avg_confidence,
                "sample_size": len(recent_predictions),
                "confidence_distribution": {
                    "min": min(confidence_scores) if confidence_scores else 0.0,
                    "max": max(confidence_scores) if confidence_scores else 0.0,
                    "mean": avg_confidence
                }
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo precisión del modelo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
