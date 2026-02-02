"""
Ejecuta la migración: nombre_cliente, intento_confirmacion, observacion en conversacion_cobranza; observacion en pagos_informes.
"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

def main():
    from app.core.database import engine
    path = os.path.join(os.path.dirname(__file__), "sql", "migracion_confirmacion_identidad.sql")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    content = "\n".join(
        line for line in content.split("\n")
        if not line.strip().startswith("--") and line.strip()
    )
    statements = [s.strip() for s in re.split(r";\s*\n", content) if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            if not stmt.endswith(";"):
                stmt = stmt + ";"
            conn.execute(text(stmt))
            print("OK:", stmt[:70].replace("\n", " ").strip() + "...")
    print("Migración confirmación identidad aplicada.")

if __name__ == "__main__":
    main()
