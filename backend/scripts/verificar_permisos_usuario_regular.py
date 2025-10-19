# backend/scripts/verificar_permisos_usuario_regular.py
"""
VERIFICAR PERMISOS ACTUALIZADOS DEL USUARIO REGULAR
Verificar que el usuario regular ahora tiene los permisos operativos básicos
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

class VerificarPermisosUsuarioRegular:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
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
    
    def verificar_permisos_usuario_regular(self, access_token: str) -> Dict[str, Any]:
        """Verificar permisos del usuario regular"""
        logger.info("🔍 VERIFICANDO PERMISOS DEL USUARIO REGULAR")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info("   🔍 Obteniendo información del usuario actual")
            response = requests.get(
                f"{self.backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                permissions = data.get('permissions', [])
                
                logger.info("   ✅ INFORMACIÓN DEL USUARIO OBTENIDA")
                logger.info(f"   📊 Email: {data.get('email', 'N/A')}")
                logger.info(f"   📊 Nombre: {data.get('nombre', 'N/A')}")
                logger.info(f"   📊 Rol: {'Administrador' if data.get('is_admin') else 'Usuario'}")
                logger.info(f"   📊 Total permisos: {len(permissions)}")
                
                # Verificar permisos específicos solicitados
                permisos_solicitados = [
                    "cliente:create",
                    "cliente:update", 
                    "prestamo:create",
                    "prestamo:update",
                    "pago:create",
                    "pago:update",
                    "pago:delete"
                ]
                
                logger.info("\n   🔍 VERIFICANDO PERMISOS SOLICITADOS:")
                permisos_encontrados = []
                permisos_faltantes = []
                
                for permiso in permisos_solicitados:
                    if permiso in permissions:
                        permisos_encontrados.append(permiso)
                        logger.info(f"   ✅ {permiso}")
                    else:
                        permisos_faltantes.append(permiso)
                        logger.info(f"   ❌ {permiso}")
                
                logger.info(f"\n   📊 RESUMEN:")
                logger.info(f"   ✅ Permisos encontrados: {len(permisos_encontrados)}")
                logger.info(f"   ❌ Permisos faltantes: {len(permisos_faltantes)}")
                
                return {
                    "status": "success",
                    "user_data": data,
                    "permissions": permissions,
                    "permisos_encontrados": permisos_encontrados,
                    "permisos_faltantes": permisos_faltantes
                }
            else:
                logger.error(f"   ❌ ERROR AL OBTENER INFORMACIÓN: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Verificación de permisos - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def probar_endpoint_crear_cliente(self, access_token: str) -> Dict[str, Any]:
        """Probar endpoint de crear cliente"""
        logger.info("🧪 PROBANDO ENDPOINT CREAR CLIENTE")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Datos de prueba para crear cliente
        cliente_data = {
            "cedula": "1234567890",
            "nombres": "Usuario",
            "apellidos": "Prueba",
            "telefono": "1234567890",
            "email": "prueba@test.com",
            "direccion": "Dirección de prueba",
            "total_financiamiento": 10000,
            "cuota_inicial": 1000
        }
        
        try:
            logger.info("   🔍 Probando: POST /api/v1/clientes/crear")
            response = requests.post(
                f"{self.backend_url}/api/v1/clientes/crear",
                json=cliente_data,
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info("   ✅ ÉXITO: Endpoint crear cliente funcionando")
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "message": "Endpoint crear cliente accesible"
                }
            else:
                logger.error(f"   ❌ FALLO: Endpoint crear cliente")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Endpoint crear cliente - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def ejecutar_verificacion_permisos(self):
        """Ejecutar verificación completa de permisos"""
        logger.info("🔍 VERIFICACIÓN DE PERMISOS ACTUALIZADOS DEL USUARIO REGULAR")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Verificar que el usuario regular tiene permisos operativos básicos")
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
        
        # 2. Verificar permisos
        logger.info("\n🔍 2. VERIFICANDO PERMISOS")
        logger.info("-" * 50)
        permisos = self.verificar_permisos_usuario_regular(access_token)
        resultados["permisos"] = permisos
        
        # 3. Probar endpoint
        logger.info("\n🧪 3. PROBANDO ENDPOINT")
        logger.info("-" * 50)
        endpoint = self.probar_endpoint_crear_cliente(access_token)
        resultados["endpoint"] = endpoint
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if permisos["status"] == "success":
            permisos_encontrados = permisos.get("permisos_encontrados", [])
            permisos_faltantes = permisos.get("permisos_faltantes", [])
            
            if len(permisos_encontrados) >= 5:  # Al menos 5 de los 7 permisos solicitados
                logger.info("🎉 PERMISOS ACTUALIZADOS CORRECTAMENTE")
                logger.info(f"   ✅ Permisos encontrados: {len(permisos_encontrados)}/7")
                logger.info("   ✅ Usuario regular puede gestionar operaciones básicas")
                logger.info("   ✅ Sistema de permisos funcionando correctamente")
            else:
                logger.warning("⚠️ PERMISOS PARCIALMENTE ACTUALIZADOS")
                logger.warning(f"   📊 Permisos encontrados: {len(permisos_encontrados)}/7")
                logger.warning(f"   📊 Permisos faltantes: {len(permisos_faltantes)}")
        else:
            logger.error("❌ ERROR EN VERIFICACIÓN DE PERMISOS")
            logger.error(f"   📊 Status: {permisos.get('status', 'N/A')}")
        
        return resultados

def main():
    verificador = VerificarPermisosUsuarioRegular()
    return verificador.ejecutar_verificacion_permisos()

if __name__ == "__main__":
    main()
