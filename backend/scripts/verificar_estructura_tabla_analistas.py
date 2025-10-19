# backend/scripts/verificar_estructura_tabla_analistas.py
"""
VERIFICAR ESTRUCTURA DE TABLA ANALISTAS
Verificar la estructura real de la tabla analistas en la base de datos
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

class VerificarEstructuraTablaAnalistas:
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
    
    def verificar_estructura_tabla(self, access_token: str) -> Dict[str, Any]:
        """Verificar estructura de la tabla analistas"""
        logger.info("🔍 VERIFICANDO ESTRUCTURA DE TABLA ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Probar endpoint que funciona
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/test-no-auth",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ Endpoint responde correctamente")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)}")
                
                # Analizar el error
                if "error" in data and "apellido does not exist" in data["error"]:
                    logger.error("   🚨 PROBLEMA CONFIRMADO: Columna 'apellido' no existe")
                    logger.error("   💡 SOLUCIÓN: Agregar columna 'apellido' a la tabla analistas")
                    
                    return {
                        "status": "error",
                        "error_type": "missing_column",
                        "missing_column": "apellido",
                        "table": "analistas",
                        "solution": "Agregar columna 'apellido' a la tabla analistas"
                    }
                else:
                    logger.info("   ✅ No hay problemas de estructura")
                    return {
                        "status": "success",
                        "data": data
                    }
            else:
                logger.error(f"   ❌ Endpoint falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error verificando estructura: {e}")
            return {"status": "error", "error": str(e)}
    
    def ejecutar_verificacion_estructura(self):
        """Ejecutar verificación de estructura de tabla"""
        logger.info("🔍 VERIFICACIÓN DE ESTRUCTURA DE TABLA ANALISTAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Verificar estructura real de la tabla analistas")
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
        
        # 2. Verificar estructura de tabla
        logger.info("\n🔍 2. VERIFICANDO ESTRUCTURA DE TABLA")
        logger.info("-" * 50)
        estructura = self.verificar_estructura_tabla(access_token)
        resultados["estructura"] = estructura
        
        # 3. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if estructura["status"] == "error" and estructura.get("error_type") == "missing_column":
            logger.error("🚨 PROBLEMA DE ESTRUCTURA DE BASE DE DATOS CONFIRMADO")
            logger.error(f"   📊 Tabla: {estructura['table']}")
            logger.error(f"   📊 Columna faltante: {estructura['missing_column']}")
            logger.error(f"   💡 Solución: {estructura['solution']}")
            logger.error("   🔧 ACCIÓN REQUERIDA: Ejecutar migración de base de datos")
        else:
            logger.info("✅ ESTRUCTURA DE TABLA CORRECTA")
            logger.info("   🎯 No se encontraron problemas de estructura")
        
        return resultados

def main():
    verificador = VerificarEstructuraTablaAnalistas()
    return verificador.ejecutar_verificacion_estructura()

if __name__ == "__main__":
    main()
