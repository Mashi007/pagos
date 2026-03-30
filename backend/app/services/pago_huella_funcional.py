"""
Huella funcional de pagos: alineada con el indice ux_pagos_fingerprint_activos
(prestamo_id, fecha_pago::date, monto_pagado, ref_norm) sobre pagos operativos.

Evita insertar un segundo pago que colisione antes del flush y centraliza la exclusion
de estados no operativos (misma logica que auditoria de cartera).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.pago import _normalizar_referencia_pago
from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera

# Misma redaccion que POST /pagos (crear) para 409 por huella.
HTTP_409_DETAIL_HUELLA_FUNCIONAL = (
    "Pago duplicado por huella funcional: mismo prestamo, fecha, monto y referencia "
    "normalizada que un pago ya registrado. Si son dos operaciones distintas, use "
    "documento o referencia que no colisionen al normalizar (p. ej. BNC/ y el mismo "
    "numero sin prefijo cuentan como la misma huella)."
)

MSG_HUELLA_DUPLICADA_EN_LOTE = (
    "Misma huella funcional que otra fila de este archivo o lote (prestamo, fecha, monto y ref. normalizada). "
    "Revise duplicados tipo BNC/REF vs REF sin prefijo."
)


def mensaje_409_huella_funcional_con_id(conflicto_id: int) -> str:
    """Detalle 409 cuando la huella ya existe en `pagos` (incluye id para verificar en listado/SQL)."""
    return (
        f"{HTTP_409_DETAIL_HUELLA_FUNCIONAL} "
        f"Conflicto con fila en BD: pagos.id={conflicto_id}. "
        "Si ya elimino ese pago, confirme en /pagos/listado o SQL que no exista; "
        "si persiste, otro pago puede compartir la misma huella o el monto en USD difiere (Bs/tasa)."
    )


def ref_norm_desde_campos(
    numero_documento: Optional[str],
    referencia_pago: Optional[str],
) -> str:
    """Alineado con el listener before_insert de Pago (numero_documento o referencia_pago)."""
    base = numero_documento or referencia_pago or ""
    return _normalizar_referencia_pago(base)


def _tupla_huella_lote(
    prestamo_id: int,
    fecha_pago: date,
    monto_pagado: Decimal,
    ref_norm: str,
) -> tuple[int, str, str, str]:
    m = Decimal(str(round(float(monto_pagado), 2)))
    return (int(prestamo_id), fecha_pago.isoformat(), format(m, "f"), ref_norm.strip())


def conflicto_huella_para_creacion(
    db: Session,
    *,
    prestamo_id: Optional[int],
    fecha_pago: Optional[date],
    monto_pagado: Optional[Decimal],
    numero_documento: Optional[str],
    referencia_pago: Optional[str],
    exclude_pago_id: Optional[int] = None,
    huellas_en_mismo_lote: Optional[set[tuple[int, str, str, str]]] = None,
) -> Optional[str]:
    """
    None si se puede crear. Mensaje de error corto si choca con BD o con otra fila del mismo lote.
    Si huellas_en_mismo_lote se pasa y no hay conflicto, registra la huella en el set.
    """
    if not prestamo_id or fecha_pago is None or monto_pagado is None:
        return None
    rn = ref_norm_desde_campos(numero_documento, referencia_pago).strip()
    if not rn:
        return None
    m = Decimal(str(round(float(monto_pagado), 2)))
    key = _tupla_huella_lote(prestamo_id, fecha_pago, m, rn)
    if huellas_en_mismo_lote is not None and key in huellas_en_mismo_lote:
        return MSG_HUELLA_DUPLICADA_EN_LOTE
    cid = primer_id_conflicto_huella_funcional(
        db,
        prestamo_id=int(prestamo_id),
        fecha_pago=fecha_pago,
        monto_pagado=m,
        ref_norm=rn,
        exclude_pago_id=exclude_pago_id,
    )
    if cid is not None:
        return mensaje_409_huella_funcional_con_id(cid)
    if huellas_en_mismo_lote is not None:
        huellas_en_mismo_lote.add(key)
    return None


def contar_prestamos_con_huella_funcional_duplicada(db: Session) -> int:
    """Prestamos con al menos un par de pagos activos que comparten huella (control auditoria 16)."""
    excl = _sql_fragment_pago_excluido_cartera("p")
    sql = f"""
        SELECT COUNT(DISTINCT s.prestamo_id) FROM (
          SELECT p.prestamo_id
          FROM pagos p
          WHERE p.prestamo_id IS NOT NULL
            AND NOT {excl}
            AND TRIM(COALESCE(p.ref_norm, '')) <> ''
          GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado, TRIM(COALESCE(p.ref_norm, ''))
          HAVING COUNT(*) > 1
        ) s
    """
    return int(db.scalar(text(sql)) or 0)


def primer_id_conflicto_huella_funcional(
    db: Session,
    *,
    prestamo_id: int,
    fecha_pago: date,
    monto_pagado: Decimal,
    ref_norm: str,
    exclude_pago_id: Optional[int] = None,
) -> Optional[int]:
    """
    ID del primer pago operativo que comparte huella, o None.
    ref_norm vacio no se considera.
    """
    rn = (ref_norm or "").strip()
    if not rn:
        return None
    excl = _sql_fragment_pago_excluido_cartera("p")
    sql = f"""
        SELECT p.id FROM pagos p
        WHERE p.prestamo_id = :pid
          AND CAST(p.fecha_pago AS date) = :fd
          AND p.monto_pagado = :monto
          AND TRIM(COALESCE(p.ref_norm, '')) = :rn
          AND NOT {excl}
          {"AND p.id <> :exid" if exclude_pago_id is not None else ""}
        ORDER BY p.id
        LIMIT 1
    """
    params: dict = {
        "pid": prestamo_id,
        "fd": fecha_pago,
        "monto": monto_pagado,
        "rn": rn,
    }
    if exclude_pago_id is not None:
        params["exid"] = exclude_pago_id
    row = db.execute(text(sql), params).first()
    if not row or row[0] is None:
        return None
    return int(row[0])


def existe_otro_pago_misma_huella_funcional(
    db: Session,
    *,
    prestamo_id: int,
    fecha_pago: date,
    monto_pagado: Decimal,
    ref_norm: str,
    exclude_pago_id: Optional[int] = None,
) -> bool:
    """
    True si ya hay un pago operativo del mismo prestamo con la misma fecha (calendario),
    monto y ref_norm. ref_norm vacio no se considera (evita falsos positivos masivos).
    """
    return (
        primer_id_conflicto_huella_funcional(
            db,
            prestamo_id=prestamo_id,
            fecha_pago=fecha_pago,
            monto_pagado=monto_pagado,
            ref_norm=ref_norm,
            exclude_pago_id=exclude_pago_id,
        )
        is not None
    )
