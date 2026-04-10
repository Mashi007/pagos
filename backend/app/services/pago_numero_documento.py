"""Consultas sobre numero_documento. Clave almacenada única por comprobante + código (compose)."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError


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
