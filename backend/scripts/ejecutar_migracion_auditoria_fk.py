#!/usr/bin/env python3
"""
Ejecuta la migración migracion_auditoria_fk_usuarios.sql en la BD.

Corrige el error: "Key (usuario_id)=(X) is not present in users"
La FK auditoria.usuario_id debe apuntar a usuarios (no a users).

Uso (desde backend/):
  python scripts/ejecutar_migracion_auditoria_fk.py

O con DATABASE_URL explícito:
  DATABASE_URL=postgresql://... python scripts/ejecutar_migracion_auditoria_fk.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.core.database import engine


def main():
    print("Ejecutando migración: auditoria.usuario_id FK -> usuarios(id)")
    print("-" * 50)

    with engine.connect() as conn:
        with conn.begin():
            # 1. DROP CONSTRAINT (IF EXISTS no falla si no existe)
            conn.execute(text("""
                ALTER TABLE auditoria
                DROP CONSTRAINT IF EXISTS auditoria_usuario_id_fkey
            """))
            print("[OK] DROP CONSTRAINT auditoria_usuario_id_fkey (si existia)")

            # 2. ADD CONSTRAINT (NOT VALID: no valida filas existentes; nuevas inserciones sí)
            # Hay filas en auditoria con usuario_id que no existe en usuarios (huérfanas).
            conn.execute(text("""
                ALTER TABLE auditoria
                ADD CONSTRAINT auditoria_usuario_id_fkey
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) NOT VALID
            """))
            print("[OK] ADD CONSTRAINT auditoria_usuario_id_fkey -> usuarios(id)")

    print("-" * 50)
    print("[OK] Migracion completada. La aprobacion manual de prestamos deberia funcionar.")


if __name__ == "__main__":
    main()
