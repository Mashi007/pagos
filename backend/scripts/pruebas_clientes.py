"""
Script de Prueba del Módulo de Clientes
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
        logging.FileHandler('pruebas_clientes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PruebasClientes:
    """Clase para realizar pruebas del módulo de clientes"""
    
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
        self.token = None
    
    def autenticar_admin(self) -> bool:
        """Autentica como administrador para las pruebas"""
        logger.info("🔐 AUTENTICANDO ADMINISTRADOR")
        logger.info("-" * 30)
        
        datos_login = {
            "email": "admin@pagos.com",
            "password": "admin123"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=datos_login,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    logger.info("✅ Autenticación exitosa")
                    return True
                else:
                    logger.warning("⚠️ Token no encontrado en respuesta")
                    return False
            else:
                logger.warning(f"⚠️ Error de autenticación - Status {response.status_code}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False
    
    def probar_listar_clientes(self) -> Dict:
        """Prueba el endpoint de listar clientes"""
        logger.info("📋 PROBANDO LISTAR CLIENTES")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Listar Clientes",
            "endpoint": f"{self.base_url}/api/v1/clientes/",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None,
            "clientes_encontrados": 0
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/clientes/", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                data = response.json()
                if "clientes" in data:
                    prueba["clientes_encontrados"] = len(data["clientes"])
                    prueba["exito"] = True
                    logger.info(f"✅ Listar clientes exitoso - {prueba['tiempo_respuesta']}s - {prueba['clientes_encontrados']} clientes")
                else:
                    prueba["error"] = "Campo 'clientes' no encontrado en respuesta"
                    logger.warning("⚠️ Listar clientes falló - Campo 'clientes' no encontrado")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Listar clientes falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en listar clientes: {e}")
        
        return prueba
    
    def probar_crear_cliente(self) -> Dict:
        """Prueba el endpoint de crear cliente"""
        logger.info("➕ PROBANDO CREAR CLIENTE")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Crear Cliente",
            "endpoint": f"{self.base_url}/api/v1/clientes/crear",
            "metodo": "POST",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None,
            "cliente_creado": False
        }
        
        datos_cliente = {
            "cedula": "1234567890",
            "nombres": "Juan",
            "apellidos": "Pérez",
            "telefono": "0987654321",
            "email": "juan.perez@test.com",
            "direccion": "Calle Test 123",
            "fecha_nacimiento": "1990-01-01",
            "estado": "ACTIVO"
        }
        
        try:
            inicio = time.time()
            response = self.session.post(
                f"{self.base_url}/api/v1/clientes/crear",
                json=datos_cliente,
                timeout=10
            )
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 201:
                data = response.json()
                if "id" in data:
                    prueba["cliente_creado"] = True
                    prueba["exito"] = True
                    logger.info(f"✅ Crear cliente exitoso - {prueba['tiempo_respuesta']}s - ID: {data['id']}")
                else:
                    prueba["error"] = "Campo 'id' no encontrado en respuesta"
                    logger.warning("⚠️ Crear cliente falló - Campo 'id' no encontrado")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Crear cliente falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en crear cliente: {e}")
        
        return prueba
    
    def probar_obtener_cliente(self, cliente_id: int = 1) -> Dict:
        """Prueba el endpoint de obtener cliente"""
        logger.info(f"👤 PROBANDO OBTENER CLIENTE (ID: {cliente_id})")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Obtener Cliente",
            "endpoint": f"{self.base_url}/api/v1/clientes/{cliente_id}",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None,
            "cliente_encontrado": False
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/clientes/{cliente_id}", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data:
                    prueba["cliente_encontrado"] = True
                    prueba["exito"] = True
                    logger.info(f"✅ Obtener cliente exitoso - {prueba['tiempo_respuesta']}s - ID: {data['id']}")
                else:
                    prueba["error"] = "Campo 'id' no encontrado en respuesta"
                    logger.warning("⚠️ Obtener cliente falló - Campo 'id' no encontrado")
            elif response.status_code == 404:
                prueba["exito"] = True  # Cliente no encontrado es válido
                logger.info(f"✅ Cliente no encontrado (esperado) - {prueba['tiempo_respuesta']}s")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Obtener cliente falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en obtener cliente: {e}")
        
        return prueba
    
    def probar_contar_clientes(self) -> Dict:
        """Prueba el endpoint de contar clientes"""
        logger.info("🔢 PROBANDO CONTAR CLIENTES")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Contar Clientes",
            "endpoint": f"{self.base_url}/api/v1/clientes/count",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None,
            "total_clientes": 0
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/clientes/count", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                data = response.json()
                if "total" in data:
                    prueba["total_clientes"] = data["total"]
                    prueba["exito"] = True
                    logger.info(f"✅ Contar clientes exitoso - {prueba['tiempo_respuesta']}s - Total: {prueba['total_clientes']}")
                else:
                    prueba["error"] = "Campo 'total' no encontrado en respuesta"
                    logger.warning("⚠️ Contar clientes falló - Campo 'total' no encontrado")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Contar clientes falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en contar clientes: {e}")
        
        return prueba
    
    def probar_ping_clientes(self) -> Dict:
        """Prueba el endpoint de ping de clientes"""
        logger.info("🏓 PROBANDO PING CLIENTES")
        logger.info("-" * 30)
        
        prueba = {
            "nombre": "Ping Clientes",
            "endpoint": f"{self.base_url}/api/v1/clientes/ping",
            "metodo": "GET",
            "exito": False,
            "tiempo_respuesta": 0,
            "error": None
        }
        
        try:
            inicio = time.time()
            response = self.session.get(f"{self.base_url}/api/v1/clientes/ping", timeout=10)
            fin = time.time()
            
            prueba["tiempo_respuesta"] = round(fin - inicio, 2)
            
            if response.status_code == 200:
                prueba["exito"] = True
                logger.info(f"✅ Ping clientes exitoso - {prueba['tiempo_respuesta']}s")
            else:
                prueba["error"] = f"Status {response.status_code}: {response.text}"
                logger.warning(f"⚠️ Ping clientes falló - Status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            prueba["error"] = str(e)
            logger.error(f"❌ Error en ping clientes: {e}")
        
        return prueba
    
    def ejecutar_pruebas_completas(self) -> Dict:
        """Ejecuta todas las pruebas del módulo de clientes"""
        logger.info("🚀 INICIANDO PRUEBAS COMPLETAS DEL MÓDULO DE CLIENTES")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🌐 URL Base: {self.base_url}")
        logger.info("=" * 60)
        
        # Autenticar primero
        if not self.autenticar_admin():
            logger.error("❌ No se pudo autenticar - Saltando pruebas que requieren autenticación")
            return self.resultados
        
        # Ejecutar pruebas
        pruebas = [
            self.probar_ping_clientes(),
            self.probar_listar_clientes(),
            self.probar_contar_clientes(),
            self.probar_obtener_cliente(),
            self.probar_crear_cliente()
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
        logger.info("🎉 PRUEBAS COMPLETAS DEL MÓDULO DE CLIENTES FINALIZADAS")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar las pruebas"""
    logger.info("🧪 INICIANDO PRUEBAS DEL MÓDULO DE CLIENTES")
    logger.info("⚠️ NOTA: Estas pruebas requieren que el servidor esté ejecutándose")
    
    # Intentar con localhost primero
    pruebas_local = PruebasClientes("http://localhost:8000")
    resultados_local = pruebas_local.ejecutar_pruebas_completas()
    
    # Guardar reporte
    with open('reporte_pruebas_clientes.json', 'w', encoding='utf-8') as f:
        json.dump(resultados_local, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_pruebas_clientes.json")
    
    return resultados_local

if __name__ == "__main__":
    main()
