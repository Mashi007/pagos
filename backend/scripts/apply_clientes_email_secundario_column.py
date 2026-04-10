"""
Aplica backend/scripts/migracion_clientes_email_secundario.sql contra la BD (DATABASE_URL).

Uso (desde la carpeta backend, con venv activo):
  python scripts/apply_clientes_email_secundario_column.py
"""
from __future__ import annotations

import os
import sys

# Raiz backend en sys.path
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    sql_path = os.path.join(os.path.dirname(__file__), "migracion_clientes_email_secundario.sql")
    with open(sql_path, encoding="utf-8") as f:
        sql = f.read().strip()
    if not sql:
        raise SystemExit("SQL vacio")
    with engine.begin() as conn:
        conn.execute(text(sql))
    print("OK: columna clientes.email_secundario (creada o ya existente).")


if __name__ == "__main__":
    main()
