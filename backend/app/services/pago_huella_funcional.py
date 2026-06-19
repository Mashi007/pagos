"""
Huella funcional de pagos: alineada con el indice ux_pagos_fingerprint_activos
(prestamo_id, fecha_pago::date, monto_pagado, ref_norm) sobre pagos operativos.

Evita insertar un segundo pago que colisione antes del flush y centraliza la exclusion
de estados no operativos (misma logica que auditoria de cartera).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.pago import _normalizar_referencia_pago
from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera

if TYPE_CHECKING:
    from app.models.pago_con_error import PagoConError

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
    if row and row[0] is not None:
        return int(row[0])

    # Pagos legacy sin ref_norm persistido: misma huella al normalizar documento/referencia.
    sql_legacy = f"""
        SELECT p.id, p.numero_documento, p.referencia_pago FROM pagos p
        WHERE p.prestamo_id = :pid
          AND CAST(p.fecha_pago AS date) = :fd
          AND p.monto_pagado = :monto
          AND TRIM(COALESCE(p.ref_norm, '')) = ''
          AND NOT {excl}
          {"AND p.id <> :exid" if exclude_pago_id is not None else ""}
    """
    for leg in db.execute(text(sql_legacy), params).all():
        if leg[0] is None:
            continue
        rn_calc = ref_norm_desde_campos(leg[1], leg[2]).strip()
        if rn_calc == rn:
            return int(leg[0])
    return None


def primer_par_huella_duplicada_prestamo(
    db: Session,
    prestamo_id: int,
) -> Optional[tuple[int, int]]:
    """
    Primer par de pagos operativos del prestamo que comparten huella funcional
    (fecha, monto, ref_norm normalizada desde documento/referencia).
    """
    from sqlalchemy import not_, select

    from app.models.pago import Pago
    from app.services.pagos_sql_where import _where_pago_excluido_operacion

    rows = db.execute(
        select(Pago).where(
            Pago.prestamo_id == prestamo_id,
            Pago.monto_pagado > 0,
            not_(_where_pago_excluido_operacion()),
        )
    ).scalars().all()

    visto: dict[tuple[int, str, str, str], int] = {}
    for p in rows:
        fp = p.fecha_pago
        if fp is not None and hasattr(fp, "date") and callable(getattr(fp, "date", None)):
            fp = fp.date()
        if not isinstance(fp, date):
            continue
        rn = ref_norm_desde_campos(p.numero_documento, p.referencia_pago).strip()
        if not rn:
            continue
        m = Decimal(str(round(float(p.monto_pagado or 0), 2)))
        key = _tupla_huella_lote(int(prestamo_id), fp, m, rn)
        pid = int(p.id)
        if key in visto:
            return (visto[key], pid)
        visto[key] = pid
    return None


HTTP_409_DETAIL_DOCUMENTO_DUPLICADO = (
    "Ya existe un pago o registro en revisión con la misma combinación comprobante + código."
)


def rechazar_si_pago_con_error_serial_duplicado(
    db: Session,
    row: "PagoConError",
    *,
    exclude_pago_con_error_id: Optional[int] = None,
) -> None:
    """
    Impide guardar/mover si el serial (documento+código) o la huella funcional ya existen en BD.
    """
    num = (getattr(row, "numero_documento", None) or "").strip()
    if num:
        from app.services.pago_numero_documento import (
            numero_documento_ya_registrado,
            pago_huerfano_adoptable_por_documento,
        )

        prestamo_dest = getattr(row, "prestamo_id", None)
        adoptable = None
        if prestamo_dest and int(prestamo_dest) > 0:
            adoptable = pago_huerfano_adoptable_por_documento(
                db,
                num,
                prestamo_id_destino=int(prestamo_dest),
                cedula_cliente=getattr(row, "cedula_cliente", None),
            )
        if adoptable is None and numero_documento_ya_registrado(
            db,
            num,
            exclude_pago_con_error_id=exclude_pago_con_error_id,
        ):
            raise HTTPException(
                status_code=409,
                detail=HTTP_409_DETAIL_DOCUMENTO_DUPLICADO,
            )
    hid = pago_con_error_conflicto_huella_existente(db, row)
    if hid is not None:
        raise HTTPException(
            status_code=409,
            detail=mensaje_409_huella_funcional_con_id(hid),
        )


def conflicto_serial_para_formulario(
    db: Session,
    *,
    numero_documento: str,
    prestamo_id: Optional[int] = None,
    cedula_cliente: Optional[str] = None,
    fecha_pago: Optional[date] = None,
    monto_pagado: Optional[float] = None,
    referencia_pago: Optional[str] = None,
    exclude_pago_id: Optional[int] = None,
    exclude_pago_con_error_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Prechequeo para UI: documento en pagos/pagos_con_errores y huella en pagos.
    """
    from app.core.documento import normalize_documento
    from app.services.pago_numero_documento import (
        numero_documento_ya_registrado,
        pago_huerfano_adoptable_por_documento,
        primer_pago_cartera_por_documento,
    )

    doc = (numero_documento or "").strip()
    clave_buscada = normalize_documento(doc)
    documento_conflicto = False
    pago_id: Optional[int] = None
    prestamo_id_doc: Optional[int] = None
    pago_con_error_id: Optional[int] = None
    puede_adoptar_pago_huerfano = False
    adoptar_pago_huerfano_id: Optional[int] = None

    if doc:
        documento_conflicto = numero_documento_ya_registrado(
            db,
            doc,
            exclude_pago_id=exclude_pago_id,
            exclude_pago_con_error_id=exclude_pago_con_error_id,
        )
        pago_id, prestamo_id_doc = primer_pago_cartera_por_documento(
            db, doc, exclude_pago_id=exclude_pago_id
        )
        if (
            documento_conflicto
            and prestamo_id
            and int(prestamo_id) > 0
            and (cedula_cliente or "").strip()
        ):
            adoptar_pago_huerfano_id = pago_huerfano_adoptable_por_documento(
                db,
                doc,
                prestamo_id_destino=int(prestamo_id),
                cedula_cliente=cedula_cliente,
                exclude_pago_id=exclude_pago_id,
            )
            if adoptar_pago_huerfano_id is not None:
                puede_adoptar_pago_huerfano = True
                pago_id = adoptar_pago_huerfano_id
                prestamo_id_doc = None
        if documento_conflicto and pago_id is None:
            from sqlalchemy import func, select

            from app.models.pago_con_error import PagoConError

            nu = doc.upper()
            q = select(PagoConError.id).where(
                func.upper(func.trim(PagoConError.numero_documento)) == nu
            )
            if exclude_pago_con_error_id is not None:
                q = q.where(PagoConError.id != exclude_pago_con_error_id)
            peid = db.scalar(q.limit(1))
            if peid is not None:
                pago_con_error_id = int(peid)

    huella_conflicto = False
    huella_pago_id: Optional[int] = None
    huella_prestamo_id: Optional[int] = None
    if prestamo_id and fecha_pago is not None and monto_pagado is not None:
        rn = ref_norm_desde_campos(doc, referencia_pago or doc).strip()
        if rn:
            huella_pago_id = primer_id_conflicto_huella_funcional(
                db,
                prestamo_id=int(prestamo_id),
                fecha_pago=fecha_pago,
                monto_pagado=Decimal(str(round(float(monto_pagado), 2))),
                ref_norm=rn,
                exclude_pago_id=exclude_pago_id,
            )
            huella_conflicto = huella_pago_id is not None
            if huella_conflicto:
                huella_prestamo_id = int(prestamo_id)

    documento_bloquea = documento_conflicto and not puede_adoptar_pago_huerfano

    return {
        "conflicto": documento_bloquea or huella_conflicto,
        "documento_conflicto": documento_conflicto,
        "documento_bloquea_guardar": documento_bloquea,
        "puede_adoptar_pago_huerfano": puede_adoptar_pago_huerfano,
        "adoptar_pago_huerfano_id": adoptar_pago_huerfano_id,
        "huella_conflicto": huella_conflicto,
        "pago_id": pago_id,
        "prestamo_id": prestamo_id_doc,
        "pago_con_error_id": pago_con_error_id,
        "huella_pago_id": huella_pago_id,
        "huella_prestamo_id": huella_prestamo_id,
        "clave_buscada": clave_buscada,
    }


def pago_con_error_conflicto_huella_existente(
    db: Session,
    perr: "PagoConError",
) -> Optional[int]:
    """
    ID del `Pago` operativo que comparte huella con este `PagoConError`, o None.

    Cubre duplicados donde `numero_documento` difiere en texto (p. ej. BNC/164… vs 164…)
    pero `ref_norm` coincide con el índice `ux_pagos_fingerprint_activos`.
    """
    if perr is None:
        return None
    prestamo_id = getattr(perr, "prestamo_id", None)
    if not prestamo_id:
        return None
    fp = getattr(perr, "fecha_pago", None)
    if fp is None:
        return None
    fecha = fp.date() if hasattr(fp, "date") else fp
    if not isinstance(fecha, date):
        return None
    monto = getattr(perr, "monto_pagado", None)
    if monto is None:
        return None
    rn = ref_norm_desde_campos(
        getattr(perr, "numero_documento", None),
        getattr(perr, "referencia_pago", None),
    ).strip()
    if not rn:
        return None
    return primer_id_conflicto_huella_funcional(
        db,
        prestamo_id=int(prestamo_id),
        fecha_pago=fecha,
        monto_pagado=Decimal(str(round(float(monto), 2))),
        ref_norm=rn,
    )


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
