"""
Regla Binance: el Id. de orden / serial solo puede existir UNA vez en cartera.

No vale desambiguar con código (§CD: / codigo_documento / validador D#### u otros).
Si se intenta una segunda carga, no entra a `pagos`; va a revisión manual
(`pagos_con_errores`).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.documento import (
    split_numero_documento_almacenado,
)
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.services.pagos_gmail.parse_campos_comprobante import digitos_operacion_compacto
from app.services.pago_numero_documento import _candidatos_evasion_columna

MSG_BINANCE_SERIAL_DUPLICADO = (
    "BINANCE: este Id. de orden/serial ya está cargado en cartera. "
    "No se permite una segunda carga ni con código/validador. "
    "El caso queda en revisión manual."
)

MSG_BINANCE_NO_CODIGO = (
    "BINANCE: no se admite código ni validador (§CD: / D####). "
    "El Id. de orden solo puede existir una vez en cartera, sin desambiguar."
)


def es_institucion_binance(institucion: Optional[str]) -> bool:
    return "BINANCE" in (institucion or "").strip().upper()


def digitos_serial_binance(numero_documento: Optional[str]) -> str:
    """Dígitos del serial base (sin §CD:)."""
    if not numero_documento:
        return ""
    base, _codigo = split_numero_documento_almacenado(numero_documento)
    return digitos_operacion_compacto(base or numero_documento)


def binance_tiene_codigo_o_validador(
    numero_documento: Optional[str] = None,
    *,
    codigo_documento: Optional[str] = None,
) -> bool:
    """True si el payload o el valor almacenado trae §CD: / codigo_documento."""
    from app.core.documento import normalize_codigo_documento

    if normalize_codigo_documento(codigo_documento):
        return True
    if not numero_documento:
        return False
    _base, codigo = split_numero_documento_almacenado(numero_documento)
    return bool(normalize_codigo_documento(codigo))


def debe_aplicar_unicidad_binance(
    *,
    institucion_bancaria: Optional[str],
    numero_documento: Optional[str],
) -> bool:
    """True solo si la institución es Binance y hay serial con dígitos.

    No inferir Binance por longitud del serial: Mercantil (p. ej. 740087… de 15 dígitos)
    y otros bancos reutilizan seriales largos y sí pueden desambiguar con §CD:/D####.
    """
    digitos = digitos_serial_binance(numero_documento)
    return _aplica_regla_binance(
        institucion_nueva=institucion_bancaria, digitos=digitos
    )


def _aplica_regla_binance(
    *,
    institucion_nueva: Optional[str],
    digitos: str,
) -> bool:
    if not digitos:
        return False
    # Única fuente de verdad: el banco declarado. No usar longitud del serial.
    return es_institucion_binance(institucion_nueva)

def mensaje_binance_rechaza_codigo() -> str:
    return MSG_BINANCE_NO_CODIGO


def primer_pago_id_mismo_serial_binance(
    db: Session,
    numero_documento: Optional[str],
    *,
    institucion_bancaria: Optional[str] = None,
    exclude_pago_id: Optional[int] = None,
) -> Optional[int]:
    """
    Id del primer `Pago` operativo en cartera con el mismo serial Binance
    (misma secuencia de dígitos, ignorando §CD:). None si no hay conflicto.
    """
    digitos = digitos_serial_binance(numero_documento)
    if not digitos:
        return None
    if not _aplica_regla_binance(
        institucion_nueva=institucion_bancaria, digitos=digitos
    ):
        return None

    seen: set[int] = set()
    for cond, _tag in _candidatos_evasion_columna(Pago.numero_documento, digitos):
        q = select(
            Pago.id,
            Pago.numero_documento,
            Pago.institucion_bancaria,
        ).where(cond)
        if exclude_pago_id is not None:
            q = q.where(Pago.id != int(exclude_pago_id))
        q = q.order_by(Pago.id.asc()).limit(80)
        for pid, stored, inst in db.execute(q).all():
            ipid = int(pid)
            if ipid in seen:
                continue
            seen.add(ipid)
            if digitos_serial_binance(stored) != digitos:
                continue
            if es_institucion_binance(institucion_bancaria) or es_institucion_binance(
                inst
            ):
                return ipid
    return None


def mensaje_conflicto_binance(conflicto_pago_id: int) -> str:
    return (
        f"{MSG_BINANCE_SERIAL_DUPLICADO} "
        f"Conflicto con pagos.id={int(conflicto_pago_id)}."
    )


def asegurar_pago_con_error_binance_duplicado(
    db: Session,
    *,
    conflicto_pago_id: int,
    cedula_cliente: Optional[str],
    prestamo_id: Optional[int],
    fecha_pago: Any,
    monto_pagado: Any,
    numero_documento: Optional[str],
    institucion_bancaria: Optional[str],
    referencia_pago: Optional[str] = None,
    usuario_registro: Optional[str] = None,
    notas: Optional[str] = None,
) -> int:
    """
    Crea o reutiliza una fila en `pagos_con_errores` para revisión manual.
    Devuelve el id del pago_con_error.
    """
    digitos = digitos_serial_binance(numero_documento)
    num_store = (numero_documento or "").strip() or None
    detalle = mensaje_conflicto_binance(conflicto_pago_id)

    # Reutilizar PE pendiente con el mismo serial (base o con §CD:).
    if digitos:
        q = (
            select(PagoConError)
            .where(
                or_(
                    PagoConError.numero_documento == num_store,
                    PagoConError.numero_documento.like(f"{digitos}%"),
                    PagoConError.referencia_pago.like(f"%{digitos}%"),
                )
            )
            .order_by(PagoConError.id.desc())
            .limit(8)
        )
        for pe in db.execute(q).scalars().all():
            if digitos_serial_binance(pe.numero_documento or pe.referencia_pago) != digitos:
                continue
            est = (pe.estado or "").strip().upper()
            if est in ("RESUELTO", "ELIMINADO", "ANULADO"):
                continue
            pe.errores_descripcion = [detalle[:400]]
            obs = f"{(pe.observaciones or '').strip()} | {detalle}".strip(" |")
            pe.observaciones = obs[:255]
            if prestamo_id and not pe.prestamo_id:
                pe.prestamo_id = int(prestamo_id)
            db.flush()
            return int(pe.id)

    if fecha_pago is not None and hasattr(fecha_pago, "date"):
        fecha_ts = fecha_pago
    elif fecha_pago is not None:
        try:
            fecha_ts = datetime.combine(fecha_pago, datetime.min.time())
        except Exception:
            fecha_ts = datetime.utcnow()
    else:
        fecha_ts = datetime.utcnow()

    try:
        monto = Decimal(str(monto_pagado)) if monto_pagado is not None else Decimal("0")
    except Exception:
        monto = Decimal("0")

    ref = (referencia_pago or num_store or digitos or "N/A")[:100]
    pe = PagoConError(
        cedula_cliente=(cedula_cliente or "").strip() or None,
        prestamo_id=int(prestamo_id) if prestamo_id else None,
        fecha_pago=fecha_ts,
        monto_pagado=monto,
        numero_documento=num_store,
        institucion_bancaria=(institucion_bancaria or "BINANCE").strip()[:255],
        estado="PENDIENTE",
        conciliado=False,
        usuario_registro=(usuario_registro or "")[:255] or None,
        notas=(notas or "")[:500] or None,
        referencia_pago=ref,
        errores_descripcion=[detalle[:400]],
        observaciones=detalle[:255],
    )
    db.add(pe)
    db.flush()
    return int(pe.id)
