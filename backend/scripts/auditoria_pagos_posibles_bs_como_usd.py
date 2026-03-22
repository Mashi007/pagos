#!/usr/bin/env python3
"""Cuenta y lista pagos con patrón Bs. copiado en monto_pagado (join operación = referencia_pago)."""
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from sqlalchemy import text  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402

SQL_A = """
SELECT COUNT(*) FROM pagos p
JOIN pagos_reportados pr ON TRIM(BOTH FROM pr.numero_operacion) = TRIM(BOTH FROM p.referencia_pago)
JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND ABS(p.monto_pagado::numeric - pr.monto::numeric) < 0.02
"""
SQL_B = """
SELECT COUNT(*) FROM pagos p
JOIN pagos_reportados pr ON TRIM(BOTH FROM pr.numero_operacion) = TRIM(BOTH FROM p.referencia_pago)
LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND ABS(p.monto_pagado::numeric - pr.monto::numeric) < 0.02
  AND tc.fecha IS NULL
"""
SQL_C = """
SELECT COUNT(*) FROM pagos p
WHERE p.conciliado IS TRUE
  AND (p.moneda_registro IS NULL OR LOWER(TRIM(p.moneda_registro)) = 'usd')
  AND p.monto_pagado > 2500
"""
SQL_SAMPLE_A = """
SELECT p.id, p.monto_pagado, p.referencia_pago, pr.referencia_interna, pr.monto AS monto_bs
FROM pagos p
JOIN pagos_reportados pr ON TRIM(BOTH FROM pr.numero_operacion) = TRIM(BOTH FROM p.referencia_pago)
JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND ABS(p.monto_pagado::numeric - pr.monto::numeric) < 0.02
ORDER BY p.monto_pagado DESC
LIMIT 30
"""
SQL_SAMPLE_C = """
SELECT p.id, p.monto_pagado, p.moneda_registro, p.referencia_pago
FROM pagos p
WHERE p.conciliado IS TRUE
  AND (p.moneda_registro IS NULL OR LOWER(TRIM(p.moneda_registro)) = 'usd')
  AND p.monto_pagado > 2500
ORDER BY p.monto_pagado DESC
LIMIT 30
"""


def main() -> None:
    db = SessionLocal()
    try:
        n_a = db.execute(text(SQL_A)).scalar()
        n_b = db.execute(text(SQL_B)).scalar()
        n_c = db.execute(text(SQL_C)).scalar()
        print("A) BS reporte = monto_pagado (con tasa):", n_a)
        print("B) Mismo patrón sin tasa en tasas_cambio_diaria:", n_b)
        print("C) Conciliado, moneda NULL/USD, monto_pagado > 2500:", n_c)
        if n_a:
            print("\nDetalle A (hasta 30):")
            for row in db.execute(text(SQL_SAMPLE_A)):
                print(" ", row)
        if n_c:
            print("\nDetalle C (hasta 30):")
            for row in db.execute(text(SQL_SAMPLE_C)):
                print(" ", row)
    finally:
        db.close()


if __name__ == "__main__":
    main()
