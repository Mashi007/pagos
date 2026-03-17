#!/usr/bin/env python3
"""
Rearticula un préstamo: borra la aplicación de pagos a cuotas y vuelve a aplicar
todos los pagos del préstamo en orden cronológico con lógica FIFO (primera cuota
pendiente primero).

Uso (desde la raíz del repo):
  cd backend && python -c "
from scripts.rearticular_prestamo_fifo import rearticular_prestamo
rearticular_prestamo(2526)  # sustituir por el prestamo_id
"
O desde backend con PYTHONPATH=.:
  python scripts/rearticular_prestamo_fifo.py 2526
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

# Añadir backend al path para imports de app
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Cargar env si existe
env_path = os.path.join(os.path.dirname(BACKEND), ".env")
if os.path.isfile(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))


def rearticular_prestamo(prestamo_id: int, db=None):
    """
    Para el préstamo dado:
    1. Borra todos los CuotaPago de las cuotas del préstamo.
    2. Resetea total_pagado, pago_id, fecha_pago y estado/dias_mora en esas cuotas.
    3. Obtiene todos los pagos del préstamo ordenados por fecha_pago, id.
    4. Aplica cada pago a cuotas con la lógica FIFO (usa _aplicar_pago_a_cuotas_interno).
    """
    from sqlalchemy import delete, select
    from sqlalchemy.orm import Session

    from app.core.database import SessionLocal
    from app.models.cuota import Cuota
    from app.models.cuota_pago import CuotaPago
    from app.models.pago import Pago

    # Importar después de tener app en path
    from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno

    session = db or SessionLocal()
    try:
        cuotas = session.execute(
            select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota.asc())
        ).scalars().all()
        if not cuotas:
            return {"ok": False, "message": f"No hay cuotas para el préstamo {prestamo_id}"}

        cuota_ids = [c.id for c in cuotas]

        # 1) Borrar registros en cuota_pagos para estas cuotas
        session.execute(delete(CuotaPago).where(CuotaPago.cuota_id.in_(cuota_ids)))

        # 2) Resetear cuotas: total_pagado=0, pago_id=None, fecha_pago=None, estado según vencimiento
        for c in cuotas:
            c.total_pagado = None
            c.pago_id = None
            c.fecha_pago = None
            c.dias_mora = None
            # Estado inicial: PENDIENTE si no vencida, si vencida se puede dejar PENDIENTE y _aplicar lo actualizará
            from datetime import date
            hoy = date.today()
            if c.fecha_vencimiento and (c.fecha_vencimiento if hasattr(c.fecha_vencimiento, "year") else c.fecha_vencimiento) < hoy:
                c.estado = "VENCIDO"
            else:
                c.estado = "PENDIENTE"

        session.flush()

        # 3) Pagos del préstamo ordenados por fecha e id
        pagos = (
            session.execute(
                select(Pago)
                .where(Pago.prestamo_id == prestamo_id)
                .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
            )
        ).scalars().all()

        if not pagos:
            session.commit()
            return {"ok": True, "message": f"Préstamo {prestamo_id}: cuotas reseteadas; no hay pagos para aplicar."}

        # 4) Aplicar cada pago con FIFO
        total_cc = 0
        total_cp = 0
        for pago in pagos:
            if float(pago.monto_pagado or 0) <= 0:
                continue
            cc, cp = _aplicar_pago_a_cuotas_interno(pago, session)
            total_cc += cc
            total_cp += cp

        session.commit()
        return {
            "ok": True,
            "message": f"Préstamo {prestamo_id} rearticulado: {len(pagos)} pagos aplicados (FIFO); "
            f"{total_cc} cuotas completadas, {total_cp} parciales.",
            "pagos_aplicados": len(pagos),
            "cuotas_completadas": total_cc,
            "cuotas_parciales": total_cp,
        }
    except Exception as e:
        session.rollback()
        return {"ok": False, "message": str(e)}
    finally:
        if not db:
            session.close()


def main():
    if len(sys.argv) < 2:
        print("Uso: python rearticular_prestamo_fifo.py <prestamo_id>")
        sys.exit(1)
    try:
        pid = int(sys.argv[1])
    except ValueError:
        print("prestamo_id debe ser un número entero")
        sys.exit(1)
    result = rearticular_prestamo(pid)
    print(result["message"])
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
