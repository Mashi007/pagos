"""
Conciliar cartera en revisión manual (solo admin):
1) Lee total ABONOS de caché Notificaciones → General (ej. $531).
2) Reserva solo bytes de comprobante (sin metadatos de pagos).
3) Borra pagos del préstamo.
4) Por cada imagen reservada: asigna su parte del total ABONOS → incorpora imagen
   → reescanea (OCR fecha/documento/banco; el monto NO sale del OCR).
5) Verifica que la suma en cartera = total ABONOS.
6) Cascada a cuotas.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import date, datetime, time as dt_time
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.documento import compose_numero_documento_almacenado
from app.models.pago import Pago
from app.models.pago_comprobante_imagen import PagoComprobanteImagen
from app.models.prestamo import Prestamo
from app.models.revision_manual_conciliacion_reserva import RevisionManualConciliacionReserva
from app.services.comparar_abonos_drive_cuotas_service import (
    UMBRAL_CONFIRMO_ABONOS_USD,
    referencia_abonos_notificaciones_general,
)
from app.services.cobros.cobros_publico_reporte_service import mime_efectivo_comprobante_web
from app.services.cuota_estado import TZ_NEGOCIO
from app.services.finiquito_conciliacion_visto_service import (
    _MAX_COMPROBANTE_RESERVA_BYTES,
    _aplicar_ocr_a_pago,
    cargar_bytes_comprobante,
)
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.pago_registro_moneda import resolver_monto_registro_pago
from app.services.pagos_cuotas_reaplicacion import eliminar_todos_pagos_prestamo
from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta
from app.services.pagos_gmail.gemini_async import extract_infopagos_campos_desde_comprobante_async
from app.services.pagos_gmail.parse_campos_comprobante import sanitizar_numero_operacion_comprobante
from app.utils.cedula_almacenamiento import CedulaPagoFkError, asegurar_cedula_pago_para_fk
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

# Namespace pg_advisory_xact_lock (key1); key2 = prestamo_id. Libera al commit/rollback.
_LOCK_NS_REVISION_CONCILIAR_CARTERA = 887766560
_TOL_CUADRE_ABONOS_USD = 0.02


def _intentar_lock_conciliar_prestamo(db: Session, prestamo_id: int) -> Optional[str]:
    """
    Evita dos ejecuciones simultáneas de Conciliar sobre el mismo préstamo.
    En PostgreSQL usa pg_try_advisory_xact_lock (no bloquea en espera).
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return "Préstamo inválido para bloqueo de conciliación."
    if pid <= 0 or pid > 2147483647:
        return "Préstamo inválido para bloqueo de conciliación."
    acquired = db.execute(
        text("SELECT pg_try_advisory_xact_lock(:ns, :pid)"),
        {"ns": _LOCK_NS_REVISION_CONCILIAR_CARTERA, "pid": pid},
    ).scalar()
    if acquired:
        return None
    return (
        "Otra conciliación de cartera está en curso para este préstamo. "
        "Espere a que termine y vuelva a intentar."
    )


def _tiene_comprobante(p: Pago) -> bool:
    if (p.link_comprobante or "").strip():
        return True
    if (p.documento_ruta or "").strip():
        return True
    return False


def _reserva_tiene_imagen_guardada(reserva: RevisionManualConciliacionReserva) -> bool:
    data = reserva.comprobante_imagen_data
    return bool(data) and len(data) > 0


def _distribuir_monto_abonos_entre_comprobantes(abonos_usd: float, n: int) -> List[Decimal]:
    """Reparte el total ABONOS entre N comprobantes; la suma coincide con abonos_usd."""
    if n <= 0:
        return []
    total = Decimal(str(round(float(abonos_usd), 2)))
    base = (total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    partes = [base] * n
    faltante = total - sum(partes)
    centavos = int((faltante * 100).to_integral_value())
    for i in range(min(centavos, n)):
        partes[i] += Decimal("0.01")
    return partes


def _placeholder_fecha_reserva() -> datetime:
    return datetime.now(ZoneInfo(TZ_NEGOCIO))


def purgar_reserva_conciliacion_prestamo(db: Session, prestamo_id: int) -> int:
    r = db.execute(
        delete(RevisionManualConciliacionReserva).where(
            RevisionManualConciliacionReserva.prestamo_id == prestamo_id
        )
    )
    return int(getattr(r, "rowcount", 0) or 0)


def _bytes_y_nombre_ocr_desde_reserva(
    reserva: RevisionManualConciliacionReserva,
) -> Tuple[Optional[bytes], str, str]:
    if not _reserva_tiene_imagen_guardada(reserva):
        return None, "", "sin_imagen_guardada_en_reserva"
    fn = (reserva.comprobante_nombre_archivo or "comprobante.jpg").strip() or "comprobante.jpg"
    return bytes(reserva.comprobante_imagen_data), fn, ""


def _vincular_comprobante_reserva_al_pago(
    db: Session,
    reserva: RevisionManualConciliacionReserva,
    pago: Pago,
) -> None:
    if not _reserva_tiene_imagen_guardada(reserva):
        return
    body = bytes(reserva.comprobante_imagen_data)
    if len(body) > _MAX_COMPROBANTE_RESERVA_BYTES:
        logger.warning(
            "revision conciliar: comprobante reserva_id=%s demasiado grande (%s bytes)",
            reserva.id,
            len(body),
        )
        return
    ct = (
        (reserva.comprobante_content_type or "image/jpeg").split(";")[0].strip()
        or "image/jpeg"
    )
    uid = uuid.uuid4().hex
    db.add(PagoComprobanteImagen(id=uid, content_type=ct, imagen_data=body))
    db.flush()
    pago.link_comprobante = url_comprobante_imagen_absoluta(uid)
    pago.documento_ruta = None


def _crear_pago_desde_reserva(
    db: Session,
    reserva: RevisionManualConciliacionReserva,
    prestamo: Prestamo,
    usuario_registro: str,
    *,
    monto_abonos_usd: Decimal,
    abonos_total_usd: float,
) -> Tuple[Optional[Pago], Optional[str]]:
    """Alta inicial: monto desde ABONOS; documento/fecha se completan con OCR."""
    ref_tmp = f"CONC-ABONOS-{prestamo.id}-{reserva.orden}-{uuid.uuid4().hex[:8]}"[:100]
    fecha_date = _placeholder_fecha_reserva().date()

    try:
        cedula_fk = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=(reserva.cedula_cliente or prestamo.cedula or "").strip() or None,
            prestamo_id=prestamo.id,
        )
    except CedulaPagoFkError as e:
        return None, str(e)

    monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(
        db,
        cedula_normalizada=(cedula_fk or "").strip().upper(),
        fecha_pago=fecha_date,
        monto_pagado=monto_abonos_usd,
        moneda_registro="USD",
        tasa_cambio_manual=None,
    )

    msg_h = conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_date,
        monto_pagado=monto_usd,
        numero_documento=ref_tmp,
        referencia_pago=ref_tmp,
    )
    if msg_h:
        return None, msg_h

    fecha_pago_ts = datetime.combine(fecha_date, dt_time.min)
    ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
    nota_abonos = (
        f"Conciliar cartera: monto desde ABONOS Notificaciones → General "
        f"(${float(abonos_total_usd):.2f} repartido entre comprobantes)."
    )

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_pago_ts,
        monto_pagado=monto_usd,
        numero_documento=ref_tmp,
        institucion_bancaria=None,
        estado="PAGADO",
        notas=nota_abonos,
        referencia_pago=ref_tmp,
        conciliado=True,
        fecha_conciliacion=ahora,
        verificado_concordancia="SI",
        usuario_registro=usuario_registro,
        moneda_registro=moneda_fin,
        monto_bs_original=monto_bs_o,
        tasa_cambio_bs_usd=tasa_o,
        fecha_tasa_referencia=fecha_tasa_o,
        link_comprobante=None,
        documento_ruta=None,
    )
    db.add(pago)
    db.flush()
    reserva.pago_id_recriado = pago.id
    return pago, None


async def _ocr_fila_reserva_revision(
    db: Session,
    reserva: RevisionManualConciliacionReserva,
    prestamo: Prestamo,
    usuario_registro: str,
    *,
    monto_abonos_usd: Decimal,
    abonos_total_usd: float,
) -> Dict[str, Any]:
    """
    Por comprobante: (1) monto desde total ABONOS, (2) imagen reservada al pago,
    (3) reescaneo OCR (sin tocar monto).
    """
    reserva_id = reserva.id
    body, filename, err_bytes = _bytes_y_nombre_ocr_desde_reserva(reserva)
    if not body:
        reserva.ocr_ok = False
        reserva.ocr_error = (err_bytes or "sin_imagen_guardada_en_reserva")[:2000]
        return {
            "reserva_id": reserva_id,
            "ok": False,
            "error": reserva.ocr_error,
            "pago_id": None,
        }

    # 1) Pegar monto (parte del total ABONOS de Notificaciones → General).
    pago, err_crear = _crear_pago_desde_reserva(
        db,
        reserva,
        prestamo,
        usuario_registro,
        monto_abonos_usd=monto_abonos_usd,
        abonos_total_usd=abonos_total_usd,
    )
    if err_crear:
        reserva.ocr_ok = False
        reserva.ocr_error = err_crear[:2000]
        return {
            "reserva_id": reserva_id,
            "ok": False,
            "error": err_crear,
            "pago_id": reserva.pago_id_recriado,
        }

    # 2) Incorporar imagen guardada en reserva al pago nuevo.
    if pago is not None:
        _vincular_comprobante_reserva_al_pago(db, reserva, pago)
        db.flush()

    # 3) Reescanear imagen (fecha, banco, documento); monto permanece del ABONOS.
    ctx_ced = normalizar_cedula_almacenamiento(
        (reserva.cedula_cliente or prestamo.cedula or "").strip()
    ) or ""
    gem = await extract_infopagos_campos_desde_comprobante_async(
        ctx_ced,
        body,
        filename,
        institucion_plantilla=None,
    )
    if pago is not None:
        monto_abonos_fijado, _, _, _, _ = resolver_monto_registro_pago(
            db,
            cedula_normalizada=(pago.cedula_cliente or "").strip().upper(),
            fecha_pago=(
                pago.fecha_pago.date()
                if hasattr(pago.fecha_pago, "date")
                else _placeholder_fecha_reserva().date()
            ),
            monto_pagado=monto_abonos_usd,
            moneda_registro="USD",
            tasa_cambio_manual=None,
        )
        _aplicar_ocr_a_pago(db, pago, gem, aplicar_monto=False)
        pago.monto_pagado = monto_abonos_fijado
        db.flush()

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

    ocr_exitoso = bool(gem.get("ok"))
    ok = pago is not None and ocr_exitoso
    if ok and pago is not None:
        db.delete(reserva)
        db.flush()
    elif pago is not None:
        db.delete(pago)
        reserva.pago_id_recriado = None
        db.flush()

    return {
        "reserva_id": reserva_id,
        "ok": ok,
        "error": reserva.ocr_error if not ok else None,
        "pago_id": pago.id if pago else None,
        "monto_abonos_usd": float(monto_abonos_usd),
    }


def _reservar_comprobantes_prestamo(
    db: Session,
    prestamo: Prestamo,
) -> Dict[str, Any]:
    """Solo bytes de comprobante; no copia montos, documentos ni fechas del pago origen."""
    pagos = (
        db.execute(
            select(Pago)
            .where(Pago.prestamo_id == prestamo.id)
            .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )
    if not pagos:
        return {
            "ok": False,
            "error": "No hay pagos en este préstamo para reservar comprobantes.",
        }

    con_img = [p for p in pagos if _tiene_comprobante(p)]
    omitidos_sin_bytes: List[str] = []
    placeholder_fecha = _placeholder_fecha_reserva()
    orden = 0

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
                "revision conciliar reserva: sin bytes pago_id=%s prestamo_id=%s: %s",
                p.id,
                prestamo.id,
                err_bytes or "sin_bytes",
            )
            continue

        orden += 1
        ct = mime_efectivo_comprobante_web(
            "",
            (filename or "comprobante.jpg").strip() or "comprobante.jpg",
        )
        db.add(
            RevisionManualConciliacionReserva(
                prestamo_id=int(prestamo.id),
                orden=orden,
                pago_id_origen=p.id,
                cedula_cliente=(prestamo.cedula or p.cedula_cliente or "").strip() or None,
                monto_pagado=Decimal("0"),
                fecha_pago=placeholder_fecha,
                numero_documento=None,
                referencia_pago="",
                institucion_bancaria=None,
                link_comprobante=None,
                documento_ruta=None,
                comprobante_imagen_data=body,
                comprobante_content_type=(ct or "image/jpeg")[:80],
                comprobante_nombre_archivo=(filename or "comprobante.jpg")[:255],
                moneda_registro=None,
                monto_bs_original=None,
                tasa_cambio_bs_usd=None,
                conciliado=False,
                notas=None,
            )
        )

    if orden == 0:
        det = (
            f" ({len(omitidos_sin_bytes)} con enlace pero sin imagen descargable)"
            if omitidos_sin_bytes
            else ""
        )
        return {
            "ok": False,
            "error": (
                "No se pudo reservar ningún comprobante con imagen"
                + det
                + ". Suba o repare los comprobantes antes de conciliar."
            ),
        }

    db.flush()
    msg = f"Reservadas {orden} imagen(es) de comprobante en tabla temporal (sin metadatos de pago)."
    if omitidos_sin_bytes:
        msg += f" Omitidos sin bytes: {len(omitidos_sin_bytes)}."
    return {
        "ok": True,
        "reservas": orden,
        "reservas_sin_imagen": 0,
        "omitidos_sin_bytes": len(omitidos_sin_bytes),
        "mensaje": msg,
    }


async def ejecutar_conciliar_cartera_revision_manual(
    db: Session,
    prestamo_id: int,
    usuario_registro: str,
    *,
    lote: Optional[str] = None,
    confirmacion_montos_altos: Optional[str] = None,
) -> Dict[str, Any]:
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Préstamo no encontrado"}

    cedula = (prestamo.cedula or "").strip()
    if not cedula:
        return {"ok": False, "error": "El préstamo no tiene cédula registrada."}

    lock_err = _intentar_lock_conciliar_prestamo(db, prestamo_id)
    if lock_err:
        return {
            "ok": False,
            "error": lock_err,
            "conciliacion_en_curso": True,
            "prestamo_id": prestamo_id,
        }

    purgar_reserva_conciliacion_prestamo(db, prestamo_id)

    snap = referencia_abonos_notificaciones_general(
        db,
        prestamo_id,
        lote=lote,
        persist_cache_si_resuelve_lote=bool((lote or "").strip()),
    )
    if snap.get("sin_cache"):
        return {
            "ok": False,
            "error": (
                "No hay valor ABONOS en caché (Notificaciones → General). "
                "Ejecute «Recalcular» en esa pantalla o espere el job semanal."
            ),
            "referencia_abonos": snap,
        }
    if snap.get("requiere_seleccion_lote"):
        return {
            "ok": False,
            "error": (
                "Hay varios lotes para esta cédula en la caché de Notificaciones → General. "
                "Indique el lote del crédito en cuestión."
            ),
            "requiere_seleccion_lote": True,
            "opciones_lote": snap.get("opciones_lote") or [],
            "referencia_abonos": snap,
        }

    abonos_drive = snap.get("abonos_drive")
    if abonos_drive is None and not snap.get("requiere_seleccion_lote"):
        return {
            "ok": False,
            "error": (
                "No hay valor ABONOS de referencia en caché (Notificaciones → General). "
                "Ejecute «Recalcular» en esa pantalla."
            ),
            "referencia_abonos": snap,
        }

    abonos_f: Optional[float] = None
    if abonos_drive is not None:
        try:
            abonos_f = float(abonos_drive)
        except (TypeError, ValueError):
            abonos_f = None
        if abonos_f is None or abonos_f <= 0:
            return {
                "ok": False,
                "error": (
                    "ABONOS en caché (Notificaciones → General) debe ser un monto positivo. "
                    "Recalcule en General y vuelva a intentar."
                ),
                "referencia_abonos": snap,
            }
        if abonos_f > UMBRAL_CONFIRMO_ABONOS_USD:
            conf = (confirmacion_montos_altos or "").strip().upper()
            if conf != "CONFIRMO":
                return {
                    "ok": False,
                    "error": (
                        "Monto ABONOS elevado (Notificaciones → General): "
                        "escriba exactamente CONFIRMO para continuar."
                    ),
                    "requiere_confirmacion_montos_altos": True,
                    "abonos_drive": abonos_f,
                    "umbral_usd": UMBRAL_CONFIRMO_ABONOS_USD,
                    "referencia_abonos": snap,
                }

    reserva_out = _reservar_comprobantes_prestamo(db, prestamo)
    if not reserva_out.get("ok"):
        return {**reserva_out, "referencia_abonos": snap}

    est_previo = (prestamo.estado or "").strip().upper()
    del_res = eliminar_todos_pagos_prestamo(
        db, int(prestamo_id), contexto_revision_conciliar=True
    )
    if not del_res.get("ok"):
        return {
            "ok": False,
            "error": del_res.get("error") or "No se pudieron eliminar los pagos del préstamo.",
            "referencia_abonos": snap,
            "estado_prestamo": est_previo,
        }

    if est_previo == "LIQUIDADO":
        prestamo.estado = "APROBADO"
        db.flush()

    filas = list(
        db.execute(
            select(RevisionManualConciliacionReserva)
            .where(RevisionManualConciliacionReserva.prestamo_id == prestamo_id)
            .order_by(RevisionManualConciliacionReserva.orden.asc())
        )
        .scalars()
        .all()
    )

    montos_abonos = _distribuir_monto_abonos_entre_comprobantes(
        float(abonos_f or abonos_drive or 0),
        len(filas),
    )

    detalle: List[Dict[str, Any]] = []
    ok_n = 0
    pagos_recriados = 0
    for idx, reserva in enumerate(filas):
        monto_fila = montos_abonos[idx] if idx < len(montos_abonos) else Decimal("0")
        item = await _ocr_fila_reserva_revision(
            db,
            reserva,
            prestamo,
            usuario_registro,
            monto_abonos_usd=monto_fila,
            abonos_total_usd=float(abonos_f or abonos_drive or 0),
        )
        detalle.append(item)
        if item.get("ok"):
            ok_n += 1
            if item.get("pago_id"):
                pagos_recriados += 1

    if ok_n == 0:
        return {
            "ok": False,
            "error": (
                "Ningún pago se pudo recrear (OCR fallido o sin datos). "
                "No se aplicó cascada; la operación debe reintentarse."
            ),
            "prestamo_id": prestamo_id,
            "reservas": int(reserva_out.get("reservas") or 0),
            "pagos_eliminados": int(del_res.get("pagos_eliminados") or 0),
            "ocr_ok": 0,
            "ocr_total": len(filas),
            "referencia_abonos": snap,
            "detalle": detalle,
        }

    ocr_fallidos = len(filas) - ok_n
    advertencia_parcial = ocr_fallidos > 0

    total_pagos_usd = float(
        db.scalar(
            select(func.coalesce(func.sum(Pago.monto_pagado), 0)).where(
                Pago.prestamo_id == prestamo_id
            )
        )
        or 0
    )

    abonos_total_objetivo = float(abonos_f or abonos_drive or 0)
    diferencia_drive_ocr: Optional[float] = None
    abonos_cuadra_total = False
    if abonos_drive is not None:
        try:
            diferencia_drive_ocr = round(total_pagos_usd - float(abonos_drive), 2)
            abonos_cuadra_total = abs(diferencia_drive_ocr) <= _TOL_CUADRE_ABONOS_USD
        except (TypeError, ValueError):
            diferencia_drive_ocr = None

    if advertencia_parcial and not abonos_cuadra_total:
        advertencia_parcial = True
    elif not abonos_cuadra_total and ok_n > 0:
        advertencia_parcial = True

    # 4) Cascada solo tras alta de pagos (total ABONOS + imágenes reescaneadas).
    cascada: Dict[str, Any] | None = None
    if ok_n > 0:
        from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline

        logger.info(
            "revision conciliar cascada prestamo_id=%s abonos_objetivo=%.2f total_cartera=%.2f ocr_ok=%s/%s",
            prestamo_id,
            abonos_total_objetivo,
            total_pagos_usd,
            ok_n,
            len(filas),
        )
        cascada = aplicar_cascada_prestamo_pipeline(int(prestamo_id), db)

    drive_msg = ""
    if abonos_drive is not None:
        try:
            drive_msg = (
                f" Total ABONOS aplicado: ${float(abonos_drive):.2f}; "
                f"suma cartera recreada: ${total_pagos_usd:.2f}; "
                f"diferencia: ${(diferencia_drive_ocr if diferencia_drive_ocr is not None else 0):.2f}."
            )
            if abonos_cuadra_total:
                drive_msg += " Cuadre ABONOS: OK."
        except (TypeError, ValueError):
            drive_msg = f" ABONOS (Notificaciones → General): {abonos_drive}."

    parcial_msg = ""
    if advertencia_parcial:
        parcial_msg = (
            f" Atención: {ocr_fallidos} pago(s) no se recrearon; "
            "revise filas pendientes en reserva temporal."
        )

    ocr_msg = (
        f"Recreados: {ok_n}/{len(filas)} pago(s): total ABONOS "
        f"${abonos_total_objetivo:.2f} + imágenes reescaneadas."
    )
    if cascada is not None:
        if cascada.get("ok"):
            cascada_msg = str(cascada.get("mensaje") or "Cascada aplicada.")
            estado = cascada.get("prestamo_estado")
            if estado:
                cascada_msg += f" Estado préstamo: {estado}."
            mensaje = (
                f"{reserva_out.get('mensaje', '')} {ocr_msg}{drive_msg}{parcial_msg} {cascada_msg}"
            )
        else:
            mensaje = (
                f"{reserva_out.get('mensaje', '')} {ocr_msg}{drive_msg}{parcial_msg} "
                f"Cascada no aplicada: {cascada.get('error') or 'error desconocido'}."
            )
    else:
        mensaje = f"{reserva_out.get('mensaje', '')} {ocr_msg}{drive_msg}{parcial_msg}"

    db.refresh(prestamo)
    prestamo_estado_final = (prestamo.estado or "").strip().upper()

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "reservas": int(reserva_out.get("reservas") or 0),
        "reservas_sin_imagen": int(reserva_out.get("reservas_sin_imagen") or 0),
        "pagos_eliminados": int(del_res.get("pagos_eliminados") or 0),
        "ocr_ok": ok_n,
        "ocr_total": len(filas),
        "ocr_fallidos": ocr_fallidos,
        "advertencia_parcial": advertencia_parcial,
        "pagos_recriados": pagos_recriados,
        "total_pagos_recriados_usd": round(total_pagos_usd, 2),
        "abonos_drive": abonos_drive,
        "abonos_total_aplicado_usd": round(abonos_total_objetivo, 2),
        "abonos_cuadra_total": abonos_cuadra_total,
        "montos_abonos_distribuidos": [float(m) for m in montos_abonos],
        "diferencia_drive_ocr_usd": diferencia_drive_ocr,
        "diferencia_referencia_ocr_usd": diferencia_drive_ocr,
        "prestamo_estado_final": prestamo_estado_final,
        "prestamo_estado_previo": est_previo,
        "referencia_abonos": snap,
        "abonos_referencia_notificaciones": abonos_drive,
        "cascada": cascada,
        "detalle": detalle,
        "mensaje": mensaje.strip(),
    }


def ejecutar_conciliar_cartera_revision_manual_sync(
    db: Session,
    prestamo_id: int,
    usuario_registro: str,
    *,
    lote: Optional[str] = None,
    confirmacion_montos_altos: Optional[str] = None,
) -> Dict[str, Any]:
    return asyncio.run(
        ejecutar_conciliar_cartera_revision_manual(
            db,
            prestamo_id,
            usuario_registro,
            lote=lote,
            confirmacion_montos_altos=confirmacion_montos_altos,
        )
    )
