"""
Ejecuta la creación de la función copia_prest_feb_a_prestamos() en la BD.
Uso: desde la carpeta backend, python run_crear_funcion_prest_feb.py
"""
import sys
from pathlib import Path

# Asegurar que se cargue el .env y el app
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.core.database import engine

SQL_FILE = Path(__file__).parent / "sql" / "programar_prest_feb_cron.sql"

def main():
    content = SQL_FILE.read_text(encoding="utf-8")
    # Extraer solo el bloque CREATE FUNCTION (hasta $$;)
    start = content.find("CREATE OR REPLACE FUNCTION")
    if start == -1:
        print("No se encontró CREATE OR REPLACE FUNCTION en el script.")
        sys.exit(1)
    end = content.find("$$;", start) + 3
    sql = content[start:end].strip()

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("OK: Función public.copia_prest_feb_a_prestamos() creada o actualizada.")

if __name__ == "__main__":
    main()
