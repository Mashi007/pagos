"""
Control 5 (pagos_mismo_dia_monto): listar candidatos y aplicar Visto (admin).
Anexa sufijo aleatorio de 4 digitos a numero_documento, marca exclusion en motor, registra auditoria.
"""
from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.models.auditoria_pago_control5_visto import AuditoriaPagoControl5Visto
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera

CODIGO_CONTROL = "pagos_mismo_dia_monto"
_MAX_DOC_LEN = 100
_MAX_TRIES_SUFFIX = 40


def _fragment_excluido_control5(alias: str) -> str:
    """Pago operativo para control 5 y no marcado con Visto previo."""
    a = alias.strip()
    excl_estado = _sql_fragment_pago_excluido_cartera(a)
    return f"(NOT ({excl_estado}) AND NOT COALESCE({a}.excluir_control_pagos_mismo_dia_monto, false))"


def listar_pagos_duplicados_fecha_monto_por_prestamo(
    db: Session, prestamo_id: int
) -> list[dict[str, Any]]:
    """Filas de `pagos` que participan en grupos (prestamo, dia, monto) con mas de un operativo no excluido."""
    pid = int(prestamo_id)
    excl = _fragment_excluido_control5("p")
    q = text(
        f"""
        WITH dup AS (
          SELECT p.prestamo_id, CAST(p.fecha_pago AS date) AS fd, p.monto_pagado
          FROM pagos p
          WHERE p.prestamo_id = :pid AND {excl}
          GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado
          HAVING COUNT(*) > 1
        )
        SELECT
          p.id AS pago_id,
          p.prestamo_id,
          CAST(p.fecha_pago AS date) AS fecha_pago,
          p.monto_pagado,
          p.conciliado,
          UPPER(TRIM(COALESCE(p.estado, ''))) AS estado_pago,
          TRIM(COALESCE(p.numero_documento, '')) AS numero_documento,
          TRIM(COALESCE(p.referencia_pago, '')) AS referencia_pago,
          TRIM(COALESCE(p.institucion_bancaria, '')) AS institucion_bancaria
        FROM pagos p
        JOIN dup d
          ON d.prestamo_id = p.prestamo_id
          AND d.fd = CAST(p.fecha_pago AS date)
          AND d.monto_pagado = p.monto_pagado
        WHERE p.prestamo_id = :pid AND {excl}
        ORDER BY p.fecha_pago, p.monto_pagado, p.id
        """
    )
    rows = db.execute(q, {"pid": pid}).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        monto = r[3]
        if monto is not None and not isinstance(monto, Decimal):
            monto = Decimal(str(monto))
        out.append(
            {
                "pago_id": int(r[0]),
                "prestamo_id": int(r[1]) if r[1] is not None else None,
                "fecha_pago": r[2].isoformat() if r[2] is not None else None,
                "monto_pagado": float(monto) if monto is not None else None,
                "conciliado": bool(r[4]) if r[4] is not None else False,
                "estado_pago": (r[5] or "")[:30],
                "numero_documento": (r[6] or "")[:100],
                "referencia_pago": (r[7] or "")[:100],
                "institucion_bancaria": (r[8] or "")[:255],
            }
        )
    return out


def _numero_documento_en_uso(db: Session, doc: str, exclude_pago_id: int) -> bool:
    d = (doc or "").strip()
    if not d:
        return False
    q1 = db.execute(
        select(Pago.id).where(Pago.numero_documento == d, Pago.id != exclude_pago_id).limit(1)
    ).scalar_one_or_none()
    if q1 is not None:
        return True
    q2 = db.execute(
        select(PagoConError.id)
        .where(
            or_(
                PagoConError.numero_documento == d,
                func.trim(PagoConError.numero_documento) == d,
            )
        )
        .limit(1)
    ).scalar_one_or_none()
    return q2 is not None


def _elegir_nuevo_numero_documento(db: Session, pago: Pago) -> tuple[str, str]:
    """Devuelve (nuevo_numero_completo, sufijo_4)."""
    prev_raw = (pago.numero_documento or "").strip()
    if not prev_raw:
        base = (pago.referencia_pago or "").strip() or f"PAGO-{pago.id}"
    else:
        base = prev_raw
    max_base = _MAX_DOC_LEN - 5
    if len(base) > max_base:
        base = base[:max_base]
    for _ in range(_MAX_TRIES_SUFFIX):
        suf = f"{secrets.randbelow(10000):04d}"
        nuevo = f"{base}-{suf}"
        if len(nuevo) > _MAX_DOC_LEN:
            continue
        if not _numero_documento_en_uso(db, nuevo, int(pago.id)):
            return nuevo, suf
    raise HTTPException(
        status_code=409,
        detail="No se pudo generar numero_documento unico tras varios intentos. Reintente.",
    )


def pago_en_grupo_duplicado_fecha_monto(db: Session, pago: Pago) -> bool:
    """True si el pago pertenece a un grupo (prestamo, dia, monto) con al menos 2 operativos no excluidos."""
    if pago.prestamo_id is None:
        return False
    excl = _fragment_excluido_control5("p")
    q = text(
        f"""
        SELECT COUNT(*)::int
        FROM pagos p
        WHERE p.prestamo_id = :pid
          AND CAST(p.fecha_pago AS date) = CAST(:fp AS date)
          AND p.monto_pagado = :monto
          AND {excl}
        """
    )
    row = db.execute(
        q,
        {
            "pid": int(pago.prestamo_id),
            "fp": pago.fecha_pago,
            "monto": pago.monto_pagado,
        },
    ).fetchone()
    n = int(row[0] or 0) if row else 0
    return n > 1


def aplicar_visto_control5_duplicado_fecha_monto(
    db: Session, pago_id: int, usuario_id: int
) -> dict[str, Any]:
    pago = db.get(Pago, int(pago_id))
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if getattr(pago, "excluir_control_pagos_mismo_dia_monto", False):
        raise HTTPException(
            status_code=400,
            detail="Este pago ya tiene Visto (excluido del control duplicado fecha/monto).",
        )
    if not pago_en_grupo_duplicado_fecha_monto(db, pago):
        raise HTTPException(
            status_code=400,
            detail="El pago no esta en un grupo duplicado (misma fecha y monto) con otro operativo, "
            "o ya no aplica tras cambios en la base.",
        )
    anterior = (pago.numero_documento or "").strip() or None
    nuevo, sufijo = _elegir_nuevo_numero_documento(db, pago)
    pago.numero_documento = nuevo
    pago.excluir_control_pagos_mismo_dia_monto = True
    bit = AuditoriaPagoControl5Visto(
        pago_id=int(pago.id),
        prestamo_id=int(pago.prestamo_id) if pago.prestamo_id is not None else None,
        usuario_id=int(usuario_id),
        numero_documento_anterior=anterior,
        numero_documento_nuevo=nuevo,
        sufijo_cuatro_digitos=sufijo,
        codigo_control=CODIGO_CONTROL,
    )
    db.add(bit)
    db.flush()
    return {
        "pago_id": int(pago.id),
        "prestamo_id": int(pago.prestamo_id) if pago.prestamo_id is not None else None,
        "numero_documento_anterior": anterior,
        "numero_documento_nuevo": nuevo,
        "sufijo_cuatro_digitos": sufijo,
        "auditoria_id": int(bit.id),
    }
