# -*- coding: utf-8 -*-
"""Cola de aprobación Auditoría Email → Recibos."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, desc, func, select, tuple_
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
    from app.services.pagos_gmail.parse_campos_comprobante import (
        es_falso_serial_imagen_archivo,
    )

    raw_serial = r.numero_referencia
    if raw_serial and es_falso_serial_imagen_archivo(raw_serial):
        # Stub IMG-{hash} / nombre de archivo: no es Serial bancario.
        raw_serial = None
    serial_canon = _norm_serial(raw_serial, institucion=getattr(r, "banco", None))
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
        "numeroReferencia": serial_canon or raw_serial,
        # Clave canónica = misma que pagos.numero_documento (solo dígitos / Zelle A-Z0-9;
        # ignora MER/, BNC/, §CD:, _A/_P). La UI debe mostrar esto para alinear con cartera.
        "serial": serial_canon or raw_serial,
        "serialCanon": serial_canon or None,
        "serialRaw": r.numero_referencia,
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


def _norm_serial(
    raw: Optional[str],
    *,
    institucion: Optional[str] = None,
) -> str:
    """
    Clave de comparación UNICO/DUPLICADO — **misma** que cartera / anti-duplicado.

    - Quita ``§CD:D####``, listado `` · D####``, pegado ``D####`` y legado ``_A/_P``.
    - Prefijos/letras/signos (``MER/``, ``BNC/``, …) no cuentan: solo dígitos.
    - Zelle: A-Z0-9 (si ``institucion`` lo indica).

    Así ``BNC/5487…``, ``5487…``, ``5487… · D7341`` y ``5487… §CD:D7341`` colisionan igual.
    """
    from app.core.documento import (
        es_institucion_zelle,
        normalize_documento,
        split_numero_documento_almacenado,
    )
    from app.services.cobros.pago_reportado_documento import (
        numero_operacion_sin_sufijo_admin_visto,
    )
    from app.services.pagos_gmail.parse_campos_comprobante import (
        digitos_operacion_compacto,
    )

    s = (raw or "").strip()
    if not s:
        return ""
    from app.services.pagos_gmail.parse_campos_comprobante import (
        es_falso_serial_imagen_archivo,
    )

    if es_falso_serial_imagen_archivo(s):
        return ""
    base, _codigo = split_numero_documento_almacenado(s)
    base = numero_operacion_sin_sufijo_admin_visto(base or s)
    if not (base or "").strip():
        return ""
    if es_institucion_zelle(institucion):
        return (normalize_documento(base, institucion=institucion) or "").strip().upper()
    compact = digitos_operacion_compacto(base, institucion=institucion)
    if compact:
        return compact
    return (normalize_documento(base, institucion=institucion) or "").strip().upper()


def _es_asiento_banco_drive(
    institucion: Optional[str],
    numero_documento: Optional[str] = None,
) -> bool:
    """
    Asiento Drive (ABONOS / hoja CONCILIACIÓN) — falso positivo en cola Recibos.

    Solo institución explícita Drive / BANCO/DRIVE o serial ABONOS-*.
    No confundir con bancos reales (BNC, Mercantil, …).
    """
    from app.services.pago_autoconciliacion import es_referencia_abonos_drive_notif

    if es_referencia_abonos_drive_notif(numero_documento):
        return True
    t = (institucion or "").strip().lower().replace(" ", "")
    t = t.replace("-", "/")
    return t in ("drive", "banco/drive", "drive/banco")


def _listar_hits_numero_documento(
    db: Session,
    norm: str,
    raw: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
    exclude_pago_con_error_id: Optional[int] = None,
) -> List[Tuple[str, int, Optional[str], Optional[str]]]:
    """
    Hits en ``pagos.numero_documento`` / ``pagos_con_errores.numero_documento``.

    Devuelve lista de (tabla, id, numero_documento, institucion) cuya clave
    canónica coincide con ``norm`` (serial del recibo = numero de documento).
    """
    from app.models.pago import Pago
    from app.models.pago_con_error import PagoConError
    from app.services.pago_numero_documento import _candidatos_evasion_columna
    from app.services.pagos_gmail.parse_campos_comprobante import (
        digitos_operacion_compacto,
        numeros_operacion_coinciden_o_evasion,
    )
    from sqlalchemy import or_

    out: List[Tuple[str, int, Optional[str], Optional[str]]] = []
    seen: set[Tuple[str, int]] = set()

    def _add(tabla: str, rid: int, num: Optional[str], inst: Optional[str]) -> None:
        key = (tabla, int(rid))
        if key in seen:
            return
        n = _norm_serial(num, institucion=inst)
        if not (
            n == norm or numeros_operacion_coinciden_o_evasion(norm, num)
        ):
            return
        seen.add(key)
        out.append((tabla, int(rid), num, inst))

    def _scan(model, tabla: str, exclude_id: Optional[int]) -> None:
        conds = [func.upper(model.numero_documento) == norm.upper()]
        # Valor compuesto en BD: "5487… §CD:D1020" o "BNC5487…"
        if len(norm) >= 4:
            conds.append(model.numero_documento.like(f"%{norm}%"))
        q = select(model.id, model.numero_documento, model.institucion_bancaria).where(
            or_(*conds)
        )
        if exclude_id is not None:
            q = q.where(model.id != int(exclude_id))
        for rid, num, inst in db.execute(q.limit(120)):
            _add(tabla, int(rid), num, inst)

        compact = digitos_operacion_compacto(raw) or (
            norm if norm.isdigit() else ""
        )
        if not compact or len(compact) < 3:
            return
        for cond, _tag in _candidatos_evasion_columna(
            model.numero_documento, compact
        ):
            q2 = select(
                model.id, model.numero_documento, model.institucion_bancaria
            ).where(cond)
            if exclude_id is not None:
                q2 = q2.where(model.id != int(exclude_id))
            for rid, num, inst in db.execute(q2.limit(150)):
                _add(tabla, int(rid), num, inst)

    _scan(Pago, "pagos", exclude_pago_id)
    _scan(PagoConError, "pagos_con_errores", exclude_pago_con_error_id)
    return out


def _serial_duplicado_cartera_real(
    db: Session,
    raw: Optional[str],
    *,
    institucion_recibo: Optional[str] = None,
    exclude_pago_id: Optional[int] = None,
    exclude_pago_con_error_id: Optional[int] = None,
) -> bool:
    """
    True si el serial (= numero_documento) ya está en cartera real.

    1) Puerta vigente ``numero_documento_ya_registrado`` (misma que alta ABCD).
    2) Hits explícitos sobre ``pagos.numero_documento``.
    3) Si todos los hits son Drive/ABONOS → falso positivo → False.
    """
    from app.services.pago_numero_documento import numero_documento_ya_registrado

    norm = _norm_serial(raw, institucion=institucion_recibo)
    if not norm:
        return False

    gate = bool(
        numero_documento_ya_registrado(
            db,
            raw,
            exclude_pago_id=exclude_pago_id,
            exclude_pago_con_error_id=exclude_pago_con_error_id,
        )
        or numero_documento_ya_registrado(
            db,
            norm,
            exclude_pago_id=exclude_pago_id,
            exclude_pago_con_error_id=exclude_pago_con_error_id,
        )
    )

    hits = _listar_hits_numero_documento(
        db,
        norm,
        raw,
        exclude_pago_id=exclude_pago_id,
        exclude_pago_con_error_id=exclude_pago_con_error_id,
    )
    real = [
        h
        for h in hits
        if not _es_asiento_banco_drive(h[3], h[2])
    ]
    if real:
        return True
    if hits and not real:
        # Solo asientos Drive → no marcar DUPLICADO
        return False
    # Sin hits listados: confiar en la puerta de numero_documento
    return gate


def _cartera_info_por_serial(
    db: Session,
    raw: Optional[str],
    *,
    institucion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sin cédula OCR: resuelve UNICO/DUPLICADO y crédito vía ``numero_documento``.

    - DUPLICADO si el serial ya está en cartera (cualquier préstamo; Drive no cuenta).
    - Cédula / Préstamo solo si el pago apunta a crédito **APROBADO**
      (no DESISTIMIENTO ni LIQUIDADO).
    """
    from app.models.pago import Pago
    from app.models.pago_con_error import PagoConError
    from app.models.prestamo import Prestamo
    from app.services.prestamos.cedula_aprobada import canon_estado_columna_prestamo

    empty: Dict[str, Any] = {
        "norm": "",
        "duplicado": False,
        "cedula": None,
        "prestamoEstados": [],
        "prestamoIds": [],
    }
    norm = _norm_serial(raw, institucion=institucion)
    if not norm:
        return empty

    hits = _listar_hits_numero_documento(db, norm, raw)
    real = [h for h in hits if not _es_asiento_banco_drive(h[3], h[2])]
    duplicado = bool(real) or _serial_duplicado_cartera_real(
        db, raw, institucion_recibo=institucion
    )
    if not real:
        return {
            "norm": norm,
            "duplicado": duplicado,
            "cedula": None,
            "prestamoEstados": [],
            "prestamoIds": [],
        }

    pago_ids = [int(h[1]) for h in real if h[0] == "pagos"]
    err_ids = [int(h[1]) for h in real if h[0] == "pagos_con_errores"]
    cedulas: List[str] = []
    prestamo_ids: List[int] = []
    tiene_aprobado = False

    def _tomar_si_aprobado(ced: Any, pid: Any, est: Any) -> None:
        nonlocal tiene_aprobado
        if canon_estado_columna_prestamo(est) != "APROBADO":
            return
        tiene_aprobado = True
        c = (str(ced).strip() if ced else "") or ""
        if c:
            cedulas.append(c)
        if pid is not None:
            prestamo_ids.append(int(pid))

    if pago_ids:
        for ced, pid, est in db.execute(
            select(Pago.cedula_cliente, Pago.prestamo_id, Prestamo.estado)
            .outerjoin(Prestamo, Prestamo.id == Pago.prestamo_id)
            .where(Pago.id.in_(pago_ids))
        ).all():
            _tomar_si_aprobado(ced, pid, est)

    if err_ids and not tiene_aprobado:
        err_rows = db.execute(
            select(
                PagoConError.cedula_cliente,
                PagoConError.prestamo_id,
                Prestamo.estado,
            )
            .outerjoin(Prestamo, Prestamo.id == PagoConError.prestamo_id)
            .where(PagoConError.id.in_(err_ids))
        ).all()
        for ced, pid, est in err_rows:
            _tomar_si_aprobado(ced, pid, est)

    return {
        "norm": norm,
        "duplicado": True,
        "cedula": cedulas[0] if cedulas else None,
        "prestamoEstados": ["APROBADO"] if tiene_aprobado else [],
        "prestamoIds": list(dict.fromkeys(prestamo_ids)),
    }


def enrich_recibos_sin_cedula_via_serial(
    db: Session, items: List[Dict[str, Any]]
) -> None:
    """
    Si el OCR no trajo cédula: compara serial con BD y rellena Cola + Préstamo.

    In-place sobre dicts de ``receipt_dict`` / listado Recibos.
    """
    for it in items:
        ced = str(it.get("cedula") or "").strip()
        if ced:
            continue
        raw = (
            it.get("serialRaw")
            or it.get("serialCanon")
            or it.get("serial")
            or it.get("numeroReferencia")
        )
        try:
            info = _cartera_info_por_serial(
                db, raw, institucion=it.get("banco")
            )
        except Exception:
            logger.exception(
                "[AUDITORIA_EMAIL] cartera por serial falló recibo=%s",
                it.get("id"),
            )
            continue
        if not info.get("norm"):
            continue
        if info.get("duplicado"):
            it["serialEstado"] = "DUPLICADO"
        elif not it.get("serialEstado") or it.get("serialEstado") == "SIN_SERIAL":
            # Serial válido sin hit → UNICO (mismo criterio que con cédula).
            if info.get("norm"):
                it["serialEstado"] = "UNICO"
        if info.get("cedula"):
            it["cedula"] = info["cedula"]
            it["cedulaDesdeSerial"] = True
        estados = list(info.get("prestamoEstados") or [])
        if estados:
            it["prestamoEstados"] = estados
            it["prestamoEstado"] = estados[0]
        if info.get("prestamoIds"):
            it["prestamoIdsDesdeSerial"] = info["prestamoIds"]


def _registered_serials_batch(db: Session, norms: List[str]) -> set[str]:
    """
    Serials (= numero_documento) ya en pagos / pagos_con_errores reales.

    Asientos Drive no entran al set (falso positivo).
    """
    from app.models.pago import Pago
    from app.models.pago_con_error import PagoConError
    from sqlalchemy import or_

    unique = list({n for n in norms if n})
    if not unique:
        return set()
    found: set[str] = set()
    chunk_size = 200
    for i in range(0, len(unique), chunk_size):
        chunk = unique[i : i + chunk_size]
        chunk_set = set(chunk)

        def _consume(rows) -> None:
            for num, inst in rows:
                if _es_asiento_banco_drive(inst, num):
                    continue
                n = _norm_serial(num, institucion=inst)
                if n and n in chunk_set:
                    found.add(n)

        # Exacto por numero_documento
        _consume(
            db.execute(
                select(Pago.numero_documento, Pago.institucion_bancaria).where(
                    func.upper(Pago.numero_documento).in_(chunk)
                )
            ).all()
        )
        _consume(
            db.execute(
                select(
                    PagoConError.numero_documento, PagoConError.institucion_bancaria
                ).where(func.upper(PagoConError.numero_documento).in_(chunk))
            ).all()
        )
        # Prefijos / §CD: / BNC… en numero_documento
        digit_chunk = [n for n in chunk if n.isdigit() and len(n) >= 4]
        if digit_chunk:
            like_pago = [Pago.numero_documento.like(f"%{n}%") for n in digit_chunk]
            like_err = [
                PagoConError.numero_documento.like(f"%{n}%") for n in digit_chunk
            ]
            _consume(
                db.execute(
                    select(Pago.numero_documento, Pago.institucion_bancaria)
                    .where(or_(*like_pago))
                    .limit(2000)
                ).all()
            )
            _consume(
                db.execute(
                    select(
                        PagoConError.numero_documento,
                        PagoConError.institucion_bancaria,
                    )
                    .where(or_(*like_err))
                    .limit(2000)
                ).all()
            )

    # Sin remate N×numero_documento_ya_registrado: el batch exacto+LIKE basta
    # para la cola. El remate hacía timeout/502 en GET /recibos.
    return found


def serial_estado_recibo(
    db: Session,
    row: AuditoriaEmailReceipt,
    *,
    pending_counts: Optional[Dict[str, int]] = None,
    registered_norms: Optional[set[str]] = None,
) -> str:
    """
    UNICO / DUPLICADO en cola Recibos.

    Condicional de esta etapa: **serial** canónico vs cartera real.
    Matches en el préstamo con institución Drive (BANCO/DRIVE) = falso positivo
    → no marcan DUPLICADO.
    """
    raw = (row.numero_referencia or "").strip()
    if not raw:
        return "SIN_SERIAL"
    banco = getattr(row, "banco", None)
    norm = _norm_serial(raw, institucion=banco)
    if not norm:
        return "SIN_SERIAL"

    def _duplicado_en_bd() -> bool:
        # Con set precomputado: confiar en el batch (evita N consultas pesadas
        # que tumban GET /recibos con 502 HTML y dejan la UI vacía).
        if registered_norms is not None:
            if norm not in registered_norms:
                return False
            if row.pago_id or row.pago_error_id:
                return _serial_duplicado_cartera_real(
                    db,
                    raw,
                    institucion_recibo=banco,
                    exclude_pago_id=int(row.pago_id) if row.pago_id else None,
                    exclude_pago_con_error_id=int(row.pago_error_id)
                    if row.pago_error_id
                    else None,
                )
            return True
        return _serial_duplicado_cartera_real(
            db,
            raw,
            institucion_recibo=banco,
            exclude_pago_id=int(row.pago_id) if row.pago_id else None,
            exclude_pago_con_error_id=int(row.pago_error_id)
            if row.pago_error_id
            else None,
        )

    if _duplicado_en_bd():
        return "DUPLICADO"

    if pending_counts is not None:
        if int(pending_counts.get(norm) or 0) > 1:
            return "DUPLICADO"
        return "UNICO"

    for _oid, oref, obanco in db.execute(
        select(
            AuditoriaEmailReceipt.id,
            AuditoriaEmailReceipt.numero_referencia,
            AuditoriaEmailReceipt.banco,
        ).where(
            AuditoriaEmailReceipt.status == "pending",
            AuditoriaEmailReceipt.id != int(row.id),
            AuditoriaEmailReceipt.numero_referencia.isnot(None),
        )
    ):
        if _norm_serial(oref, institucion=obanco) == norm:
            return "DUPLICADO"
    return "UNICO"


def _pending_serial_counts(db: Session) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _rid, ref, banco in db.execute(
        select(
            AuditoriaEmailReceipt.id,
            AuditoriaEmailReceipt.numero_referencia,
            AuditoriaEmailReceipt.banco,
        ).where(
            AuditoriaEmailReceipt.status == "pending",
            AuditoriaEmailReceipt.numero_referencia.isnot(None),
        )
    ):
        norm = _norm_serial(ref, institucion=banco)
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
    prestamo_estado: Optional[str] = None,
    cola_estado: Optional[str] = None,
) -> Dict[str, Any]:
    st = (status or "pending").strip().lower()
    skip_n = max(0, int(skip or 0))
    limit_n = max(1, int(limit or 50))
    pe_raw = (prestamo_estado or "").strip().upper()
    if pe_raw in ("", "ALL", "*", "TODOS", "TODO"):
        pe_filtro = ""
    elif pe_raw in ("SIN", "SIN_PRESTAMO", "SIN-PRESTAMO", "NA", "NINGUNO", "NONE"):
        pe_filtro = "SIN"
    elif pe_raw == "APROBADO":
        pe_filtro = "APROBADO"
    else:
        pe_filtro = ""

    cola_raw = (cola_estado or "").strip().upper().replace(" ", "_")
    if cola_raw in ("", "ALL", "*", "TODOS", "TODO"):
        cola_filtro = ""
    elif cola_raw in ("UNICO", "ÚNICO"):
        cola_filtro = "UNICO"
    elif cola_raw in ("DUPLICADO", "DUP"):
        cola_filtro = "DUPLICADO"
    elif cola_raw in ("SIN_SERIAL", "SIN-SERIAL", "SINSERIAL", "SIN"):
        cola_filtro = "SIN_SERIAL"
    else:
        cola_filtro = ""

    # COUNT y SELECT independientes: reutilizar el mismo Select tras .subquery()
    # en SQLAlchemy puede devolver total=N e items de 1 fila.
    count_stmt = select(func.count()).select_from(AuditoriaEmailReceipt)
    list_stmt = select(AuditoriaEmailReceipt)
    if st not in ("all", "*", ""):
        filtro = AuditoriaEmailReceipt.status == st
        count_stmt = count_stmt.where(filtro)
        list_stmt = list_stmt.where(filtro)
    else:
        # No mostrar descartados (eliminados de la cola) en «Todos».
        filtro = AuditoriaEmailReceipt.status != "descartado"
        count_stmt = count_stmt.where(filtro)
        list_stmt = list_stmt.where(filtro)

    from app.services.prestamos.cedula_aprobada import (
        attach_prestamo_estado_items,
        estados_cartera_visibles_por_cedulas,
    )

    matching_ids: Optional[List[int]] = None
    if pe_filtro:
        meta_stmt_pe = select(
            AuditoriaEmailReceipt.id,
            AuditoriaEmailReceipt.cedula,
            AuditoriaEmailReceipt.numero_referencia,
            AuditoriaEmailReceipt.banco,
        )
        if st not in ("all", "*", ""):
            meta_stmt_pe = meta_stmt_pe.where(AuditoriaEmailReceipt.status == st)
        else:
            meta_stmt_pe = meta_stmt_pe.where(
                AuditoriaEmailReceipt.status != "descartado"
            )
        meta_rows = (
            db.execute(meta_stmt_pe.order_by(desc(AuditoriaEmailReceipt.id)))
            .all()
        )
        by_estados = estados_cartera_visibles_por_cedulas(
            db, [ced for _, ced, _, _ in meta_rows]
        )
        matching_ids = []
        for rid, ced, ref, banco in meta_rows:
            raw = (str(ced).strip() if ced else "") or ""
            estados = list(by_estados.get(raw) or [])
            # Sin cédula OCR: estados vía serial ↔ pagos.numero_documento.
            if not raw and (ref or "").strip():
                try:
                    info = _cartera_info_por_serial(
                        db, ref, institucion=banco
                    )
                    estados = list(info.get("prestamoEstados") or [])
                except Exception:
                    logger.exception(
                        "[AUDITORIA_EMAIL] filtro préstamo vía serial id=%s",
                        rid,
                    )
                    estados = []
            if pe_filtro == "SIN":
                if not estados:
                    matching_ids.append(int(rid))
            elif pe_filtro in estados:
                matching_ids.append(int(rid))

    if cola_filtro:
        # Necesitamos serialEstado de todos los candidatos antes de paginar.
        if matching_ids is not None:
            cand_ids = matching_ids
            if cand_ids:
                fetched = (
                    db.execute(
                        select(AuditoriaEmailReceipt).where(
                            AuditoriaEmailReceipt.id.in_(cand_ids)
                        )
                    )
                    .scalars()
                    .all()
                )
                by_id = {int(r.id): r for r in fetched}
                cand_rows = [by_id[i] for i in cand_ids if i in by_id]
            else:
                cand_rows = []
        else:
            cand_rows = (
                db.execute(list_stmt.order_by(desc(AuditoriaEmailReceipt.id)))
                .scalars()
                .all()
            )
        pending_counts: Optional[Dict[str, int]] = None
        registered_norms: Optional[set[str]] = None
        try:
            if st in ("pending", "all", "*", ""):
                pending_counts = _pending_serial_counts(db)
            norms = [
                _norm_serial(
                    r.numero_referencia, institucion=getattr(r, "banco", None)
                )
                for r in cand_rows
            ]
            registered_norms = _registered_serials_batch(db, norms)
        except Exception:
            logger.exception(
                "[AUDITORIA_EMAIL] precompute seriales (filtro cola) falló"
            )
            pending_counts = None
            registered_norms = None
        filtered_rows: List[AuditoriaEmailReceipt] = []
        for r in cand_rows:
            se = _serial_estado_safe(
                db,
                r,
                pending_counts=pending_counts,
                registered_norms=registered_norms,
            )
            if se == cola_filtro:
                filtered_rows.append(r)
        total = len(filtered_rows)
        rows = filtered_rows[skip_n : skip_n + limit_n]
        # Reutilizar precompute ya calculado para la página
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
    elif matching_ids is not None:
        total = len(matching_ids)
        page_ids = matching_ids[skip_n : skip_n + limit_n]
        if page_ids:
            fetched = (
                db.execute(
                    select(AuditoriaEmailReceipt).where(
                        AuditoriaEmailReceipt.id.in_(page_ids)
                    )
                )
                .scalars()
                .all()
            )
            by_id = {int(r.id): r for r in fetched}
            rows = [by_id[i] for i in page_ids if i in by_id]
        else:
            rows = []
        items = None  # se arma abajo
    else:
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
        items = None

    if items is None:
        pending_counts = None
        registered_norms = None
        try:
            if st in ("pending", "all", "*", ""):
                pending_counts = _pending_serial_counts(db)
            norms = [
                _norm_serial(
                    r.numero_referencia, institucion=getattr(r, "banco", None)
                )
                for r in rows
            ]
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

    attach_prestamo_estado_items(db, items)
    try:
        enrich_recibos_sin_cedula_via_serial(db, items)
    except Exception:
        logger.exception("[AUDITORIA_EMAIL] enrich sin cédula vía serial falló")
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
            .select_from(AuditoriaEmailReceipt)
            .where(
                AuditoriaEmailReceipt.status == "pending",
                AuditoriaEmailReceipt.route == "revision_sin_aprobado",
            )
        ).scalar()
        or 0
    )
    return {
        "total": total,
        "returned": len(items),
        "items": items,
        "status": status,
        "prestamoEstado": pe_filtro or None,
        "colaEstado": cola_filtro or None,
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
    - Toda imagen/comprobante digitalizado entra en pending (revisión manual incluida).
    - La única puerta dura de APROBADO es al pulsar OK (``aprobar_recibo``).

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

    def _cedula_tiene_aprobado(cedula: Optional[str]) -> bool:
        raw = (str(cedula).strip() if cedula else "") or ""
        if not raw:
            return False
        clave = normalizar_cedula_clave_cupo(raw)
        if not clave:
            return False
        return clave in aprobados_claves

    def _route_para_cola(
        cedula: Optional[str],
        *,
        numero_ref: Optional[str] = None,
        banco: Optional[str] = None,
    ) -> str:
        if _cedula_tiene_aprobado(cedula):
            return "pendiente_aprobacion"
        # Sin cédula: si el serial ya está en un pago de crédito APROBADO.
        if not (str(cedula or "").strip()) and (numero_ref or "").strip():
            try:
                info = _cartera_info_por_serial(
                    db, numero_ref, institucion=banco
                )
                if "APROBADO" in (info.get("prestamoEstados") or []):
                    return "pendiente_aprobacion"
            except Exception:
                logger.exception(
                    "[AUDITORIA_EMAIL] route vía serial falló ref=%s",
                    numero_ref,
                )
        return "revision_sin_aprobado"

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
        cedula_norm = (str(cedula).strip() if cedula else None) or None
        monto_f = _as_float(monto_raw)
        banco_s = (str(banco).strip() if banco else None) or None
        # Serial canónico (= clave cartera): alinea recibo BD con pagos.numero_documento.
        raw_ref = (str(numero_ref).strip() if numero_ref else "") or ""
        from app.services.pagos_gmail.parse_campos_comprobante import (
            es_falso_serial_imagen_archivo,
        )

        if raw_ref and es_falso_serial_imagen_archivo(raw_ref):
            raw_ref = ""
        serial_canon = _norm_serial(raw_ref, institucion=banco_s) if raw_ref else ""
        numero_ref_store = serial_canon or (raw_ref or None)
        # Sin cédula OCR: adoptar cédula del pago en cartera con ese serial.
        if not cedula_norm and numero_ref_store:
            try:
                info = _cartera_info_por_serial(
                    db, numero_ref_store, institucion=banco_s
                )
                if info.get("cedula"):
                    cedula_norm = str(info["cedula"]).strip() or None
            except Exception:
                logger.exception(
                    "[AUDITORIA_EMAIL] materializar cédula vía serial falló"
                )
        if cedula_norm and not _cedula_tiene_aprobado(cedula_norm):
            omitidos_no_aprobado.append(gmail_mid)
        # Buscar recibo existente del mismo sync_item o mismo serial+message.
        # Incluye no-pending: si el usuario lo eliminó (descartado) o ya OK,
        # no se debe reabrir ni crear un duplicado al rematerializar el lote.
        existing = None
        if sync_item_id:
            existing = (
                db.execute(
                    select(AuditoriaEmailReceipt)
                    .where(AuditoriaEmailReceipt.sync_item_id == sync_item_id)
                    .order_by(desc(AuditoriaEmailReceipt.id))
                )
                .scalars()
                .first()
            )
        if existing is None and numero_ref_store:
            candidates = (
                db.execute(
                    select(AuditoriaEmailReceipt)
                    .where(AuditoriaEmailReceipt.message_id == db_msg_id)
                    .order_by(desc(AuditoriaEmailReceipt.id))
                )
                .scalars()
                .all()
            )
            for cand in candidates:
                cref = (cand.numero_referencia or "").strip()
                if cref == numero_ref_store or cref == raw_ref:
                    existing = cand
                    break
                if serial_canon and _norm_serial(
                    cand.numero_referencia, institucion=cand.banco or banco_s
                ) == serial_canon:
                    existing = cand
                    break
        if existing is not None:
            est = (existing.status or "").strip().lower() or "pending"
            if est in ("descartado", "approved", "revision"):
                return
        payload = dict(
            message_id=db_msg_id,
            gmail_message_id=gmail_mid,
            filename=filename,
            cedula=cedula_norm,
            monto=monto_f,
            banco=banco_s,
            fecha_pago=(str(fecha_pago).strip() if fecha_pago else None) or None,
            numero_referencia=numero_ref_store,
            image_url=image_url or None,
            status="pending",
            sync_id=sid,
            sync_item_id=sync_item_id,
            gmail_temporal_id=temporal_id,
            route=_route_para_cola(
                cedula_norm,
                numero_ref=numero_ref_store,
                banco=banco_s,
            ),
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
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(
                "[AUDITORIA_EMAIL] alta directa pagos_con_errores recibo=%s: %s",
                row.id,
                e,
            )
            # Re-cargar fila tras rollback para poder marcar revision.
            row = db.get(AuditoriaEmailReceipt, int(row.id)) or row

    if pago_error_id is None and row.numero_referencia:
        ref_raw = str(row.numero_referencia).strip()
        ref_canon = _norm_serial(ref_raw, institucion=row.banco) or ref_raw
        pe = (
            db.execute(
                select(PagoConError)
                .where(
                    (PagoConError.referencia_pago == ref_raw[:100])
                    | (PagoConError.referencia_pago == ref_canon[:100])
                    | (func.upper(PagoConError.numero_documento) == ref_canon.upper())
                )
                .order_by(desc(PagoConError.id))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if pe is None and ref_canon and ref_canon.isdigit() and len(ref_canon) >= 6:
            for num, pe_id in db.execute(
                select(PagoConError.numero_documento, PagoConError.id)
                .where(PagoConError.numero_documento.like(f"%{ref_canon}%"))
                .order_by(desc(PagoConError.id))
                .limit(40)
            ):
                if _norm_serial(num) == ref_canon:
                    pe = db.get(PagoConError, int(pe_id))
                    break
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

    from app.services.prestamos.cedula_aprobada import cedula_tiene_prestamo_aprobado

    ced_ok = (row.cedula or "").strip()
    # Sin cédula OCR: resolver vía serial (= numero_documento) en cartera.
    if not ced_ok:
        try:
            info = _cartera_info_por_serial(
                db,
                row.numero_referencia,
                institucion=row.banco,
            )
        except Exception:
            logger.exception(
                "[AUDITORIA_EMAIL] aprobar: cartera por serial id=%s", receipt_id
            )
            info = {}
        if info.get("cedula") and "APROBADO" in (info.get("prestamoEstados") or []):
            ced_ok = str(info["cedula"]).strip()
            row.cedula = ced_ok
            db.add(row)
            db.flush()
        elif info.get("duplicado"):
            out = _enviar_a_pagos_con_errores(
                db,
                row,
                motivo="sin_cedula_serial_duplicado",
            )
            out["motivo"] = "sin_cedula_serial_duplicado"
            out["serialEstado"] = "DUPLICADO"
            return out
        else:
            out = _enviar_a_pagos_con_errores(
                db,
                row,
                motivo="sin_cedula",
            )
            out["motivo"] = "sin_cedula"
            out["serialEstado"] = "UNICO" if info.get("norm") else "SIN_SERIAL"
            return out

    if ced_ok and not cedula_tiene_prestamo_aprobado(db, ced_ok):
        out = _enviar_a_pagos_con_errores(
            db,
            row,
            motivo="sin_prestamo_aprobado",
        )
        out["motivo"] = "sin_prestamo_aprobado"
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
                numero_referencia=(
                    _norm_serial(row.numero_referencia, institucion=row.banco)
                    or row.numero_referencia
                    or ""
                ),
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
                numero_referencia=(
                    _norm_serial(row.numero_referencia, institucion=row.banco)
                    or row.numero_referencia
                    or ""
                ),
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
        db.flush()
        # Savepoint: fallo en temporal no debe invalidar el approved.
        if row.gmail_temporal_id:
            try:
                with db.begin_nested():
                    db.execute(
                        delete(GmailTemporal).where(
                            GmailTemporal.id == int(row.gmail_temporal_id)
                        )
                    )
            except Exception as e:
                logger.warning(
                    "[AUDITORIA_EMAIL] aprobar: temporal id=%s: %s",
                    row.gmail_temporal_id,
                    e,
                )
        elif row.gmail_message_id and row.numero_referencia:
            try:
                with db.begin_nested():
                    db.execute(
                        delete(GmailTemporal).where(
                            GmailTemporal.gmail_message_id == row.gmail_message_id,
                            GmailTemporal.numero_referencia == row.numero_referencia,
                        )
                    )
            except Exception as e:
                logger.warning(
                    "[AUDITORIA_EMAIL] aprobar: temporal mid=%s: %s",
                    row.gmail_message_id,
                    e,
                )
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
            try:
                db.rollback()
            except Exception:
                pass
            errores.append({"id": rid, "motivo": str(e)})
            continue
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
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
            # validadores / banco / sin APROBADO → revisión manual
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
    Saca el caso de la cola Recibos.

    Marca ``descartado`` (no hard-delete) para que un rematerializar del mismo
    sync_item / serial no lo vuelva a crear mientras el OCR del lote sigue.
    Limpia temporal ligado en transacción anidada (si falla, el descartado igual
    queda persistido; antes un fallo en temporal abortaba todo el commit).
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
    if st == "descartado":
        return {"ok": True, "eliminado": True, "id": receipt_id, "yaDescartado": True}

    # Snapshot liviano (sin serial_estado): evita N consultas pesadas en lotes.
    snapshot = receipt_dict(row)
    tid = row.gmail_temporal_id
    mid = row.gmail_message_id
    nref = row.numero_referencia

    row.status = "descartado"
    row.resolved_at = _utcnow()
    row.last_error = None
    db.add(row)
    db.flush()

    # Savepoint: un fallo en temporal no debe invalidar el descartado.
    if tid:
        try:
            with db.begin_nested():
                db.execute(delete(GmailTemporal).where(GmailTemporal.id == int(tid)))
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] eliminar recibo: temporal id=%s: %s", tid, e
            )
    elif mid and nref:
        try:
            with db.begin_nested():
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
    """
    Eliminación masiva de recibos pending (cola Recibos).

    Soft-delete en **una** transacción + limpieza de temporales en bloque.
    Evita N commits y el cálculo UNICO/DUPLICADO por fila (causa típica de
    timeouts / 502 HTML en proxy cuando la cola es grande).
    """
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

    # Tope defensivo: lotes enormes → trocear en el cliente; aquí evitamos OOM.
    MAX_LOTE = 500
    if len(ordered) > MAX_LOTE:
        raise ValueError(
            f"Máximo {MAX_LOTE} recibos por lote (recibidos {len(ordered)}). "
            "Seleccioná menos o eliminá por páginas."
        )

    ahora = _utcnow()
    rows = (
        db.execute(
            select(AuditoriaEmailReceipt).where(
                AuditoriaEmailReceipt.id.in_(ordered)
            )
        )
        .scalars()
        .all()
    )
    by_id = {int(r.id): r for r in rows}

    temporal_ids: List[int] = []
    temporal_pairs: List[Tuple[str, str]] = []
    a_descartar: List[AuditoriaEmailReceipt] = []

    for rid in ordered:
        row = by_id.get(rid)
        if row is None:
            errores.append({"id": rid, "motivo": "no_encontrado"})
            continue
        st = (row.status or "").strip().lower() or "pending"
        if st == "descartado":
            omitidos.append({"id": rid, "motivo": "ya_descartado"})
            continue
        if st == "approved" and row.pago_id:
            omitidos.append({"id": rid, "motivo": "estado_no_pending (approved)"})
            continue
        if st != "pending":
            omitidos.append({"id": rid, "motivo": f"estado_no_pending ({st})"})
            continue
        a_descartar.append(row)
        if row.gmail_temporal_id:
            try:
                temporal_ids.append(int(row.gmail_temporal_id))
            except (TypeError, ValueError):
                pass
        elif row.gmail_message_id and row.numero_referencia:
            temporal_pairs.append(
                (str(row.gmail_message_id), str(row.numero_referencia))
            )

    for row in a_descartar:
        row.status = "descartado"
        row.resolved_at = ahora
        row.last_error = None
        db.add(row)
        eliminados.append({"id": int(row.id), "ok": True, "eliminado": True})

    if a_descartar:
        try:
            db.flush()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception("[AUDITORIA_EMAIL] lote eliminar flush: %s", e)
            raise

        # Un solo savepoint para todos los temporales (sin N deletes por fila).
        try:
            with db.begin_nested():
                if temporal_ids:
                    db.execute(
                        delete(GmailTemporal).where(
                            GmailTemporal.id.in_(list(set(temporal_ids)))
                        )
                    )
                if temporal_pairs:
                    uniq_pairs = list(set(temporal_pairs))
                    db.execute(
                        delete(GmailTemporal).where(
                            tuple_(
                                GmailTemporal.gmail_message_id,
                                GmailTemporal.numero_referencia,
                            ).in_(uniq_pairs)
                        )
                    )
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] lote eliminar: temporales (%d ids / %d pairs): %s",
                len(temporal_ids),
                len(temporal_pairs),
                e,
            )

        try:
            db.commit()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception("[AUDITORIA_EMAIL] lote eliminar commit: %s", e)
            raise

    logger.info(
        "[AUDITORIA_EMAIL] lote eliminar: total=%s eliminados=%s omitidos=%s errores=%s",
        len(ordered),
        len(eliminados),
        len(omitidos),
        len(errores),
    )
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
