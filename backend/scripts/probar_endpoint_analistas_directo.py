# backend/scripts/probar_endpoint_analistas_directo.py
"""
PROBAR ENDPOINT ANALISTAS DIRECTO
Probar el endpoint analistas sin autenticación para verificar si funciona
"""
import os
import sys
import logging
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProbarEndpointAnalistasDirecto:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        
    def probar_endpoint_sin_auth(self) -> Dict[str, Any]:
        """Probar endpoint analistas sin autenticación"""
        logger.info("🔍 PROBANDO ENDPOINT ANALISTAS SIN AUTENTICACIÓN")
        logger.info("-" * 50)
        
        endpoints_sin_auth = [
            "/api/v1/analistas/test-no-auth",
            "/api/v1/analistas/test-simple",
            "/api/v1/analistas/list-no-auth"
        ]
        
        resultados = {}
        
        for endpoint in endpoints_sin_auth:
            try:
                logger.info(f"   🔍 Probando: {endpoint}")
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    timeout=15
                )
                
                logger.info(f"   📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"   ✅ ÉXITO: {endpoint}")
                    logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)[:200]}...")
                    resultados[endpoint] = {
                        "status": "success",
                        "status_code": response.status_code,
                        "data": data
                    }
                else:
                    logger.error(f"   ❌ FALLO: {endpoint}")
                    logger.error(f"   📊 Respuesta: {response.text[:200]}")
                    resultados[endpoint] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    }
                    
            except Exception as e:
                logger.error(f"   ❌ ERROR: {endpoint} - {e}")
                resultados[endpoint] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return resultados
    
    def probar_endpoint_principal(self) -> Dict[str, Any]:
        """Probar endpoint principal analistas"""
        logger.info("🔍 PROBANDO ENDPOINT PRINCIPAL ANALISTAS")
        logger.info("-" * 50)
        
        try:
            logger.info("   🔍 Probando: /api/v1/analistas/")
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/",
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ ÉXITO: Endpoint principal funcionando")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)[:200]}...")
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": data
                }
            else:
                logger.error(f"   ❌ FALLO: Endpoint principal")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Endpoint principal - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def ejecutar_prueba_directa(self):
        """Ejecutar prueba directa del endpoint analistas"""
        logger.info("🔍 PRUEBA DIRECTA DEL ENDPOINT ANALISTAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Probar endpoint analistas sin autenticación")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Probar endpoints sin autenticación
        logger.info("\n🔍 1. PROBANDO ENDPOINTS SIN AUTENTICACIÓN")
        logger.info("-" * 50)
        sin_auth = self.probar_endpoint_sin_auth()
        resultados["sin_auth"] = sin_auth
        
        # 2. Probar endpoint principal
        logger.info("\n🔍 2. PROBANDO ENDPOINT PRINCIPAL")
        logger.info("-" * 50)
        principal = self.probar_endpoint_principal()
        resultados["principal"] = principal
        
        # 3. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        endpoints_exitosos = 0
        endpoints_fallidos = 0
        
        for endpoint, resultado in sin_auth.items():
            if resultado["status"] == "success":
                endpoints_exitosos += 1
            else:
                endpoints_fallidos += 1
        
        if principal["status"] == "success":
            endpoints_exitosos += 1
        else:
            endpoints_fallidos += 1
        
        logger.info(f"📊 ENDPOINTS EXITOSOS: {endpoints_exitosos}")
        logger.info(f"📊 ENDPOINTS FALLIDOS: {endpoints_fallidos}")
        
        if endpoints_exitosos > 0:
            logger.info("✅ ALGUNOS ENDPOINTS FUNCIONAN")
            logger.info("   💡 El problema puede estar en la autenticación")
        else:
            logger.error("❌ TODOS LOS ENDPOINTS FALLAN")
            logger.error("   💡 El problema está en el router o la configuración")
        
        return resultados

def main():
    probador = ProbarEndpointAnalistasDirecto()
    return probador.ejecutar_prueba_directa()

if __name__ == "__main__":
    main()
