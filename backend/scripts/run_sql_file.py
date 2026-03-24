"""Ejecuta un archivo .sql contra DATABASE_URL (una sentencia por bloque BEGIN/COMMIT o script completo)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/run_sql_file.py <ruta_relativa_o_absoluta.sql>")
        sys.exit(1)
    raw = sys.argv[1]
    p = Path(raw)
    if not p.is_file():
        p = Path(__file__).resolve().parents[2] / raw
    if not p.is_file():
        print("No existe:", raw)
        sys.exit(1)
    sql = p.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))
    print("OK:", p)


if __name__ == "__main__":
    main()
