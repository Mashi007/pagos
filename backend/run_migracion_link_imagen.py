"""
Ejecuta la migración: link_imagen en pagos_whatsapp + conversacion_cobranza + pagos_informes.
Usa DATABASE_URL del entorno o .env.
"""
import os
import sys
import re

# Asegurar que el directorio backend esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

def main():
    from app.core.database import engine
    migracion_path = os.path.join(os.path.dirname(__file__), "sql", "migracion_pagos_whatsapp_link_imagen.sql")
    with open(migracion_path, encoding="utf-8") as f:
        content = f.read()
    # Quitar líneas que son solo comentarios
    content = "\n".join(
        line for line in content.split("\n")
        if not line.strip().startswith("--") and line.strip()
    )
    # Dividir por ";\n" para no cortar dentro de un CREATE TABLE (solo al final de sentencia)
    statements = [s.strip() for s in re.split(r";\s*\n", content) if s.strip()]
    with engine.begin() as conn:  # begin() hace commit al salir
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            if not stmt.endswith(";"):
                stmt = stmt + ";"
            try:
                conn.execute(text(stmt))
                print("OK:", stmt[:70].replace("\n", " ").strip() + "...")
            except Exception as e:
                print("Error en:", stmt[:70], "->", e)
                raise
    print("Migración aplicada correctamente.")

if __name__ == "__main__":
    main()
