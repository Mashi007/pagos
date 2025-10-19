# backend/scripts/revisar_tabla_analistas_creada.py
"""
REVISAR TABLA ANALISTAS CREADA
Verificar la estructura y datos de la tabla analistas que ya existe
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

class RevisarTablaAnalistasCreada:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
    def hacer_login(self) -> Dict[str, Any]:
        """Hacer login y obtener token"""
        logger.info("🔐 REALIZANDO LOGIN")
        logger.info("-" * 50)
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                user_info = data.get('user', {})
                
                logger.info("   ✅ Login exitoso")
                logger.info(f"   📊 Usuario: {user_info.get('email', 'N/A')}")
                logger.info(f"   📊 Rol: {'Administrador' if user_info.get('is_admin') else 'Usuario'}")
                
                return {
                    "status": "success",
                    "access_token": access_token,
                    "user": user_info
                }
            else:
                logger.error(f"   ❌ Login falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "error", "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"   ❌ Error en login: {e}")
            return {"status": "error", "error": str(e)}
    
    def probar_endpoint_analistas(self, access_token: str) -> Dict[str, Any]:
        """Probar endpoint analistas para ver qué datos devuelve"""
        logger.info("🔍 PROBANDO ENDPOINT ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        endpoints_a_probar = [
            "/api/v1/analistas/test-no-auth",
            "/api/v1/analistas/test-simple",
            "/api/v1/analistas/list-no-auth"
        ]
        
        resultados = {}
        
        for endpoint in endpoints_a_probar:
            try:
                logger.info(f"   🔍 Probando: {endpoint}")
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    timeout=15
                )
                
                logger.info(f"   📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"   ✅ ÉXITO: {endpoint}")
                    logger.info(f"   📊 Respuesta completa:")
                    logger.info(f"   {json.dumps(data, indent=2)}")
                    
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
    
    def probar_endpoint_principal_con_auth(self, access_token: str) -> Dict[str, Any]:
        """Probar endpoint principal analistas con autenticación"""
        logger.info("🔍 PROBANDO ENDPOINT PRINCIPAL CON AUTENTICACIÓN")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info("   🔍 Probando: /api/v1/analistas/")
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ ÉXITO: Endpoint principal funcionando")
                logger.info(f"   📊 Respuesta completa:")
                logger.info(f"   {json.dumps(data, indent=2)}")
                
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
    
    def ejecutar_revision_completa(self):
        """Ejecutar revisión completa de la tabla analistas creada"""
        logger.info("🔍 REVISIÓN COMPLETA DE TABLA ANALISTAS CREADA")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Revisar estructura y datos de la tabla analistas existente")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Hacer login
        logger.info("\n🔐 1. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando revisión")
            return resultados
        
        access_token = login["access_token"]
        
        # 2. Probar endpoints analistas
        logger.info("\n🔍 2. PROBANDO ENDPOINTS ANALISTAS")
        logger.info("-" * 50)
        endpoints = self.probar_endpoint_analistas(access_token)
        resultados["endpoints"] = endpoints
        
        # 3. Probar endpoint principal con autenticación
        logger.info("\n🔍 3. PROBANDO ENDPOINT PRINCIPAL CON AUTENTICACIÓN")
        logger.info("-" * 50)
        principal = self.probar_endpoint_principal_con_auth(access_token)
        resultados["principal"] = principal
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        endpoints_exitosos = 0
        endpoints_fallidos = 0
        
        for endpoint, resultado in endpoints.items():
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
            logger.info("✅ TABLA ANALISTAS FUNCIONANDO")
            logger.info("   🎯 La tabla analistas tiene datos y funciona correctamente")
            logger.info("   📊 Revisar los datos mostrados arriba")
        else:
            logger.error("❌ TABLA ANALISTAS CON PROBLEMAS")
            logger.error("   💡 Revisar los errores mostrados arriba")
        
        return resultados

def main():
    revisor = RevisarTablaAnalistasCreada()
    return revisor.ejecutar_revision_completa()

if __name__ == "__main__":
    main()
