# -*- coding: utf-8 -*-
"""Cola de aprobación Auditoría Email → Recibos."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.models.auditoria_email import AuditoriaEmailMessage, AuditoriaEmailReceipt
from app.models.pagos_gmail_sync import GmailTemporal, PagosGmailSyncItem
from app.services.pagos_gmail.anti_limbo_post_lote import _fmt_desde_banco

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        s = str(v).replace(",", ".").strip()
        cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
        return float(cleaned) if cleaned not in ("", "-", ".") else None
    except (TypeError, ValueError):
        return None


def receipt_dict(
    r: AuditoriaEmailReceipt,
    *,
    serial_estado: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": r.id,
        "messageId": r.message_id,
        "gmailMessageId": r.gmail_message_id,
        "filename": r.filename,
        "mimeType": r.mime_type,
        "sizeKb": r.size_kb,
        "cedula": r.cedula,
        "monto": r.monto,
        "banco": r.banco,
        "fechaPago": r.fecha_pago,
        "numeroReferencia": r.numero_referencia,
        "serial": r.numero_referencia,
        "imageUrl": r.image_url,
        "status": r.status or "pending",
        "syncId": r.sync_id,
        "syncItemId": r.sync_item_id,
        "gmailTemporalId": r.gmail_temporal_id,
        "pagoId": r.pago_id,
        "pagoErrorId": r.pago_error_id,
        "lastError": r.last_error,
        "route": r.route,
        "ocrStatus": r.ocr_status,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "resolvedAt": r.resolved_at.isoformat() if r.resolved_at else None,
    }
    if serial_estado is not None:
        out["serialEstado"] = serial_estado
    return out


def _norm_serial(raw: Optional[str]) -> str:
    from app.core.documento import normalize_documento

    return (normalize_documento(raw) or str(raw or "")).strip().upper()


def _registered_serials_batch(db: Session, norms: List[str]) -> set[str]:
    """Serials ya presentes en pagos / pagos_con_errores (match exacto normalizado)."""
    from app.models.pago import Pago
    from app.models.pago_con_error import PagoConError

    unique = list({n for n in norms if n})
    if not unique:
        return set()
    found: set[str] = set()
    chunk_size = 400
    for i in range(0, len(unique), chunk_size):
        chunk = unique[i : i + chunk_size]
        for num in db.scalars(
            select(func.upper(Pago.numero_documento)).where(
                func.upper(Pago.numero_documento).in_(chunk)
            )
        ).all():
            if num:
                found.add(str(num).strip().upper())
        for num in db.scalars(
            select(func.upper(PagoConError.numero_documento)).where(
                func.upper(PagoConError.numero_documento).in_(chunk)
            )
        ).all():
            if num:
                found.add(str(num).strip().upper())
    return found


def serial_estado_recibo(
    db: Session,
    row: AuditoriaEmailReceipt,
    *,
    pending_counts: Optional[Dict[str, int]] = None,
    registered_norms: Optional[set[str]] = None,
) -> str:
    """
    UNICO / DUPLICADO con la misma regla vigente de ABCD:
    existe en ``pagos`` o ``pagos_con_errores``, o hay otro pending con el mismo serial.
    """
    from app.services.pago_numero_documento import numero_documento_ya_registrado

    raw = (row.numero_referencia or "").strip()
    if not raw:
        return "SIN_SERIAL"
    norm = _norm_serial(raw)
    if not norm:
        return "SIN_SERIAL"

    if registered_norms is not None:
        if norm in registered_norms:
            if row.pago_id or row.pago_error_id:
                if numero_documento_ya_registrado(
                    db,
                    raw,
                    exclude_pago_id=int(row.pago_id) if row.pago_id else None,
                    exclude_pago_con_error_id=int(row.pago_error_id)
                    if row.pago_error_id
                    else None,
                ):
                    return "DUPLICADO"
            else:
                return "DUPLICADO"
    elif numero_documento_ya_registrado(
        db,
        raw,
        exclude_pago_id=int(row.pago_id) if row.pago_id else None,
        exclude_pago_con_error_id=int(row.pago_error_id) if row.pago_error_id else None,
    ):
        return "DUPLICADO"

    if pending_counts is not None:
        if int(pending_counts.get(norm) or 0) > 1:
            return "DUPLICADO"
        return "UNICO"

    for _oid, oref in db.execute(
        select(AuditoriaEmailReceipt.id, AuditoriaEmailReceipt.numero_referencia).where(
            AuditoriaEmailReceipt.status == "pending",
            AuditoriaEmailReceipt.id != int(row.id),
            AuditoriaEmailReceipt.numero_referencia.isnot(None),
        )
    ):
        if _norm_serial(oref) == norm:
            return "DUPLICADO"
    return "UNICO"


def _pending_serial_counts(db: Session) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _rid, ref in db.execute(
        select(AuditoriaEmailReceipt.id, AuditoriaEmailReceipt.numero_referencia).where(
            AuditoriaEmailReceipt.status == "pending",
            AuditoriaEmailReceipt.numero_referencia.isnot(None),
        )
    ):
        norm = _norm_serial(ref)
        if not norm:
            continue
        counts[norm] = int(counts.get(norm) or 0) + 1
    return counts


def _serial_estado_safe(
    db: Session,
    row: AuditoriaEmailReceipt,
    *,
    pending_counts: Optional[Dict[str, int]] = None,
    registered_norms: Optional[set[str]] = None,
) -> str:
    """UNICO/DUPLICADO sin tumbar el listado si un serial rompe la consulta."""
    try:
        return serial_estado_recibo(
            db,
            row,
            pending_counts=pending_counts,
            registered_norms=registered_norms,
        )
    except Exception:
        logger.exception(
            "[AUDITORIA_EMAIL] serial_estado falló recibo=%s", getattr(row, "id", None)
        )
        return "UNICO"


def list_receipts(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = "pending",
) -> Dict[str, Any]:
    st = (status or "pending").strip().lower()
    skip_n = max(0, int(skip or 0))
    limit_n = max(1, int(limit or 50))

    # COUNT y SELECT independientes: reutilizar el mismo Select tras .subquery()
    # en SQLAlchemy puede devolver total=N e items de 1 fila.
    count_stmt = select(func.count()).select_from(AuditoriaEmailReceipt)
    list_stmt = select(AuditoriaEmailReceipt)
    if st not in ("all", "*", ""):
        filtro = AuditoriaEmailReceipt.status == st
        count_stmt = count_stmt.where(filtro)
        list_stmt = list_stmt.where(filtro)
    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = (
        db.execute(
            list_stmt.order_by(desc(AuditoriaEmailReceipt.id))
            .offset(skip_n)
            .limit(limit_n)
        )
        .scalars()
        .all()
    )
    expected = min(limit_n, max(0, total - skip_n))
    if len(rows) != expected:
        logger.warning(
            "[AUDITORIA_EMAIL] list_receipts desajuste status=%s total=%s "
            "skip=%s limit=%s filas=%s esperado=%s",
            st,
            total,
            skip_n,
            limit_n,
            len(rows),
            expected,
        )
    pending_counts: Optional[Dict[str, int]] = None
    registered_norms: Optional[set[str]] = None
    try:
        if st in ("pending", "all", "*", ""):
            pending_counts = _pending_serial_counts(db)
        norms = [_norm_serial(r.numero_referencia) for r in rows]
        registered_norms = _registered_serials_batch(db, norms)
    except Exception:
        logger.exception("[AUDITORIA_EMAIL] precompute seriales Recibos falló")
        pending_counts = None
        registered_norms = None
    items = [
        receipt_dict(
            r,
            serial_estado=_serial_estado_safe(
                db,
                r,
                pending_counts=pending_counts,
                registered_norms=registered_norms,
            ),
        )
        for r in rows
    ]
    from app.services.prestamos.cedula_aprobada import attach_prestamo_estado_items

    attach_prestamo_estado_items(db, items)
    by_status = {
        str(k): int(n or 0)
        for k, n in db.execute(
            select(AuditoriaEmailReceipt.status, func.count())
            .group_by(AuditoriaEmailReceipt.status)
        ).all()
        if k
    }
    omitidos_sin_aprobado = int(
        db.execute(
            select(func.count())
            .select_from(AuditoriaEmailMessage)
            .where(AuditoriaEmailMessage.classify == "sin_prestamo_aprobado")
        ).scalar()
        or 0
    )
    return {
        "total": total,
        "returned": len(items),
        "items": items,
        "status": status,
        "counts": {
            "pending": int(by_status.get("pending") or 0),
            "approved": int(by_status.get("approved") or 0),
            "revision": int(by_status.get("revision") or 0),
            "omitidos_sin_aprobado": omitidos_sin_aprobado,
        },
    }


def _claves_con_prestamo_aprobado(db: Session, claves: List[str]) -> set[str]:
    """
    Claves (normalizadas) con al menos un préstamo APROBADO.
    Une ``prestamos.cedula`` (cupo) y ``Cliente.cedula`` (misma vía que OK/A–D).
    Mismo criterio que usa el pipeline antes de gastar OCR.
    """
    from app.services.prestamos.cedula_aprobada import claves_con_prestamo_aprobado

    return claves_con_prestamo_aprobado(db, claves)


def materializar_recibos_desde_sync(
    db: Session,
    *,
    sync_id: Optional[int],
    message_ids: List[str],
    message_db_by_gmail: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Crea/actualiza filas pending en auditoria_email_receipts desde sync_items / temporal.

    Regla de ingreso a cola Recibos:
    - Sin cédula identificable → se carga (revisión manual).
    - Con cédula → solo si existe préstamo en estado ``APROBADO``.

    Devuelve gmail_message_ids que quedaron con al menos un recibo.
    """
    from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

    mids = [str(x).strip() for x in message_ids if str(x).strip()]
    if not mids:
        return {
            "creados": 0,
            "actualizados": 0,
            "listos_analizados": [],
            "omitidos_no_aprobado": [],
        }

    if sync_id is not None:
        items = (
            db.execute(
                select(PagosGmailSyncItem).where(
                    PagosGmailSyncItem.gmail_message_id.in_(mids),
                    PagosGmailSyncItem.sync_id == sync_id,
                )
            )
            .scalars()
            .all()
        )
    else:
        items = (
            db.execute(
                select(PagosGmailSyncItem).where(
                    PagosGmailSyncItem.gmail_message_id.in_(mids),
                )
            )
            .scalars()
            .all()
        )
    if not items and sync_id is None:
        items = []

    # Fallback: temporales por message_id
    temporals = (
        db.execute(
            select(GmailTemporal).where(GmailTemporal.gmail_message_id.in_(mids))
        )
        .scalars()
        .all()
    )
    temp_by_key: Dict[str, GmailTemporal] = {}
    for t in temporals:
        key = f"{t.gmail_message_id}|{t.numero_referencia or ''}|{t.cedula or ''}"
        temp_by_key[key] = t

    msg_id_map = dict(message_db_by_gmail or {})
    if not msg_id_map:
        for row in (
            db.execute(
                select(AuditoriaEmailMessage).where(
                    AuditoriaEmailMessage.gmail_message_id.in_(mids)
                )
            )
            .scalars()
            .all()
        ):
            msg_id_map[str(row.gmail_message_id)] = int(row.id)

    # Pre-cargar APROBADO por cédula (prestamos.cedula ∪ Cliente.cedula).
    cedulas_raw: List[str] = []
    for si in items:
        c = (si.cedula or "").strip()
        if not c:
            gt = temp_by_key.get(
                f"{si.gmail_message_id}|{si.numero_referencia or ''}|{si.cedula or ''}"
            )
            c = (gt.cedula if gt and gt.cedula else "") or ""
        if c.strip():
            cedulas_raw.append(c.strip())
    for gt in temporals:
        if (gt.cedula or "").strip():
            cedulas_raw.append(str(gt.cedula).strip())
    claves = []
    for c in cedulas_raw:
        k = normalizar_cedula_clave_cupo(c)
        if k:
            claves.append(k)
    aprobados_claves = _claves_con_prestamo_aprobado(db, claves)

    creados = 0
    actualizados = 0
    listos: List[str] = []
    omitidos_no_aprobado: List[str] = []

    def _cedula_permite_cola(cedula: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Returns (ok_ingresar, motivo_omitir).
        Sin cédula → ok. Con cédula sin APROBADO → omitir.
        """
        raw = (str(cedula).strip() if cedula else "") or ""
        if not raw:
            return True, None
        clave = normalizar_cedula_clave_cupo(raw)
        if not clave:
            # No se pudo normalizar → tratar como no identificable → cargar.
            return True, None
        if clave in aprobados_claves:
            return True, None
        return False, "sin_prestamo_aprobado"

    def _mark_msg_omitido(gmail_mid: str, cedula: Optional[str]) -> None:
        db_msg_id = msg_id_map.get(gmail_mid)
        if not db_msg_id:
            return
        msg = db.get(AuditoriaEmailMessage, int(db_msg_id))
        if msg is None:
            return
        msg.classify = "sin_prestamo_aprobado"
        msg.route = "omitido_no_aprobado"
        extract = dict(msg.extract_json or {})
        if cedula:
            extract["cedula"] = str(cedula).strip()
        extract["omit_reason"] = "sin_prestamo_aprobado"
        msg.extract_json = extract
        db.add(msg)
        # Quitar pending previos de esta cédula/mensaje (re-OCR cambió el filtro).
        db.execute(
            delete(AuditoriaEmailReceipt).where(
                AuditoriaEmailReceipt.message_id == int(db_msg_id),
                AuditoriaEmailReceipt.status == "pending",
            )
        )

    def _upsert_from(
        *,
        gmail_mid: str,
        cedula: Optional[str],
        monto_raw: Any,
        banco: Optional[str],
        fecha_pago: Optional[str],
        numero_ref: Optional[str],
        image_url: Optional[str],
        filename: Optional[str],
        sync_item_id: Optional[int],
        temporal_id: Optional[int],
        sid: Optional[int],
    ) -> None:
        nonlocal creados, actualizados
        db_msg_id = msg_id_map.get(gmail_mid)
        if not db_msg_id:
            return
        ok, motivo = _cedula_permite_cola(cedula)
        if not ok:
            omitidos_no_aprobado.append(gmail_mid)
            _mark_msg_omitido(gmail_mid, cedula)
            logger.info(
                "[AUDITORIA_EMAIL] omitido cola recibos mid=%s cedula=%s motivo=%s",
                gmail_mid,
                cedula,
                motivo,
            )
            return
        monto_f = _as_float(monto_raw)
        # Buscar recibo existente pending del mismo sync_item o mismo serial+message
        existing = None
        if sync_item_id:
            existing = (
                db.execute(
                    select(AuditoriaEmailReceipt).where(
                        AuditoriaEmailReceipt.sync_item_id == sync_item_id
                    )
                )
                .scalars()
                .first()
            )
        if existing is None and numero_ref:
            existing = (
                db.execute(
                    select(AuditoriaEmailReceipt).where(
                        AuditoriaEmailReceipt.message_id == db_msg_id,
                        AuditoriaEmailReceipt.numero_referencia == numero_ref,
                        AuditoriaEmailReceipt.status == "pending",
                    )
                )
                .scalars()
                .first()
            )
        payload = dict(
            message_id=db_msg_id,
            gmail_message_id=gmail_mid,
            filename=filename,
            cedula=(str(cedula).strip() if cedula else None) or None,
            monto=monto_f,
            banco=(str(banco).strip() if banco else None) or None,
            fecha_pago=(str(fecha_pago).strip() if fecha_pago else None) or None,
            numero_referencia=(str(numero_ref).strip() if numero_ref else None) or None,
            image_url=image_url or None,
            status="pending",
            sync_id=sid,
            sync_item_id=sync_item_id,
            gmail_temporal_id=temporal_id,
            route="pendiente_aprobacion",
            ocr_status="pagos_gmail",
        )
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            db.add(existing)
            actualizados += 1
        else:
            db.add(AuditoriaEmailReceipt(**payload, created_at=_utcnow()))
            creados += 1
        listos.append(gmail_mid)

    seen_items = set()
    for si in items:
        gmid = str(si.gmail_message_id or "").strip()
        if not gmid:
            continue
        seen_items.add(int(si.id))
        key = f"{gmid}|{si.numero_referencia or ''}|{si.cedula or ''}"
        gt = temp_by_key.get(key)
        _upsert_from(
            gmail_mid=gmid,
            cedula=si.cedula or (gt.cedula if gt else None),
            monto_raw=si.monto or (gt.monto if gt else None),
            banco=si.banco or (gt.banco if gt else None),
            fecha_pago=si.fecha_pago or (gt.fecha_pago if gt else None),
            numero_ref=si.numero_referencia or (gt.numero_referencia if gt else None),
            image_url=(si.drive_link or (gt.drive_link if gt else None)),
            filename=getattr(si, "filename", None) or (gt.banco if gt else None),
            sync_item_id=int(si.id),
            temporal_id=int(gt.id) if gt else None,
            sid=int(si.sync_id) if si.sync_id else sync_id,
        )

    # Temporales sin sync_item (raro) o huérfanos del lote
    for gt in temporals:
        gmid = str(gt.gmail_message_id or "").strip()
        if not gmid:
            continue
        # Si ya hay sync_item del mismo ref, ya materializado
        already = any(
            str(si.gmail_message_id) == gmid
            and (si.numero_referencia or "") == (gt.numero_referencia or "")
            for si in items
        )
        if already:
            continue
        _upsert_from(
            gmail_mid=gmid,
            cedula=gt.cedula,
            monto_raw=gt.monto,
            banco=gt.banco,
            fecha_pago=gt.fecha_pago,
            numero_ref=gt.numero_referencia,
            image_url=gt.drive_link,
            filename=gt.banco,
            sync_item_id=None,
            temporal_id=int(gt.id),
            sid=sync_id,
        )

    db.commit()
    unique_listos = list(dict.fromkeys(listos))
    unique_omit = list(dict.fromkeys(omitidos_no_aprobado))
    logger.info(
        "[AUDITORIA_EMAIL] materializar recibos sync=%s creados=%s actualizados=%s "
        "msgs=%s omitidos_no_aprobado=%s",
        sync_id,
        creados,
        actualizados,
        len(unique_listos),
        len(unique_omit),
    )
    return {
        "creados": creados,
        "actualizados": actualizados,
        "listos_analizados": unique_listos,
        "omitidos_no_aprobado": unique_omit,
    }


def _enviar_a_pagos_con_errores(
    db: Session, row: AuditoriaEmailReceipt, *, motivo: Optional[str] = None
) -> Dict[str, Any]:
    """Puerta a revisión manual vigente: migra temporal → pagos_con_errores."""
    from app.api.v1.endpoints.pagos_gmail.routes import (
        _migrar_pendientes_gmail_a_con_errores_core,
    )
    from app.models.pago_con_error import PagoConError

    mid = str(row.gmail_message_id or "").strip()
    if mid:
        mig = _migrar_pendientes_gmail_a_con_errores_core(
            db, gmail_message_ids=[mid]
        )
    else:
        mig = {"migrados": 0}

    # Si no había temporal, crear fila mínima en pagos_con_errores desde el recibo.
    pago_error_id = None
    if int(mig.get("migrados") or 0) == 0 and (
        row.cedula or row.numero_referencia or row.monto
    ):
        try:
            from app.api.v1.endpoints.pagos_gmail.routes import (
                _documento_ruta_desde_gmail_temporal,
                _parse_fecha_pago_gmail_temporal,
            )
            from app.core.documento import (
                compose_numero_documento_almacenado,
                normalize_documento,
            )
            from app.services.pago_numero_documento import numero_documento_ya_registrado
            from app.services.pagos_gmail.helpers import (
                format_monto_excel_pagos_gmail,
                formatear_cedula,
            )

            fallback = _utcnow()
            fecha_pago, _ = _parse_fecha_pago_gmail_temporal(
                row.fecha_pago,
                fallback,
                es_binance=(row.banco or "").strip().upper() == "BINANCE",
            )
            cedula = formatear_cedula(row.cedula or "")
            monto_txt = format_monto_excel_pagos_gmail(
                str(row.monto) if row.monto is not None else ""
            )
            try:
                monto_num = float(monto_txt) if monto_txt else float(row.monto or 0)
            except (TypeError, ValueError):
                monto_num = float(row.monto or 0)
            numero_base = normalize_documento(row.numero_referencia)
            numero_doc = compose_numero_documento_almacenado(
                numero_base or f"AUDREC-{row.id}", None
            )
            if not (numero_doc and numero_documento_ya_registrado(db, numero_doc)):
                obs = "Pendiente desde Auditoría Email (cola aprobación)"
                if motivo:
                    obs = f"{obs}; {motivo}"[:255]
                nuevo = PagoConError(
                    prestamo_id=None,
                    cedula_cliente=cedula or None,
                    fecha_pago=fecha_pago,
                    monto_pagado=monto_num,
                    numero_documento=numero_doc,
                    institucion_bancaria=(row.banco or None),
                    estado="PENDIENTE",
                    conciliado=False,
                    usuario_registro="AUDITORIA_EMAIL",
                    notas=f"Recibo auditoría email id={row.id}"[:1000],
                    referencia_pago=(numero_base or f"AUDREC-{row.id}")[:100],
                    observaciones=obs,
                    documento_ruta=_documento_ruta_desde_gmail_temporal(row.image_url),
                    documento_nombre=("Comprobante email" if row.image_url else None),
                )
                db.add(nuevo)
                db.flush()
                pago_error_id = int(nuevo.id)
                mig = {
                    **mig,
                    "migrados": 1,
                    "creado_desde_recibo": True,
                }
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] alta directa pagos_con_errores recibo=%s: %s",
                row.id,
                e,
            )

    if pago_error_id is None and row.numero_referencia:
        pe = (
            db.execute(
                select(PagoConError)
                .where(
                    PagoConError.referencia_pago == str(row.numero_referencia)[:100]
                )
                .order_by(desc(PagoConError.id))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if pe:
            pago_error_id = int(pe.id)
    if pago_error_id is None and row.cedula:
        pe = (
            db.execute(
                select(PagoConError)
                .where(PagoConError.cedula_cliente == row.cedula)
                .order_by(desc(PagoConError.id))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if pe:
            pago_error_id = int(pe.id)

    row.status = "revision"
    row.pago_error_id = pago_error_id
    row.resolved_at = _utcnow()
    row.route = "revision_manual"
    if motivo:
        row.last_error = str(motivo)[:500]
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "ok": False,
        "redirect": "/pagos?pestana=revision&revisar=1",
        "pagoErrorId": pago_error_id,
        "migracion": mig,
        "hint": "/pagos?pestana=revision",
        **receipt_dict(row),
    }


def aprobar_recibo(db: Session, receipt_id: int) -> Dict[str, Any]:
    """
    Puerta a procesos vigentes: validadores + alta + cuotas + cascada.
    Si pasa → cartera (approved). Si no → pagos_con_errores + redirect revisión.
    """
    row = db.get(AuditoriaEmailReceipt, receipt_id)
    if row is None:
        raise ValueError("Recibo no encontrado")
    st = (row.status or "").strip().lower() or "pending"
    if st == "approved":
        return {"ok": True, "already": True, **receipt_dict(row)}
    if st != "pending":
        # Evita re-alta / segundo pagos_con_errores si ya está en revisión u otro estado.
        out: Dict[str, Any] = {
            "ok": False,
            "already": True,
            "motivo": f"estado_no_pending ({st})",
            **receipt_dict(row),
        }
        if st == "revision":
            out["redirect"] = "/pagos?pestana=revision&revisar=1"
            out["hint"] = "/pagos?pestana=revision"
        return out

    fmt = _fmt_desde_banco(row.banco)
    if not fmt:
        return _enviar_a_pagos_con_errores(
            db,
            row,
            motivo="banco_solo_revision (E/F u otro no elegible para auto-alta)",
        )

    from app.services.pagos_gmail.pago_abcd_auto_service import (
        crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd,
    )
    from app.services.pagos_gmail.pago_nr_auto_service import (
        crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr,
    )

    try:
        if fmt == "NR":
            res = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr(
                db,
                cedula_columna=row.cedula or "",
                fecha_pago_str=row.fecha_pago or "",
                monto_operacion_str=str(row.monto) if row.monto is not None else "",
                numero_referencia=row.numero_referencia or "",
                institucion_bancaria=row.banco,
                link_comprobante=row.image_url,
                filename=row.filename,
                sync_id=row.sync_id,
                sync_item_id=row.sync_item_id,
                comprobante_imagen_id=None,
            )
        else:
            res = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
                db,
                cedula_columna=row.cedula or "",
                fecha_pago_str=row.fecha_pago or "",
                monto_str=str(row.monto) if row.monto is not None else "",
                numero_referencia=row.numero_referencia or "",
                institucion_bancaria=row.banco,
                link_comprobante=row.image_url,
                fmt=fmt,
                filename=row.filename,
                sync_id=row.sync_id,
                sync_item_id=row.sync_item_id,
                comprobante_imagen_id=None,
            )
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] aprobar recibo %s: %s", receipt_id, e)
        # Fallo técnico: dejar pending para reintento; no mezclar con validadores.
        row.last_error = str(e)[:500]
        row.status = "pending"
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "ok": False,
            "motivo": "exception",
            "error": str(e)[:300],
            **receipt_dict(row),
        }

    if res.get("ok") and str(res.get("etapa_final") or "") == "CUOTAS_OK":
        row.status = "approved"
        row.pago_id = res.get("pago_id")
        row.last_error = None
        row.resolved_at = _utcnow()
        row.route = "aprobado_cartera"
        db.add(row)
        if row.gmail_temporal_id:
            try:
                db.execute(
                    delete(GmailTemporal).where(
                        GmailTemporal.id == int(row.gmail_temporal_id)
                    )
                )
            except Exception:
                pass
        elif row.gmail_message_id and row.numero_referencia:
            try:
                db.execute(
                    delete(GmailTemporal).where(
                        GmailTemporal.gmail_message_id == row.gmail_message_id,
                        GmailTemporal.numero_referencia == row.numero_referencia,
                    )
                )
            except Exception:
                pass
        db.commit()
        db.refresh(row)
        return {"ok": True, "resultado": res, **receipt_dict(row)}

    # No pasó validadores / no CUOTAS_OK → revisión manual en /pagos
    motivo = str(res.get("motivo") or res.get("etapa_final") or "validacion")
    out = _enviar_a_pagos_con_errores(db, row, motivo=motivo)
    out["motivo"] = motivo
    out["resultado"] = res
    return out


def revision_manual_recibo(db: Session, receipt_id: int) -> Dict[str, Any]:
    """Envío explícito a pagos_con_errores (botón Revisión manual)."""
    row = db.get(AuditoriaEmailReceipt, receipt_id)
    if row is None:
        raise ValueError("Recibo no encontrado")
    out = _enviar_a_pagos_con_errores(db, row, motivo="revision_manual_usuario")
    out["ok"] = True
    return out


def aprobar_recibos_lote(db: Session, receipt_ids: List[int]) -> Dict[str, Any]:
    """
    Aprobación en lote (selección múltiple en Recibos).
    Por cada pending: validadores OK → cuotas/cartera; si no → pagos_con_errores.
    El escaneo NUNCA dispara alta; solo esta acción.
    """
    ids = [int(x) for x in receipt_ids if x is not None]
    # únicos preservando orden
    seen = set()
    ordered: List[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    if not ordered:
        raise ValueError("receiptIds vacío")

    aprobados: List[Dict[str, Any]] = []
    revision: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []
    omitidos: List[Dict[str, Any]] = []

    for rid in ordered:
        try:
            res = aprobar_recibo(db, rid)
        except ValueError as e:
            errores.append({"id": rid, "motivo": str(e)})
            continue
        except Exception as e:
            logger.exception("[AUDITORIA_EMAIL] lote aprobar id=%s: %s", rid, e)
            errores.append({"id": rid, "motivo": "exception", "error": str(e)[:300]})
            continue

        item = {
            "id": rid,
            "ok": bool(res.get("ok")),
            "status": res.get("status"),
            "pagoId": res.get("pagoId") or res.get("pago_id"),
            "pagoErrorId": res.get("pagoErrorId"),
            "motivo": res.get("motivo"),
            "already": res.get("already"),
        }
        if res.get("ok"):
            aprobados.append(item)
        elif res.get("motivo") and str(res.get("motivo")).startswith("estado_no_pending"):
            omitidos.append(item)
        elif res.get("motivo") == "exception":
            errores.append(item)
        else:
            # validadores / banco → revisión manual
            revision.append(item)

    return {
        "ok": True,
        "total": len(ordered),
        "aprobados": len(aprobados),
        "revision": len(revision),
        "errores": len(errores),
        "omitidos": len(omitidos),
        "itemsAprobados": aprobados,
        "itemsRevision": revision,
        "itemsErrores": errores,
        "itemsOmitidos": omitidos,
        "redirectRevision": "/pagos?pestana=revision&revisar=1"
        if revision
        else None,
    }


def eliminar_recibo(db: Session, receipt_id: int) -> Dict[str, Any]:
    """
    Elimina por completo el caso de la cola Recibos (fila + temporal ligado).
    No borra pagos ya aplicados ni quita etiquetas Gmail.
    """
    row = db.get(AuditoriaEmailReceipt, receipt_id)
    if row is None:
        raise ValueError("Recibo no encontrado")

    st = (row.status or "").strip().lower() or "pending"
    if st == "approved" and row.pago_id:
        raise ValueError(
            "No se puede eliminar un recibo ya aplicado a cuotas; anule el pago desde Pagos."
        )

    snapshot = receipt_dict(row, serial_estado=serial_estado_recibo(db, row))
    tid = row.gmail_temporal_id
    mid = row.gmail_message_id
    nref = row.numero_referencia

    db.delete(row)
    db.flush()

    if tid:
        try:
            db.execute(delete(GmailTemporal).where(GmailTemporal.id == int(tid)))
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] eliminar recibo: temporal id=%s: %s", tid, e
            )
    elif mid and nref:
        try:
            db.execute(
                delete(GmailTemporal).where(
                    GmailTemporal.gmail_message_id == mid,
                    GmailTemporal.numero_referencia == nref,
                )
            )
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] eliminar recibo: temporal mid=%s: %s", mid, e
            )

    db.commit()
    return {"ok": True, "eliminado": True, "id": receipt_id, "antes": snapshot}


def eliminar_recibos_lote(db: Session, receipt_ids: List[int]) -> Dict[str, Any]:
    """Eliminación masiva de recibos pending (cola Recibos)."""
    ids = [int(x) for x in receipt_ids if x is not None]
    seen = set()
    ordered: List[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    if not ordered:
        raise ValueError("receiptIds vacío")

    eliminados: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []
    omitidos: List[Dict[str, Any]] = []

    for rid in ordered:
        try:
            row = db.get(AuditoriaEmailReceipt, rid)
            if row is None:
                errores.append({"id": rid, "motivo": "no_encontrado"})
                continue
            st = (row.status or "").strip().lower() or "pending"
            if st != "pending":
                omitidos.append({"id": rid, "motivo": f"estado_no_pending ({st})"})
                continue
            res = eliminar_recibo(db, rid)
            eliminados.append({"id": rid, "ok": True, "eliminado": res.get("eliminado")})
        except ValueError as e:
            errores.append({"id": rid, "motivo": str(e)})
        except Exception as e:
            logger.exception("[AUDITORIA_EMAIL] lote eliminar id=%s: %s", rid, e)
            errores.append({"id": rid, "motivo": "exception", "error": str(e)[:300]})

    return {
        "ok": True,
        "total": len(ordered),
        "eliminados": len(eliminados),
        "errores": len(errores),
        "omitidos": len(omitidos),
        "itemsEliminados": eliminados,
        "itemsErrores": errores,
        "itemsOmitidos": omitidos,
    }
