"""
Digitalización incompleta / imagen compleja → revisión manual (sin truncar el proceso).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional, Tuple

from app.services.institucion_bancaria_requerida import es_institucion_bancaria_valida

MSG_REVISION_MANUAL_BASE = (
    "Comprobante complejo o ilegible: no se pudo digitalizar con consistencia. "
    "Pase a revisión manual, complete los campos y guarde. "
    "El proceso no se trunca: el comprobante queda en borrador/servidor para continuar."
)


def campos_criticos_faltantes_digitalizacion(
    *,
    fecha_pago: Any,
    institucion_financiera: Optional[str],
    numero_operacion: Optional[str],
    monto: Any,
) -> Tuple[str, ...]:
    """Nombres de campos críticos ausentes o inválidos tras OCR."""
    faltan: list[str] = []
    if not isinstance(fecha_pago, date):
        faltan.append("fecha")
    if not es_institucion_bancaria_valida(institucion_financiera):
        faltan.append("institución bancaria")
    if not (numero_operacion or "").strip():
        faltan.append("número de operación")
    if monto is None:
        faltan.append("monto")
    return tuple(faltan)


def mensaje_revision_manual_digitalizacion_incompleta(
    faltan: Tuple[str, ...],
) -> str:
    if not faltan:
        return MSG_REVISION_MANUAL_BASE
    lista = ", ".join(faltan)
    return (
        f"{MSG_REVISION_MANUAL_BASE} "
        f"Campos no digitalizados: {lista}."
    )


def fusionar_mensaje_revision(
    actual: Optional[str],
    nuevo: str,
) -> str:
    a = (actual or "").strip()
    n = (nuevo or "").strip()
    if not a:
        return n
    if not n or n in a:
        return a
    return f"{a} {n}".strip()


def digitalizacion_requiere_revision_manual(
    *,
    fecha_pago: Any,
    institucion_financiera: Optional[str],
    numero_operacion: Optional[str],
    monto: Any,
) -> Optional[str]:
    """
    Si faltan campos críticos tras OCR, devuelve mensaje de revisión manual.
    Si está completo, None.
    """
    faltan = campos_criticos_faltantes_digitalizacion(
        fecha_pago=fecha_pago,
        institucion_financiera=institucion_financiera,
        numero_operacion=numero_operacion,
        monto=monto,
    )
    if not faltan:
        return None
    return mensaje_revision_manual_digitalizacion_incompleta(faltan)
