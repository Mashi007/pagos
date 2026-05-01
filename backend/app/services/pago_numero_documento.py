"""
Consultas sobre numero_documento.

Regla: el valor guardado en columna `numero_documento` es **único** en cartera. La única vía para dos pagos con el
mismo número “visible” del banco es que el **valor almacenado** difiera por **código** compuesto (`§CD:` vía
`compose_numero_documento_almacenado`), p. ej. revisión manual con token A####/P####.
"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError


def primer_pago_cartera_por_documento(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
) -> tuple[Optional[int], Optional[int]]:
    """
    Primer `Pago` en cartera cuyo `numero_documento` normalizado coincide.

    Returns (pago_id, prestamo_id) o (None, None). `exclude_pago_id` excluye el
    pago en edición para detectar *otro* registro con el mismo documento.
    """
    num = normalize_documento(numero_documento)
    if not num:
        return None, None
    nu = num.upper()
    q = select(Pago.id, Pago.prestamo_id).where(func.upper(Pago.numero_documento) == nu)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    q = q.order_by(Pago.id.asc()).limit(1)
    row = db.execute(q).first()
    if row is None:
        return None, None
    pid = int(row[0])
    prid = row[1]
    return pid, (int(prid) if prid is not None else None)


def documento_ya_en_tabla_pagos(db: Session, numero_documento: Optional[str]) -> bool:
    """
    True si el documento normalizado ya existe en la tabla `pagos` (cartera operativa).

    Usado en listados de `pagos_con_errores` para marcar filas que no podrán moverse
    hasta desambiguar con código (misma regla que mover-a-pagos).
    """
    other_id, _ = primer_pago_cartera_por_documento(db, numero_documento)
    return other_id is not None


def numero_documento_ya_registrado(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
) -> bool:
    """
    True si el valor almacenado (comprobante + §CD: + código) ya existe en `pagos` o `pagos_con_errores`.

    Comparación **insensible a mayúsculas** sobre la columna completa, alineada con duplicados
    que solo diferían en casing (misma clave operativa para el usuario).
    """
    num = normalize_documento(numero_documento)
    if not num:
        return False

    nu = num.upper()

    q = select(Pago.id).where(func.upper(Pago.numero_documento) == nu)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    if db.scalar(q) is not None:
        return True

    qe = (
        select(PagoConError.id)
        .where(func.upper(PagoConError.numero_documento) == nu)
        .limit(1)
    )
    return db.scalar(qe) is not None
