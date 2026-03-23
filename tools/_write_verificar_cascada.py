from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "backend" / "verificar_cascada.py"
p.write_text(
    r'''"""
Verificacion en cascada: comprueba que los pagos aplicados a cuotas respetan el orden
de numero_cuota (primero la cuota mas antigua), sin "saltos" hacia cuotas posteriores.

Uso:
  cd backend && python -m verificar_cascada
  o: python backend/verificar_cascada.py

Requiere DATABASE_URL en .env o variables de entorno.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import SessionLocal
from app.models.cuota import Cuota


def verificar_cascada(db: Session) -> dict:
    """
    Detecta violaciones de orden en cascada: cuota posterior con pago mientras una anterior
    no esta totalmente pagada (total_pagado < monto - 0.01).
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
    cumple = len(violaciones) == 0
    resultado_cascada = "CUMPLE_CASCADA" if cumple else "NO_CUMPLE_CASCADA"
    resultado_fifo = "CUMPLE_FIFO" if cumple else "NO_CUMPLE_FIFO"
    total_prestamos = len({v["prestamo_id"] for v in violaciones}) if violaciones else 0
    return {
        "resultado_cascada": resultado_cascada,
        "resultado_fifo": resultado_fifo,
        "total_violaciones": len(violaciones),
        "total_prestamos_afectados": total_prestamos,
        "violaciones": violaciones,
    }


def main() -> None:
    db = SessionLocal()
    try:
        out = verificar_cascada(db)
        print("Resultado cascada:", out["resultado_cascada"])
        print("Total violaciones:", out["total_violaciones"])
        print("Prestamos afectados:", out["total_prestamos_afectados"])
        if out["violaciones"]:
            print("\nDetalle (primeras 20):")
            for v in out["violaciones"][:20]:
                print(
                    f"  Prestamo {v['prestamo_id']}: cuota {v['numero_cuota_anterior']} "
                    f"(id={v['cuota_anterior_id']}) no completada vs cuota {v['numero_cuota_posterior']} "
                    f"(id={v['cuota_posterior_id']}) con pago."
                )
        ok = out["resultado_cascada"] == "CUMPLE_CASCADA"
        sys.exit(0 if ok else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
''',
    encoding="utf-8",
    newline="\n",
)
print("wrote", p)

wf = ROOT / "backend" / "verificar_fifo.py"
wf.write_text(
    '''"""Compat: nombre historico; delega en verificar_cascada."""
from __future__ import annotations

from verificar_cascada import main, verificar_cascada

verificar_fifo = verificar_cascada

if __name__ == "__main__":
    main()
''',
    encoding="utf-8",
    newline="\n",
)
print("wrote", wf)
