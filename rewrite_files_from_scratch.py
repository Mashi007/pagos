#!/usr/bin/env python3
"""
Script para reescribir completamente archivos problemáticos desde cero
"""

import os
import shutil

def create_clean_file(file_path, content):
    """Crear archivo limpio desde cero"""
    
    print(f"Creando archivo limpio: {file_path}")
    
    # Crear backup del archivo original
    if os.path.exists(file_path):
        backup_path = file_path + ".backup_original"
        shutil.copy2(file_path, backup_path)
        print(f"  Backup creado: {backup_path}")
    
    # Escribir archivo completamente nuevo
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"  OK: Archivo creado exitosamente")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def create_intermittent_failure_analyzer():
    """Crear archivo intermittent_failure_analyzer.py desde cero"""
    
    content = '''# backend/app/api/v1/endpoints/intermittent_failure_analyzer.py
"""Analizador de fallos intermitentes específicos"""

import statistics
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


class IntermittentFailureAnalyzer:
    """Analizador de fallos intermitentes específicos"""
    
    def __init__(self):
        self.successful_requests = deque(maxlen=1000)  # Requests exitosos
        self.failed_requests = deque(maxlen=1000)  # Requests fallidos
        self.intermittent_patterns = {}  # Patrones intermitentes
        self.lock = threading.Lock()
    
    def log_request(self, request_data: Dict[str, Any], success: bool):
        """Registrar un request"""
        with self.lock:
            request_entry = {
                "timestamp": datetime.now(),
                "endpoint": request_data.get("endpoint"),
                "user_id": request_data.get("user_id"),
                "token_length": len(request_data.get("token", "")),
                "success": success,
            }
            
            if success:
                self.successful_requests.append(request_entry)
            else:
                self.failed_requests.append(request_entry)
    
    def analyze_intermittent_patterns(self) -> Dict[str, Any]:
        """Analizar patrones intermitentes"""
        with self.lock:
            analysis = {
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
                "successful_longer": avg_successful > avg_failed,
            }
        
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
                    recommendations.append(f"Usuario {user_id} tiene alta tasa de fallos")
        
        # Recomendaciones por token
        if "tokens" in patterns and "comparison" in patterns["tokens"]:
            comparison = patterns["tokens"]["comparison"]
            if comparison["length_difference"] > 10:
                recommendations.append("Diferencia significativa en longitud de tokens entre éxitos y fallos")
        
        return recommendations


# Instancia global del analizador
analyzer = IntermittentFailureAnalyzer()


@router.get("/intermittent-failure-analysis")
async def get_intermittent_failure_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener análisis de fallos intermitentes"""
    try:
        analysis = analyzer.analyze_intermittent_patterns()
        return {
            "status": "success",
            "data": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")


@router.post("/log-request")
async def log_request(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar un request para análisis"""
    try:
        success = request_data.get("success", True)
        analyzer.log_request(request_data, success)
        
        return {
            "status": "success",
            "message": "Request registrado exitosamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar request: {str(e)}")
'''
    
    return create_clean_file("backend/app/api/v1/endpoints/intermittent_failure_analyzer.py", content)

def create_network_diagnostic():
    """Crear archivo network_diagnostic.py desde cero"""
    
    content = '''# backend/app/api/v1/endpoints/network_diagnostic.py
"""Sistema de diagnóstico de red y latencia"""

import asyncio
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


class NetworkDiagnostic:
    """Sistema de diagnóstico de red y latencia"""
    
    def __init__(self):
        self.latency_measurements = deque(maxlen=1000)  # Mediciones de latencia
        self.connectivity_tests = deque(maxlen=500)  # Pruebas de conectividad
        self.network_stats = defaultdict(list)  # Estadísticas de red
        self.lock = threading.Lock()
        
        # Iniciar monitoreo de red en background
        self._start_network_monitoring()
    
    def _start_network_monitoring(self):
        """Iniciar monitoreo de red en background"""        
        def monitoring_loop():
            while True:
                try:
                    self._test_connectivity()
                    self._measure_latency()
                    time.sleep(300)  # Monitorear cada 5 minutos
                except Exception as e:
                    print(f"Error en monitoreo de red: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
    
    def _test_connectivity(self):
        """Probar conectividad a servicios externos"""
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://httpbin.org/get",
        ]
        
        for url in test_urls:
            try:
                start_time = time.time()
                response = httpx.get(url, timeout=10)
                end_time = time.time()
                
                test_result = {
                    "url": url,
                    "status_code": response.status_code,
                    "response_time": round((end_time - start_time) * 1000, 2),
                    "timestamp": datetime.now(),
                    "success": response.status_code == 200
                }
                
                with self.lock:
                    self.connectivity_tests.append(test_result)
                    
            except Exception as e:
                test_result = {
                    "url": url,
                    "status_code": None,
                    "response_time": None,
                    "timestamp": datetime.now(),
                    "success": False,
                    "error": str(e)
                }
                
                with self.lock:
                    self.connectivity_tests.append(test_result)
    
    def _measure_latency(self):
        """Medir latencia de red"""
        try:
            start_time = time.time()
            # Simular medición de latencia
            time.sleep(0.001)  # 1ms de simulación
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # Convertir a ms
            
            measurement = {
                "latency_ms": round(latency, 2),
                "timestamp": datetime.now(),
                "source": "internal"
            }
            
            with self.lock:
                self.latency_measurements.append(measurement)
                
        except Exception as e:
            print(f"Error en medición de latencia: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """Obtener estado de la red"""
        with self.lock:
            # Calcular estadísticas de conectividad
            recent_tests = list(self.connectivity_tests)[-10:]  # Últimos 10 tests
            success_rate = sum(1 for test in recent_tests if test["success"]) / len(recent_tests) * 100 if recent_tests else 0
            
            # Calcular latencia promedio
            recent_latency = list(self.latency_measurements)[-10:]  # Últimas 10 mediciones
            avg_latency = sum(m["latency_ms"] for m in recent_latency) / len(recent_latency) if recent_latency else 0
            
            return {
                "connectivity": {
                    "success_rate": round(success_rate, 2),
                    "total_tests": len(self.connectivity_tests),
                    "recent_tests": recent_tests
                },
                "latency": {
                    "average_ms": round(avg_latency, 2),
                    "total_measurements": len(self.latency_measurements),
                    "recent_measurements": recent_latency
                },
                "status": "healthy" if success_rate > 80 and avg_latency < 1000 else "degraded"
            }
    
    def test_endpoint_connectivity(self, endpoint: str) -> Dict[str, Any]:
        """Probar conectividad a un endpoint específico"""
        try:
            start_time = time.time()
            response = httpx.get(endpoint, timeout=10)
            end_time = time.time()
            
            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "success": response.status_code == 200,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Instancia global del diagnóstico de red
network_diagnostic = NetworkDiagnostic()


@router.get("/network-status")
async def get_network_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener estado de la red"""
    try:
        status = network_diagnostic.get_network_status()
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estado de red: {str(e)}")


@router.post("/test-connectivity")
async def test_connectivity(
    endpoint: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Probar conectividad a un endpoint específico"""
    try:
        result = network_diagnostic.test_endpoint_connectivity(endpoint)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al probar conectividad: {str(e)}")
'''
    
    return create_clean_file("backend/app/api/v1/endpoints/network_diagnostic.py", content)

def create_temporal_analysis():
    """Crear archivo temporal_analysis.py desde cero"""
    
    content = '''# backend/app/api/v1/endpoints/temporal_analysis.py
"""Sistema temporal para análisis de timing y sincronización"""

import statistics
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


class TemporalAnalysisSystem:
    """Sistema temporal para análisis de timing y sincronización"""
    
    def __init__(self):
        self.timing_events = deque(maxlen=10000)  # Eventos de timing
        self.clock_sync_data = deque(maxlen=1000)  # Datos de sincronización de reloj
        self.token_lifecycle_data = deque(maxlen=5000)  # Datos de ciclo de vida de tokens
        self.timing_correlations = {}  # Correlaciones temporales
        self.lock = threading.Lock()
        
        # Iniciar monitoreo temporal en background
        self._start_temporal_monitoring()
    
    def _start_temporal_monitoring(self):
        """Iniciar monitoreo temporal en background"""        
        def monitoring_loop():
            while True:
                try:
                    self._collect_timing_data()
                    self._analyze_timing_patterns()
                    time.sleep(60)  # Monitorear cada minuto
                except Exception as e:
                    print(f"Error en monitoreo temporal: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
    
    def _collect_timing_data(self):
        """Recopilar datos de timing"""
        current_time = datetime.now()
        
        # Simular recopilación de datos de timing
        timing_event = {
            "timestamp": current_time,
            "event_type": "system_check",
            "duration_ms": 5.2,
            "source": "temporal_monitor"
        }
        
        with self.lock:
            self.timing_events.append(timing_event)
    
    def _analyze_timing_patterns(self):
        """Analizar patrones temporales"""
        with self.lock:
            if len(self.timing_events) < 10:
                return
            
            # Analizar patrones de duración
            recent_events = list(self.timing_events)[-100:]  # Últimos 100 eventos
            durations = [event.get("duration_ms", 0) for event in recent_events]
            
            if durations:
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                min_duration = min(durations)
                
                self.timing_correlations["duration_stats"] = {
                    "average_ms": round(avg_duration, 2),
                    "max_ms": round(max_duration, 2),
                    "min_ms": round(min_duration, 2),
                    "sample_size": len(durations)
                }
    
    def log_timing_event(self, event_data: Dict[str, Any]):
        """Registrar un evento de timing"""
        with self.lock:
            event = {
                "timestamp": datetime.now(),
                "event_type": event_data.get("event_type", "unknown"),
                "duration_ms": event_data.get("duration_ms", 0),
                "source": event_data.get("source", "manual"),
                "metadata": event_data.get("metadata", {})
            }
            
            self.timing_events.append(event)
    
    def log_token_lifecycle(self, token_data: Dict[str, Any]):
        """Registrar ciclo de vida de token"""
        with self.lock:
            lifecycle_event = {
                "timestamp": datetime.now(),
                "token_id": token_data.get("token_id"),
                "action": token_data.get("action"),  # created, used, expired
                "duration_ms": token_data.get("duration_ms", 0),
                "user_id": token_data.get("user_id")
            }
            
            self.token_lifecycle_data.append(lifecycle_event)
    
    def get_temporal_analysis(self) -> Dict[str, Any]:
        """Obtener análisis temporal completo"""
        with self.lock:
            analysis = {
                "timing_events": {
                    "total_events": len(self.timing_events),
                    "recent_events": list(self.timing_events)[-10:]
                },
                "token_lifecycle": {
                    "total_events": len(self.token_lifecycle_data),
                    "recent_events": list(self.token_lifecycle_data)[-10:]
                },
                "correlations": self.timing_correlations,
                "clock_sync": {
                    "total_measurements": len(self.clock_sync_data),
                    "recent_measurements": list(self.clock_sync_data)[-5:]
                }
            }
            
            return analysis
    
    def get_timing_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de timing"""
        with self.lock:
            if not self.timing_events:
                return {"error": "No hay datos de timing disponibles"}
            
            recent_events = list(self.timing_events)[-100:]  # Últimos 100 eventos
            durations = [event.get("duration_ms", 0) for event in recent_events]
            
            if not durations:
                return {"error": "No hay datos de duración disponibles"}
            
            return {
                "sample_size": len(durations),
                "average_duration_ms": round(statistics.mean(durations), 2),
                "median_duration_ms": round(statistics.median(durations), 2),
                "min_duration_ms": round(min(durations), 2),
                "max_duration_ms": round(max(durations), 2),
                "std_deviation_ms": round(statistics.stdev(durations) if len(durations) > 1 else 0, 2)
            }


# Instancia global del sistema temporal
temporal_system = TemporalAnalysisSystem()


@router.get("/temporal-analysis")
async def get_temporal_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener análisis temporal completo"""
    try:
        analysis = temporal_system.get_temporal_analysis()
        return {
            "status": "success",
            "data": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis temporal: {str(e)}")


@router.get("/timing-statistics")
async def get_timing_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas de timing"""
    try:
        stats = temporal_system.get_timing_statistics()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")


@router.post("/log-timing-event")
async def log_timing_event(
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar un evento de timing"""
    try:
        temporal_system.log_timing_event(event_data)
        return {
            "status": "success",
            "message": "Evento de timing registrado exitosamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar evento: {str(e)}")


@router.post("/log-token-lifecycle")
async def log_token_lifecycle(
    token_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar ciclo de vida de token"""
    try:
        temporal_system.log_token_lifecycle(token_data)
        return {
            "status": "success",
            "message": "Ciclo de vida de token registrado exitosamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar ciclo de vida: {str(e)}")
'''
    
    return create_clean_file("backend/app/api/v1/endpoints/temporal_analysis.py", content)

def main():
    """Función principal"""
    
    print("REESCRIBIENDO ARCHIVOS PROBLEMÁTICOS DESDE CERO")
    print("=" * 60)
    
    success_count = 0
    
    # Crear archivos desde cero
    if create_intermittent_failure_analyzer():
        success_count += 1
    
    if create_network_diagnostic():
        success_count += 1
    
    if create_temporal_analysis():
        success_count += 1
    
    print(f"\nRESUMEN: {success_count}/3 archivos creados exitosamente")
    print("Archivos reescritos desde cero con codificación UTF-8 limpia")

if __name__ == "__main__":
    main()
