import os, sys
from pathlib import Path
from datetime import date, timedelta

# load .env
env_path = Path("backend/.env")
for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

sys.path.insert(0, "backend")
os.chdir("backend")

from sqlalchemy import create_engine, text
from app.core.config import settings

eng = create_engine(settings.DATABASE_URL)
ced = "E84491751"
# also try without E / digits only variants
desde = date(2026, 6, 1)
hasta = date(2026, 8, 2)
limite = hasta + timedelta(days=1)

sql = text("""
WITH norm AS (
  SELECT
    p.id AS prestamo_id,
    p.cedula,
    p.estado AS prestamo_estado,
    c.id AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto,
    c.estado AS cuota_estado,
    c.fecha_pago,
    c.total_pagado,
    COALESCE((
      SELECT SUM(cp.monto_aplicado)
      FROM cuota_pagos cp
      JOIN pagos pg ON pg.id = cp.pago_id
      WHERE cp.cuota_id = c.id
        AND pg.fecha_pago < :limite
        AND UPPER(TRIM(COALESCE(pg.estado,''))) NOT LIKE 'ANULADO%'
        AND UPPER(TRIM(COALESCE(pg.estado,''))) IS DISTINCT FROM 'DUPLICADO'
    ), 0) AS pagado_asof
  FROM prestamos p
  JOIN clientes cl ON cl.id = p.cliente_id
  JOIN cuotas c ON c.prestamo_id = p.id
  WHERE cl.estado = 'ACTIVO'
    AND UPPER(TRIM(p.estado)) IN ('APROBADO','LIQUIDADO')
    AND regexp_replace(UPPER(TRIM(COALESCE(p.cedula,''))), '[^0-9A-Z]', '', 'g')
        LIKE '%' || regexp_replace(UPPER(:ced), '[^0-9A-Z]', '', 'g') || '%'
)
SELECT
  prestamo_id, cedula, prestamo_estado, cuota_id, numero_cuota,
  fecha_vencimiento, monto, cuota_estado, fecha_pago, total_pagado, pagado_asof,
  CASE
    WHEN fecha_pago IS NOT NULL AND fecha_pago <= :hasta AND pagado_asof <= 0.009 THEN monto
    ELSE pagado_asof
  END AS pagado_efectivo
FROM norm
ORDER BY prestamo_id, numero_cuota
""")

with eng.connect() as conn:
    rows = conn.execute(sql, {"ced": ced, "limite": limite, "hasta": hasta}).mappings().all()
    print("TOTAL_CUOTAS", len(rows))
    if not rows:
        # broader search
        r2 = conn.execute(text("""
          SELECT id, cedula, estado FROM prestamos
          WHERE cedula ILIKE :c OR cedula ILIKE :c2
          LIMIT 20
        """), {"c": f"%84491751%", "c2": f"%E84491751%"}).mappings().all()
        print("PRESTAMOS_MATCH", list(r2))
    else:
        en_periodo = []
        for r in rows:
            fv = r["fecha_vencimiento"]
            if hasattr(fv, "date"):
                fv = fv.date()
            pe = float(r["pagado_efectivo"] or 0)
            mon = float(r["monto"] or 0)
            pagada = pe >= (mon - 0.01)
            impaga = (not pagada) and (str(r["cuota_estado"] or "") != "CANCELADA")
            flag_periodo = fv is not None and desde <= fv <= hasta
            if flag_periodo:
                en_periodo.append((r, pagada, impaga, pe, mon, fv))
            print(
                f"p={r['prestamo_id']} est={r['prestamo_estado']} n={r['numero_cuota']} "
                f"venc={fv} monto={mon} pagado_asof={pe:.2f} "
                f"{'PAGADA' if pagada else 'IMPAGA'} "
                f"{'IN_RANGE' if flag_periodo else 'out'}"
            )
        n_pag = sum(1 for _, pagada, _, _, _, _ in en_periodo if pagada)
        n_imp = sum(1 for _, pagada, impaga, _, _, _ in en_periodo if impaga)
        print("--- PERIODO", desde, hasta)
        print("n_pagadas", n_pag, "n_impagas", n_imp, "D=pagadas-impagas", n_pag - n_imp)
        print("filas_en_periodo", len(en_periodo))
