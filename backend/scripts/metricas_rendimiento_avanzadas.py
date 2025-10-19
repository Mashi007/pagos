"""
Sistema de Métricas de Rendimiento Avanzadas
Monitoreo y análisis de performance del sistema
"""
import requests
import json
import time
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class MetricaRendimiento:
    """Métrica individual de rendimiento"""
    timestamp: str
    endpoint: str
    tiempo_respuesta: float
    codigo_respuesta: int
    tamaño_respuesta: int
    memoria_usada: Optional[float] = None
    cpu_usado: Optional[float] = None

@dataclass
class ResumenMetricas:
    """Resumen de métricas de rendimiento"""
    periodo: str
    total_requests: int
    requests_exitosos: int
    requests_fallidos: int
    tiempo_promedio: float
    tiempo_mediana: float
    tiempo_p95: float
    tiempo_p99: float
    throughput_rps: float
    tasa_error: float
    endpoints_mas_lentos: List[Dict]
    tendencia_rendimiento: str

class MonitorRendimiento:
    """Monitor avanzado de rendimiento del sistema"""
    
    def __init__(self, base_url: str = "https://pagos-f2qf.onrender.com"):
        self.base_url = base_url
        self.metricas_historicas = deque(maxlen=1000)  # Mantener últimas 1000 métricas
        self.endpoints_monitoreo = [
            {"url": "/api/v1/auth/login", "metodo": "POST", "peso": 1.0, "critico": True},
            {"url": "/api/v1/clientes/ping", "metodo": "GET", "peso": 0.8, "critico": True},
            {"url": "/api/v1/validadores/ping", "metodo": "GET", "peso": 0.8, "critico": True},
            {"url": "/api/v1/usuarios/", "metodo": "GET", "peso": 0.6, "critico": False},
            {"url": "/api/v1/clientes/count", "metodo": "GET", "peso": 0.4, "critico": False},
            {"url": "/api/v1/clientes/opciones-configuracion", "metodo": "GET", "peso": 0.3, "critico": False},
            {"url": "/api/v1/ia/scoring-crediticio", "metodo": "GET", "peso": 0.7, "critico": False},
            {"url": "/api/v1/validadores/verificacion-validadores", "metodo": "GET", "peso": 0.5, "critico": False}
        ]
        
        # Umbrales de rendimiento
        self.umbrales = {
            "tiempo_respuesta_excelente": 1.0,  # < 1s
            "tiempo_respuesta_bueno": 3.0,      # < 3s
            "tiempo_respuesta_aceptable": 5.0,   # < 5s
            "tasa_error_critica": 0.05,         # > 5%
            "tasa_error_alta": 0.02,            # > 2%
            "throughput_minimo": 10.0           # > 10 RPS
        }
    
    def medir_rendimiento_endpoint(self, endpoint: Dict) -> MetricaRendimiento:
        """Mide el rendimiento de un endpoint específico"""
        url = f"{self.base_url}{endpoint['url']}"
        
        # Preparar datos para POST
        datos_post = None
        headers = {"Content-Type": "application/json"}
        
        if endpoint['metodo'] == "POST" and endpoint['url'] == "/api/v1/auth/login":
            datos_post = {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**"
            }
        
        try:
            inicio = time.time()
            
            # Realizar request
            if endpoint['metodo'] == "GET":
                response = requests.get(url, timeout=30)
            elif endpoint['metodo'] == "POST":
                response = requests.post(url, json=datos_post, headers=headers, timeout=30)
            
            tiempo_respuesta = time.time() - inicio
            tamaño_respuesta = len(response.content)
            
            return MetricaRendimiento(
                timestamp=datetime.now().isoformat(),
                endpoint=endpoint['url'],
                tiempo_respuesta=tiempo_respuesta,
                codigo_respuesta=response.status_code,
                tamaño_respuesta=tamaño_respuesta
            )
            
        except Exception as e:
            logger.warning(f"Error midiendo {endpoint['url']}: {e}")
            return MetricaRendimiento(
                timestamp=datetime.now().isoformat(),
                endpoint=endpoint['url'],
                tiempo_respuesta=30.0,  # Timeout
                codigo_respuesta=0,
                tamaño_respuesta=0
            )
    
    def ejecutar_prueba_carga(self, duracion_segundos: int = 60, requests_por_segundo: int = 5) -> List[MetricaRendimiento]:
        """Ejecuta una prueba de carga controlada"""
        logger.info(f"🔥 INICIANDO PRUEBA DE CARGA")
        logger.info(f"⏱️ Duración: {duracion_segundos}s")
        logger.info(f"📊 Requests por segundo: {requests_por_segundo}")
        logger.info("-" * 50)
        
        metricas = []
        inicio_prueba = time.time()
        request_count = 0
        
        while time.time() - inicio_prueba < duracion_segundos:
            # Seleccionar endpoint aleatorio basado en peso
            endpoint = self._seleccionar_endpoint_ponderado()
            
            # Medir rendimiento
            metrica = self.medir_rendimiento_endpoint(endpoint)
            metricas.append(metrica)
            self.metricas_historicas.append(metrica)
            
            request_count += 1
            
            # Log progreso cada 10 requests
            if request_count % 10 == 0:
                tiempo_transcurrido = time.time() - inicio_prueba
                rps_actual = request_count / tiempo_transcurrido
                logger.info(f"📈 Progreso: {request_count} requests, RPS actual: {rps_actual:.1f}")
            
            # Controlar rate limiting
            time.sleep(1.0 / requests_por_segundo)
        
        logger.info(f"✅ Prueba de carga completada: {request_count} requests en {duracion_segundos}s")
        return metricas
    
    def _seleccionar_endpoint_ponderado(self) -> Dict:
        """Selecciona un endpoint basado en pesos"""
        import random
        
        # Crear lista ponderada
        endpoints_ponderados = []
        for endpoint in self.endpoints_monitoreo:
            peso = int(endpoint['peso'] * 10)  # Convertir a entero
            endpoints_ponderados.extend([endpoint] * peso)
        
        return random.choice(endpoints_ponderados)
    
    def calcular_metricas_avanzadas(self, metricas: List[MetricaRendimiento]) -> ResumenMetricas:
        """Calcula métricas avanzadas de rendimiento"""
        if not metricas:
            return ResumenMetricas(
                periodo="N/A",
                total_requests=0,
                requests_exitosos=0,
                requests_fallidos=0,
                tiempo_promedio=0,
                tiempo_mediana=0,
                tiempo_p95=0,
                tiempo_p99=0,
                throughput_rps=0,
                tasa_error=0,
                endpoints_mas_lentos=[],
                tendencia_rendimiento="N/A"
            )
        
        # Métricas básicas
        total_requests = len(metricas)
        requests_exitosos = sum(1 for m in metricas if m.codigo_respuesta in [200, 201])
        requests_fallidos = total_requests - requests_exitosos
        
        # Tiempos de respuesta
        tiempos = [m.tiempo_respuesta for m in metricas]
        tiempo_promedio = statistics.mean(tiempos)
        tiempo_mediana = statistics.median(tiempos)
        
        # Percentiles
        tiempos_ordenados = sorted(tiempos)
        p95_index = int(len(tiempos_ordenados) * 0.95)
        p99_index = int(len(tiempos_ordenados) * 0.99)
        tiempo_p95 = tiempos_ordenados[p95_index] if p95_index < len(tiempos_ordenados) else tiempos_ordenados[-1]
        tiempo_p99 = tiempos_ordenados[p99_index] if p99_index < len(tiempos_ordenados) else tiempos_ordenados[-1]
        
        # Throughput
        if metricas:
            tiempo_total = (datetime.fromisoformat(metricas[-1].timestamp) - 
                          datetime.fromisoformat(metricas[0].timestamp)).total_seconds()
            throughput_rps = total_requests / tiempo_total if tiempo_total > 0 else 0
        else:
            throughput_rps = 0
        
        # Tasa de error
        tasa_error = requests_fallidos / total_requests if total_requests > 0 else 0
        
        # Endpoints más lentos
        endpoints_lentos = self._calcular_endpoints_mas_lentos(metricas)
        
        # Tendencia de rendimiento
        tendencia = self._calcular_tendencia_rendimiento(metricas)
        
        return ResumenMetricas(
            periodo=f"{len(metricas)} requests",
            total_requests=total_requests,
            requests_exitosos=requests_exitosos,
            requests_fallidos=requests_fallidos,
            tiempo_promedio=round(tiempo_promedio, 3),
            tiempo_mediana=round(tiempo_mediana, 3),
            tiempo_p95=round(tiempo_p95, 3),
            tiempo_p99=round(tiempo_p99, 3),
            throughput_rps=round(throughput_rps, 2),
            tasa_error=round(tasa_error, 3),
            endpoints_mas_lentos=endpoints_lentos,
            tendencia_rendimiento=tendencia
        )
    
    def _calcular_endpoints_mas_lentos(self, metricas: List[MetricaRendimiento]) -> List[Dict]:
        """Calcula los endpoints más lentos"""
        endpoint_tiempos = {}
        
        for metrica in metricas:
            if metrica.endpoint not in endpoint_tiempos:
                endpoint_tiempos[metrica.endpoint] = []
            endpoint_tiempos[metrica.endpoint].append(metrica.tiempo_respuesta)
        
        # Calcular promedio por endpoint
        endpoints_promedio = []
        for endpoint, tiempos in endpoint_tiempos.items():
            promedio = statistics.mean(tiempos)
            endpoints_promedio.append({
                "endpoint": endpoint,
                "tiempo_promedio": round(promedio, 3),
                "total_requests": len(tiempos)
            })
        
        # Ordenar por tiempo promedio (más lento primero)
        endpoints_promedio.sort(key=lambda x: x["tiempo_promedio"], reverse=True)
        
        return endpoints_promedio[:5]  # Top 5 más lentos
    
    def _calcular_tendencia_rendimiento(self, metricas: List[MetricaRendimiento]) -> str:
        """Calcula la tendencia de rendimiento"""
        if len(metricas) < 10:
            return "Datos insuficientes"
        
        # Dividir en dos mitades
        mitad = len(metricas) // 2
        primera_mitad = metricas[:mitad]
        segunda_mitad = metricas[mitad:]
        
        # Calcular promedio de cada mitad
        prom_primera = statistics.mean([m.tiempo_respuesta for m in primera_mitad])
        prom_segunda = statistics.mean([m.tiempo_respuesta for m in segunda_mitad])
        
        # Determinar tendencia
        diferencia_porcentual = ((prom_segunda - prom_primera) / prom_primera) * 100
        
        if diferencia_porcentual > 10:
            return "📈 Degradación significativa"
        elif diferencia_porcentual > 5:
            return "📊 Degradación leve"
        elif diferencia_porcentual < -10:
            return "📉 Mejora significativa"
        elif diferencia_porcentual < -5:
            return "📊 Mejora leve"
        else:
            return "➡️ Estable"
    
    def evaluar_salud_sistema(self, resumen: ResumenMetricas) -> Dict:
        """Evalúa la salud general del sistema"""
        logger.info("🏥 EVALUACIÓN DE SALUD DEL SISTEMA")
        logger.info("-" * 40)
        
        salud = {
            "puntuacion_general": 0,
            "componentes": {},
            "alertas": [],
            "recomendaciones": []
        }
        
        # Evaluar tiempo de respuesta
        if resumen.tiempo_promedio <= self.umbrales["tiempo_respuesta_excelente"]:
            salud["componentes"]["tiempo_respuesta"] = {"estado": "🟢 Excelente", "puntuacion": 25}
        elif resumen.tiempo_promedio <= self.umbrales["tiempo_respuesta_bueno"]:
            salud["componentes"]["tiempo_respuesta"] = {"estado": "🟡 Bueno", "puntuacion": 20}
        elif resumen.tiempo_promedio <= self.umbrales["tiempo_respuesta_aceptable"]:
            salud["componentes"]["tiempo_respuesta"] = {"estado": "🟠 Aceptable", "puntuacion": 15}
        else:
            salud["componentes"]["tiempo_respuesta"] = {"estado": "🔴 Crítico", "puntuacion": 5}
            salud["alertas"].append("Tiempo de respuesta crítico")
        
        # Evaluar tasa de error
        if resumen.tasa_error <= 0.01:  # < 1%
            salud["componentes"]["tasa_error"] = {"estado": "🟢 Excelente", "puntuacion": 25}
        elif resumen.tasa_error <= self.umbrales["tasa_error_alta"]:  # < 2%
            salud["componentes"]["tasa_error"] = {"estado": "🟡 Bueno", "puntuacion": 20}
        elif resumen.tasa_error <= self.umbrales["tasa_error_critica"]:  # < 5%
            salud["componentes"]["tasa_error"] = {"estado": "🟠 Aceptable", "puntuacion": 15}
        else:
            salud["componentes"]["tasa_error"] = {"estado": "🔴 Crítico", "puntuacion": 5}
            salud["alertas"].append("Tasa de error crítica")
        
        # Evaluar throughput
        if resumen.throughput_rps >= 50:
            salud["componentes"]["throughput"] = {"estado": "🟢 Excelente", "puntuacion": 25}
        elif resumen.throughput_rps >= 20:
            salud["componentes"]["throughput"] = {"estado": "🟡 Bueno", "puntuacion": 20}
        elif resumen.throughput_rps >= self.umbrales["throughput_minimo"]:
            salud["componentes"]["throughput"] = {"estado": "🟠 Aceptable", "puntuacion": 15}
        else:
            salud["componentes"]["throughput"] = {"estado": "🔴 Crítico", "puntuacion": 5}
            salud["alertas"].append("Throughput insuficiente")
        
        # Evaluar estabilidad (P95 vs promedio)
        if resumen.tiempo_p95 > 0:
            ratio_p95_promedio = resumen.tiempo_p95 / resumen.tiempo_promedio
            if ratio_p95_promedio <= 2.0:
                salud["componentes"]["estabilidad"] = {"estado": "🟢 Excelente", "puntuacion": 25}
            elif ratio_p95_promedio <= 3.0:
                salud["componentes"]["estabilidad"] = {"estado": "🟡 Bueno", "puntuacion": 20}
            elif ratio_p95_promedio <= 5.0:
                salud["componentes"]["estabilidad"] = {"estado": "🟠 Aceptable", "puntuacion": 15}
            else:
                salud["componentes"]["estabilidad"] = {"estado": "🔴 Crítico", "puntuacion": 5}
                salud["alertas"].append("Alta variabilidad en tiempos de respuesta")
        
        # Calcular puntuación general
        salud["puntuacion_general"] = sum(comp["puntuacion"] for comp in salud["componentes"].values())
        
        # Generar recomendaciones
        salud["recomendaciones"] = self._generar_recomendaciones_rendimiento(resumen, salud)
        
        # Log de salud
        logger.info(f"📊 Puntuación general: {salud['puntuacion_general']}/100")
        for componente, info in salud["componentes"].items():
            logger.info(f"   {componente}: {info['estado']} ({info['puntuacion']}/25)")
        
        if salud["alertas"]:
            logger.warning(f"⚠️ Alertas: {', '.join(salud['alertas'])}")
        
        return salud
    
    def _generar_recomendaciones_rendimiento(self, resumen: ResumenMetricas, salud: Dict) -> List[str]:
        """Genera recomendaciones basadas en el rendimiento"""
        recomendaciones = []
        
        # Recomendaciones por tiempo de respuesta
        if resumen.tiempo_promedio > self.umbrales["tiempo_respuesta_aceptable"]:
            recomendaciones.append("🐌 Optimizar tiempos de respuesta - considerar cache o CDN")
        
        # Recomendaciones por tasa de error
        if resumen.tasa_error > self.umbrales["tasa_error_critica"]:
            recomendaciones.append("🔧 Revisar logs de error y mejorar manejo de excepciones")
        
        # Recomendaciones por throughput
        if resumen.throughput_rps < self.umbrales["throughput_minimo"]:
            recomendaciones.append("📈 Escalar recursos o optimizar consultas de base de datos")
        
        # Recomendaciones por endpoints lentos
        if resumen.endpoints_mas_lentos:
            endpoint_mas_lento = resumen.endpoints_mas_lentos[0]
            if endpoint_mas_lento["tiempo_promedio"] > 5:
                recomendaciones.append(f"🎯 Optimizar endpoint más lento: {endpoint_mas_lento['endpoint']}")
        
        # Recomendaciones por tendencia
        if resumen.tendencia_rendimiento.startswith("📈"):
            recomendaciones.append("📊 Monitorear degradación de rendimiento - posible problema de recursos")
        
        if not recomendaciones:
            recomendaciones.append("✅ Rendimiento óptimo - mantener monitoreo continuo")
        
        return recomendaciones
    
    def ejecutar_analisis_completo_rendimiento(self, duracion_prueba: int = 60) -> Dict:
        """Ejecuta un análisis completo de rendimiento"""
        logger.info("🚀 INICIANDO ANÁLISIS COMPLETO DE RENDIMIENTO")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"⏱️ Duración de prueba: {duracion_prueba}s")
        logger.info("=" * 60)
        
        # Ejecutar prueba de carga
        metricas = self.ejecutar_prueba_carga(duracion_prueba)
        
        # Calcular métricas avanzadas
        resumen = self.calcular_metricas_avanzadas(metricas)
        
        # Evaluar salud del sistema
        salud = self.evaluar_salud_sistema(resumen)
        
        # Generar reporte completo
        reporte = {
            "fecha_analisis": datetime.now().isoformat(),
            "configuracion_prueba": {
                "duracion_segundos": duracion_prueba,
                "endpoints_monitoreados": len(self.endpoints_monitoreo),
                "umbrales_configurados": self.umbrales
            },
            "metricas_rendimiento": asdict(resumen),
            "evaluacion_salud": salud,
            "metricas_detalladas": [asdict(m) for m in metricas[-50:]]  # Últimas 50 métricas
        }
        
        logger.info("")
        logger.info("🎉 ANÁLISIS DE RENDIMIENTO COMPLETADO")
        logger.info("=" * 60)
        
        return reporte

def main():
    """Función principal para ejecutar el análisis de rendimiento"""
    monitor = MonitorRendimiento()
    reporte = monitor.ejecutar_analisis_completo_rendimiento(duracion_prueba=60)
    
    # Guardar reporte
    with open('reporte_metricas_rendimiento.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_metricas_rendimiento.json")
    
    return reporte

if __name__ == "__main__":
    main()
