from collections import deque
# backend/app/api/v1/endpoints/intermittent_failure_analyzer.py

import statistics
import threading
from collections import defaultdict, deque
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


class IntermittentFailureAnalyzer:


    def __init__(self):
        self.intermittent_patterns = {}  # Patrones intermitentes
        self.lock = threading.Lock()


    def log_request(self, request_data: Dict[str, Any], success: bool):
        """Registrar un request"""
        with self.lock:
            request_entry = 

            if success:
                self.successful_requests.append(request_entry)
            else:
                self.failed_requests.append(request_entry)


    def analyze_intermittent_patterns(self) -> Dict[str, Any]:
        """Analizar patrones intermitentes"""
        with self.lock:
            analysis = 
                "patterns": {},
                "recommendations": [],

        if len(self.successful_requests) == 0 and len(self.failed_requests) == 0:
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
                endpoint_analysis[endpoint] = 

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
                user_analysis[user_id] = 

        return user_analysis


    def _analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analizar patrones temporales"""
        # Agrupar por hora del día
        hourly_stats = defaultdict(lambda: {"successful": 0, "failed": 0})

        for request in self.successful_requests:
            hourly_stats[hour]["successful"] += 1

        for request in self.failed_requests:
            hourly_stats[hour]["failed"] += 1

        # Calcular tasas por hora
        hourly_analysis = {}
        for hour, stats in hourly_stats.items():
            total = stats["successful"] + stats["failed"]
            if total > 0:
                success_rate = stats["successful"] / total * 100
                hourly_analysis[hour] = 

        return hourly_analysis


    def _analyze_token_patterns(self) -> Dict[str, Any]:
        """Analizar patrones de token"""
        token_lengths_successful = [r["token_length"] for r in self.successful_requests if r["token_length"]]
        token_lengths_failed = [r["token_length"] for r in self.failed_requests if r["token_length"]]

        analysis = {}

        if token_lengths_successful:
            analysis["successful_tokens"] = 

        if token_lengths_failed:
            analysis["failed_tokens"] = 

        # Comparar longitudes
        if token_lengths_successful and token_lengths_failed:
            avg_successful = statistics.mean(token_lengths_successful)
            avg_failed = statistics.mean(token_lengths_failed)

            analysis["comparison"] = 

        return analysis


    def _generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en patrones"""
        recommendations = []

        # Recomendaciones por endpoint
        if "endpoints" in patterns:
            for endpoint, data in patterns["endpoints"].items():
                if data.get("intermittent"):
                    recommendations.append(f"Endpoint {endpoint} muestra comportamiento intermitente")

        # Recomendaciones por usuario
        if "users" in patterns:
            for user_id, data in patterns["users"].items():
                if data.get("problematic"):

        # Recomendaciones por token
        if "tokens" in patterns and "comparison" in patterns["tokens"]:
            comparison = patterns["tokens"]["comparison"]
            if comparison["length_difference"] > 10:

        return recommendations


# Instancia global del analizador
analyzer = IntermittentFailureAnalyzer()


@router.get("/intermittent-failure-analysis")
async def get_intermittent_failure_analysis
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        analysis = analyzer.analyze_intermittent_patterns()
        return 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")


async def log_request
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar un request para análisis"""
    try:
        success = request_data.get("success", True)
        analyzer.log_request(request_data, success)

        return 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar request: {str(e)}")
