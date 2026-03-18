"""Ejecuta la verificacion SQL de cuotas MENSUAL (mismo dia cada mes) e imprime resultado."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import text
from app.core.database import SessionLocal

SQL = """
WITH base AS (
  SELECT p.id AS prestamo_id,
    COALESCE((p.fecha_aprobacion)::date, p.fecha_base_calculo) AS fecha_base
  FROM prestamos p
  WHERE UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
    AND (p.fecha_aprobacion IS NOT NULL OR p.fecha_base_calculo IS NOT NULL)
),
expected AS (
  SELECT b.prestamo_id, c.numero_cuota, c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
),
desactualizados AS (
  SELECT DISTINCT prestamo_id FROM expected WHERE actual_vencimiento <> esperado_vencimiento
)
SELECT
  (SELECT COUNT(*) FROM prestamos WHERE UPPER(TRIM(COALESCE(modalidad_pago, ''))) = 'MENSUAL') AS total_mensual,
  (SELECT COUNT(*) FROM desactualizados) AS desactualizados,
  (SELECT COUNT(*) FROM desactualizados) = 0 AS se_cumple_en_todos
FROM prestamos LIMIT 1;
"""

def main():
    db = SessionLocal()
    try:
        r = db.execute(text(SQL)).fetchone()
        total, desact, cumple = r[0], r[1], r[2]
        print(f"total_prestamos_mensual={total} | prestamos_con_cuotas_desactualizadas={desact} | se_cumple_en_todos={cumple}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
