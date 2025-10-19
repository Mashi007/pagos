"""
Sistema de Verificación con Retry Automático
Extensión del tercer enfoque con reintentos inteligentes
"""
import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ResultadoEndpoint:
    """Resultado de la verificación de un endpoint"""
    url: str
    descripcion: str
    exitoso: bool
    codigo_respuesta: int
    tiempo_respuesta: float
    intentos_realizados: int
    error: Optional[str] = None

class VerificadorConRetry:
    """Verificador con sistema de retry automático"""
    
    def __init__(self, base_url: str = "https://pagos-f2qf.onrender.com"):
        self.base_url = base_url
        self.max_intentos = 3
        self.delay_entre_intentos = 2
        self.timeout_por_intento = 15
        
        self.endpoints_criticos = [
            {"url": "/api/v1/auth/login", "metodo": "POST", "descripcion": "Autenticación", "critico": True},
            {"url": "/api/v1/clientes/ping", "metodo": "GET", "descripcion": "Clientes", "critico": True},
            {"url": "/api/v1/validadores/ping", "metodo": "GET", "descripcion": "Validadores", "critico": True},
            {"url": "/api/v1/usuarios/", "metodo": "GET", "descripcion": "Usuarios", "critico": False},
            {"url": "/api/v1/clientes/count", "metodo": "GET", "descripcion": "Conteo Clientes", "critico": False},
            {"url": "/api/v1/clientes/opciones-configuracion", "metodo": "GET", "descripcion": "Configuración", "critico": False},
            {"url": "/api/v1/ia/scoring-crediticio", "metodo": "GET", "descripcion": "IA Scoring", "critico": False},
            {"url": "/api/v1/validadores/verificacion-validadores", "metodo": "GET", "descripcion": "Verificación Validadores", "critico": False}
        ]
    
    def verificar_endpoint_con_retry(self, endpoint: Dict) -> ResultadoEndpoint:
        """Verifica un endpoint con sistema de retry automático"""
        url = f"{self.base_url}{endpoint['url']}"
        descripcion = endpoint['descripcion']
        metodo = endpoint['metodo']
        
        logger.info(f"🔍 Verificando: {descripcion}")
        
        ultimo_error = None
        tiempo_total = 0
        
        for intento in range(1, self.max_intentos + 1):
            try:
                logger.info(f"   Intento {intento}/{self.max_intentos}")
                
                inicio = time.time()
                
                # Preparar datos para POST si es necesario
                datos_post = None
                headers = {"Content-Type": "application/json"}
                
                if metodo == "POST" and endpoint['url'] == "/api/v1/auth/login":
                    datos_post = {
                        "email": "itmaster@rapicreditca.com",
                        "password": "R@pi_2025**"
                    }
                
                # Realizar request
                if metodo == "GET":
                    response = requests.get(url, timeout=self.timeout_por_intento)
                elif metodo == "POST":
                    response = requests.post(url, json=datos_post, headers=headers, timeout=self.timeout_por_intento)
                
                tiempo_respuesta = time.time() - inicio
                tiempo_total += tiempo_respuesta
                
                # Verificar si es exitoso
                if response.status_code in [200, 201]:
                    logger.info(f"   ✅ Éxito en intento {intento} - {response.status_code} ({tiempo_respuesta:.2f}s)")
                    return ResultadoEndpoint(
                        url=endpoint['url'],
                        descripcion=descripcion,
                        exitoso=True,
                        codigo_respuesta=response.status_code,
                        tiempo_respuesta=tiempo_respuesta,
                        intentos_realizados=intento
                    )
                else:
                    logger.warning(f"   ⚠️ Intento {intento} falló - {response.status_code}")
                    ultimo_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    
            except requests.exceptions.Timeout:
                logger.warning(f"   ⏰ Timeout en intento {intento}")
                ultimo_error = "Timeout"
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"   🔌 Error de conexión en intento {intento}")
                ultimo_error = "Connection Error"
                
            except Exception as e:
                logger.warning(f"   ❌ Error en intento {intento}: {e}")
                ultimo_error = str(e)
            
            # Esperar antes del siguiente intento (excepto en el último)
            if intento < self.max_intentos:
                logger.info(f"   ⏳ Esperando {self.delay_entre_intentos}s antes del siguiente intento...")
                time.sleep(self.delay_entre_intentos)
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"   ❌ Todos los intentos fallaron para {descripcion}")
        return ResultadoEndpoint(
            url=endpoint['url'],
            descripcion=descripcion,
            exitoso=False,
            codigo_respuesta=0,
            tiempo_respuesta=tiempo_total,
            intentos_realizados=self.max_intentos,
            error=ultimo_error
        )
    
    def verificar_todos_endpoints(self) -> List[ResultadoEndpoint]:
        """Verifica todos los endpoints con retry automático"""
        logger.info("🔗 VERIFICACIÓN COMPLETA CON RETRY AUTOMÁTICO")
        logger.info("=" * 60)
        
        resultados = []
        
        for endpoint in self.endpoints_criticos:
            resultado = self.verificar_endpoint_con_retry(endpoint)
            resultados.append(resultado)
            
            # Pequeña pausa entre endpoints
            time.sleep(0.5)
        
        return resultados
    
    def analizar_resultados(self, resultados: List[ResultadoEndpoint]) -> Dict:
        """Analiza los resultados y genera estadísticas"""
        logger.info("📊 ANÁLISIS DE RESULTADOS")
        logger.info("-" * 40)
        
        total_endpoints = len(resultados)
        exitosos = sum(1 for r in resultados if r.exitoso)
        fallidos = total_endpoints - exitosos
        
        # Separar por criticidad
        criticos_exitosos = sum(1 for r in resultados if r.exitoso and self._es_endpoint_critico(r.url))
        criticos_total = sum(1 for r in resultados if self._es_endpoint_critico(r.url))
        
        # Calcular tiempos
        tiempos_exitosos = [r.tiempo_respuesta for r in resultados if r.exitoso]
        tiempo_promedio = sum(tiempos_exitosos) / len(tiempos_exitosos) if tiempos_exitosos else 0
        
        # Calcular intentos promedio
        intentos_promedio = sum(r.intentos_realizados for r in resultados) / len(resultados)
        
        estadisticas = {
            "resumen": {
                "total_endpoints": total_endpoints,
                "exitosos": exitosos,
                "fallidos": fallidos,
                "porcentaje_exito": round((exitosos / total_endpoints) * 100, 1),
                "criticos_exitosos": criticos_exitosos,
                "criticos_total": criticos_total,
                "porcentaje_criticos": round((criticos_exitosos / criticos_total) * 100, 1) if criticos_total > 0 else 0
            },
            "rendimiento": {
                "tiempo_promedio": round(tiempo_promedio, 2),
                "tiempo_maximo": round(max(tiempos_exitosos), 2) if tiempos_exitosos else 0,
                "tiempo_minimo": round(min(tiempos_exitosos), 2) if tiempos_exitosos else 0,
                "intentos_promedio": round(intentos_promedio, 1)
            },
            "estado_general": self._determinar_estado_general(exitosos, total_endpoints, criticos_exitosos, criticos_total)
        }
        
        # Log de estadísticas
        logger.info(f"📈 Total endpoints: {total_endpoints}")
        logger.info(f"✅ Exitosos: {exitosos} ({estadisticas['resumen']['porcentaje_exito']}%)")
        logger.info(f"❌ Fallidos: {fallidos}")
        logger.info(f"🔴 Críticos exitosos: {criticos_exitosos}/{criticos_total} ({estadisticas['resumen']['porcentaje_criticos']}%)")
        logger.info(f"⏱️ Tiempo promedio: {estadisticas['rendimiento']['tiempo_promedio']}s")
        logger.info(f"🔄 Intentos promedio: {estadisticas['rendimiento']['intentos_promedio']}")
        logger.info(f"🎯 Estado general: {estadisticas['estado_general']}")
        
        return estadisticas
    
    def _es_endpoint_critico(self, url: str) -> bool:
        """Determina si un endpoint es crítico"""
        endpoint_critico = next((e for e in self.endpoints_criticos if e['url'] == url), None)
        return endpoint_critico and endpoint_critico.get('critico', False)
    
    def _determinar_estado_general(self, exitosos: int, total: int, criticos_exitosos: int, criticos_total: int) -> str:
        """Determina el estado general del sistema"""
        porcentaje_exito = (exitosos / total) * 100
        porcentaje_criticos = (criticos_exitosos / criticos_total) * 100 if criticos_total > 0 else 100
        
        if porcentaje_exito >= 90 and porcentaje_criticos >= 100:
            return "🟢 EXCELENTE"
        elif porcentaje_exito >= 80 and porcentaje_criticos >= 100:
            return "🟡 BUENO"
        elif porcentaje_criticos >= 80:
            return "🟠 ACEPTABLE"
        else:
            return "🔴 CRÍTICO"
    
    def generar_reporte_detallado(self, resultados: List[ResultadoEndpoint], estadisticas: Dict) -> Dict:
        """Genera un reporte detallado de la verificación"""
        logger.info("📋 GENERANDO REPORTE DETALLADO")
        logger.info("-" * 40)
        
        reporte = {
            "fecha_verificacion": datetime.now().isoformat(),
            "configuracion": {
                "max_intentos": self.max_intentos,
                "delay_entre_intentos": self.delay_entre_intentos,
                "timeout_por_intento": self.timeout_por_intento
            },
            "estadisticas": estadisticas,
            "resultados_detallados": [
                {
                    "url": r.url,
                    "descripcion": r.descripcion,
                    "exitoso": r.exitoso,
                    "codigo_respuesta": r.codigo_respuesta,
                    "tiempo_respuesta": round(r.tiempo_respuesta, 2),
                    "intentos_realizados": r.intentos_realizados,
                    "error": r.error,
                    "critico": self._es_endpoint_critico(r.url)
                }
                for r in resultados
            ],
            "recomendaciones": self._generar_recomendaciones_avanzadas(resultados, estadisticas)
        }
        
        return reporte
    
    def _generar_recomendaciones_avanzadas(self, resultados: List[ResultadoEndpoint], estadisticas: Dict) -> List[str]:
        """Genera recomendaciones avanzadas basadas en los resultados"""
        recomendaciones = []
        
        # Analizar endpoints fallidos
        fallidos = [r for r in resultados if not r.exitoso]
        criticos_fallidos = [r for r in fallidos if self._es_endpoint_critico(r.url)]
        
        if criticos_fallidos:
            recomendaciones.append(f"🔴 URGENTE: {len(criticos_fallidos)} endpoint(s) crítico(s) fallando")
            for endpoint in criticos_fallidos:
                recomendaciones.append(f"   - {endpoint.descripcion}: {endpoint.error}")
        
        # Analizar tiempos de respuesta
        tiempos_lentos = [r for r in resultados if r.exitoso and r.tiempo_respuesta > 5]
        if tiempos_lentos:
            recomendaciones.append(f"🐌 {len(tiempos_lentos)} endpoint(s) con respuesta lenta (>5s)")
        
        # Analizar múltiples intentos
        muchos_intentos = [r for r in resultados if r.intentos_realizados >= self.max_intentos]
        if muchos_intentos:
            recomendaciones.append(f"🔄 {len(muchos_intentos)} endpoint(s) requirieron máximo de intentos")
        
        # Analizar estado general
        if estadisticas['estado_general'] == "🔴 CRÍTICO":
            recomendaciones.append("🚨 Estado crítico - revisión inmediata requerida")
        elif estadisticas['estado_general'] == "🟠 ACEPTABLE":
            recomendaciones.append("⚠️ Estado aceptable - monitoreo continuo recomendado")
        
        if not recomendaciones:
            recomendaciones.append("✅ Sistema funcionando correctamente - sin acciones requeridas")
        
        return recomendaciones
    
    def ejecutar_verificacion_completa_con_retry(self) -> Dict:
        """Ejecuta una verificación completa con retry automático"""
        logger.info("🚀 INICIANDO VERIFICACIÓN CON RETRY AUTOMÁTICO")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Configuración: {self.max_intentos} intentos, {self.delay_entre_intentos}s delay")
        logger.info("=" * 60)
        
        # Verificar todos los endpoints
        resultados = self.verificar_todos_endpoints()
        
        # Analizar resultados
        estadisticas = self.analizar_resultados(resultados)
        
        # Generar reporte
        reporte = self.generar_reporte_detallado(resultados, estadisticas)
        
        logger.info("")
        logger.info("🎉 VERIFICACIÓN CON RETRY COMPLETADA")
        logger.info("=" * 60)
        
        return reporte

def main():
    """Función principal para ejecutar la verificación con retry"""
    verificador = VerificadorConRetry()
    reporte = verificador.ejecutar_verificacion_completa_con_retry()
    
    # Guardar reporte
    with open('reporte_verificacion_con_retry.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_verificacion_con_retry.json")
    
    return reporte

if __name__ == "__main__":
    main()
