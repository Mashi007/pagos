#!/usr/bin/env python3
"""
Script para generar SQL completo con hash incluido
Genera un archivo SQL listo para ejecutar directamente en la base de datos
"""

import sys
import os
from datetime import datetime

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash

def generar_sql_completo(email: str, password: str, archivo_salida: str = "UPDATE_PASSWORD_FINAL.sql"):
    """Genera SQL completo con hash incluido"""

    # Generar hash de la contraseña
    hashed = get_password_hash(password)

    sql = f"""-- ============================================================================
-- SCRIPT SQL PARA ACTUALIZAR CONTRASEÑA EN BASE DE DATOS
-- Generado automáticamente el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- ============================================================================
--
-- Usuario: {email}
-- Nueva contraseña: {password}
-- Hash: {hashed}
--
-- INSTRUCCIONES:
-- 1. Ejecuta este script en tu base de datos PostgreSQL
-- 2. Verifica que el usuario existe antes de actualizar
-- 3. Los cambios se confirman automáticamente con COMMIT
--
-- Para ejecutar desde línea de comandos:
--   psql -U tu_usuario -d tu_base_de_datos -f {archivo_salida}
--
-- O copia y pega este contenido en pgAdmin, DBeaver, o tu cliente SQL favorito
-- ============================================================================

BEGIN;

-- Paso 1: Verificar que el usuario existe
SELECT
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    created_at,
    updated_at
FROM users
WHERE email = '{email}';

-- Paso 2: Actualizar contraseña con hash generado
UPDATE users
SET
    hashed_password = '{hashed}',
    updated_at = NOW()
WHERE email = '{email}';

-- Paso 3: Verificar que se actualizó correctamente
SELECT
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at,
    CASE
        WHEN updated_at > NOW() - INTERVAL '1 minute' THEN '✅ Contraseña actualizada correctamente'
        ELSE '⚠️ Verificar actualización'
    END as estado
FROM users
WHERE email = '{email}';

-- Paso 4: Confirmar cambios
COMMIT;

-- ============================================================================
-- ✅ Script completado
-- Ahora puedes iniciar sesión con:
--   Email: {email}
--   Contraseña: {password}
-- ============================================================================
"""

    # Guardar en archivo
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(sql)

    print("=" * 80)
    print("✅ SQL GENERADO EXITOSAMENTE")
    print("=" * 80)
    print(f"\n📄 Archivo generado: {archivo_salida}")
    print(f"👤 Usuario: {email}")
    print(f"🔑 Nueva contraseña: {password}")
    print(f"🔐 Hash generado: {hashed[:50]}...")
    print("\n" + "=" * 80)
    print("INSTRUCCIONES PARA EJECUTAR:")
    print("=" * 80)
    print("\n1. Ejecutar desde línea de comandos PostgreSQL:")
    print(f"   psql -U tu_usuario -d tu_base_de_datos -f {archivo_salida}")
    print("\n2. O desde psql interactivo:")
    print("   psql -U tu_usuario -d tu_base_de_datos")
    print(f"   \\i {archivo_salida}")
    print("\n3. O copia y pega el contenido del archivo en:")
    print("   - pgAdmin")
    print("   - DBeaver")
    print("   - DBeaver Cloud")
    print("   - Cualquier cliente SQL")
    print("\n" + "=" * 80)

    return archivo_salida

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_sql_completo.py <email> <password> [archivo_salida.sql]")
        print("\nEjemplo:")
        print("  python generar_sql_completo.py itmaster@rapicreditca.com Casa1803+")
        print("  python generar_sql_completo.py itmaster@rapicreditca.com Casa1803+ update.sql")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    archivo_salida = sys.argv[3] if len(sys.argv) > 3 else "UPDATE_PASSWORD_FINAL.sql"

    generar_sql_completo(email, password, archivo_salida)
