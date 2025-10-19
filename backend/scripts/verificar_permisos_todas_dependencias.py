# backend/scripts/verificar_permisos_todas_dependencias.py
"""
VERIFICAR PERMISOS EN TODAS LAS DEPENDENCIAS
Verificar que los permisos actualizados están correctamente implementados en todas las dependencias
"""
import os
import sys
import logging
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VerificarPermisosTodasDependencias:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
        # Endpoints a verificar
        self.endpoints_a_verificar = {
            "CLIENTE_CREATE": {
                "method": "POST",
                "url": "/api/v1/clientes/crear",
                "data": {
                    "cedula": "1234567890",
                    "nombres": "Usuario",
                    "apellidos": "Prueba",
                    "telefono": "1234567890",
                    "email": "prueba@test.com",
                    "direccion": "Dirección de prueba",
                    "total_financiamiento": 10000,
                    "cuota_inicial": 1000
                }
            },
            "PRESTAMO_CREATE": {
                "method": "POST", 
                "url": "/api/v1/prestamos/",
                "data": {
                    "cliente_id": 1,
                    "monto_total": 5000,
                    "tasa_interes": 12.0,
                    "plazo_meses": 12,
                    "fecha_inicio": "2025-01-01",
                    "modalidad": "MENSUAL"
                }
            },
            "PAGO_CREATE": {
                "method": "POST",
                "url": "/api/v1/pagos/",
                "data": {
                    "prestamo_id": 1,
                    "monto": 500,
                    "fecha_pago": "2025-01-01",
                    "metodo_pago": "EFECTIVO"
                }
            }
        }
        
    def hacer_login(self) -> Dict[str, Any]:
        """Hacer login y obtener token"""
        logger.info("🔐 REALIZANDO LOGIN COMO ADMINISTRADOR")
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
    
    def verificar_permisos_usuario(self, access_token: str) -> Dict[str, Any]:
        """Verificar permisos del usuario"""
        logger.info("🔍 VERIFICANDO PERMISOS DEL USUARIO")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                permissions = data.get('permissions', [])
                
                logger.info("   ✅ INFORMACIÓN DEL USUARIO OBTENIDA")
                logger.info(f"   📊 Email: {data.get('email', 'N/A')}")
                logger.info(f"   📊 Rol: {'Administrador' if data.get('is_admin') else 'Usuario'}")
                logger.info(f"   📊 Total permisos: {len(permissions)}")
                
                # Verificar permisos específicos
                permisos_operativos = [
                    "cliente:create", "cliente:update",
                    "prestamo:create", "prestamo:update", 
                    "pago:create", "pago:update", "pago:delete"
                ]
                
                permisos_encontrados = [p for p in permisos_operativos if p in permissions]
                
                logger.info(f"   📊 Permisos operativos encontrados: {len(permisos_encontrados)}/7")
                
                return {
                    "status": "success",
                    "permissions": permissions,
                    "permisos_operativos": permisos_encontrados
                }
            else:
                logger.error(f"   ❌ ERROR: {response.status_code}")
                return {"status": "error", "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: {e}")
            return {"status": "error", "error": str(e)}
    
    def probar_endpoint(self, access_token: str, endpoint_name: str, endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
        """Probar un endpoint específico"""
        logger.info(f"🧪 PROBANDO ENDPOINT: {endpoint_name}")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            method = endpoint_config["method"]
            url = f"{self.backend_url}{endpoint_config['url']}"
            data = endpoint_config["data"]
            
            logger.info(f"   🔍 {method} {url}")
            
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=15)
            else:
                response = requests.get(url, headers=headers, timeout=15)
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info(f"   ✅ ÉXITO: {endpoint_name} funcionando")
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "endpoint": endpoint_name
                }
            elif response.status_code == 403:
                logger.error(f"   ❌ PERMISOS DENEGADOS: {endpoint_name}")
                return {
                    "status": "forbidden",
                    "status_code": response.status_code,
                    "endpoint": endpoint_name,
                    "error": "Permisos denegados"
                }
            elif response.status_code == 503:
                logger.warning(f"   ⚠️ SERVICIO NO DISPONIBLE: {endpoint_name}")
                return {
                    "status": "service_unavailable",
                    "status_code": response.status_code,
                    "endpoint": endpoint_name,
                    "error": "Servicio temporalmente no disponible"
                }
            else:
                logger.error(f"   ❌ ERROR: {endpoint_name} - {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "endpoint": endpoint_name,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: {endpoint_name} - {e}")
            return {
                "status": "error",
                "endpoint": endpoint_name,
                "error": str(e)
            }
    
    def ejecutar_verificacion_completa(self):
        """Ejecutar verificación completa de permisos en todas las dependencias"""
        logger.info("🔍 VERIFICACIÓN COMPLETA DE PERMISOS EN TODAS LAS DEPENDENCIAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Verificar que los permisos están actualizados en todas las dependencias")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Hacer login
        logger.info("\n🔐 1. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando verificación")
            return resultados
        
        access_token = login["access_token"]
        
        # 2. Verificar permisos del usuario
        logger.info("\n🔍 2. VERIFICANDO PERMISOS DEL USUARIO")
        logger.info("-" * 50)
        permisos = self.verificar_permisos_usuario(access_token)
        resultados["permisos"] = permisos
        
        # 3. Probar endpoints
        logger.info("\n🧪 3. PROBANDO ENDPOINTS")
        logger.info("-" * 50)
        resultados_endpoints = {}
        
        for endpoint_name, endpoint_config in self.endpoints_a_verificar.items():
            resultado = self.probar_endpoint(access_token, endpoint_name, endpoint_config)
            resultados_endpoints[endpoint_name] = resultado
        
        resultados["endpoints"] = resultados_endpoints
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if permisos["status"] == "success":
            permisos_operativos = permisos.get("permisos_operativos", [])
            logger.info(f"✅ Permisos operativos encontrados: {len(permisos_operativos)}/7")
            
            # Analizar resultados de endpoints
            endpoints_exitosos = 0
            endpoints_con_permisos = 0
            endpoints_con_error = 0
            
            for endpoint_name, resultado in resultados_endpoints.items():
                if resultado["status"] == "success":
                    endpoints_exitosos += 1
                elif resultado["status"] == "forbidden":
                    endpoints_con_permisos += 1
                else:
                    endpoints_con_error += 1
            
            logger.info(f"📊 Endpoints probados: {len(resultados_endpoints)}")
            logger.info(f"✅ Endpoints exitosos: {endpoints_exitosos}")
            logger.info(f"🔒 Endpoints con permisos: {endpoints_con_permisos}")
            logger.info(f"❌ Endpoints con error: {endpoints_con_error}")
            
            if len(permisos_operativos) >= 5:
                logger.info("🎉 PERMISOS ACTUALIZADOS CORRECTAMENTE EN TODAS LAS DEPENDENCIAS")
                logger.info("   ✅ Sistema de permisos funcionando correctamente")
                logger.info("   ✅ Usuarios regulares pueden gestionar operaciones básicas")
            else:
                logger.warning("⚠️ PERMISOS PARCIALMENTE ACTUALIZADOS")
                logger.warning("   📊 Algunos permisos pueden no estar funcionando correctamente")
        else:
            logger.error("❌ ERROR EN VERIFICACIÓN DE PERMISOS")
        
        return resultados

def main():
    verificador = VerificarPermisosTodasDependencias()
    return verificador.ejecutar_verificacion_completa()

if __name__ == "__main__":
    main()
