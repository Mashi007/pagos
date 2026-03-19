"""
Reaplica pagos conciliados a las cuotas de préstamos (p. ej. tras regenerar
la tabla de amortización con actualizar_amortizacion_mensual.py).
Llama a aplicar_pagos_pendientes_prestamo por cada préstamo.

Uso (desde backend, con venv activo):
  python conciliar_amortizacion_masiva.py              # todos los que tengan pagos pendientes de aplicar
  python conciliar_amortizacion_masiva.py --dry-run   # solo listar prestamo_ids que se procesarían
  python conciliar_amortizacion_masiva.py --ids 3425,3435,3436  # solo esos IDs
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo


def prestamos_con_pagos_pendientes_aplicar(db: Session):
    """Prestamo_ids que tienen al menos un pago conciliado con monto y sin fila en cuota_pagos."""
    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    r = db.execute(
        select(Pago.prestamo_id)
        .where(
            Pago.prestamo_id.isnot(None),
            Pago.conciliado == True,
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .distinct()
    ).scalars().all()
    return [x for x in r if x is not None]


def main():
    ap = argparse.ArgumentParser(description="Conciliar amortización masiva: aplicar pagos a cuotas")
    ap.add_argument("--dry-run", action="store_true", help="Solo listar préstamos a procesar, no modificar BD")
    ap.add_argument("--ids", type=str, default=None, help="Lista de prestamo_id separados por coma (ej. 3425,3435,3436)")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        if args.ids:
            ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        else:
            ids = prestamos_con_pagos_pendientes_aplicar(db)

        if not ids:
            print("No hay préstamos con pagos pendientes de aplicar a cuotas.")
            return

        print(f"Préstamos a procesar: {len(ids)}")
        if args.dry_run:
            print("IDs:", ids[:50], "..." if len(ids) > 50 else "")
            return

        pagos_aplicados = 0
        for prestamo_id in ids:
            try:
                n = aplicar_pagos_pendientes_prestamo(prestamo_id, db)
                if n > 0:
                    db.commit()
                    pagos_aplicados += n
                    print(f"  Préstamo {prestamo_id}: {n} pago(s) aplicados a cuotas.")
            except Exception as e:
                db.rollback()
                print(f"  Préstamo {prestamo_id}: Error - {e}")

        print(f"Listo. Total pagos aplicados: {pagos_aplicados}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
