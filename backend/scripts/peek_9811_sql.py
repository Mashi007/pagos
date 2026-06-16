import os, sys
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)
for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
url = os.environ.get("DATABASE_URL", "")[:60]
print("DB:", url)
print(db.execute(text("SELECT id,estado,updated_at FROM pagos_reportados WHERE id=9811")).fetchone())
db.close()
