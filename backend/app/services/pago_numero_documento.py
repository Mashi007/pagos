"""Unicidad global del numero_documento de pago (pagos + pagos_con_errores)."""

from typing import Optional

from sqlalchemy import select
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
    True si el documento normalizado ya existe en `pagos` o en `pagos_con_errores`.

    Vacío/None no colisiona. Misma clave canónica que normalize_documento().
    """
    num = normalize_documento(numero_documento)
    if not num:
        return False

    q = select(Pago.id).where(Pago.numero_documento == num)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    if db.scalar(q) is not None:
        return True

    qe = select(PagoConError.id).where(PagoConError.numero_documento == num).limit(1)
    return db.scalar(qe) is not None
