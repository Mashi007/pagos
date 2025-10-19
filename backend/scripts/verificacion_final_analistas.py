# backend/scripts/verificacion_final_analistas.py
"""
VERIFICACIÓN FINAL: Confirmar que analistas funciona después de corrección de emojis
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

class VerificacionFinalAnalistas:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
    def verificar_servidor_activo(self) -> Dict[str, Any]:
        """Verificar que el servidor está activo"""
        logger.info("🌐 VERIFICANDO SERVIDOR ACTIVO")
        logger.info("-" * 50)
        
        try:
            response = requests.get(f"{self.backend_url}/docs", timeout=10)
            if response.status_code == 200:
                logger.info("   ✅ Servidor activo y respondiendo")
                return {"status": "success", "message": "Servidor activo"}
            else:
                logger.error(f"   ❌ Servidor respondiendo con status: {response.status_code}")
                return {"status": "error", "status_code": response.status_code}
        except Exception as e:
            logger.error(f"   ❌ Error conectando al servidor: {e}")
            return {"status": "error", "error": str(e)}
    
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
    
    def verificar_endpoint_analistas(self, access_token: str) -> Dict[str, Any]:
        """Verificar el endpoint de analistas"""
        logger.info("👥 VERIFICANDO ENDPOINT ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas",
                headers=headers,
                params={'limit': 100},
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total_analistas = data.get('total', 0)
                items = data.get('items', [])
                
                logger.info("   ✅ ENDPOINT ANALISTAS FUNCIONANDO CORRECTAMENTE")
                logger.info(f"   📊 Total analistas: {total_analistas}")
                logger.info(f"   📊 Items retornados: {len(items)}")
                
                if items:
                    primer_analista = items[0]
                    logger.info(f"   📊 Primer analista: {primer_analista.get('nombre', 'N/A')} {primer_analista.get('apellido', 'N/A')}")
                
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "total_analistas": total_analistas,
                    "items_count": len(items),
                    "data": data
                }
            else:
                logger.error(f"   ❌ ENDPOINT ANALISTAS AÚN FALLANDO: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error verificando endpoint: {e}")
            return {"status": "error", "error": str(e)}
    
    def verificar_endpoints_adicionales(self, access_token: str) -> Dict[str, Any]:
        """Verificar otros endpoints críticos"""
        logger.info("🔍 VERIFICANDO ENDPOINTS ADICIONALES")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        endpoints_a_verificar = [
            ("/api/v1/clientes", "Clientes"),
            ("/api/v1/dashboard", "Dashboard"),
            ("/api/v1/kpis", "KPIs")
        ]
        
        resultados = {}
        
        for endpoint, nombre in endpoints_a_verificar:
            try:
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"   ✅ {nombre}: OK")
                    resultados[nombre] = "OK"
                else:
                    logger.error(f"   ❌ {nombre}: {response.status_code}")
                    resultados[nombre] = f"Error {response.status_code}"
                    
            except Exception as e:
                logger.error(f"   ❌ {nombre}: Error - {e}")
                resultados[nombre] = f"Error: {e}"
        
        return resultados
    
    def ejecutar_verificacion_final(self):
        """Ejecutar verificación final completa"""
        logger.info("🎯 VERIFICACIÓN FINAL: ANALISTAS DESPUÉS DE CORRECCIÓN DE EMOJIS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Confirmar que el problema 405 está resuelto")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Verificar servidor activo
        logger.info("\n🌐 1. VERIFICANDO SERVIDOR ACTIVO")
        logger.info("-" * 50)
        servidor = self.verificar_servidor_activo()
        resultados["servidor"] = servidor
        
        if servidor["status"] != "success":
            logger.error("❌ SERVidor no disponible, abortando verificación")
            return resultados
        
        # 2. Hacer login
        logger.info("\n🔐 2. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando verificación")
            return resultados
        
        access_token = login["access_token"]
        
        # 3. Verificar endpoint analistas
        logger.info("\n👥 3. VERIFICANDO ENDPOINT ANALISTAS")
        logger.info("-" * 50)
        analistas = self.verificar_endpoint_analistas(access_token)
        resultados["analistas"] = analistas
        
        # 4. Verificar endpoints adicionales
        logger.info("\n🔍 4. VERIFICANDO ENDPOINTS ADICIONALES")
        logger.info("-" * 50)
        adicionales = self.verificar_endpoints_adicionales(access_token)
        resultados["adicionales"] = adicionales
        
        # 5. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if analistas["status"] == "success":
            logger.info("🎉 ¡PROBLEMA RESUELTO EXITOSAMENTE!")
            logger.info("   ✅ Endpoint analistas funcionando correctamente")
            logger.info(f"   📊 Total analistas: {analistas.get('total_analistas', 0)}")
            logger.info("   🎯 Error 405 Method Not Allowed: RESUELTO")
            logger.info("   💡 Causa raíz: Emojis problemáticos en docstrings")
            logger.info("   🔧 Solución: Remoción de emojis problemáticos")
        else:
            logger.error("❌ PROBLEMA PERSISTE")
            logger.error(f"   📊 Status: {analistas.get('status_code', 'N/A')}")
            logger.error(f"   📊 Error: {analistas.get('error', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")
        
        return resultados

def main():
    verificador = VerificacionFinalAnalistas()
    return verificador.ejecutar_verificacion_final()

if __name__ == "__main__":
    main()
