"""Sistema de Diagnóstico de Red y Latencia
Analiza problemas de conectividad y rendimiento de red
"""

import logging
import socket
import statistics
import threading
import time
import urllib.request
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
# SISTEMA DE DIAGNÓSTICO DE RED
# ============================================

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
                    logger.error(f"Error en monitoreo de red: {e}")
                    time.sleep(600)
        
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🌐 Monitor de red iniciado")
    
    def _test_connectivity(self):
        """Probar conectividad a servicios externos"""
        test_urls = [
            "https://www.google.com",
            "https://www.github.com",
            "https://httpbin.org/status/200",
        ]
        
        for url in test_urls:
            try:
                start_time = time.time()
                response = urllib.request.urlopen(url, timeout=10)
                end_time = time.time()
                
                connectivity_test = {
                    "timestamp": datetime.now(),
                    "url": url,
                    "status_code": response.getcode(),
                    "response_time_ms": (end_time - start_time) * 1000,
                    "success": True,
                }
                
                with self.lock:
                    self.connectivity_tests.append(connectivity_test)
                
            except Exception as e:
                connectivity_test = {
                    "timestamp": datetime.now(),
                    "url": url,
                    "error": str(e),
                    "success": False,
                }
                
                with self.lock:
                    self.connectivity_tests.append(connectivity_test)
    
    def _measure_latency(self):
        """Medir latencia de red"""
        try:
            # Medir latencia a DNS
            start_time = time.time()
            socket.gethostbyname("www.google.com")
            dns_latency = (time.time() - start_time) * 1000
            
            latency_measurement = {
                "timestamp": datetime.now(),
                "dns_latency_ms": dns_latency,
                "network_status": "ok" if dns_latency < 100 else "slow",
            }
            
            with self.lock:
                self.latency_measurements.append(latency_measurement)
                
        except Exception as e:
            logger.error(f"Error midiendo latencia: {e}")
    
    def test_endpoint_connectivity(self, endpoint: str) -> Dict[str, Any]:
        """Probar conectividad a un endpoint específico"""
        try:
            start_time = time.time()
            response = urllib.request.urlopen(endpoint, timeout=10)
            end_time = time.time()
            
            return {
                "endpoint": endpoint,
                "status_code": response.getcode(),
                "response_time_ms": (end_time - start_time) * 1000,
                "success": True,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat(),
            }
    
    def get_network_health(self) -> Dict[str, Any]:
        """Obtener estado de salud de la red"""
        with self.lock:
            # Analizar pruebas de conectividad recientes
            recent_tests = [
                test for test in self.connectivity_tests
                if (datetime.now() - test["timestamp"]).total_seconds() < 3600
            ]
            
            successful_tests = [test for test in recent_tests if test["success"]]
            success_rate = len(successful_tests) / len(recent_tests) if recent_tests else 0
            
            # Analizar mediciones de latencia recientes
            recent_latencies = [
                measurement for measurement in self.latency_measurements
                if (datetime.now() - measurement["timestamp"]).total_seconds() < 3600
            ]
            
            avg_latency = 0
            if recent_latencies:
                latencies = [m["dns_latency_ms"] for m in recent_latencies]
                avg_latency = statistics.mean(latencies)
            
            return {
                "connectivity_success_rate": success_rate,
                "average_latency_ms": avg_latency,
                "total_tests": len(recent_tests),
                "total_latency_measurements": len(recent_latencies),
                "network_status": "healthy" if success_rate > 0.8 and avg_latency < 200 else "degraded",
                "last_update": datetime.now().isoformat(),
            }

# Instancia global del diagnóstico de red
network_diagnostic = NetworkDiagnostic()

# ============================================
# ENDPOINTS DEL DIAGNÓSTICO DE RED
# ============================================

@router.post("/network/test-connectivity", response_model=Dict[str, Any])
async def test_endpoint_connectivity(
    endpoint: str,
    current_user: User = Depends(get_current_user),
):
    """Probar conectividad a un endpoint específico"""
    return network_diagnostic.test_endpoint_connectivity(endpoint)

@router.get("/network/health", response_model=Dict[str, Any])
async def get_network_health(
    current_user: User = Depends(get_current_user),
):
    """Obtener estado de salud de la red"""
    return network_diagnostic.get_network_health()

@router.get("/network/latency-history", response_model=Dict[str, Any])
async def get_latency_history(
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de mediciones de latencia"""
    with network_diagnostic.lock:
        recent_measurements = list(network_diagnostic.latency_measurements)[-100:]
        
        return {
            "latency_measurements": recent_measurements,
            "total_count": len(network_diagnostic.latency_measurements),
            "last_update": datetime.now().isoformat(),
        }