"""Aplicar pagos pendientes a cuotas por préstamo (lógica compartida API + tests sin FastAPI)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, func, not_, select
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.pagos_cascada_aplicacion import _aplicar_pago_a_cuotas_interno
from app.services.pagos_sql_where import (
    _where_pago_elegible_reaplicacion_cascada,
    _where_pago_excluido_operacion,
)

logger = logging.getLogger(__name__)


def aplicar_pagos_pendientes_prestamo_con_diagnostico(prestamo_id: int, db: Session) -> dict[str, Any]:
    """
    Igual que aplicar_pagos_pendientes_prestamo pero devuelve diagnóstico para UI y soporte.

    diagnostico incluye conteos antes de aplicar y listas de pagos sin abono o con error.
    """
    vacio: dict[str, Any] = {
        "pagos_operativos_sin_cuota_pagos": 0,
        "pagos_elegibles_cascada_sin_cuota_pagos": 0,
        "pagos_no_elegibles_sin_cuota_pagos": 0,
        "pagos_con_intento_sin_abono_ids": [],
        "errores_por_pago": [],
    }
    prestamo_chk = db.get(Prestamo, prestamo_id)
    if prestamo_chk and (prestamo_chk.estado or "").strip().upper() == "DESISTIMIENTO":
        return {"pagos_con_aplicacion": 0, "diagnostico": vacio}

    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    base_operativo = and_(
        Pago.prestamo_id == prestamo_id,
        Pago.monto_pagado > 0,
        ~Pago.id.in_(subq),
        not_(_where_pago_excluido_operacion()),
    )
    n_oper = int(db.scalar(select(func.count()).select_from(Pago).where(base_operativo)) or 0)

    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            _where_pago_elegible_reaplicacion_cascada(),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
    ).scalars().all()

    n_eleg = len(rows)
    n_no_eleg = max(0, n_oper - n_eleg)

    n = 0
    sin_abono: list[int] = []
    errores: list[dict[str, Any]] = []

    for pago in rows:
        try:
            cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
            if cc > 0 or cp > 0:
                pago.estado = "PAGADO"
                n += 1
            else:
                sin_abono.append(int(pago.id))
        except Exception as e:
            logger.warning(
                "aplicar_pagos_pendientes_prestamo prestamo_id=%s pago id=%s: %s",
                prestamo_id,
                pago.id,
                e,
            )
            errores.append({"pago_id": int(pago.id), "error": str(e)})

    return {
        "pagos_con_aplicacion": n,
        "diagnostico": {
            "pagos_operativos_sin_cuota_pagos": n_oper,
            "pagos_elegibles_cascada_sin_cuota_pagos": n_eleg,
            "pagos_no_elegibles_sin_cuota_pagos": n_no_eleg,
            "pagos_con_intento_sin_abono_ids": sin_abono,
            "errores_por_pago": errores,
        },
    }


def aplicar_pagos_pendientes_prestamo(prestamo_id: int, db: Session) -> int:
    """
    Aplica a cuotas los pagos del préstamo que aún no tienen enlaces en cuota_pagos.

    Criterio de elegibilidad: conciliado, verificado_concordancia SI, o estado PAGADO;
    excluye anulados/reversados/duplicado declarado (alineado con auditoria cartera).

    No hace commit. Retorna el número de pagos a los que se les aplicó algo (cc o cp > 0).
    """
    return int(aplicar_pagos_pendientes_prestamo_con_diagnostico(prestamo_id, db)["pagos_con_aplicacion"])
