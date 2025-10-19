# backend/scripts/agregar_columna_apellido_analistas.py
"""
AGREGAR COLUMNA APELLIDO A TABLA ANALISTAS
Script para agregar la columna apellido faltante a la tabla analistas
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

class AgregarColumnaApellidoAnalistas:
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
    
    def ejecutar_migracion_apellido(self, access_token: str) -> Dict[str, Any]:
        """Ejecutar migración para agregar columna apellido"""
        logger.info("🔧 EJECUTANDO MIGRACIÓN PARA AGREGAR COLUMNA APELLIDO")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # SQL para agregar la columna apellido
        sql_migration = """
        ALTER TABLE analistas 
        ADD COLUMN IF NOT EXISTS apellido VARCHAR(255);
        
        -- Actualizar registros existentes con apellido vacío si es necesario
        UPDATE analistas 
        SET apellido = '' 
        WHERE apellido IS NULL;
        
        -- Hacer la columna NOT NULL con valor por defecto
        ALTER TABLE analistas 
        ALTER COLUMN apellido SET DEFAULT '';
        
        -- Crear índice si es necesario
        CREATE INDEX IF NOT EXISTS idx_analistas_apellido ON analistas(apellido);
        """
        
        try:
            # Usar endpoint de migración de emergencia si existe
            response = requests.post(
                f"{self.backend_url}/api/v1/fix-database",
                json={
                    "sql": sql_migration,
                    "description": "Agregar columna apellido a tabla analistas"
                },
                headers=headers,
                timeout=30
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ Migración ejecutada exitosamente")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)}")
                
                return {
                    "status": "success",
                    "data": data
                }
            else:
                logger.error(f"   ❌ Migración falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error ejecutando migración: {e}")
            return {"status": "error", "error": str(e)}
    
    def verificar_migracion_exitosa(self, access_token: str) -> Dict[str, Any]:
        """Verificar que la migración fue exitosa"""
        logger.info("🔍 VERIFICANDO MIGRACIÓN EXITOSA")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Probar endpoint analistas
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/test-no-auth",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") == True:
                    logger.info("   ✅ Migración exitosa - Endpoint analistas funcionando")
                    logger.info(f"   📊 Total analistas: {data.get('total_analistas', 0)}")
                    return {
                        "status": "success",
                        "data": data
                    }
                else:
                    logger.error("   ❌ Migración falló - Error persiste")
                    logger.error(f"   📊 Error: {data.get('error', 'N/A')}")
                    return {
                        "status": "error",
                        "error": data.get('error', 'N/A')
                    }
            else:
                logger.error(f"   ❌ Verificación falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error verificando migración: {e}")
            return {"status": "error", "error": str(e)}
    
    def ejecutar_agregar_columna_apellido(self):
        """Ejecutar proceso completo para agregar columna apellido"""
        logger.info("🔧 AGREGAR COLUMNA APELLIDO A TABLA ANALISTAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Agregar columna apellido faltante a la tabla analistas")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Hacer login
        logger.info("\n🔐 1. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando proceso")
            return resultados
        
        access_token = login["access_token"]
        
        # 2. Ejecutar migración
        logger.info("\n🔧 2. EJECUTANDO MIGRACIÓN")
        logger.info("-" * 50)
        migracion = self.ejecutar_migracion_apellido(access_token)
        resultados["migracion"] = migracion
        
        if migracion["status"] != "success":
            logger.error("❌ Migración falló, abortando proceso")
            return resultados
        
        # 3. Verificar migración exitosa
        logger.info("\n🔍 3. VERIFICANDO MIGRACIÓN EXITOSA")
        logger.info("-" * 50)
        verificacion = self.verificar_migracion_exitosa(access_token)
        resultados["verificacion"] = verificacion
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if verificacion["status"] == "success":
            logger.info("🎉 MIGRACIÓN EXITOSA")
            logger.info("   ✅ Columna apellido agregada correctamente")
            logger.info("   ✅ Endpoint analistas funcionando")
            logger.info("   🚀 PROBLEMA RESUELTO COMPLETAMENTE")
        else:
            logger.error("❌ MIGRACIÓN FALLÓ")
            logger.error(f"   📊 Error: {verificacion.get('error', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")
        
        return resultados

def main():
    migrador = AgregarColumnaApellidoAnalistas()
    return migrador.ejecutar_agregar_columna_apellido()

if __name__ == "__main__":
    main()
