import os
from pathlib import Path
from datetime import date, timedelta
from urllib.parse import urlparse

env_path = Path("backend/.env")
db_url = None
for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    if line.startswith("DATABASE_URL="):
        db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
print("db host", urlparse(db_url).hostname if db_url else None)

from sqlalchemy import create_engine, text
eng = create_engine(db_url)
ced = "E84491751"
desde = date(2026, 6, 1)
hasta = date(2026, 8, 2)
limite = hasta + timedelta(days=1)

# discover table names
with eng.connect() as conn:
    tabs = conn.execute(text("""
      SELECT table_name FROM information_schema.tables
      WHERE table_schema='public' AND table_name ILIKE ANY(ARRAY['%prestamo%','%cuota%','%cliente%','%pago%'])
      ORDER BY 1
    """)).scalars().all()
    print("tables", tabs[:40])
