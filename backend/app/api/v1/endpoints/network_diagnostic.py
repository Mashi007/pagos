"""
Sistema de Diagnóstico de Red y Latencia
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


class NetworkDiagnosticSystem:
    """Sistema de diagnóstico de red y latencia"""

    def __init__(self):
        self.latency_history = deque(maxlen=1000)  # Historial de latencia
        self.connection_tests = deque(maxlen=100)  # Tests de conexión
        self.network_metrics = defaultdict(list)  # Métricas de red
        self.lock = threading.Lock()

        # Iniciar monitoreo en background
        self._start_background_monitoring()

    def _start_background_monitoring(self):
        """Iniciar monitoreo de red en background"""

        def monitoring_loop():
            while True:
                try:
                    self._perform_network_tests()
                    time.sleep(60)  # Test cada minuto
                except Exception as e:
                    logger.error(f"Error en monitoreo de red: {e}")
                    time.sleep(120)

        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🌐 Sistema de diagnóstico de red iniciado")

    def _perform_network_tests(self):
        """Realizar tests de red periódicos"""
        with self.lock:
            # Test de conectividad básica
            connectivity_test = self._test_connectivity()
            self.connection_tests.append(connectivity_test)

            # Test de latencia a servicios externos
            latency_tests = self._test_latency()
            for test in latency_tests:
                self.latency_history.append(test)

    def _test_connectivity(self) -> Dict[str, Any]:
        """Test básico de conectividad"""
        test_result = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "overall_status": "unknown",
        }

        # Test de DNS
        try:
            socket.gethostbyname("google.com")
            test_result["tests"]["dns"] = {"status": "success", "latency_ms": 0}
        except Exception as e:
            test_result["tests"]["dns"] = {"status": "failed", "error": str(e)}

        # Test de conectividad HTTP
        try:
            import urllib.request

            start_time = time.time()
            urllib.request.urlopen("http://httpbin.org/get", timeout=10)
            latency = (time.time() - start_time) * 1000
            test_result["tests"]["http"] = {"status": "success", "latency_ms": latency}
        except Exception as e:
            test_result["tests"]["http"] = {"status": "failed", "error": str(e)}

        # Test de conectividad HTTPS
        try:
            start_time = time.time()
            urllib.request.urlopen("https://httpbin.org/get", timeout=10)
            latency = (time.time() - start_time) * 1000
            test_result["tests"]["https"] = {"status": "success", "latency_ms": latency}
        except Exception as e:
            test_result["tests"]["https"] = {"status": "failed", "error": str(e)}

        # Determinar estado general
        failed_tests = [
            test for test in test_result["tests"].values() if test["status"] == "failed"
        ]
        if len(failed_tests) == 0:
            test_result["overall_status"] = "excellent"
        elif len(failed_tests) == 1:
            test_result["overall_status"] = "good"
        elif len(failed_tests) == 2:
            test_result["overall_status"] = "degraded"
        else:
            test_result["overall_status"] = "poor"

        return test_result

    def _test_latency(self) -> List[Dict[str, Any]]:
        """Test de latencia a varios servicios"""
        latency_tests = []

        # Servicios a testear
        services = [
            {"name": "google_dns", "host": "8.8.8.8", "port": 53},
            {"name": "cloudflare_dns", "host": "1.1.1.1", "port": 53},
            {"name": "google_http", "url": "https://www.google.com"},
            {"name": "cloudflare_http", "url": "https://www.cloudflare.com"},
        ]

        for service in services:
            test_result = {
                "service": service["name"],
                "timestamp": datetime.now().isoformat(),
                "latency_ms": None,
                "status": "unknown",
                "error": None,
            }

            try:
                if "url" in service:
                    # Test HTTP/HTTPS
                    start_time = time.time()
                    urllib.request.urlopen(service["url"], timeout=10)
                    latency = (time.time() - start_time) * 1000
                    test_result["latency_ms"] = latency
                    test_result["status"] = "success"
                else:
                    # Test TCP
                    start_time = time.time()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((service["host"], service["port"]))
                    sock.close()
                    latency = (time.time() - start_time) * 1000
                    test_result["latency_ms"] = latency
                    test_result["status"] = "success"

            except Exception as e:
                test_result["status"] = "failed"
                test_result["error"] = str(e)

            latency_tests.append(test_result)

        return latency_tests

    def analyze_network_health(self) -> Dict[str, Any]:
        """Analizar salud general de la red"""
        with self.lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=10)  # Últimos 10 minutos

            # Filtrar tests recientes
            recent_tests = [
                test
                for test in self.connection_tests
                if datetime.fromisoformat(test["timestamp"]) > cutoff_time
            ]

            recent_latency = [
                test
                for test in self.latency_history
                if datetime.fromisoformat(test["timestamp"]) > cutoff_time
            ]

            # Análisis de conectividad
            connectivity_analysis = self._analyze_connectivity(recent_tests)

            # Análisis de latencia
            latency_analysis = self._analyze_latency(recent_latency)

            # Análisis de tendencias
            trend_analysis = self._analyze_trends()

            return {
                "timestamp": current_time.isoformat(),
                "overall_health": self._calculate_overall_health(
                    connectivity_analysis, latency_analysis
                ),
                "connectivity": connectivity_analysis,
                "latency": latency_analysis,
                "trends": trend_analysis,
                "recommendations": self._generate_network_recommendations(
                    connectivity_analysis, latency_analysis
                ),
            }

    def _analyze_connectivity(self, recent_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizar conectividad"""
        if not recent_tests:
            return {"status": "no_data", "message": "No hay datos recientes"}

        # Contar tests exitosos por tipo
        test_types = defaultdict(lambda: {"success": 0, "failed": 0})

        for test in recent_tests:
            for test_type, result in test["tests"].items():
                if result["status"] == "success":
                    test_types[test_type]["success"] += 1
                else:
                    test_types[test_type]["failed"] += 1

        # Calcular porcentajes de éxito
        connectivity_stats = {}
        for test_type, counts in test_types.items():
            total = counts["success"] + counts["failed"]
            success_rate = (counts["success"] / total * 100) if total > 0 else 0
            connectivity_stats[test_type] = {
                "success_rate": success_rate,
                "success_count": counts["success"],
                "failed_count": counts["failed"],
            }

        # Estado general de conectividad
        overall_success_rate = (
            sum(stats["success_rate"] for stats in connectivity_stats.values())
            / len(connectivity_stats)
            if connectivity_stats
            else 0
        )

        if overall_success_rate >= 95:
            connectivity_status = "excellent"
        elif overall_success_rate >= 80:
            connectivity_status = "good"
        elif overall_success_rate >= 60:
            connectivity_status = "degraded"
        else:
            connectivity_status = "poor"

        return {
            "status": connectivity_status,
            "overall_success_rate": overall_success_rate,
            "test_results": connectivity_stats,
            "total_tests": len(recent_tests),
        }

    def _analyze_latency(self, recent_latency: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizar latencia"""
        if not recent_latency:
            return {
                "status": "no_data",
                "message": "No hay datos de latencia recientes",
            }

        # Agrupar por servicio
        service_latencies = defaultdict(list)
        for test in recent_latency:
            if test["status"] == "success" and test["latency_ms"] is not None:
                service_latencies[test["service"]].append(test["latency_ms"])

        # Calcular estadísticas por servicio
        latency_stats = {}
        for service, latencies in service_latencies.items():
            if latencies:
                latency_stats[service] = {
                    "avg_latency_ms": statistics.mean(latencies),
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                    "median_latency_ms": statistics.median(latencies),
                    "test_count": len(latencies),
                }

        # Calcular latencia promedio general
        all_latencies = [lat for latencies in service_latencies.values() for lat in latencies]
        overall_avg_latency = statistics.mean(all_latencies) if all_latencies else 0

        # Determinar estado de latencia
        if overall_avg_latency < 100:
            latency_status = "excellent"
        elif overall_avg_latency < 300:
            latency_status = "good"
        elif overall_avg_latency < 1000:
            latency_status = "degraded"
        else:
            latency_status = "poor"

        return {
            "status": latency_status,
            "overall_avg_latency_ms": overall_avg_latency,
            "service_stats": latency_stats,
            "total_tests": len(recent_latency),
        }

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analizar tendencias de red"""
        with self.lock:
            if len(self.latency_history) < 10:
                return {"status": "insufficient_data"}

            # Analizar tendencia de latencia
            recent_latencies = list(self.latency_history)[-20:]  # Últimos 20 tests
            successful_tests = [test for test in recent_latencies if test["status"] == "success"]

            if len(successful_tests) < 5:
                return {"status": "insufficient_successful_tests"}

            # Calcular tendencia
            latencies = [test["latency_ms"] for test in successful_tests]
            if len(latencies) >= 2:
                # Tendencia simple: comparar primera mitad vs segunda mitad
                mid_point = len(latencies) // 2
                first_half_avg = statistics.mean(latencies[:mid_point])
                second_half_avg = statistics.mean(latencies[mid_point:])

                trend_direction = "improving" if second_half_avg < first_half_avg else "degrading"
                trend_magnitude = abs(second_half_avg - first_half_avg)

                return {
                    "status": "analyzed",
                    "trend_direction": trend_direction,
                    "trend_magnitude_ms": trend_magnitude,
                    "first_half_avg_ms": first_half_avg,
                    "second_half_avg_ms": second_half_avg,
                }

            return {"status": "insufficient_data"}

    def _calculate_overall_health(
        self, connectivity: Dict[str, Any], latency: Dict[str, Any]
    ) -> str:
        """Calcular salud general de la red"""
        connectivity_status = connectivity.get("status", "unknown")
        latency_status = latency.get("status", "unknown")

        # Mapear estados a números para cálculo
        status_scores = {
            "excellent": 4,
            "good": 3,
            "degraded": 2,
            "poor": 1,
            "unknown": 0,
            "no_data": 0,
        }

        connectivity_score = status_scores.get(connectivity_status, 0)
        latency_score = status_scores.get(latency_status, 0)

        avg_score = (connectivity_score + latency_score) / 2

        if avg_score >= 3.5:
            return "excellent"
        elif avg_score >= 2.5:
            return "good"
        elif avg_score >= 1.5:
            return "degraded"
        else:
            return "poor"

    def _generate_network_recommendations(
        self, connectivity: Dict[str, Any], latency: Dict[str, Any]
    ) -> List[str]:
        """Generar recomendaciones de red"""
        recommendations = []

        # Recomendaciones basadas en conectividad
        connectivity_status = connectivity.get("status", "unknown")
        if connectivity_status == "poor":
            recommendations.append("🔴 Conectividad crítica - Verificar configuración de red")
        elif connectivity_status == "degraded":
            recommendations.append("🟡 Conectividad degradada - Revisar DNS y firewall")

        # Recomendaciones basadas en latencia
        latency_status = latency.get("status", "unknown")
        if latency_status == "poor":
            recommendations.append("🔴 Latencia muy alta - Considerar CDN o servidor más cercano")
        elif latency_status == "degraded":
            recommendations.append("🟡 Latencia alta - Optimizar queries y conexiones")

        # Recomendaciones específicas por servicio
        test_results = connectivity.get("test_results", {})
        for test_type, result in test_results.items():
            if result["success_rate"] < 80:
                if test_type == "dns":
                    recommendations.append("🔧 Problemas de DNS - Verificar configuración DNS")
                elif test_type == "https":
                    recommendations.append("🔒 Problemas HTTPS - Verificar certificados SSL")

        if not recommendations:
            recommendations.append("✅ Red funcionando correctamente")

        return recommendations


# Instancia global del sistema de diagnóstico
network_diagnostic = NetworkDiagnosticSystem()

# ============================================
# ENDPOINTS DE DIAGNÓSTICO DE RED
# ============================================


@router.get("/network-health")
async def get_network_health(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    🌐 Análisis completo de salud de red
    """
    try:
        health_analysis = network_diagnostic.analyze_network_health()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": health_analysis,
        }

    except Exception as e:
        logger.error(f"Error analizando salud de red: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/test-connectivity")
async def test_connectivity_now(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    🔍 Test inmediato de conectividad
    """
    try:
        # Realizar test inmediato
        test_result = network_diagnostic._test_connectivity()

        # Agregar a historial
        with network_diagnostic.lock:
            network_diagnostic.connection_tests.append(test_result)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "test_result": test_result,
        }

    except Exception as e:
        logger.error(f"Error en test de conectividad: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.post("/test-latency")
async def test_latency_now(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    ⚡ Test inmediato de latencia
    """
    try:
        # Realizar test inmediato
        latency_tests = network_diagnostic._test_latency()

        # Agregar a historial
        with network_diagnostic.lock:
            for test in latency_tests:
                network_diagnostic.latency_history.append(test)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "latency_tests": latency_tests,
        }

    except Exception as e:
        logger.error(f"Error en test de latencia: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/network-statistics")
async def get_network_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    📊 Estadísticas históricas de red
    """
    try:
        with network_diagnostic.lock:
            # Estadísticas de conectividad
            connectivity_stats = {
                "total_tests": len(network_diagnostic.connection_tests),
                "recent_tests": (
                    list(network_diagnostic.connection_tests)[-10:]
                    if network_diagnostic.connection_tests
                    else []
                ),
            }

            # Estadísticas de latencia
            latency_stats = {
                "total_tests": len(network_diagnostic.latency_history),
                "recent_tests": (
                    list(network_diagnostic.latency_history)[-20:]
                    if network_diagnostic.latency_history
                    else []
                ),
            }

            # Calcular métricas agregadas
            if network_diagnostic.latency_history:
                all_latencies = [
                    test["latency_ms"]
                    for test in network_diagnostic.latency_history
                    if test["status"] == "success" and test["latency_ms"] is not None
                ]

                if all_latencies:
                    latency_stats["aggregated"] = {
                        "avg_latency_ms": statistics.mean(all_latencies),
                        "min_latency_ms": min(all_latencies),
                        "max_latency_ms": max(all_latencies),
                        "median_latency_ms": statistics.median(all_latencies),
                    }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "statistics": {
                "connectivity": connectivity_stats,
                "latency": latency_stats,
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de red: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/network-trends")
async def get_network_trends(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    📈 Análisis de tendencias de red
    """
    try:
        trends = network_diagnostic._analyze_trends()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "trends": trends,
        }

    except Exception as e:
        logger.error(f"Error analizando tendencias de red: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }
