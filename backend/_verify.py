from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
try:
    q = lambda s: db.execute(text(s)).scalar()
    print("pend_sin_cuota", q(
        "SELECT COUNT(*) FROM pagos p WHERE UPPER(COALESCE(estado,''))='PENDIENTE' AND COALESCE(activo,true)=true "
        "AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id=p.id)"
    ))
    print("pend_total", q("SELECT COUNT(*) FROM pagos WHERE UPPER(COALESCE(estado,''))='PENDIENTE' AND COALESCE(activo,true)=true"))
    print("pagado_sin_cuota", q(
        "SELECT COUNT(*) FROM pagos p WHERE UPPER(COALESCE(estado,''))='PAGADO' AND COALESCE(activo,true)=true "
        "AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id=p.id)"
    ))
    # remaining limbos from original list
    print("still_open_sample")
    for r in db.execute(text(
        "SELECT id, estado, conciliado, prestamo_id, monto_pagado FROM pagos "
        "WHERE id IN (84900,86456,87469,87438) ORDER BY id"
    )).mappings():
        print(dict(r))
        tiene = db.execute(text("SELECT COUNT(*) FROM cuota_pagos WHERE pago_id=:i"), {"i": r["id"]}).scalar()
        print("  cuota_pagos", tiene)
finally:
    db.close()