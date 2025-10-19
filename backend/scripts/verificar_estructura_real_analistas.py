# backend/scripts/verificar_estructura_real_analistas.py
"""
VERIFICAR ESTRUCTURA REAL DE TABLA ANALISTAS
Verificar qué columnas existen realmente en la tabla analistas
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

class VerificarEstructuraRealAnalistas:
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
    
    def consultar_estructura_tabla(self, access_token: str) -> Dict[str, Any]:
        """Consultar estructura real de la tabla analistas"""
        logger.info("🔍 CONSULTANDO ESTRUCTURA REAL DE TABLA ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # SQL para consultar estructura de la tabla
        sql_estructura = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_name = 'analistas' 
        ORDER BY ordinal_position;
        """
        
        try:
            # Usar endpoint de consulta SQL si existe
            response = requests.post(
                f"{self.backend_url}/api/v1/fix-database",
                json={
                    "sql": sql_estructura,
                    "description": "Consultar estructura de tabla analistas"
                },
                headers=headers,
                timeout=30
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ Consulta ejecutada exitosamente")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)}")
                
                return {
                    "status": "success",
                    "data": data
                }
            else:
                logger.error(f"   ❌ Consulta falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error consultando estructura: {e}")
            return {"status": "error", "error": str(e)}
    
    def consultar_datos_existentes(self, access_token: str) -> Dict[str, Any]:
        """Consultar datos existentes en la tabla analistas"""
        logger.info("🔍 CONSULTANDO DATOS EXISTENTES EN TABLA ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # SQL para consultar datos existentes
        sql_datos = """
        SELECT * FROM analistas LIMIT 5;
        """
        
        try:
            # Usar endpoint de consulta SQL si existe
            response = requests.post(
                f"{self.backend_url}/api/v1/fix-database",
                json={
                    "sql": sql_datos,
                    "description": "Consultar datos existentes en tabla analistas"
                },
                headers=headers,
                timeout=30
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ Consulta ejecutada exitosamente")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)}")
                
                return {
                    "status": "success",
                    "data": data
                }
            else:
                logger.error(f"   ❌ Consulta falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error consultando datos: {e}")
            return {"status": "error", "error": str(e)}
    
    def ejecutar_verificacion_estructura_real(self):
        """Ejecutar verificación de estructura real"""
        logger.info("🔍 VERIFICACIÓN DE ESTRUCTURA REAL DE TABLA ANALISTAS")
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
        
        # 2. Consultar estructura de tabla
        logger.info("\n🔍 2. CONSULTANDO ESTRUCTURA DE TABLA")
        logger.info("-" * 50)
        estructura = self.consultar_estructura_tabla(access_token)
        resultados["estructura"] = estructura
        
        # 3. Consultar datos existentes
        logger.info("\n🔍 3. CONSULTANDO DATOS EXISTENTES")
        logger.info("-" * 50)
        datos = self.consultar_datos_existentes(access_token)
        resultados["datos"] = datos
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if estructura["status"] == "success":
            logger.info("✅ ESTRUCTURA DE TABLA CONSULTADA")
            logger.info("   📊 Verificar columnas existentes en la respuesta")
        else:
            logger.error("❌ NO SE PUDO CONSULTAR ESTRUCTURA")
            logger.error(f"   📊 Error: {estructura.get('error', 'N/A')}")
        
        if datos["status"] == "success":
            logger.info("✅ DATOS EXISTENTES CONSULTADOS")
            logger.info("   📊 Verificar datos existentes en la respuesta")
        else:
            logger.error("❌ NO SE PUDIERON CONSULTAR DATOS")
            logger.error(f"   📊 Error: {datos.get('error', 'N/A')}")
        
        return resultados

def main():
    verificador = VerificarEstructuraRealAnalistas()
    return verificador.ejecutar_verificacion_estructura_real()

if __name__ == "__main__":
    main()
