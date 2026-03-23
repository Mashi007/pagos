"""One-off patch script; run from repo root: python tools/_patch_cascada_auto.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_reaplicacion() -> None:
    p = ROOT / "backend/app/services/pagos_cuotas_reaplicacion.py"
    text = p.read_text(encoding="utf-8")
    old = """from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.prestamo import Prestamo"""
    new = """from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo"""
    if old not in text:
        raise SystemExit("reaplicacion: import block not found")
    text = text.replace(old, new, 1)
    marker = """    }


def reset_y_reaplicar_cascada_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:"""
    insert = """    }


def prestamo_requiere_correccion_cascada(db: Session, prestamo_id: int) -> bool:
    \"\"\"True si hace falta reaplicar en cascada: integridad rota u orfano en pagos conciliados sin cuota_pagos.\"\"\"
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return False
    n_cuotas = int(
        db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    )
    if n_cuotas == 0:
        return False
    integ = integridad_cuotas_prestamo(db, prestamo_id)
    if integ.get("ok") and not integ.get("integridad_ok"):
        return True
    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    n_orphans = db.scalar(
        select(func.count())
        .select_from(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
    ) or 0
    return int(n_orphans) > 0


def reset_y_reaplicar_cascada_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:"""
    if marker not in text:
        raise SystemExit("reaplicacion: marker not found")
    text = text.replace(marker, insert, 1)
    p.write_text(text, encoding="utf-8")
    print("patched", p)


def patch_sincronizacion() -> None:
    p = ROOT / "backend/app/services/pagos_cuotas_sincronizacion.py"
    text = p.read_text(encoding="utf-8")
    old = '''"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session


def sincronizar_pagos_pendientes_a_prestamos(db: Session, prestamo_ids: List[int]) -> int:
    """
    Por cada prAcstamo, aplica a cuotas los pagos que aA�n no tienen fila en cuota_pagos.
    Hace commit si al menos un pago fue procesado. Retorna cuA�ntos pagos recibieron aplicaciA3n (suma de retornos internos).
    """
    if not prestamo_ids:
        return 0
    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo

    n = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
    if n > 0:
        db.commit()
    return n
'''
    # File may have different encoding for special chars - read actual and match flexibly
    if "def sincronizar_pagos_pendientes_a_prestamos" not in text:
        raise SystemExit("sincronizacion: function not found")

    # Replace entire file with clean UTF-8 version
    new = '''"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def sincronizar_pagos_pendientes_a_prestamos(db: Session, prestamo_ids: List[int]) -> int:
    """
    Por cada prestamo:
    1) Aplica pagos conciliados que aun no tienen fila en cuota_pagos.
    2) Si la integridad cuota/total_pagado vs cuota_pagos falla o quedan pagos conciliados
       sin articulacion, reaplica en cascada (misma logica que POST reaplicar-cascada-aplicacion).

    Hace commit si hubo aplicacion incremental o reaplicacion en cascada.
    Retorna cuantos pagos recibieron aplicacion incremental (compatibilidad con llamadas existentes).
    """
    if not prestamo_ids:
        return 0
    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo
    from app.services.pagos_cuotas_reaplicacion import (
        prestamo_requiere_correccion_cascada,
        reset_y_reaplicar_cascada_prestamo,
    )

    n = 0
    cascadas = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
        if prestamo_requiere_correccion_cascada(db, pid):
            r = reset_y_reaplicar_cascada_prestamo(db, pid)
            if r.get("ok"):
                cascadas += 1
                logger.info(
                    "reaplicacion cascada auto prestamo_id=%s pagos_reaplicados=%s",
                    pid,
                    r.get("pagos_reaplicados"),
                )
            else:
                logger.warning(
                    "reaplicacion cascada auto omitida prestamo_id=%s error=%s",
                    pid,
                    r.get("error"),
                )
    if n > 0 or cascadas > 0:
        db.commit()
    return n
'''
    # Avoid replacing wrong content: only replace function body region
    if "prestamo_requiere_correccion_cascada" in text:
        print("sincronizacion already patched")
        return
    p.write_text(new, encoding="utf-8")
    print("patched", p)


if __name__ == "__main__":
    patch_reaplicacion()
    patch_sincronizacion()
