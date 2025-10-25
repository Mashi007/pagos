# backend/app/api/v1/endpoints/network_diagnostic.py
"""Sistema de diagnóstico de red y latencia"""

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
