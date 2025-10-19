# backend/scripts/reconstruir_tabla_analistas_completa.py
"""
RECONSTRUIR TABLA ANALISTAS COMPLETA
Script para reconstruir la tabla analistas con todas las columnas necesarias
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

class ReconstruirTablaAnalistasCompleta:
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
    
    def reconstruir_tabla_analistas(self, access_token: str) -> Dict[str, Any]:
        """Reconstruir tabla analistas con todas las columnas necesarias"""
        logger.info("🔧 RECONSTRUYENDO TABLA ANALISTAS COMPLETA")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # SQL para reconstruir la tabla analistas completamente
        sql_reconstruccion = """
        -- Crear tabla temporal con la estructura correcta
        CREATE TABLE IF NOT EXISTS analistas_temp (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            apellido VARCHAR(255) DEFAULT '',
            email VARCHAR(255) UNIQUE,
            telefono VARCHAR(20),
            especialidad VARCHAR(255),
            comision_porcentaje INTEGER CHECK (comision_porcentaje >= 0 AND comision_porcentaje <= 100),
            activo BOOLEAN DEFAULT TRUE,
            notas TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Copiar datos existentes si la tabla original existe
        INSERT INTO analistas_temp (id, nombre, apellido, email, telefono, especialidad, comision_porcentaje, activo, notas, created_at, updated_at)
        SELECT 
            id,
            COALESCE(nombre, 'Analista') as nombre,
            COALESCE(apellido, '') as apellido,
            COALESCE(email, '') as email,
            COALESCE(telefono, '') as telefono,
            COALESCE(especialidad, '') as especialidad,
            COALESCE(comision_porcentaje, 0) as comision_porcentaje,
            COALESCE(activo, TRUE) as activo,
            COALESCE(notas, '') as notas,
            COALESCE(created_at, NOW()) as created_at,
            COALESCE(updated_at, NOW()) as updated_at
        FROM analistas
        ON CONFLICT (id) DO NOTHING;
        
        -- Eliminar tabla original
        DROP TABLE IF EXISTS analistas CASCADE;
        
        -- Renombrar tabla temporal
        ALTER TABLE analistas_temp RENAME TO analistas;
        
        -- Crear índices
        CREATE INDEX IF NOT EXISTS idx_analistas_nombre ON analistas(nombre);
        CREATE INDEX IF NOT EXISTS idx_analistas_apellido ON analistas(apellido);
        CREATE INDEX IF NOT EXISTS idx_analistas_email ON analistas(email);
        CREATE INDEX IF NOT EXISTS idx_analistas_activo ON analistas(activo);
        
        -- Insertar datos de ejemplo si no hay datos
        INSERT INTO analistas (nombre, apellido, email, telefono, especialidad, comision_porcentaje, activo, notas)
        SELECT 'Juan', 'Pérez', 'juan.perez@rapicreditca.com', '3001234567', 'Vehículos Nuevos', 5, TRUE, 'Analista principal'
        WHERE NOT EXISTS (SELECT 1 FROM analistas LIMIT 1);
        
        INSERT INTO analistas (nombre, apellido, email, telefono, especialidad, comision_porcentaje, activo, notas)
        SELECT 'María', 'González', 'maria.gonzalez@rapicreditca.com', '3007654321', 'Vehículos Usados', 7, TRUE, 'Analista especializada'
        WHERE NOT EXISTS (SELECT 1 FROM analistas WHERE email = 'maria.gonzalez@rapicreditca.com');
        """
        
        try:
            # Usar endpoint de migración de emergencia si existe
            response = requests.post(
                f"{self.backend_url}/api/v1/fix-database",
                json={
                    "sql": sql_reconstruccion,
                    "description": "Reconstruir tabla analistas con estructura completa"
                },
                headers=headers,
                timeout=60
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ Reconstrucción ejecutada exitosamente")
                logger.info(f"   📊 Respuesta: {json.dumps(data, indent=2)}")
                
                return {
                    "status": "success",
                    "data": data
                }
            else:
                logger.error(f"   ❌ Reconstrucción falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error ejecutando reconstrucción: {e}")
            return {"status": "error", "error": str(e)}
    
    def verificar_reconstruccion_exitosa(self, access_token: str) -> Dict[str, Any]:
        """Verificar que la reconstrucción fue exitosa"""
        logger.info("🔍 VERIFICANDO RECONSTRUCCIÓN EXITOSA")
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
                    logger.info("   ✅ Reconstrucción exitosa - Endpoint analistas funcionando")
                    logger.info(f"   📊 Total analistas: {data.get('total_analistas', 0)}")
                    logger.info(f"   📊 Analistas: {json.dumps(data.get('analistas', []), indent=2)}")
                    return {
                        "status": "success",
                        "data": data
                    }
                else:
                    logger.error("   ❌ Reconstrucción falló - Error persiste")
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
            logger.error(f"   ❌ Error verificando reconstrucción: {e}")
            return {"status": "error", "error": str(e)}
    
    def ejecutar_reconstruccion_completa(self):
        """Ejecutar proceso completo para reconstruir tabla analistas"""
        logger.info("🔧 RECONSTRUCCIÓN COMPLETA DE TABLA ANALISTAS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Reconstruir tabla analistas con estructura completa")
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
        
        # 2. Ejecutar reconstrucción
        logger.info("\n🔧 2. EJECUTANDO RECONSTRUCCIÓN")
        logger.info("-" * 50)
        reconstruccion = self.reconstruir_tabla_analistas(access_token)
        resultados["reconstruccion"] = reconstruccion
        
        if reconstruccion["status"] != "success":
            logger.error("❌ Reconstrucción falló, abortando proceso")
            return resultados
        
        # 3. Verificar reconstrucción exitosa
        logger.info("\n🔍 3. VERIFICANDO RECONSTRUCCIÓN EXITOSA")
        logger.info("-" * 50)
        verificacion = self.verificar_reconstruccion_exitosa(access_token)
        resultados["verificacion"] = verificacion
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if verificacion["status"] == "success":
            logger.info("🎉 RECONSTRUCCIÓN EXITOSA")
            logger.info("   ✅ Tabla analistas reconstruida correctamente")
            logger.info("   ✅ Todas las columnas necesarias agregadas")
            logger.info("   ✅ Endpoint analistas funcionando")
            logger.info("   🚀 PROBLEMA RESUELTO COMPLETAMENTE")
        else:
            logger.error("❌ RECONSTRUCCIÓN FALLÓ")
            logger.error(f"   📊 Error: {verificacion.get('error', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")
        
        return resultados

def main():
    reconstructor = ReconstruirTablaAnalistasCompleta()
    return reconstructor.ejecutar_reconstruccion_completa()

if __name__ == "__main__":
    main()
