import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class PredictiveAnalyzer:
    """Analizador predictivo para detectar patrones sospechosos"""

    def __init__(self):
        self.user_data = {}
        self.predictions = deque(maxlen=1000)
        self.model_accuracy = {}

    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Obtener o crear datos de usuario"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "login_attempts": deque(maxlen=1000),
                "successful_logins": deque(maxlen=1000),
                "failed_logins": deque(maxlen=1000),
                "ip_addresses": deque(maxlen=100),
                "user_agents": deque(maxlen=100),
                "session_durations": deque(maxlen=1000),
            }
        return self.user_data[user_id]

    def record_authentication_event(self, user_id: str, success: bool, request_context: Dict[str, Any]) -> None:
        # Registrar evento de autenticación para análisis
        user_data = self._get_user_data(user_id)

        # Registrar intento de login
        user_data["login_attempts"].append(
            {
                "timestamp": datetime.now(),
                "success": success,
                "ip": request_context.get("client_ip"),
                "user_agent": request_context.get("user_agent"),
            }
        )

        if success:
            user_data["successful_logins"].append(datetime.now())
        else:
            user_data["failed_logins"].append(datetime.now())

        # Registrar IP y User Agent únicos
        if request_context.get("client_ip"):
            user_data["ip_addresses"].append(request_context["client_ip"])
        if request_context.get("user_agent"):
            user_data["user_agents"].append(request_context["user_agent"])

    def analyze_login_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analizar patrones de login de un usuario"""
        user_data = self._get_user_data(user_id)

        if not user_data["login_attempts"]:
            return {"message": "No hay datos de login para este usuario"}

        # Análisis de frecuencia
        recent_attempts = [
            attempt for attempt in user_data["login_attempts"] if attempt["timestamp"] > datetime.now() - timedelta(hours=24)
        ]

        # Análisis de IPs
        unique_ips = len(set(user_data["ip_addresses"]))

        # Análisis de User Agents
        unique_user_agents = len(set(user_data["user_agents"]))

        # Detección de patrones sospechosos
        risk_score = 0
        risk_factors = []

        # Factor 1: Muchos intentos fallidos recientes
        failed_recent = len([a for a in recent_attempts if not a["success"]])
        if failed_recent > 5:
            risk_score += 30
            risk_factors.append("Muchos intentos fallidos recientes")

        # Factor 2: Múltiples IPs
        if unique_ips > 3:
            risk_score += 20
            risk_factors.append("Múltiples direcciones IP")

        # Factor 3: Múltiples User Agents
        if unique_user_agents > 2:
            risk_score += 15
            risk_factors.append("Múltiples User Agents")

        # Factor 4: Patrón de horarios inusuales
        if recent_attempts:
            hours = [attempt["timestamp"].hour for attempt in recent_attempts]
            if any(hour < 6 or hour > 22 for hour in hours):
                risk_score += 10
                risk_factors.append("Horarios inusuales de acceso")

        return {
            "user_id": user_id,
            "total_attempts": len(user_data["login_attempts"]),
            "recent_attempts_24h": len(recent_attempts),
            "failed_recent": failed_recent,
            "unique_ips": unique_ips,
            "unique_user_agents": unique_user_agents,
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
            "risk_level": self._get_risk_level(risk_score),
        }

    def _get_risk_level(self, score: int) -> str:
        """Determinar nivel de riesgo basado en el score"""
        if score >= 70:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    def predict_future_risk(self, user_id: str) -> Dict[str, Any]:
        """Predecir riesgo futuro basado en patrones históricos"""
        user_data = self._get_user_data(user_id)

        if len(user_data["login_attempts"]) < 10:
            return {"message": "Insuficientes datos para predicción"}

        # Análisis de tendencias
        recent_attempts = user_data["login_attempts"][-20:]  # Últimos 20 intentos

        # Calcular tasa de éxito reciente
        recent_success_rate = len([a for a in recent_attempts if a["success"]]) / len(recent_attempts) * 100

        # Predicción basada en tendencias
        if recent_success_rate < 50:
            prediction = "HIGH_RISK"
            confidence = 85
        elif recent_success_rate < 80:
            prediction = "MEDIUM_RISK"
            confidence = 70
        else:
            prediction = "LOW_RISK"
            confidence = 90

        return {
            "user_id": user_id,
            "prediction": prediction,
            "confidence": confidence,
            "recent_success_rate": recent_success_rate,
            "recommendation": self._get_recommendation(prediction),
        }

    def _get_recommendation(self, prediction: str) -> str:
        """Obtener recomendación basada en predicción"""
        recommendations = {
            "HIGH_RISK": "Considerar bloqueo temporal o verificación adicional",
            "MEDIUM_RISK": "Monitorear actividad de cerca",
            "LOW_RISK": "Actividad normal, continuar monitoreo",
        }
        return recommendations.get(prediction, "Sin recomendación específica")


# Instancia global del analizador
analyzer = PredictiveAnalyzer()


@router.get("/predictive-analysis/user/{user_id}")
def analyze_user_patterns(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    # Analizar patrones de un usuario específico
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden acceder a este análisis",
        )

    try:
        analysis = analyzer.analyze_login_patterns(user_id)
        return analysis

    except Exception as e:
        logger.error(f"Error analizando patrones de usuario {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/predictive-analysis/prediction/{user_id}")
def get_user_prediction(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    # Obtener predicción de riesgo para un usuario
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder a predicciones")

    try:
        prediction = analyzer.predict_future_risk(user_id)
        return prediction

    except Exception as e:
        logger.error(f"Error obteniendo predicción para usuario {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/predictive-analysis/record-event")
def record_auth_event(
    user_id: str,
    success: bool,
    request_context: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    # Registrar evento de autenticación
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden registrar eventos")

    try:
        analyzer.record_authentication_event(user_id, success, request_context)
        return {"message": "Evento registrado exitosamente"}

    except Exception as e:
        logger.error(f"Error registrando evento: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/predictive-analysis/system-overview")
def get_system_overview(
    current_user: User = Depends(get_current_user),
):
    # Obtener resumen del sistema de análisis predictivo
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder a este resumen")

    try:
        total_users = len(analyzer.user_data)
        total_predictions = len(analyzer.predictions)

        # Calcular estadísticas generales
        high_risk_users = 0
        medium_risk_users = 0
        low_risk_users = 0

        for user_id in analyzer.user_data.keys():
            analysis = analyzer.analyze_login_patterns(user_id)
            risk_level = analysis.get("risk_level", "LOW")

            if risk_level == "HIGH":
                high_risk_users += 1
            elif risk_level == "MEDIUM":
                medium_risk_users += 1
            else:
                low_risk_users += 1

        return {
            "total_users_monitored": total_users,
            "total_predictions": total_predictions,
            "risk_distribution": {
                "high_risk": high_risk_users,
                "medium_risk": medium_risk_users,
                "low_risk": low_risk_users,
            },
            "system_status": "ACTIVE",
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen del sistema: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
