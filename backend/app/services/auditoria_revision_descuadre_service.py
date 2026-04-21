"""
Detalle para revision UI: totales pagos operativos vs aplicado (cuota_pagos) y listado de pagos del prestamo.
Misma exclusion de pagos no operativos que `prestamo_cartera_auditoria`.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.services.prestamo_cartera_auditoria import (
    _sql_fragment_pago_excluido_cartera,
    totales_pagos_operativos_y_aplicado_cuotas_prestamo,
)

_TOL = Decimal("0.02")


def _dec(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def revision_descuadre_pagos_cuotas_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    pid = int(prestamo_id)
    row_p = db.get(Prestamo, pid)
    if not row_p:
        return {"error": "prestamo_no_encontrado", "prestamo_id": pid}

    sp, sa = totales_pagos_operativos_y_aplicado_cuotas_prestamo(db, pid)
    diff = abs(sp - sa)

    excl = _sql_fragment_pago_excluido_cartera("p")
    rows = db.execute(
        text(
            f"""
            SELECT
              p.id,
              p.fecha_pago,
              p.monto_pagado,
              p.estado,
              p.numero_documento,
              p.referencia_pago,
              p.moneda_registro,
              p.conciliado,
              COALESCE((
                SELECT SUM(cp.monto_aplicado)
                FROM cuota_pagos cp
                WHERE cp.pago_id = p.id
              ), 0) AS sum_aplicado,
              CASE WHEN NOT ({excl}) THEN true ELSE false END AS cuenta_operativo
            FROM pagos p
            WHERE p.prestamo_id = :pid
            ORDER BY p.fecha_pago NULLS LAST, p.id
            """
        ),
        {"pid": pid},
    ).fetchall()

    pagos_out: list[dict[str, Any]] = []
    tiene_huerfano_operativo = False
    for r in rows:
        monto = _dec(r[2])
        sum_ap = _dec(r[8])
        cuenta_op = bool(r[9])
        conc = r[7]
        saldo = monto - sum_ap
        if cuenta_op and monto > 0 and saldo > _TOL:
            tiene_huerfano_operativo = True
        pagos_out.append(
            {
                "pago_id": int(r[0]),
                "fecha_pago": r[1].isoformat() if r[1] else None,
                "monto_pagado": str(monto),
                "estado": r[3] or "",
                "numero_documento": r[4] or "",
                "referencia_pago": r[5] or "",
                "moneda_registro": r[6] or "",
                "conciliado": bool(conc) if conc is not None else False,
                "cuenta_operativo_cartera": cuenta_op,
                "sum_aplicado_cuotas": str(sum_ap),
                "saldo_sin_aplicar_usd": str(saldo),
            }
        )

    cu_rows = db.execute(
        text(
            """
            SELECT id, numero_cuota, monto_cuota, COALESCE(total_pagado, 0) AS total_pagado, estado
            FROM cuotas
            WHERE prestamo_id = :pid
            ORDER BY numero_cuota
            """
        ),
        {"pid": pid},
    ).fetchall()
    cuotas_out = [
        {
            "cuota_id": int(c[0]),
            "numero_cuota": int(c[1] or 0),
            "monto_cuota": str(_dec(c[2])),
            "total_pagado": str(_dec(c[3])),
            "estado": (c[4] or "").strip(),
        }
        for c in cu_rows
    ]

    cuadrado = diff <= _TOL and not tiene_huerfano_operativo
    es_liq = (row_p.estado or "").strip().upper() == "LIQUIDADO"
    falta_fecha_liq = es_liq and row_p.fecha_liquidado is None
    if cuadrado and falta_fecha_liq:
        semaforo = "amarillo"
    elif cuadrado:
        semaforo = "verde"
    else:
        semaforo = "rojo"

    fecha_liq = row_p.fecha_liquidado.isoformat() if row_p.fecha_liquidado else None

    sum_monto_cuotas = sum(_dec(c["monto_cuota"]) for c in cuotas_out)
    sum_total_pagado_column = sum(_dec(c["total_pagado"]) for c in cuotas_out)
    n_pagos_bd = len(pagos_out)
    n_pagos_op = sum(1 for p in pagos_out if p.get("cuenta_operativo_cartera"))
    n_cuotas_bd = len(cuotas_out)
    n_pagos_saldo_fuera_tol = sum(
        1
        for p in pagos_out
        if p.get("cuenta_operativo_cartera")
        and _dec(p.get("monto_pagado")) > 0
        and _dec(p.get("saldo_sin_aplicar_usd")) > _TOL
    )

    return {
        "prestamo_id": pid,
        "cliente_id": int(row_p.cliente_id) if row_p.cliente_id is not None else None,
        "prestamo_cedula": (row_p.cedula or "").strip(),
        "prestamo_nombres": (row_p.nombres or "").strip(),
        "total_financiamiento_usd": str(_dec(row_p.total_financiamiento)),
        "numero_cuotas_config": int(row_p.numero_cuotas or 0),
        "sum_monto_cuotas_usd": str(sum_monto_cuotas),
        "sum_total_pagado_column_cuotas_usd": str(sum_total_pagado_column),
        "n_pagos_en_bd": n_pagos_bd,
        "n_pagos_operativos_cartera": n_pagos_op,
        "n_pagos_operativos_saldo_fuera_tol": n_pagos_saldo_fuera_tol,
        "n_cuotas_en_bd": n_cuotas_bd,
        "estado_prestamo": (row_p.estado or "").strip(),
        "fecha_liquidado": fecha_liq,
        "sum_pagos_operativos_usd": str(sp),
        "sum_aplicado_cuotas_usd": str(sa),
        "diff_usd": str(diff),
        "tolerancia_usd": str(_TOL),
        "semaforo_cuadre": semaforo,
        "tiene_pago_operativo_sin_aplicar_fuera_tol": tiene_huerfano_operativo,
        "pagos": pagos_out,
        "cuotas": cuotas_out,
    }
