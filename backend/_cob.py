from sqlalchemy import text
from app.core.database import SessionLocal
db=SessionLocal()
try:
  tables=set(r[0] for r in db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).fetchall())
  for t in sorted(tables):
    if "report" in t or "cobro" in t:
      print("T", t)
  # pagos_reportados if exists
  if "pagos_reportados" in tables:
    cols=[c["name"] for c in __import__("sqlalchemy").inspect(db.bind).get_columns("pagos_reportados")]
    print("cols", cols[:40])
    for r in db.execute(text(
      "SELECT estado, COUNT(*) n FROM pagos_reportados GROUP BY 1 ORDER BY n DESC LIMIT 20"
    )).mappings():
      print("est", dict(r))
    for r in db.execute(text(
      "SELECT COUNT(*) n FROM pagos_reportados WHERE created_at >= NOW() - INTERVAL '7 days'"
    )).mappings():
      print("7d", dict(r))
    print("sample recent")
    for r in db.execute(text(
      "SELECT id, estado, cedula, monto, moneda, LEFT(COALESCE(motivo_revision,''),80) mot, created_at "
      "FROM pagos_reportados ORDER BY id DESC LIMIT 15"
    )).mappings():
      print(dict(r))
finally:
  db.close()