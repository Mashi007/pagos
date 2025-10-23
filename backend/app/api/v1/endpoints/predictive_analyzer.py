"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
 Sistema de Análisis Predictivo de Autenticación
Machine Learning y análisis estadístico para predecir problemas de autenticación
"""

from dataclasses import dataclass

logger = logging.getLogger(__name__)
router = APIRouter()

dataclass
class AuthMetrics:
    """Métricas de autenticación"""
    timestamp: datetime
    success_rate: float
    avg_response_time: float
    error_count: int
    total_requests: int
    unique_users: int
    token_expiry_rate: float

# Almacenamiento para métricas históricas
historical_metrics = deque(maxlen=1000)  # Mantener últimos 1000 puntos de métricas
prediction_models = {}  # Modelos de predicción

class PredictiveAnalyzer:
    """Analizador predictivo para problemas de autenticación"""

    @staticmethod
    def calculate_trend(data_points: List[float], window_size: int = 5) -> Dict[str, float]:
        """Calcular tendencia de datos"""
        if len(data_points) < window_size:
            return {"trend": "insufficient_data", "slope": 0.0, "confidence": 0.0}

        recent_data = data_points[-window_size:]
        older_data = data_points[-window_size*2:-window_size] if len(data_points) >= window_size*2 else recent_data

        recent_avg = statistics.mean(recent_data)
        older_avg = statistics.mean(older_data)

        slope = recent_avg - older_avg
        trend = "increasing" if slope > 0.05 else "decreasing" if slope < -0.05 else "stable"

        # Calcular confianza basada en variabilidad
        variance = statistics.variance(recent_data) if len(recent_data) > 1 else 0
        confidence = max(0, 1 - (variance / (recent_avg + 0.001)))

        return {
            "trend": trend,
            "slope": slope,
            "confidence": confidence,
            "recent_avg": recent_avg,
            "older_avg": older_avg
        }

    @staticmethod
    def detect_anomaly_patterns(metrics: List[AuthMetrics]) -> List[Dict[str, Any]]:
        """Detectar patrones anómalos en métricas históricas"""
        anomalies = []

        if len(metrics) < 10:
            return anomalies

        # Extraer series temporales
        success_rates = [m.success_rate for m in metrics]
        response_times = [m.avg_response_time for m in metrics]
        error_counts = [m.error_count for m in metrics]

        # Anomalía 1: Caída súbita en tasa de éxito
        success_trend = PredictiveAnalyzer.calculate_trend(success_rates)
        if success_trend["trend"] == "decreasing" and success_trend["confidence"] > 0.7:
            anomalies.append({
                "type": "success_rate_decline",
                "severity": "high",
                "description": f"Success rate declining (slope: {success_trend['slope']:.3f})",
                "confidence": success_trend["confidence"],
                "recommendation": "Investigate recent changes to authentication system"
            })

        # Anomalía 2: Aumento en tiempo de respuesta
        response_trend = PredictiveAnalyzer.calculate_trend(response_times)
        if response_trend["trend"] == "increasing" and response_trend["confidence"] > 0.6:
            anomalies.append({
                "type": "response_time_increase",
                "severity": "medium",
                "description": f"Response time increasing (slope: {response_trend['slope']:.1f}ms)",
                "confidence": response_trend["confidence"],
                "recommendation": "Check database performance and server load"
            })

        # Anomalía 3: Picos de errores
        if len(error_counts) >= 5:
            recent_errors = error_counts[-5:]
            avg_recent_errors = statistics.mean(recent_errors)
            historical_avg = statistics.mean(error_counts[:-5]) if len(error_counts) > 5 else avg_recent_errors

            if avg_recent_errors > historical_avg * 2:  # Doble del promedio histórico
                anomalies.append({
                    "type": "error_spike",
                    "severity": "high",
                    "description": f"Error count spike: {avg_recent_errors:.1f} vs {historical_avg:.1f} historical avg",
                    "confidence": 0.8,
                    "recommendation": "Investigate error patterns and root causes"
                })

        return anomalies

    @staticmethod
    def predict_future_issues(metrics: List[AuthMetrics]) -> Dict[str, Any]:
        """Predecir problemas futuros basado en tendencias"""
        if len(metrics) < 20:
            return {"status": "insufficient_data", "message": "Need at least 20 data points"}

        predictions = {}

        # Extraer series temporales
        success_rates = [m.success_rate for m in metrics]
        response_times = [m.avg_response_time for m in metrics]
        error_counts = [m.error_count for m in metrics]

        # Predicción 1: Tasa de éxito
        success_trend = PredictiveAnalyzer.calculate_trend(success_rates, window_size=10)
        if success_trend["trend"] == "decreasing":
            # Calcular cuándo podría llegar a un umbral crítico
            current_rate = success_rates[-1]
            critical_threshold = 0.7  # 70% success rate

            if current_rate > critical_threshold and success_trend["slope"] < 0:
                days_to_critical = (current_rate - critical_threshold) / abs(success_trend["slope"])
                predictions["success_rate_critical"] = {
                    "probability": min(0.9, success_trend["confidence"]),
                    "days_to_critical": max(1, int(days_to_critical)),
                    "current_rate": current_rate,
                    "trend_slope": success_trend["slope"]
                }

        # Predicción 2: Tiempo de respuesta
        response_trend = PredictiveAnalyzer.calculate_trend(response_times, window_size=10)
        if response_trend["trend"] == "increasing":
            current_time = response_times[-1]
            warning_threshold = 2000  # 2 segundos

            if current_time < warning_threshold and response_trend["slope"] > 0:
                days_to_warning = (warning_threshold - current_time) / response_trend["slope"]
                predictions["response_time_warning"] = {
                    "probability": min(0.8, response_trend["confidence"]),
                    "days_to_warning": max(1, int(days_to_warning)),
                    "current_time": current_time,
                    "trend_slope": response_trend["slope"]
                }

        return {
            "status": "success",
            "predictions": predictions,
            "analysis_period": f"{len(metrics)} data points",
            "last_update": metrics[-1].timestamp.isoformat() if metrics else None
        }

@router.post("/auth-metrics")
async def collect_authentication_metrics(
    db: Session = Depends(get_db)
):
    """
    📊 Recolectar métricas actuales de autenticación
    """
    try:
        # Calcular métricas del último período (última hora)
        cutoff_time = datetime.now() - timedelta(hours=1)

        # Simular recolección de métricas (en producción vendría de logs/monitoring)
        # Por ahora, calcularemos métricas básicas

        # Contar usuarios activos
        active_users = db.query(User).filter(User.is_active ).count()
        total_users = db.query(User).count()

        # Métricas simuladas basadas en configuración
        metrics = AuthMetrics(
            timestamp=datetime.now(),
            success_rate=0.85,  # Simulado - en producción vendría de logs
            avg_response_time=1200.0,  # Simulado
            error_count=15,  # Simulado
            total_requests=100,  # Simulado
            unique_users=active_users,
            token_expiry_rate=0.05  # Simulado
        )

        # Agregar a métricas históricas
        historical_metrics.append(metrics)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "metrics": {
                "success_rate": metrics.success_rate,
                "avg_response_time_ms": metrics.avg_response_time,
                "error_count": metrics.error_count,
                "total_requests": metrics.total_requests,
                "unique_users": metrics.unique_users,
                "token_expiry_rate": metrics.token_expiry_rate
            },
            "historical_data_points": len(historical_metrics)
        }

    except Exception as e:
        logger.error(f"Error recolectando métricas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/predictive-analysis")
async def get_predictive_analysis():
    """
    🔮 Análisis predictivo de problemas de autenticación
    """
    try:
        if len(historical_metrics) < 5:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "insufficient_data",
                "message": "Need at least 5 data points for analysis",
                "current_points": len(historical_metrics)
            }

        # Convertir a lista para análisis
        metrics_list = list(historical_metrics)

        # Detectar anomalías
        anomalies = PredictiveAnalyzer.detect_anomaly_patterns(metrics_list)

        # Generar predicciones
        predictions = PredictiveAnalyzer.predict_future_issues(metrics_list)

        # Análisis de tendencias
        success_rates = [m.success_rate for m in metrics_list]
        response_times = [m.avg_response_time for m in metrics_list]
        error_counts = [m.error_count for m in metrics_list]

        trends = {
            "success_rate": PredictiveAnalyzer.calculate_trend(success_rates),
            "response_time": PredictiveAnalyzer.calculate_trend(response_times),
            "error_count": PredictiveAnalyzer.calculate_trend(error_counts)
        }

        # Generar recomendaciones predictivas
        recommendations = []

        if predictions.get("status") == "success":
            pred_data = predictions.get("predictions", {})

            if "success_rate_critical" in pred_data:
                pred = pred_data["success_rate_critical"]
                recommendations.append(f"🚨 Predicción: Tasa de éxito crítica en {pred['days_to_critical']} días (probabilidad: {pred['probability']:.1%})")

            if "response_time_warning" in pred_data:
                pred = pred_data["response_time_warning"]
                recommendations.append(f"⚠️ Predicción: Tiempo de respuesta alto en {pred['days_to_warning']} días (probabilidad: {pred['probability']:.1%})")

        # Recomendaciones basadas en tendencias
        if trends["success_rate"]["trend"] == "decreasing":
            recommendations.append("📉 Tendencia: Tasa de éxito disminuyendo - Monitorear de cerca")

        if trends["response_time"]["trend"] == "increasing":
            recommendations.append("⏱️ Tendencia: Tiempo de respuesta aumentando - Optimizar sistema")

        if trends["error_count"]["trend"] == "increasing":
            recommendations.append("❌ Tendencia: Errores aumentando - Investigar causas")

        if not recommendations:
            recommendations.append("✅ Sistema estable - Continuar monitoreo rutinario")

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": {
                "anomalies": anomalies,
                "predictions": predictions,
                "trends": trends,
                "data_points": len(metrics_list),
                "analysis_period": f"{len(metrics_list)} data points"
            },
            "recommendations": recommendations,
            "summary": {
                "total_anomalies": len(anomalies),
                "critical_anomalies": len([a for a in anomalies if a["severity"] == "high"]),
                "predictions_count": len(predictions.get("predictions", {})) if predictions.get("status") == "success" else 0
            }
        }

    except Exception as e:
        logger.error(f"Error en análisis predictivo: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/health-score")
async def calculate_authentication_health_score():
    """
    🏥 Calcular puntuación de salud del sistema de autenticación
    """
    try:
        if len(historical_metrics) < 3:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "insufficient_data",
                "message": "Need at least 3 data points for health score"
            }

        # Obtener métricas más recientes
        recent_metrics = list(historical_metrics)[-5:]  # Últimos 5 puntos

        # Calcular componentes del health score
        components = {}

        # 1. Tasa de éxito (40% del score)
        avg_success_rate = statistics.mean([m.success_rate for m in recent_metrics])
        success_score = min(100, avg_success_rate * 100)
        components["success_rate"] = {
            "value": avg_success_rate,
            "score": success_score,
            "weight": 0.4
        }

        # 2. Tiempo de respuesta (30% del score)
        avg_response_time = statistics.mean([m.avg_response_time for m in recent_metrics])
        # Score basado en tiempo de respuesta (mejor = más rápido)
        response_score = max(0, 100 - (avg_response_time / 50))  # Penalizar >5s
        components["response_time"] = {
            "value": avg_response_time,
            "score": response_score,
            "weight": 0.3
        }

        # 3. Estabilidad de errores (20% del score)
        error_counts = [m.error_count for m in recent_metrics]
        error_variance = statistics.variance(error_counts) if len(error_counts) > 1 else 0
        avg_errors = statistics.mean(error_counts)
        stability_score = max(0, 100 - (error_variance / 10) - (avg_errors / 2))
        components["error_stability"] = {
            "value": avg_errors,
            "variance": error_variance,
            "score": stability_score,
            "weight": 0.2
        }

        # 4. Disponibilidad de usuarios (10% del score)
        avg_unique_users = statistics.mean([m.unique_users for m in recent_metrics])
        user_score = min(100, (avg_unique_users / 10) * 100)  # Normalizar a 10 usuarios
        components["user_availability"] = {
            "value": avg_unique_users,
            "score": user_score,
            "weight": 0.1
        }

        # Calcular score total ponderado
        total_score = (
            success_score * components["success_rate"]["weight"] +
            response_score * components["response_time"]["weight"] +
            stability_score * components["error_stability"]["weight"] +
            user_score * components["user_availability"]["weight"]
        )

        # Determinar estado de salud
        if total_score >= 90:
            health_status = "excellent"
            health_color = "green"
        elif total_score >= 75:
            health_status = "good"
            health_color = "yellow"
        elif total_score >= 60:
            health_status = "fair"
            health_color = "orange"
        else:
            health_status = "poor"
            health_color = "red"

        # Generar recomendaciones basadas en componentes
        recommendations = []
        if success_score < 80:
            recommendations.append("🔧 Mejorar tasa de éxito de autenticación")
        if response_score < 70:
            recommendations.append("⚡ Optimizar tiempo de respuesta")
        if stability_score < 60:
            recommendations.append("🛡️ Reducir variabilidad en errores")
        if user_score < 50:
            recommendations.append("👥 Verificar disponibilidad de usuarios")

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "health_score": {
                "total_score": round(total_score, 1),
                "health_status": health_status,
                "health_color": health_color,
                "components": components
            },
            "recommendations": recommendations,
            "analysis_period": f"{len(recent_metrics)} recent data points",
            "last_updated": recent_metrics[-1].timestamp.isoformat() if recent_metrics else None
        }

    except Exception as e:
        logger.error(f"Error calculando health score: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/metrics-history")
async def get_metrics_history(
    hours: int = 24,
    limit: int = 100
:
    """
    📈 Obtener historial de métricas
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Filtrar métricas por tiempo
        filtered_metrics = [
            m for m in historical_metrics
            if m.timestamp > cutoff_time
        ]

        # Limitar resultados
        if limit:
            filtered_metrics = filtered_metrics[-limit:]

        # Convertir a formato serializable
        metrics_data = []
        for metric in filtered_metrics:
            metrics_data.append({
                "timestamp": metric.timestamp.isoformat(),
                "success_rate": metric.success_rate,
                "avg_response_time_ms": metric.avg_response_time,
                "error_count": metric.error_count,
                "total_requests": metric.total_requests,
                "unique_users": metric.unique_users,
                "token_expiry_rate": metric.token_expiry_rate
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "history": {
                "period_hours": hours,
                "total_points": len(metrics_data),
                "metrics": metrics_data
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo historial de métricas: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
