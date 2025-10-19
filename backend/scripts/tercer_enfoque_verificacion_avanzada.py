"""
Tercer Enfoque de Verificación Avanzada
Sistema de monitoreo continuo y verificación robusta
Basado en los logs exitosos del segundo enfoque
"""
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import schedule

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tercer_enfoque_verificacion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://pagos-f2qf.onrender.com"

class TercerEnfoqueVerificacion:
    """Sistema de verificación avanzada con monitoreo continuo"""
    
    def __init__(self):
        self.estado_sistema = {
            "servidor": False,
            "base_datos": False,
            "autenticacion": False,
            "endpoints_criticos": False,
            "ultima_verificacion": None,
            "metricas": {
                "tiempo_respuesta": [],
                "errores_consecutivos": 0,
                "verificaciones_exitosas": 0,
                "verificaciones_fallidas": 0
            }
        }
        self.endpoints_criticos = [
            {"url": "/api/v1/auth/login", "metodo": "POST", "descripcion": "Autenticación"},
            {"url": "/api/v1/clientes/ping", "metodo": "GET", "descripcion": "Clientes"},
            {"url": "/api/v1/validadores/ping", "metodo": "GET", "descripcion": "Validadores"},
            {"url": "/api/v1/usuarios/", "metodo": "GET", "descripcion": "Usuarios"},
            {"url": "/api/v1/clientes/count", "metodo": "GET", "descripcion": "Conteo Clientes"},
            {"url": "/api/v1/clientes/opciones-configuracion", "metodo": "GET", "descripcion": "Configuración"}
        ]
        
    def verificar_conectividad_basica(self) -> bool:
        """Verificación mejorada de conectividad básica"""
        logger.info("🌐 VERIFICACIÓN DE CONECTIVIDAD BÁSICA")
        logger.info("-" * 50)
        
        try:
            inicio = time.time()
            response = requests.get(f"{BASE_URL}/", timeout=15)
            tiempo_respuesta = time.time() - inicio
            
            self.estado_sistema["metricas"]["tiempo_respuesta"].append(tiempo_respuesta)
            
            if response.status_code == 200:
                logger.info(f"✅ Servidor respondiendo - Status: {response.status_code}")
                logger.info(f"⏱️ Tiempo de respuesta: {tiempo_respuesta:.2f}s")
                self.estado_sistema["servidor"] = True
                self.estado_sistema["metricas"]["errores_consecutivos"] = 0
                return True
            else:
                logger.warning(f"⚠️ Servidor con problemas - Status: {response.status_code}")
                self.estado_sistema["servidor"] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Error de conectividad: {e}")
            self.estado_sistema["servidor"] = False
            self.estado_sistema["metricas"]["errores_consecutivos"] += 1
            return False
    
    def verificar_autenticacion_robusta(self) -> bool:
        """Verificación robusta de autenticación con múltiples intentos"""
        logger.info("🔑 VERIFICACIÓN ROBUSTA DE AUTENTICACIÓN")
        logger.info("-" * 50)
        
        credenciales = [
            {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "descripcion": "Administrador Principal"
            }
        ]
        
        for credencial in credenciales:
            logger.info(f"🔐 Probando: {credencial['descripcion']}")
            
            try:
                inicio = time.time()
                response = requests.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    json={"email": credencial["email"], "password": credencial["password"]},
                    timeout=20
                )
                tiempo_respuesta = time.time() - inicio
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ LOGIN EXITOSO!")
                    logger.info(f"👤 Usuario: {data.get('user', {}).get('email', 'N/A')}")
                    logger.info(f"🎫 Token: {data.get('access_token', 'N/A')[:20]}...")
                    logger.info(f"⏱️ Tiempo: {tiempo_respuesta:.2f}s")
                    
                    self.estado_sistema["autenticacion"] = True
                    self.estado_sistema["metricas"]["verificaciones_exitosas"] += 1
                    return True
                    
                elif response.status_code == 503:
                    logger.error(f"❌ ERROR 503: Servicio no disponible")
                    logger.error(f"📄 Detalles: {response.text}")
                    
                elif response.status_code == 401:
                    logger.warning(f"⚠️ ERROR 401: Credenciales incorrectas")
                    
                else:
                    logger.error(f"❌ Status inesperado: {response.status_code}")
                    logger.error(f"📄 Respuesta: {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ Error en autenticación: {e}")
                
            # Esperar antes del siguiente intento
            time.sleep(2)
        
        self.estado_sistema["autenticacion"] = False
        self.estado_sistema["metricas"]["verificaciones_fallidas"] += 1
        return False
    
    def verificar_endpoints_criticos(self) -> bool:
        """Verificación exhaustiva de endpoints críticos"""
        logger.info("🔗 VERIFICACIÓN DE ENDPOINTS CRÍTICOS")
        logger.info("-" * 50)
        
        resultados = []
        
        for endpoint in self.endpoints_criticos:
            logger.info(f"🔍 Verificando: {endpoint['descripcion']}")
            
            try:
                inicio = time.time()
                
                if endpoint["metodo"] == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint['url']}", timeout=15)
                elif endpoint["metodo"] == "POST":
                    response = requests.post(f"{BASE_URL}{endpoint['url']}", timeout=15)
                
                tiempo_respuesta = time.time() - inicio
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ {endpoint['descripcion']}: OK ({response.status_code}) - {tiempo_respuesta:.2f}s")
                    resultados.append(True)
                else:
                    logger.warning(f"⚠️ {endpoint['descripcion']}: {response.status_code} - {tiempo_respuesta:.2f}s")
                    resultados.append(False)
                    
            except Exception as e:
                logger.error(f"❌ {endpoint['descripcion']}: Error - {e}")
                resultados.append(False)
            
            # Pequeña pausa entre verificaciones
            time.sleep(0.5)
        
        # Calcular porcentaje de éxito
        exitosos = sum(resultados)
        total = len(resultados)
        porcentaje = (exitosos / total) * 100
        
        logger.info(f"📊 Resultados: {exitosos}/{total} endpoints funcionando ({porcentaje:.1f}%)")
        
        self.estado_sistema["endpoints_criticos"] = porcentaje >= 80
        return self.estado_sistema["endpoints_criticos"]
    
    def calcular_metricas_rendimiento(self) -> Dict:
        """Calcula métricas de rendimiento del sistema"""
        metricas = self.estado_sistema["metricas"]
        
        if metricas["tiempo_respuesta"]:
            tiempo_promedio = sum(metricas["tiempo_respuesta"]) / len(metricas["tiempo_respuesta"])
            tiempo_maximo = max(metricas["tiempo_respuesta"])
            tiempo_minimo = min(metricas["tiempo_respuesta"])
        else:
            tiempo_promedio = tiempo_maximo = tiempo_minimo = 0
        
        total_verificaciones = metricas["verificaciones_exitosas"] + metricas["verificaciones_fallidas"]
        tasa_exito = (metricas["verificaciones_exitosas"] / total_verificaciones * 100) if total_verificaciones > 0 else 0
        
        return {
            "tiempo_respuesta_promedio": round(tiempo_promedio, 2),
            "tiempo_respuesta_maximo": round(tiempo_maximo, 2),
            "tiempo_respuesta_minimo": round(tiempo_minimo, 2),
            "tasa_exito": round(tasa_exito, 1),
            "errores_consecutivos": metricas["errores_consecutivos"],
            "total_verificaciones": total_verificaciones
        }
    
    def generar_reporte_completo(self) -> Dict:
        """Genera un reporte completo del estado del sistema"""
        logger.info("📊 GENERANDO REPORTE COMPLETO")
        logger.info("=" * 60)
        
        self.estado_sistema["ultima_verificacion"] = datetime.now().isoformat()
        metricas = self.calcular_metricas_rendimiento()
        
        reporte = {
            "fecha_verificacion": self.estado_sistema["ultima_verificacion"],
            "estado_general": "✅ OPERATIVO" if all([
                self.estado_sistema["servidor"],
                self.estado_sistema["autenticacion"],
                self.estado_sistema["endpoints_criticos"]
            ]) else "⚠️ PROBLEMAS DETECTADOS",
            
            "componentes": {
                "servidor": "✅ OK" if self.estado_sistema["servidor"] else "❌ PROBLEMA",
                "autenticacion": "✅ OK" if self.estado_sistema["autenticacion"] else "❌ PROBLEMA",
                "endpoints_criticos": "✅ OK" if self.estado_sistema["endpoints_criticos"] else "❌ PROBLEMA"
            },
            
            "metricas_rendimiento": metricas,
            
            "recomendaciones": self._generar_recomendaciones()
        }
        
        # Log del reporte
        logger.info(f"🎯 Estado General: {reporte['estado_general']}")
        logger.info(f"🌐 Servidor: {reporte['componentes']['servidor']}")
        logger.info(f"🔑 Autenticación: {reporte['componentes']['autenticacion']}")
        logger.info(f"🔗 Endpoints: {reporte['componentes']['endpoints_criticos']}")
        logger.info(f"⏱️ Tiempo promedio: {metricas['tiempo_respuesta_promedio']}s")
        logger.info(f"📈 Tasa de éxito: {metricas['tasa_exito']}%")
        
        return reporte
    
    def _generar_recomendaciones(self) -> List[str]:
        """Genera recomendaciones basadas en el estado actual"""
        recomendaciones = []
        
        if not self.estado_sistema["servidor"]:
            recomendaciones.append("🔧 Revisar conectividad del servidor")
        
        if not self.estado_sistema["autenticacion"]:
            recomendaciones.append("🔐 Verificar credenciales y configuración de autenticación")
        
        if not self.estado_sistema["endpoints_criticos"]:
            recomendaciones.append("🔗 Revisar endpoints críticos que están fallando")
        
        if self.estado_sistema["metricas"]["errores_consecutivos"] > 3:
            recomendaciones.append("⚠️ Múltiples errores consecutivos - revisar estabilidad del sistema")
        
        metricas = self.calcular_metricas_rendimiento()
        if metricas["tiempo_respuesta_promedio"] > 5:
            recomendaciones.append("🐌 Tiempo de respuesta lento - considerar optimización")
        
        if not recomendaciones:
            recomendaciones.append("✅ Sistema funcionando correctamente")
        
        return recomendaciones
    
    def ejecutar_verificacion_completa(self) -> Dict:
        """Ejecuta una verificación completa del sistema"""
        logger.info("🚀 INICIANDO TERCER ENFOQUE DE VERIFICACIÓN AVANZADA")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Verificación robusta con métricas de rendimiento")
        logger.info("=" * 60)
        
        # 1. Verificar conectividad básica
        logger.info("")
        conectividad_ok = self.verificar_conectividad_basica()
        
        if not conectividad_ok:
            logger.error("❌ Fallo en conectividad básica. Abortando verificación completa.")
            return self.generar_reporte_completo()
        
        # Esperar estabilización
        logger.info("⏳ Esperando 3 segundos para estabilización...")
        time.sleep(3)
        
        # 2. Verificar autenticación
        logger.info("")
        auth_ok = self.verificar_autenticacion_robusta()
        
        # 3. Verificar endpoints críticos
        logger.info("")
        endpoints_ok = self.verificar_endpoints_criticos()
        
        # 4. Generar reporte final
        logger.info("")
        reporte = self.generar_reporte_completo()
        
        logger.info("")
        logger.info("🎉 VERIFICACIÓN COMPLETA FINALIZADA")
        logger.info("=" * 60)
        
        return reporte

def main():
    """Función principal para ejecutar el tercer enfoque"""
    verificador = TercerEnfoqueVerificacion()
    reporte = verificador.ejecutar_verificacion_completa()
    
    # Guardar reporte en archivo
    with open('reporte_tercer_enfoque.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_tercer_enfoque.json")
    
    return reporte

if __name__ == "__main__":
    main()
