#!/usr/bin/env python3
"""
Script para generar SQL directo para actualizar contraseña en la base de datos
Genera un archivo SQL listo para ejecutar
"""

import sys
import os
from datetime import datetime

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash

def generar_sql_password(email: str, password: str, output_file: str = None):
    """Genera SQL para actualizar contraseña"""
    hashed = get_password_hash(password)

    sql = f"""-- Script SQL para actualizar contraseña de usuario
-- Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Email: {email}
-- Nueva contraseña: {password}

-- Verificar usuario antes de actualizar
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

-- Actualizar contraseña
UPDATE users
SET
    hashed_password = '{hashed}',
    updated_at = NOW()
WHERE email = '{email}';

-- Verificar actualización
SELECT
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at,
    CASE
        WHEN hashed_password = '{hashed}' THEN '✅ Contraseña actualizada correctamente'
        ELSE '❌ Error: La contraseña no se actualizó'
    END as estado
FROM users
WHERE email = '{email}';

-- Confirmar cambios
COMMIT;
"""

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sql)
        print(f"✅ SQL generado en: {output_file}")
        print("\nPara ejecutar en PostgreSQL:")
        print(f"  psql -U tu_usuario -d tu_base_de_datos -f {output_file}")
        print("\nO copia y pega el contenido del archivo en tu cliente SQL.")
    else:
        print(sql)

    return sql

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python actualizar_password_sql.py <email> <password> [archivo_salida.sql]")
        print("\nEjemplo:")
        print("  python actualizar_password_sql.py itmaster@rapicreditca.com Casa1803+")
        print("  python actualizar_password_sql.py itmaster@rapicreditca.com Casa1803+ update_password.sql")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    print("🔄 Generando SQL para actualizar contraseña...")
    print(f"   Email: {email}")
    print(f"   Nueva contraseña: {password}\n")

    generar_sql_password(email, password, output_file)
