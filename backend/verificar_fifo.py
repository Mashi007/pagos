"""
Verificación FIFO: comprueba que los pagos aplicados a cuotas respetan
First In, First Out (primero la cuota más antigua por numero_cuota).

Uso:
  cd backend && python -m verificar_fifo
  o desde el directorio del proyecto:
  python backend/verificar_fifo.py

Requiere DATABASE_URL en .env o variables de entorno.
"""
from decimal import Decimal
import os
import sys

# Añadir backend al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import SessionLocal
from app.models.cuota import Cuota


def verificar_fifo(db: Session) -> dict:
    """
    Detecta violaciones FIFO: cuota posterior con pago mientras una anterior
    no está totalmente pagada (total_pagado < monto - 0.01).
    """
    C1 = aliased(Cuota, name="c_anterior")
    C2 = aliased(Cuota, name="c_posterior")
    q = (
        select(
            C1.prestamo_id,
            C1.id.label("cuota_anterior_id"),
            C1.numero_cuota.label("numero_cuota_anterior"),
            C1.monto.label("monto_anterior"),
            C1.total_pagado.label("total_pagado_anterior"),
            C1.estado.label("estado_anterior"),
            C2.id.label("cuota_posterior_id"),
            C2.numero_cuota.label("numero_cuota_posterior"),
            C2.monto.label("monto_posterior"),
            C2.total_pagado.label("total_pagado_posterior"),
            C2.estado.label("estado_posterior"),
        )
        .select_from(C1)
        .join(
            C2,
            and_(
                C1.prestamo_id == C2.prestamo_id,
                C1.numero_cuota < C2.numero_cuota,
            ),
        )
        .where(
            and_(
                C2.total_pagado.isnot(None),
                C2.total_pagado > 0,
                or_(
                    C1.total_pagado.is_(None),
                    C1.total_pagado < C1.monto - Decimal("0.01"),
                ),
            )
        )
        .order_by(C1.prestamo_id, C1.numero_cuota, C2.numero_cuota)
    )
    rows = db.execute(q).all()
    violaciones = [
        {
            "prestamo_id": r.prestamo_id,
            "cuota_anterior_id": r.cuota_anterior_id,
            "numero_cuota_anterior": r.numero_cuota_anterior,
            "monto_anterior": float(r.monto_anterior) if r.monto_anterior is not None else None,
            "total_pagado_anterior": float(r.total_pagado_anterior) if r.total_pagado_anterior is not None else None,
            "estado_anterior": r.estado_anterior,
            "cuota_posterior_id": r.cuota_posterior_id,
            "numero_cuota_posterior": r.numero_cuota_posterior,
            "monto_posterior": float(r.monto_posterior) if r.monto_posterior is not None else None,
            "total_pagado_posterior": float(r.total_pagado_posterior) if r.total_pagado_posterior is not None else None,
            "estado_posterior": r.estado_posterior,
        }
        for r in rows
    ]
    resultado = "CUMPLE_FIFO" if len(violaciones) == 0 else "NO_CUMPLE_FIFO"
    total_prestamos = len({v["prestamo_id"] for v in violaciones}) if violaciones else 0
    return {
        "resultado_fifo": resultado,
        "total_violaciones": len(violaciones),
        "total_prestamos_afectados": total_prestamos,
        "violaciones": violaciones,
    }


def main() -> None:
    db = SessionLocal()
    try:
        out = verificar_fifo(db)
        print("Resultado FIFO:", out["resultado_fifo"])
        print("Total violaciones:", out["total_violaciones"])
        print("Préstamos afectados:", out["total_prestamos_afectados"])
        if out["violaciones"]:
            print("\nDetalle (primeras 20):")
            for v in out["violaciones"][:20]:
                print(
                    f"  Préstamo {v['prestamo_id']}: cuota {v['numero_cuota_anterior']} "
                    f"(id={v['cuota_anterior_id']}) no completada vs cuota {v['numero_cuota_posterior']} "
                    f"(id={v['cuota_posterior_id']}) con pago."
                )
        sys.exit(0 if out["resultado_fifo"] == "CUMPLE_FIFO" else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
