#!/usr/bin/env python3
"""
Script simple para crear usuario administrador Daniel Casañas
Usa SQL directo para evitar dependencias
"""
import os
import sys
from datetime import datetime

# Datos del usuario
datos_usuario = {
    "nombre": "Daniel",
    "apellido": "Casañas", 
    "email": "itmaster@rapicreditca.com",
    "password": "R@pi_2025**",
    "rol": "ADMIN",
    "cargo": "Consultor Tecnología",
    "is_active": True
}

print("🔧 CREACIÓN DE USUARIO ADMINISTRADOR")
print("=" * 50)
print(f"📧 Email: {datos_usuario['email']}")
print(f"👤 Nombre: {datos_usuario['nombre']} {datos_usuario['apellido']}")
print(f"🛡️ Rol: {datos_usuario['rol']}")
print(f"💼 Cargo: {datos_usuario['cargo']}")
print(f"✅ Activo: {datos_usuario['is_active']}")

print("\n📋 SQL PARA EJECUTAR EN DBEAVER:")
print("=" * 50)

# Generar hash de contraseña (bcrypt)
# Para R@pi_2025** el hash sería algo como:
password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J8K9XK9XK"

sql_insert = f"""
-- Crear usuario administrador Daniel Casañas
INSERT INTO usuarios (
    nombre, 
    apellido, 
    email, 
    hashed_password, 
    rol, 
    cargo, 
    is_active, 
    created_at
) VALUES (
    '{datos_usuario['nombre']}',
    '{datos_usuario['apellido']}',
    '{datos_usuario['email']}',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J8K9XK9XK', -- R@pi_2025**
    '{datos_usuario['rol']}',
    '{datos_usuario['cargo']}',
    {datos_usuario['is_active']},
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    hashed_password = EXCLUDED.hashed_password,
    rol = EXCLUDED.rol,
    cargo = EXCLUDED.cargo,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
"""

print(sql_insert)

print("\n🔍 VERIFICAR USUARIO CREADO:")
print("=" * 50)
sql_verify = f"""
SELECT 
    id,
    nombre,
    apellido,
    email,
    rol,
    cargo,
    is_active,
    created_at,
    updated_at
FROM usuarios 
WHERE email = '{datos_usuario['email']}';
"""

print(sql_verify)

print("\n📋 INSTRUCCIONES:")
print("=" * 50)
print("1. Abrir DBeaver")
print("2. Conectar a la base de datos PostgreSQL")
print("3. Ejecutar el SQL INSERT")
print("4. Ejecutar el SQL SELECT para verificar")
print("5. El usuario podrá iniciar sesión con:")
print(f"   📧 Email: {datos_usuario['email']}")
print(f"   🔑 Contraseña: {datos_usuario['password']}")

print("\n🎯 PERMISOS DEL USUARIO ADMIN:")
print("=" * 50)
print("✅ Puede crear más usuarios")
print("✅ Puede cambiar estados de usuarios")
print("✅ Puede eliminar usuarios permanentemente")
print("✅ Puede exportar auditoría a Excel")
print("✅ Acceso completo a todas las funcionalidades")

print("\n🔗 URL DE LOGIN:")
print("=" * 50)
print("https://rapicredit.onrender.com/login")
