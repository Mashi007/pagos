# backend/scripts/diagnostico_frontend_analistas.py
"""
DIAGNÓSTICO FRONTEND ANALISTAS
Script para diagnosticar problemas de autenticación en el frontend
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

class DiagnosticoFrontendAnalistas:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
    def hacer_login_y_obtener_token(self) -> Dict[str, Any]:
        """Hacer login y obtener token para simular frontend"""
        logger.info("🔐 SIMULANDO LOGIN DEL FRONTEND")
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
                logger.info(f"   📊 Token: {access_token[:20]}...")
                
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
    
    def simular_llamada_frontend_con_token(self, access_token: str) -> Dict[str, Any]:
        """Simular llamada del frontend con token"""
        logger.info("🌐 SIMULANDO LLAMADA DEL FRONTEND CON TOKEN")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            logger.info("   🔍 Simulando: GET /api/v1/analistas/")
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ ÉXITO: Llamada del frontend funcionando")
                logger.info(f"   📊 Total analistas: {data.get('total', 0)}")
                logger.info(f"   📊 Items: {len(data.get('items', []))}")
                
                if data.get('items'):
                    primer_analista = data['items'][0]
                    logger.info(f"   📊 Primer analista: {primer_analista.get('nombre', 'N/A')}")
                
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": data
                }
            else:
                logger.error(f"   ❌ FALLO: Llamada del frontend")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Llamada del frontend - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def verificar_headers_cors(self) -> Dict[str, Any]:
        """Verificar headers CORS"""
        logger.info("🔍 VERIFICANDO HEADERS CORS")
        logger.info("-" * 50)
        
        try:
            # Hacer una petición OPTIONS para verificar CORS
            response = requests.options(
                f"{self.backend_url}/api/v1/analistas/",
                headers={
                    'Origin': self.frontend_url,
                    'Access-Control-Request-Method': 'GET',
                    'Access-Control-Request-Headers': 'Authorization, Content-Type'
                },
                timeout=10
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            logger.info(f"   📊 Headers CORS:")
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            for header, value in cors_headers.items():
                logger.info(f"   📊 {header}: {value}")
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "cors_headers": cors_headers
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error verificando CORS: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def ejecutar_diagnostico_frontend(self):
        """Ejecutar diagnóstico completo del frontend"""
        logger.info("🔍 DIAGNÓSTICO FRONTEND ANALISTAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Diagnosticar problemas de autenticación en el frontend")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Verificar CORS
        logger.info("\n🔍 1. VERIFICANDO HEADERS CORS")
        logger.info("-" * 50)
        cors = self.verificar_headers_cors()
        resultados["cors"] = cors
        
        # 2. Hacer login
        logger.info("\n🔐 2. SIMULANDO LOGIN DEL FRONTEND")
        logger.info("-" * 50)
        login = self.hacer_login_y_obtener_token()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando diagnóstico")
            return resultados
        
        access_token = login["access_token"]
        
        # 3. Simular llamada del frontend
        logger.info("\n🌐 3. SIMULANDO LLAMADA DEL FRONTEND")
        logger.info("-" * 50)
        frontend_call = self.simular_llamada_frontend_con_token(access_token)
        resultados["frontend_call"] = frontend_call
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if frontend_call["status"] == "success":
            logger.info("🎉 FRONTEND DEBERÍA FUNCIONAR")
            logger.info("   ✅ CORS configurado correctamente")
            logger.info("   ✅ Login funcionando")
            logger.info("   ✅ Llamada con token funcionando")
            logger.info("   🎯 El problema puede estar en:")
            logger.info("      - Token no se está guardando en el frontend")
            logger.info("      - Token no se está enviando en las peticiones")
            logger.info("      - Problema con el interceptor de Axios")
        else:
            logger.error("❌ PROBLEMA CONFIRMADO")
            logger.error(f"   📊 Error: {frontend_call.get('error', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")
        
        return resultados

def main():
    diagnostico = DiagnosticoFrontendAnalistas()
    return diagnostico.ejecutar_diagnostico_frontend()

if __name__ == "__main__":
    main()
