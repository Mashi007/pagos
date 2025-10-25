"""Sistema de Análisis de Fallos Intermitentes
Identifica patrones específicos que causan fallos 401 intermitentes
"""

import logging
import statistics
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE ANÁLISIS DE FALLOS INTERMITENTES
# ============================================

class IntermittentFailureAnalyzer:
    """Analizador de fallos intermitentes específicos"""
    
    def __init__(self):
        self.successful_requests = deque(maxlen=1000)  # Requests exitosos
        self.failed_requests = deque(maxlen=1000)  # Requests fallidos
        self.intermittent_patterns = {}  # Patrones intermitentes
        self.lock = threading.Lock()
    
    def log_successful_request(self, request_data: Dict[str, Any]):
        """Registrar request exitoso"""
        with self.lock:
                request = {
                "timestamp": datetime.now(),
                "endpoint": request_data.get("endpoint"),
                "method": request_data.get("method"),
                "user_id": request_data.get("user_id"),
                "token_length": request_data.get("token_length"),
                "response_time_ms": request_data.get("response_time_ms"),
                "client_ip": request_data.get("client_ip"),
                "user_agent": request_data.get("user_agent"),
                "success": True,
        }
        self.successful_requests.append(request)
        
        logger.debug(
                f"✅ Request exitoso registrado: {request['endpoint']}"
        )
    
    def log_failed_request(self, request_data: Dict[str, Any]):
        """Registrar request fallido"""
        with self.lock:
                request = {
                "timestamp": datetime.now(),
                "endpoint": request_data.get("endpoint"),
                "method": request_data.get("method"),
                "user_id": request_data.get("user_id"),
                "token_length": request_data.get("token_length"),
                "response_time_ms": request_data.get("response_time_ms"),
                "client_ip": request_data.get("client_ip"),
                "user_agent": request_data.get("user_agent"),
                "error_code": request_data.get("error_code"),
                "error_message": request_data.get("error_message"),
                "success": False,
        }
        self.failed_requests.append(request)
        
        logger.warning(
                f"❌ Request fallido registrado: {request['endpoint']} - {request['error_code']}"
        )
    
def analyze_intermittent_patterns(self) -> Dict[str, Any]:
        """Analizar patrones intermitentes"""
        with self.lock:
                analysis = {
                "timestamp": datetime.now().isoformat(),
                "total_successful": len(self.successful_requests),
                "total_failed": len(self.failed_requests),
                "patterns": {},
                "recommendations": [],
        }
        
        if len(self.successful_requests) == 0 and len(self.failed_requests) == 0:
                analysis["patterns"]["no_data"] = "No hay datos suficientes para análisis"
                return analysis
        
        # Analizar patrones por endpoint
        endpoint_patterns = self._analyze_endpoint_patterns()
        analysis["patterns"]["endpoints"] = endpoint_patterns
        
        # Analizar patrones por usuario
        user_patterns = self._analyze_user_patterns()
        analysis["patterns"]["users"] = user_patterns
        
        # Analizar patrones temporales
        temporal_patterns = self._analyze_temporal_patterns()
        analysis["patterns"]["temporal"] = temporal_patterns
        
        # Analizar patrones de token
        token_patterns = self._analyze_token_patterns()
        analysis["patterns"]["tokens"] = token_patterns
        
        # Generar recomendaciones
        analysis["recommendations"] = self._generate_recommendations(analysis["patterns"])
        
        return analysis
    
    def _analyze_endpoint_patterns(self) -> Dict[str, Any]:
        """Analizar patrones por endpoint"""
        endpoint_stats = defaultdict(lambda: {"successful": 0, "failed": 0})
        
        # Contar por endpoint
        for request in self.successful_requests:
            endpoint_stats[request["endpoint"]]["successful"] += 1
        
        for request in self.failed_requests:
            endpoint_stats[request["endpoint"]]["failed"] += 1
        
        # Calcular tasas de éxito
        endpoint_analysis = {}
        for endpoint, stats in endpoint_stats.items():
            total = stats["successful"] + stats["failed"]
            if total > 0:
                success_rate = stats["successful"] / total * 100
                endpoint_analysis[endpoint] = {
                    "success_rate": round(success_rate, 2),
                    "total_requests": total,
                    "successful": stats["successful"],
                    "failed": stats["failed"],
                    "intermittent": 20 < success_rate < 80,  # Considerar intermitente si está entre 20-80%
                }
        
        return endpoint_analysis
    
    def _analyze_user_patterns(self) -> Dict[str, Any]:
        """Analizar patrones por usuario"""
        user_stats = defaultdict(lambda: {"successful": 0, "failed": 0})
        
        # Contar por usuario
        for request in self.successful_requests:
            if request["user_id"]:
                user_stats[request["user_id"]]["successful"] += 1
        
        for request in self.failed_requests:
            if request["user_id"]:
                user_stats[request["user_id"]]["failed"] += 1
        
        # Calcular tasas de éxito por usuario
        user_analysis = {}
        for user_id, stats in user_stats.items():
            total = stats["successful"] + stats["failed"]
            if total > 0:
                success_rate = stats["successful"] / total * 100
                user_analysis[user_id] = {
                    "success_rate": round(success_rate, 2),
                    "total_requests": total,
                    "successful": stats["successful"],
                    "failed": stats["failed"],
                    "problematic": success_rate < 50,  # Usuario problemático si éxito < 50%
                }
        
        return user_analysis
    
    def _analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analizar patrones temporales"""
        # Agrupar por hora del día
        hourly_stats = defaultdict(lambda: {"successful": 0, "failed": 0})
        
        for request in self.successful_requests:
            hour = request["timestamp"].hour
            hourly_stats[hour]["successful"] += 1
        
        for request in self.failed_requests:
            hour = request["timestamp"].hour
            hourly_stats[hour]["failed"] += 1
        
        # Calcular tasas por hora
        hourly_analysis = {}
        for hour, stats in hourly_stats.items():
            total = stats["successful"] + stats["failed"]
            if total > 0:
                success_rate = stats["successful"] / total * 100
                hourly_analysis[hour] = {
                    "success_rate": round(success_rate, 2),
                    "total_requests": total,
                    "peak_hour": total > 10,  # Hora pico si más de 10 requests
                }
        
        return hourly_analysis
    
    def _analyze_token_patterns(self) -> Dict[str, Any]:
        """Analizar patrones de token"""
        token_lengths_successful = [r["token_length"] for r in self.successful_requests if r["token_length"]]
        token_lengths_failed = [r["token_length"] for r in self.failed_requests if r["token_length"]]
        
        analysis = {}
        
        if token_lengths_successful:
            analysis["successful_tokens"] = {
                "avg_length": round(statistics.mean(token_lengths_successful), 2),
                "min_length": min(token_lengths_successful),
                "max_length": max(token_lengths_successful),
                "count": len(token_lengths_successful),
            }
        
        if token_lengths_failed:
            analysis["failed_tokens"] = {
                "avg_length": round(statistics.mean(token_lengths_failed), 2),
                "min_length": min(token_lengths_failed),
                "max_length": max(token_lengths_failed),
                "count": len(token_lengths_failed),
            }
        
        # Comparar longitudes
        if token_lengths_successful and token_lengths_failed:
            avg_successful = statistics.mean(token_lengths_successful)
            avg_failed = statistics.mean(token_lengths_failed)
            
            analysis["comparison"] = {
                "length_difference": round(abs(avg_successful - avg_failed), 2),
                "failed_tokens_shorter": avg_failed < avg_successful,
                "potential_issue": abs(avg_successful - avg_failed) > 50,
            }
        
        return analysis
    
    def _generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en patrones"""
        recommendations = []
        
        # Recomendaciones basadas en endpoints
        endpoints = patterns.get("endpoints", {})
        for endpoint, stats in endpoints.items():
        if stats.get("intermittent"):
                recommendations.append(f"Endpoint {endpoint} muestra comportamiento intermitente - revisar configuración")
        
        # Recomendaciones basadas en usuarios
        users = patterns.get("users", {})
        problematic_users = [user_id for user_id, stats in users.items() if stats.get("problematic")]
        if problematic_users:
        recommendations.append(f"Usuarios problemáticos detectados: {', '.join(problematic_users)}")
        
        # Recomendaciones basadas en tokens
        tokens = patterns.get("tokens", {})
        comparison = tokens.get("comparison", {})
        if comparison.get("potential_issue"):
        recommendations.append("Diferencia significativa en longitud de tokens entre éxitos y fallos")
        
        # Recomendaciones generales
        if not recommendations:
        recommendations.append("No se detectaron patrones intermitentes obvios")
        
        return recommendations
    
        def get_failure_rate_by_timeframe(self, minutes: int = 60) -> Dict[str, Any]:
        """Obtener tasa de fallo por período de tiempo"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
                recent_successful = [
                r for r in self.successful_requests 
                if r["timestamp"] > cutoff
        ]
        recent_failed = [
                r for r in self.failed_requests 
                if r["timestamp"] > cutoff
        ]
        
        total_recent = len(recent_successful) + len(recent_failed)
        failure_rate = (len(recent_failed) / total_recent * 100) if total_recent > 0 else 0
        
        return {
        "timeframe_minutes": minutes,
        "total_requests": total_recent,
        "successful_requests": len(recent_successful),
        "failed_requests": len(recent_failed),
        "failure_rate_percent": round(failure_rate, 2),
        "timestamp": datetime.now().isoformat(),
        }

# Instancia global del analizador
failure_analyzer = IntermittentFailureAnalyzer()

# ============================================
# ENDPOINTS DE ANÁLISIS DE FALLOS INTERMITENTES
# ============================================

@router.post("/log-successful-request")
async def log_successful_request(
        request_data: Dict[str, Any],
        current_user: User = Depends(get_current_user),
):
        """Registrar request exitoso"""
        try:
        failure_analyzer.log_successful_request(request_data)
        
        return {
        "success": True,
        "message": "Request exitoso registrado"
        }
        
        except Exception as e:
        logger.error(f"Error registrando request exitoso: {e}")
        raise HTTPException(
        status_code=500,
        detail=f"Error interno: {str(e)}"
        )

@router.post("/log-failed-request")
async def log_failed_request(
        request_data: Dict[str, Any],
        current_user: User = Depends(get_current_user),
):
        """Registrar request fallido"""
        try:
        failure_analyzer.log_failed_request(request_data)
        
        return {
        "success": True,
        "message": "Request fallido registrado"
        }
        
        except Exception as e:
        logger.error(f"Error registrando request fallido: {e}")
        raise HTTPException(
        status_code=500,
        detail=f"Error interno: {str(e)}"
        )

@router.get("/analyze-patterns")
async def analyze_intermittent_patterns(
        current_user: User = Depends(get_current_user),
):
        """Analizar patrones intermitentes"""
        try:
        analysis = failure_analyzer.analyze_intermittent_patterns()
        
        return {
        "success": True,
        "analysis": analysis
        }
        
        except Exception as e:
        logger.error(f"Error analizando patrones: {e}")
        raise HTTPException(
        status_code=500,
        detail=f"Error interno: {str(e)}"
        )

@router.get("/failure-rate")
async def get_failure_rate(
        minutes: int = 60,
        current_user: User = Depends(get_current_user),
):
        """Obtener tasa de fallo por período de tiempo"""
        try:
        failure_rate = failure_analyzer.get_failure_rate_by_timeframe(minutes)
        
        return {
        "success": True,
        "failure_rate": failure_rate
        }
        
        except Exception as e:
        logger.error(f"Error obteniendo tasa de fallo: {e}")
        raise HTTPException(
        status_code=500,
        detail=f"Error interno: {str(e)}"
        )

@router.get("/endpoint-analysis")
async def get_endpoint_analysis(
        current_user: User = Depends(get_current_user),
):
        """Obtener análisis específico por endpoint"""
        try:
        analysis = failure_analyzer.analyze_intermittent_patterns()
        endpoint_analysis = analysis["patterns"].get("endpoints", {})
        
        return {
        "success": True,
        "endpoint_analysis": endpoint_analysis
        }
        
        except Exception as e:
        logger.error(f"Error obteniendo análisis de endpoints: {e}")
        raise HTTPException(
        status_code=500,
        detail=f"Error interno: {str(e)}"
        )
