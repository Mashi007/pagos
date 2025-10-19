"""
Script de Prueba del Sistema de Login
Pruebas completas mientras el deploy sucede
"""
import requests
import json
import time
from datetime import datetime
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pruebas_login.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PruebasLogin:
    """Clase para realizar pruebas del sistema de login"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.resultados = {
            "fecha_pruebas": datetime.now().isoformat(),
            "pruebas_realizadas": [],
            "pruebas_exitosas": 0,
            "pruebas_fallidas": 0,
            "problemas_encontrados": []
        }
    
    def probar_health_check(self) -> Dict:
        """Prueba el endpoint de health check"""
        logger.info("🏥 PROBANDO HEALTH CHECK")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Health Check",
            "endpoint": f"{self.base_url}/api/v1/health",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/health", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                prueba["exito"] = True
                logger.info(f"✅ Health check exitoso - {prueba['tiempo_respuesta']}s")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Health check falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en health check: {e}")
        
        return prueba
    
    def probar_login_admin(self) -> Dict:
        """Prueba el login de administrador"""
        logger.info("👑 PROBANDO LOGIN ADMIN")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Login Admin",
            "endpoint": f"{self.base_url}/api/v1/auth/login",
            "metodo": "POST",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None,
            "token_obtenido": False
        }
        
        datos_login = {
            "email": "admin@pagos.com",
            "password": "admin123"
        }
        
        try:
            inicio = time.time()
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=datos_login,
                timeout=10
            )
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    prueba["exito"] = True
                    prueba["token_obtenido"] = True
                    self.session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
                    logger.info(f"✅ Login admin exitoso - {prueba['tiempo_respuesta']}s")
                else:
                    prueba["error"] = "Token no encontrado en respuesta"
                    logger.warning("⚠️ Login admin falló - Token no encontrado")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Login admin falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en login admin: {e}")
        
        return prueba
    
    def probar_endpoint_protegido(self) -> Dict:
        """Prueba un endpoint protegido"""
        logger.info("🔒 PROBANDO ENDPOINT PROTEGIDO")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Endpoint Protegido",
            "endpoint": f"{self.base_url}/api/v1/auth/me",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/auth/me", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                prueba["exito"] = True
                logger.info(f"✅ Endpoint protegido exitoso - {prueba['tiempo_respuesta']}s")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Endpoint protegido falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en endpoint protegido: {e}")
        
        return prueba
    
    def probar_refresh_token(self) -> Dict:
        """Prueba el refresh token"""
        logger.info("🔄 PROBANDO REFRESH TOKEN")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Refresh Token",
            "endpoint": f"{self.base_url}/api/v1/auth/refresh",
            "metodo": "POST",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None
        }
        
        # Necesitamos un refresh token válido
        datos_refresh = {
            "refresh_token": "dummy_refresh_token"  # Esto probablemente fallará
        }
        
        try:
            inicio = time.time()
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json=datos_refresh,
                timeout=10
            )
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            # Esperamos que falle con refresh token dummy
            if response.status_code == 401:
                prueba["exito"] = True  # Fallo esperado
                logger.info(f"✅ Refresh token falló como esperado - {prueba['tiempo_respuesta']}s")
            else:
                prueba["error"] = f"Status inesperado {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Refresh token status inesperado - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en refresh token: {e}")
        
        return prueba
    
    def ejecutar_pruebas_completas(self) -> Dict:
        """Ejecuta todas las pruebas del sistema de login"""
        logger.info("🚀 INICIANDO PRUEBAS COMPLETAS DEL SISTEMA DE LOGIN")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🌐 URL Base: {self.base_url}")
        logger.info("=" * 60)
        
        # Ejecutar pruebas
        pruebas = [
            self.probar_health_check(),
            self.probar_login_admin(),
            self.probar_endpoint_protegido(),
            self.probar_refresh_token()
        ]
        
        # Procesar resultados
        for prueba in pruebas:
            self.resultados["pruebas_realizadas"].append(prueba)
            
            if prueba["exito"]:
                self.resultados["pruebas_exitosas"] += 1
            else:
                self.resultados["pruebas_fallidas"] += 1
                if prueba["error"]:
                    self.resultados["problemas_encontrados"].append({
                        "prueba": prueba["nombre"],
                        "error": prueba["error"]
                    })
        
        # Mostrar resumen
        logger.info("")
        logger.info("📊 RESUMEN DE PRUEBAS")
        logger.info("-" * 40)
        logger.info(f"✅ Pruebas exitosas: {self.resultados['pruebas_exitosas']}")
        logger.info(f"❌ Pruebas fallidas: {self.resultados['pruebas_fallidas']}")
        logger.info(f"📄 Total pruebas: {len(pruebas)}")
        logger.info(f"🎯 Tasa de éxito: {(self.resultados['pruebas_exitosas']/len(pruebas)*100):.1f}%")
        
        if self.resultados["problemas_encontrados"]:
            logger.info("")
            logger.info("⚠️ PROBLEMAS ENCONTRADOS:")
            for problema in self.resultados["problemas_encontrados"]:
                logger.info(f"   - {problema['prueba']}: {problema['error']}")
        
        logger.info("")
        logger.info("🎉 PRUEBAS COMPLETAS DEL SISTEMA DE LOGIN FINALIZADAS")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar las pruebas"""
    logger.info("🧪 INICIANDO PRUEBAS DEL SISTEMA DE LOGIN")
    logger.info("⚠️ NOTA: Estas pruebas requieren que el servidor esté ejecutándose")
    
    # Intentar con localhost primero
    pruebas_local = PruebasLogin("http://localhost:8000")
    resultados_local = pruebas_local.ejecutar_pruebas_completas()
    
    # Guardar reporte
    with open('reporte_pruebas_login.json', 'w', encoding='utf-8') as f:
        json.dump(resultados_local, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_pruebas_login.json")
    
    return resultados_local

if __name__ == "__main__":
    main()
