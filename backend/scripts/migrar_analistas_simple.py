#!/usr/bin/env python3
"""
Script simple para migrar la tabla analistas usando la URL de producción
"""
import requests
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def migrar_tabla_analistas():
    """Migrar tabla analistas con todas las columnas necesarias"""
    logger.info("🔧 MIGRANDO TABLA ANALISTAS COMPLETA")
    logger.info("-" * 50)
    
    # URL del backend en producción
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales
    username = "itmaster@rapicreditca.com"
    password = "Admin123!"
    
    # Paso 1: Login
    logger.info("🔐 HACIENDO LOGIN")
    try:
        login_data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            data=login_data,
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            
            if access_token:
                logger.info("✅ LOGIN EXITOSO")
                logger.info(f"   🔑 Token obtenido: {access_token[:20]}...")
            else:
                logger.error("❌ No se encontró access_token en la respuesta")
                return
        else:
            logger.error(f"❌ Error en login: {response.status_code}")
            logger.error(f"   📄 Respuesta: {response.text}")
            return
            
    except Exception as e:
        logger.error(f"❌ Error en login: {str(e)}")
        return
    
    # Paso 2: Migrar tabla
    logger.info("🔧 EJECUTANDO MIGRACIÓN")
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # SQL para migrar la tabla analistas completamente
    sql_migration = """
    -- Agregar columnas que faltan
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS apellido VARCHAR(255) DEFAULT '';
    
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS email VARCHAR(255);
    
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(20);
    
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS especialidad VARCHAR(255);
    
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS comision_porcentaje INTEGER;
    
    ALTER TABLE analistas 
    ADD COLUMN IF NOT EXISTS notas TEXT;
    
    -- Actualizar registros existentes con valores por defecto
    UPDATE analistas 
    SET apellido = '' 
    WHERE apellido IS NULL;
    
    UPDATE analistas 
    SET email = '' 
    WHERE email IS NULL;
    
    UPDATE analistas 
    SET telefono = '' 
    WHERE telefono IS NULL;
    
    UPDATE analistas 
    SET especialidad = '' 
    WHERE especialidad IS NULL;
    
    UPDATE analistas 
    SET comision_porcentaje = 0 
    WHERE comision_porcentaje IS NULL;
    
    UPDATE analistas 
    SET notas = '' 
    WHERE notas IS NULL;
    
    -- Crear índices
    CREATE INDEX IF NOT EXISTS idx_analistas_apellido ON analistas(apellido);
    CREATE INDEX IF NOT EXISTS idx_analistas_email ON analistas(email);
    CREATE INDEX IF NOT EXISTS idx_analistas_especialidad ON analistas(especialidad);
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
        migration_data = {
            "sql": sql_migration,
            "description": "Migración completa de tabla analistas con todas las columnas"
        }
        
        response = requests.post(
            f"{backend_url}/api/v1/fix-db/execute-sql",
            json=migration_data,
            headers=headers,
            timeout=60
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ MIGRACIÓN EXITOSA")
            logger.info(f"   📄 Resultado: {result}")
        else:
            logger.error(f"❌ Error en migración: {response.status_code}")
            logger.error(f"   📄 Respuesta: {response.text}")
            return
            
    except Exception as e:
        logger.error(f"❌ Error en migración: {str(e)}")
        return
    
    # Paso 3: Verificar migración
    logger.info("🔍 VERIFICANDO MIGRACIÓN")
    try:
        response = requests.get(
            f"{backend_url}/api/v1/analistas",
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            analistas_data = response.json()
            logger.info("✅ ENDPOINT ANALISTAS FUNCIONANDO")
            logger.info(f"   📊 Total analistas: {analistas_data.get('total', 0)}")
            logger.info(f"   📊 Items recibidos: {len(analistas_data.get('items', []))}")
            
            # Mostrar algunos analistas si existen
            items = analistas_data.get('items', [])
            if items:
                logger.info(f"\n📋 ANALISTAS ENCONTRADOS:")
                for i, analista in enumerate(items[:3]):
                    logger.info(f"   {i+1}. ID: {analista.get('id')}, Nombre: {analista.get('nombre')}")
                    logger.info(f"      Email: {analista.get('email')}, Activo: {analista.get('activo')}")
                    logger.info(f"      Especialidad: {analista.get('especialidad')}")
            
            logger.info("🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
        else:
            logger.error(f"❌ Error verificando endpoint: {response.status_code}")
            logger.error(f"   📄 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando migración: {str(e)}")

if __name__ == "__main__":
    migrar_tabla_analistas()
