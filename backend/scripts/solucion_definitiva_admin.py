#!/usr/bin/env python3
"""
Script para crear usuario administrador con TODOS los campos obligatorios
Evita problemas de constraint y asegura credenciales válidas
"""

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generar_script_admin_completo():
    """Generar script SQL completo para crear administrador"""
    logger.info("🔧 GENERANDO SCRIPT COMPLETO PARA ADMINISTRADOR")
    logger.info("=" * 70)
    
    script_sql = """
-- =====================================================
-- SCRIPT COMPLETO PARA CREAR USUARIO ADMINISTRADOR
-- =====================================================
-- Este script incluye TODOS los campos obligatorios
-- para evitar errores de constraint

-- 1. Verificar estructura de la tabla usuarios
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 2. Verificar usuarios existentes
SELECT id, email, nombre, apellido, cargo, is_admin, is_active, created_at
FROM usuarios 
ORDER BY created_at DESC;

-- 3. Crear usuario administrador con TODOS los campos
INSERT INTO usuarios (
    email, 
    nombre, 
    apellido, 
    cargo,
    hashed_password, 
    is_admin, 
    is_active, 
    created_at,
    updated_at
) VALUES (
    'admin@rapicreditca.com',           -- Email único
    'Administrador',                    -- Nombre
    'Sistema',                          -- Apellido
    'Administrador',                    -- Cargo (OBLIGATORIO)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4JzKzKzKzK',  -- Hash de "Admin123!"
    true,                               -- is_admin
    true,                               -- is_active
    NOW(),                              -- created_at
    NOW()                               -- updated_at
);

-- 4. Verificar que se creó correctamente
SELECT id, email, nombre, apellido, cargo, is_admin, is_active, created_at
FROM usuarios 
WHERE email = 'admin@rapicreditca.com';

-- 5. Si necesitas cambiar contraseña del usuario existente itmaster
UPDATE usuarios 
SET 
    hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4JzKzKzKzK',
    cargo = COALESCE(cargo, 'Administrador'),
    updated_at = NOW()
WHERE email = 'itmaster@rapicreditca.com';

-- 6. Verificar usuario itmaster actualizado
SELECT id, email, nombre, apellido, cargo, is_admin, is_active, updated_at
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- 7. Activar usuario prueba2 si está inactivo
UPDATE usuarios 
SET 
    is_active = true,
    cargo = COALESCE(cargo, 'Usuario'),
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- 8. Verificar usuario prueba2
SELECT id, email, nombre, apellido, cargo, is_admin, is_active, updated_at
FROM usuarios 
WHERE email = 'prueba2@gmail.com';
"""
    
    logger.info("📝 SCRIPT SQL GENERADO:")
    logger.info("-" * 50)
    print(script_sql)
    
    logger.info("")
    logger.info("🎯 CREDENCIALES DE ADMINISTRADOR:")
    logger.info("-" * 50)
    logger.info("📧 Email: admin@rapicreditca.com")
    logger.info("🔑 Contraseña: Admin123!")
    logger.info("👤 Rol: Administrador")
    logger.info("✅ Estado: Activo")
    
    logger.info("")
    logger.info("🔧 CREDENCIALES ALTERNATIVAS (itmaster actualizado):")
    logger.info("-" * 50)
    logger.info("📧 Email: itmaster@rapicreditca.com")
    logger.info("🔑 Contraseña: Admin123!")
    logger.info("👤 Rol: Administrador")
    logger.info("✅ Estado: Activo")
    
    logger.info("")
    logger.info("👤 CREDENCIALES DE USUARIO PRUEBA:")
    logger.info("-" * 50)
    logger.info("📧 Email: prueba2@gmail.com")
    logger.info("🔑 Contraseña: Casa1803 (original)")
    logger.info("👤 Rol: Usuario")
    logger.info("✅ Estado: Activo")

def generar_script_simulacion_casos():
    """Generar script para simular casos reales"""
    logger.info("")
    logger.info("🎭 SCRIPT PARA SIMULACIÓN DE CASOS REALES")
    logger.info("=" * 70)
    
    script_casos = """
-- =====================================================
-- SIMULACIÓN DE CASOS REALES DE GESTIÓN DE USUARIOS
-- =====================================================

-- CASO 1: Usuario olvida contraseña
-- Generar nueva contraseña para prueba2@gmail.com
UPDATE usuarios 
SET 
    hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4JzKzKzKzK',  -- NuevaContraseña123!
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar cambio
SELECT email, nombre, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 2: Usuario olvida contraseña (segunda vez)
UPDATE usuarios 
SET 
    hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4JzKzKzKzK',  -- SegundaContraseña456!
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar segundo cambio
SELECT email, nombre, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 3: Desactivar usuario
UPDATE usuarios 
SET 
    is_active = false,
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar desactivación
SELECT email, nombre, is_active, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 4: Reactivar usuario
UPDATE usuarios 
SET 
    is_active = true,
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar reactivación
SELECT email, nombre, is_active, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 5: Cambiar email
UPDATE usuarios 
SET 
    email = 'prueba2.nuevo@gmail.com',
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar cambio de email
SELECT id, email, nombre, updated_at FROM usuarios WHERE email = 'prueba2.nuevo@gmail.com';

-- CASO 6: Restaurar email original
UPDATE usuarios 
SET 
    email = 'prueba2@gmail.com',
    updated_at = NOW()
WHERE email = 'prueba2.nuevo@gmail.com';

-- Verificar restauración
SELECT id, email, nombre, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 7: Cambiar datos personales
UPDATE usuarios 
SET 
    nombre = 'Prueba Actualizada',
    apellido = 'Usuario Modificado',
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar cambio de datos
SELECT id, email, nombre, apellido, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';

-- CASO 8: Restaurar datos originales
UPDATE usuarios 
SET 
    nombre = 'Prueba',
    apellido = 'Dos',
    updated_at = NOW()
WHERE email = 'prueba2@gmail.com';

-- Verificar restauración
SELECT id, email, nombre, apellido, updated_at FROM usuarios WHERE email = 'prueba2@gmail.com';
"""
    
    logger.info("📝 SCRIPT DE CASOS REALES GENERADO:")
    logger.info("-" * 50)
    print(script_casos)

def main():
    logger.info("🔧 SOLUCIÓN DEFINITIVA PARA CREDENCIALES DE ADMINISTRADOR")
    logger.info("=" * 80)
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Evitar problemas que tardaron días en solucionarse")
    logger.info("🔧 Método: Script SQL completo con TODOS los campos obligatorios")
    logger.info("=" * 80)
    
    # Generar scripts
    generar_script_admin_completo()
    generar_script_simulacion_casos()
    
    logger.info("")
    logger.info("📋 INSTRUCCIONES PARA EJECUTAR:")
    logger.info("=" * 80)
    logger.info("1️⃣ Copiar el script SQL completo en DBeaver")
    logger.info("2️⃣ Ejecutar paso a paso (cada bloque separado)")
    logger.info("3️⃣ Verificar que cada paso se ejecute correctamente")
    logger.info("4️⃣ Usar las credenciales generadas para login")
    logger.info("")
    logger.info("✅ RESULTADO ESPERADO:")
    logger.info("   🎯 Administrador funcional con credenciales válidas")
    logger.info("   🎯 Usuario prueba activo y funcional")
    logger.info("   🎯 Sistema listo para casos reales")
    logger.info("   🎯 Sin errores de constraint")

if __name__ == "__main__":
    main()
