"""
Flujo conciliacion Visto (finiquito area revision):
reserva comprobantes -> borrado manual pagos -> conciliacion hoja -> recrear pagos + OCR Gemini -> cascada.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.services.pagos_gmail.parse_campos_comprobante import (
    sanitizar_numero_operacion_comprobante,
)
from app.models.finiquito import FiniquitoCaso
from app.models.finiquito_conciliacion_reserva import FiniquitoConciliacionReserva
from app.models.pago import Pago
from app.models.pago_comprobante_imagen import PagoComprobanteImagen
from app.utils.cedula_almacenamiento import CedulaPagoFkError, asegurar_cedula_pago_para_fk
from app.services.cuota_estado import TZ_NEGOCIO
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.pago_registro_moneda import resolver_monto_registro_pago
from app.services.pagos_cuotas_reaplicacion import eliminar_todos_pagos_prestamo
from app.services.pagos.migracion_comprobante_drive_a_bd import (
    descargar_archivo_drive_con_api,
    descargar_archivo_drive_uc_export,
    extraer_google_drive_file_id,
)
from app.services.pagos_gmail.gemini_async import extract_infopagos_campos_desde_comprobante_async
from app.services.cobros.cobros_publico_reporte_service import (
    mime_efectivo_comprobante_web,
    validar_adjunto_comprobante_bytes,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

_RE_COMPROBANTE_ID = re.compile(
    r"/pagos/comprobante-imagen/([0-9a-fA-F]{32})\b",
    re.IGNORECASE,
)


def _tiene_comprobante(p: Pago) -> bool:
    if (p.link_comprobante or "").strip():
        return True
    if (p.documento_ruta or "").strip():
        return True
    return False


def _reserva_tiene_imagen_guardada(reserva: FiniquitoConciliacionReserva) -> bool:
    data = reserva.comprobante_imagen_data
    return bool(data) and len(data) > 0


def _bytes_y_nombre_ocr_desde_reserva(
    reserva: FiniquitoConciliacionReserva,
) -> Tuple[Optional[bytes], str, str]:
    """
    Solo bytes persistidos en la reserva (flujo Visto).
    No re-lee Drive ni pago_comprobante_imagen en recrear-ocr.
    """
    if not _reserva_tiene_imagen_guardada(reserva):
        return None, "", "sin_imagen_guardada_en_reserva"
    fn = (reserva.comprobante_nombre_archivo or "comprobante.jpg").strip() or "comprobante.jpg"
    return bytes(reserva.comprobante_imagen_data), fn, ""


def caso_tiene_reserva_activa(db: Session, caso_id: int) -> bool:
    n = int(
        db.scalar(
            select(func.count())
            .select_from(FiniquitoConciliacionReserva)
            .where(FiniquitoConciliacionReserva.caso_id == caso_id)
        )
        or 0
    )
    return n > 0


def prestamo_tiene_reserva_finiquito_activa(db: Session, prestamo_id: int) -> bool:
    """Reserva vigente: caso en ACEPTADO con filas en tabla temporal."""
    n = int(
        db.scalar(
            select(func.count())
            .select_from(FiniquitoConciliacionReserva)
            .join(FiniquitoCaso, FiniquitoCaso.id == FiniquitoConciliacionReserva.caso_id)
            .where(
                FiniquitoConciliacionReserva.prestamo_id == prestamo_id,
                FiniquitoCaso.estado == "ACEPTADO",
            )
        )
        or 0
    )
    return n > 0


def prestamo_ids_conciliacion_visto_protegidos(db: Session) -> set[int]:
    """Prestamos con reserva temporal en flujo Visto (no borrar finiquito_casos al refrescar)."""
    rows = db.execute(
        select(FiniquitoConciliacionReserva.prestamo_id)
        .join(FiniquitoCaso, FiniquitoCaso.id == FiniquitoConciliacionReserva.caso_id)
        .where(FiniquitoCaso.estado == "ACEPTADO")
        .distinct()
    ).all()
    return {int(r[0]) for r in rows if r[0] is not None}


def purgar_reserva_conciliacion_caso(db: Session, caso_id: int) -> int:
    r = db.execute(
        delete(FiniquitoConciliacionReserva).where(
            FiniquitoConciliacionReserva.caso_id == caso_id
        )
    )
    return int(getattr(r, "rowcount", 0) or 0)


def map_conciliacion_visto_activa_por_caso(
    db: Session, caso_ids: List[int]
) -> Dict[int, bool]:
    if not caso_ids:
        return {}
    rows = db.execute(
        select(FiniquitoConciliacionReserva.caso_id, func.count())
        .where(FiniquitoConciliacionReserva.caso_id.in_(caso_ids))
        .group_by(FiniquitoConciliacionReserva.caso_id)
    ).all()
    activos = {int(r[0]): int(r[1] or 0) > 0 for r in rows}
    return {cid: activos.get(cid, False) for cid in caso_ids}


def iniciar_visto_reserva(db: Session, caso_id: int) -> Dict[str, Any]:
    caso = db.get(FiniquitoCaso, caso_id)
    if not caso:
        return {"ok": False, "error": "Caso no encontrado"}
    if (caso.estado or "").upper().strip() != "ACEPTADO":
        return {
            "ok": False,
            "error": "Visto solo desde el area de revision (estado ACEPTADO).",
        }

    if caso_tiene_reserva_activa(db, caso_id):
        n = int(
            db.scalar(
                select(func.count())
                .select_from(FiniquitoConciliacionReserva)
                .where(FiniquitoConciliacionReserva.caso_id == caso_id)
            )
            or 0
        )
        return {
            "ok": True,
            "ya_iniciado": True,
            "reservas": n,
            "mensaje": "La reserva temporal ya existe para este caso.",
        }

    pagos = (
        db.execute(
            select(Pago)
            .where(Pago.prestamo_id == caso.prestamo_id)
            .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )
    con_img = [p for p in pagos if _tiene_comprobante(p)]
    if not con_img:
        return {
            "ok": False,
            "error": "No hay pagos con comprobante (link o documento) para reservar.",
        }

    orden = 0
    omitidos_sin_bytes: List[str] = []
    for p in con_img:
        body, filename, err_bytes = cargar_bytes_comprobante(
            db,
            link_comprobante=p.link_comprobante,
            documento_ruta=p.documento_ruta,
        )
        if not body:
            ref = (p.numero_documento or p.referencia_pago or str(p.id or "")).strip()
            omitidos_sin_bytes.append(ref or f"pago_id={p.id}")
            logger.warning(
                "visto reserva: no se guardo comprobante pago_id=%s prestamo_id=%s: %s",
                p.id,
                caso.prestamo_id,
                err_bytes or "sin_bytes",
            )
            continue
        orden += 1
        ct = mime_efectivo_comprobante_web(
            "",
            (filename or "comprobante.jpg").strip() or "comprobante.jpg",
        )
        db.add(
            FiniquitoConciliacionReserva(
                caso_id=caso.id,
                prestamo_id=int(caso.prestamo_id),
                orden=orden,
                pago_id_origen=p.id,
                cedula_cliente=p.cedula_cliente,
                monto_pagado=p.monto_pagado,
                fecha_pago=p.fecha_pago,
                numero_documento=p.numero_documento,
                referencia_pago=p.referencia_pago or "",
                institucion_bancaria=p.institucion_bancaria,
                link_comprobante=p.link_comprobante,
                documento_ruta=p.documento_ruta,
                comprobante_imagen_data=body,
                comprobante_content_type=(ct or "image/jpeg")[:80],
                comprobante_nombre_archivo=(filename or "comprobante.jpg")[:255],
                moneda_registro=p.moneda_registro,
                monto_bs_original=p.monto_bs_original,
                tasa_cambio_bs_usd=p.tasa_cambio_bs_usd,
                conciliado=bool(p.conciliado),
                notas=p.notas,
            )
        )

    if orden == 0:
        det = (
            f" ({len(omitidos_sin_bytes)} con link pero sin poder guardar imagen)"
            if omitidos_sin_bytes
            else ""
        )
        return {
            "ok": False,
            "error": (
                "No se pudo guardar ningun comprobante en la reserva temporal"
                + det
                + ". Revise BD/Drive antes de Visto."
            ),
        }

    db.flush()

    # Reserva persistida en la misma transaccion antes de borrar pagos (excepcion LIQUIDADO).
    del_res = eliminar_todos_pagos_prestamo(db, int(caso.prestamo_id))
    if not del_res.get("ok"):
        return {
            "ok": False,
            "error": (
                del_res.get("error")
                or "No se pudieron eliminar los pagos del prestamo tras la reserva."
            ),
        }

    n_del = int(del_res.get("pagos_eliminados") or 0)
    msg = (
        f"Guardados {orden} comprobante(s) en reserva (imagen en BD temporal); "
        f"eliminados {n_del} pago(s) del prestamo."
    )
    if omitidos_sin_bytes:
        msg += f" Omitidos sin imagen guardada: {len(omitidos_sin_bytes)}."
    return {
        "ok": True,
        "ya_iniciado": False,
        "reservas": orden,
        "pagos_eliminados": n_del,
        "mensaje": msg,
    }


def _extraer_comprobante_id_hex(link: Optional[str], documento_ruta: Optional[str]) -> Optional[str]:
    for raw in (link, documento_ruta):
        s = (raw or "").strip()
        if not s:
            continue
        m = _RE_COMPROBANTE_ID.search(s)
        if m:
            return m.group(1).lower()
    return None


def cargar_bytes_comprobante(
    db: Session,
    *,
    link_comprobante: Optional[str],
    documento_ruta: Optional[str],
) -> Tuple[Optional[bytes], str, str]:
    """
    Retorna (bytes, filename, error). filename para Gemini.
    """
    cid = _extraer_comprobante_id_hex(link_comprobante, documento_ruta)
    if cid:
        row = db.get(PagoComprobanteImagen, cid)
        if row and row.imagen_data:
            fn = f"comprobante_{cid[:8]}.jpg"
            ct = (row.content_type or "image/jpeg").split(";")[0]
            if "pdf" in ct.lower():
                fn = f"comprobante_{cid[:8]}.pdf"
            return bytes(row.imagen_data), fn, ""

    for raw in (link_comprobante, documento_ruta):
        fid = extraer_google_drive_file_id((raw or "").strip())
        if not fid:
            continue
        body, mime, name, err = descargar_archivo_drive_con_api(fid)
        if not body:
            body, mime_uc, err_uc = descargar_archivo_drive_uc_export(fid)
            if body:
                mime = mime_uc
                err = err_uc
                name = name or f"drive_{fid[:8]}"
        if body:
            fn = (name or f"drive_{fid[:8]}").strip() or "comprobante.jpg"
            err_file, fn_ok = validar_adjunto_comprobante_bytes(
                body,
                mime_efectivo_comprobante_web(mime or "", fn),
                fn,
                mensaje_excel_largo=False,
            )
            if err_file:
                return None, fn, err_file
            return body, fn_ok, ""
        if err:
            return None, "", err

    return None, "", "No se pudo obtener la imagen del comprobante (BD ni Drive)."


def _aplicar_ocr_a_pago(
    db: Session,
    pago: Pago,
    gem: Dict[str, Any],
) -> None:
    if not gem.get("ok"):
        return
    inst = (gem.get("institucion_financiera") or "").strip()
    if inst:
        pago.institucion_bancaria = inst[:255]
    num_op = sanitizar_numero_operacion_comprobante(gem.get("numero_operacion"))
    if num_op:
        compuesto = compose_numero_documento_almacenado(num_op, None)
        if compuesto:
            pago.numero_documento = compuesto[:100]
            pago.referencia_pago = (compuesto[:100] or pago.referencia_pago or "")[:100]
    fecha_d = gem.get("fecha_pago")
    if isinstance(fecha_d, date) and not isinstance(fecha_d, datetime):
        pago.fecha_pago = datetime.combine(fecha_d, dt_time.min)
    monto = gem.get("monto")
    if monto is not None:
        try:
            pago.monto_pagado = Decimal(str(round(float(monto), 2)))
        except (TypeError, ValueError):
            pass


def _crear_o_actualizar_pago_desde_reserva(
    db: Session,
    reserva: FiniquitoConciliacionReserva,
    caso: FiniquitoCaso,
    usuario_registro: str,
) -> Tuple[Optional[Pago], Optional[str]]:
    if reserva.pago_id_recriado:
        pago = db.get(Pago, int(reserva.pago_id_recriado))
        if pago is None:
            reserva.pago_id_recriado = None
        else:
            return pago, None

    num = (reserva.numero_documento or "").strip()
    if not num:
        num = (reserva.referencia_pago or f"FINIQ-RES-{reserva.id}")[:100]
    num_stored = compose_numero_documento_almacenado(num, None) or num[:100]
    ref = (reserva.referencia_pago or num_stored or "N/A")[:100]

    fecha_date = reserva.fecha_pago.date() if hasattr(reserva.fecha_pago, "date") else reserva.fecha_pago
    if not isinstance(fecha_date, date):
        fecha_date = datetime.now(ZoneInfo(TZ_NEGOCIO)).date()

    try:
        cedula_fk = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=(reserva.cedula_cliente or caso.cedula or "").strip() or None,
            prestamo_id=caso.prestamo_id,
        )
    except CedulaPagoFkError as e:
        return None, str(e)

    monto_dec = Decimal(str(round(float(reserva.monto_pagado or 0), 2)))
    monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(
        db,
        cedula_normalizada=(cedula_fk or "").strip().upper(),
        fecha_pago=fecha_date,
        monto_pagado=monto_dec,
        moneda_registro=(reserva.moneda_registro or "USD"),
        tasa_cambio_manual=None,
    )

    msg_h = conflicto_huella_para_creacion(
        db,
        prestamo_id=caso.prestamo_id,
        fecha_pago=fecha_date,
        monto_pagado=monto_usd,
        numero_documento=num_stored,
        referencia_pago=ref,
    )
    if msg_h:
        return None, msg_h

    conciliado = bool(reserva.conciliado)
    fecha_pago_ts = (
        reserva.fecha_pago
        if isinstance(reserva.fecha_pago, datetime)
        else datetime.combine(fecha_date, dt_time.min)
    )

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=caso.prestamo_id,
        fecha_pago=fecha_pago_ts,
        monto_pagado=monto_usd,
        numero_documento=num_stored,
        institucion_bancaria=(reserva.institucion_bancaria or "")[:255] or None,
        estado="PAGADO" if conciliado else "PENDIENTE",
        notas=reserva.notas,
        referencia_pago=ref,
        conciliado=conciliado,
        fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,
        verificado_concordancia="SI" if conciliado else "",
        usuario_registro=usuario_registro,
        moneda_registro=moneda_fin,
        monto_bs_original=monto_bs_o,
        tasa_cambio_bs_usd=tasa_o,
        fecha_tasa_referencia=fecha_tasa_o,
        link_comprobante=(reserva.link_comprobante or "").strip() or None,
        documento_ruta=(reserva.documento_ruta or "").strip() or None,
    )
    db.add(pago)
    db.flush()
    reserva.pago_id_recriado = pago.id
    return pago, None


async def _ocr_fila_reserva(
    db: Session,
    reserva: FiniquitoConciliacionReserva,
    caso: FiniquitoCaso,
    usuario_registro: str,
) -> Dict[str, Any]:
    pago, err_crear = _crear_o_actualizar_pago_desde_reserva(db, reserva, caso, usuario_registro)
    if err_crear:
        reserva.ocr_ok = False
        reserva.ocr_error = err_crear[:2000]
        return {
            "reserva_id": reserva.id,
            "ok": False,
            "error": err_crear,
            "pago_id": reserva.pago_id_recriado,
        }

    body, filename, err_bytes = _bytes_y_nombre_ocr_desde_reserva(reserva)
    if not body:
        reserva.ocr_ok = False
        reserva.ocr_error = (err_bytes or "sin_imagen_guardada")[:2000]
        return {
            "reserva_id": reserva.id,
            "ok": False,
            "error": (
                "Sin imagen guardada en reserva Visto; "
                "inicie Visto de nuevo para guardar el comprobante."
            ),
            "pago_id": pago.id if pago else None,
            "ocr_omitido": True,
        }

    ctx_ced = normalizar_cedula_almacenamiento(
        (reserva.cedula_cliente or caso.cedula or "").strip()
    ) or ""
    gem = await extract_infopagos_campos_desde_comprobante_async(
        ctx_ced,
        body,
        filename,
        institucion_plantilla=(reserva.institucion_bancaria or "").strip() or None,
    )
    if pago is not None:
        _aplicar_ocr_a_pago(db, pago, gem)

    reserva.ocr_ok = bool(gem.get("ok"))
    reserva.ocr_error = None if gem.get("ok") else (str(gem.get("error") or "OCR fallido"))[:2000]
    try:
        reserva.ocr_sugerencia_json = json.dumps(
            {
                "fecha_pago": (
                    gem.get("fecha_pago").isoformat()
                    if isinstance(gem.get("fecha_pago"), date)
                    else None
                ),
                "monto": gem.get("monto"),
                "institucion_financiera": gem.get("institucion_financiera"),
                "numero_operacion": gem.get("numero_operacion"),
                "moneda": gem.get("moneda"),
            },
            ensure_ascii=False,
        )[:4000]
    except Exception:
        reserva.ocr_sugerencia_json = None

    db.flush()
    return {
        "reserva_id": reserva.id,
        "ok": bool(gem.get("ok")),
        "error": reserva.ocr_error,
        "pago_id": pago.id if pago else None,
    }


async def recrear_pagos_y_ocr_lote(
    db: Session,
    caso_id: int,
    usuario_registro: str,
) -> Dict[str, Any]:
    caso = db.get(FiniquitoCaso, caso_id)
    if not caso:
        return {"ok": False, "error": "Caso no encontrado"}
    if (caso.estado or "").upper().strip() != "ACEPTADO":
        return {
            "ok": False,
            "error": "Recrear pagos solo con el caso en area de revision (ACEPTADO).",
        }
    if not caso_tiene_reserva_activa(db, caso_id):
        return {
            "ok": False,
            "error": "Primero inicie Visto para crear la reserva temporal.",
        }

    filas = (
        db.execute(
            select(FiniquitoConciliacionReserva)
            .where(FiniquitoConciliacionReserva.caso_id == caso_id)
            .order_by(FiniquitoConciliacionReserva.orden.asc())
        )
        .scalars()
        .all()
    )

    filas_con_imagen = [r for r in filas if _reserva_tiene_imagen_guardada(r)]
    sin_imagen = len(filas) - len(filas_con_imagen)

    detalle: List[Dict[str, Any]] = []
    ok_n = 0
    for reserva in filas:
        if not _reserva_tiene_imagen_guardada(reserva):
            detalle.append(
                {
                    "reserva_id": reserva.id,
                    "ok": False,
                    "error": "sin_imagen_guardada_en_reserva",
                    "pago_id": reserva.pago_id_recriado,
                    "ocr_omitido": True,
                }
            )
            continue
        item = await _ocr_fila_reserva(db, reserva, caso, usuario_registro)
        detalle.append(item)
        if item.get("ok"):
            ok_n += 1

    return {
        "ok": ok_n > 0,
        "total": len(filas_con_imagen),
        "ocr_ok": ok_n,
        "ocr_fallidos": len(filas_con_imagen) - ok_n,
        "ocr_omitidos_sin_imagen_guardada": sin_imagen,
        "detalle": detalle,
        "mensaje": (
            f"OCR (solo imagenes guardadas en Visto): {ok_n}/{len(filas_con_imagen)}."
            + (f" {sin_imagen} fila(s) sin imagen en reserva." if sin_imagen else "")
        ),
    }


def recrear_pagos_y_ocr_lote_sync(
    db: Session,
    caso_id: int,
    usuario_registro: str,
) -> Dict[str, Any]:
    return asyncio.run(recrear_pagos_y_ocr_lote(db, caso_id, usuario_registro))


def listar_reserva_caso(db: Session, caso_id: int) -> List[FiniquitoConciliacionReserva]:
    return list(
        db.execute(
            select(FiniquitoConciliacionReserva)
            .where(FiniquitoConciliacionReserva.caso_id == caso_id)
            .order_by(FiniquitoConciliacionReserva.orden.asc())
        )
        .scalars()
        .all()
    )
