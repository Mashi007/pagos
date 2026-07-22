"""
Conciliar cartera en revisión manual (solo admin):
1) Lee total ABONOS de caché Notificaciones → General (ej. $531).
2) Reserva solo bytes de comprobante (sin metadatos de pagos).
3) Borra pagos del préstamo.
4) **Siempre** un asiento ABONOS (total General, sea cual sea el monto, sin comprobante).
5) **Siempre** un asiento por cada imagen guardada y reescaneada (monto OCR + imagen).
6) Cascada a cuotas.

Fórmula: 1 ABONOS + N comprobantes OCR → N+1 asientos.
Ejemplo (1 imagen): $531 ABONOS + $177 OCR = 2 asientos.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.documento import compose_numero_documento_almacenado
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.models.pagos_gmail_sync import PagosGmailSyncItem
from app.models.prestamo import Prestamo
from app.models.revision_manual_conciliacion_reserva import RevisionManualConciliacionReserva
from app.services.comparar_abonos_drive_cuotas_service import (
    UMBRAL_CONFIRMO_ABONOS_USD,
    referencia_abonos_notificaciones_general,
)
from app.services.cobros.cobros_publico_reporte_service import mime_efectivo_comprobante_web
from app.services.cuota_estado import TZ_NEGOCIO
from app.services.finiquito_conciliacion_visto_service import (
    _extraer_comprobante_id_hex,
    _vincular_comprobante_reserva_al_pago,
    cargar_bytes_comprobante,
)
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.services.pago_registro_moneda import resolver_monto_registro_pago
from app.services.pagos.comprobante_link_desde_gmail import (
    drive_raw_a_url,
    enriquecer_items_link_comprobante_desde_gmail,
)
from app.services.pagos_cuotas_reaplicacion import eliminar_todos_pagos_prestamo
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


def _placeholder_fecha_reserva() -> datetime:
    return datetime.now(ZoneInfo(TZ_NEGOCIO))


@dataclass(frozen=True)
class _FuenteComprobanteConciliar:
    """Origen de un comprobante candidato a reserva temporal (Conciliar cartera)."""

    fuente: str  # pago | pago_con_error | gmail_sync
    fuente_id: int
    link_comprobante: Optional[str]
    documento_ruta: Optional[str]
    referencia: str
    cedula_cliente: Optional[str]


def _cedula_sql_norm(col) -> Any:
    return func.upper(func.replace(func.coalesce(col, ""), "-", ""))


def _cedula_param_norm(cedula: Optional[str]) -> str:
    return (normalizar_cedula_almacenamiento(cedula or "") or "").replace("-", "").upper()


def _clave_enlace_comprobante(link: Optional[str], documento_ruta: Optional[str]) -> str:
    for raw in (link, documento_ruta):
        cid = _extraer_comprobante_id_hex(raw, None)
        if cid:
            return f"bd:{cid}"
        s = (raw or "").strip().lower()
        if s:
            return f"url:{s}"
    return ""


def _iter_fuentes_comprobante_conciliar_revision(
    db: Session,
    prestamo: Prestamo,
) -> List[_FuenteComprobanteConciliar]:
    """
    Pagos en cartera + pagos_con_errores (misma cédula) + ítems Gmail con drive_link.
    Conciliar debe reservar todas las imágenes disponibles, no solo filas ya en `pagos`.
    """
    out: List[_FuenteComprobanteConciliar] = []
    seen_enlaces: set[str] = set()
    ced_norm = _cedula_param_norm(prestamo.cedula)

    def _append(
        fuente: str,
        fuente_id: int,
        link: Optional[str],
        documento_ruta: Optional[str],
        referencia: str,
        cedula_cliente: Optional[str],
    ) -> None:
        if not (link or "").strip() and not (documento_ruta or "").strip():
            return
        clave = _clave_enlace_comprobante(link, documento_ruta)
        if not clave or clave in seen_enlaces:
            return
        seen_enlaces.add(clave)
        out.append(
            _FuenteComprobanteConciliar(
                fuente=fuente,
                fuente_id=int(fuente_id),
                link_comprobante=(link or "").strip() or None,
                documento_ruta=(documento_ruta or "").strip() or None,
                referencia=(referencia or "").strip() or f"{fuente}:{fuente_id}",
                cedula_cliente=(cedula_cliente or prestamo.cedula or "").strip() or None,
            )
        )

    pagos = (
        db.execute(
            select(Pago)
            .where(Pago.prestamo_id == prestamo.id)
            .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )
    for p in pagos:
        if not _tiene_comprobante(p):
            continue
        ref = (p.numero_documento or p.referencia_pago or str(p.id or "")).strip()
        _append(
            "pago",
            int(p.id or 0),
            p.link_comprobante,
            p.documento_ruta,
            ref or f"pago_id={p.id}",
            getattr(p, "cedula_cliente", None),
        )

    if ced_norm:
        cond_pce = [PagoConError.prestamo_id == prestamo.id]
        pc = _cedula_sql_norm(PagoConError.cedula_cliente)
        cond_pce.append(
            and_(PagoConError.prestamo_id.is_(None), pc == ced_norm)
        )
        pces = (
            db.execute(
                select(PagoConError)
                .where(or_(*cond_pce))
                .order_by(PagoConError.id.asc())
            )
            .scalars()
            .all()
        )
        for pce in pces:
            item: Dict[str, Any] = {
                "numero_documento": pce.numero_documento,
                "link_comprobante": None,
                "documento_ruta": pce.documento_ruta,
            }
            enriquecer_items_link_comprobante_desde_gmail(db, [item])
            ref = (pce.numero_documento or pce.referencia_pago or str(pce.id or "")).strip()
            _append(
                "pago_con_error",
                int(pce.id or 0),
                item.get("link_comprobante"),
                item.get("documento_ruta"),
                ref or f"pago_con_error_id={pce.id}",
                pce.cedula_cliente,
            )

        gsi_rows = (
            db.execute(
                select(PagosGmailSyncItem)
                .where(
                    _cedula_sql_norm(PagosGmailSyncItem.cedula) == ced_norm,
                    PagosGmailSyncItem.drive_link.isnot(None),
                    PagosGmailSyncItem.drive_link != "",
                )
                .order_by(PagosGmailSyncItem.id.asc())
            )
            .scalars()
            .all()
        )
        for gsi in gsi_rows:
            url = drive_raw_a_url(gsi.drive_link)
            ref = (gsi.numero_referencia or f"gmail-sync-{gsi.id}").strip()
            _append(
                "gmail_sync",
                int(gsi.id or 0),
                url,
                None,
                ref,
                gsi.cedula,
            )

    return out


def _evaluar_fuentes_comprobante_reserva(
    db: Session,
    fuentes: List[_FuenteComprobanteConciliar],
) -> Tuple[List[Tuple[_FuenteComprobanteConciliar, bytes, str]], List[Dict[str, Any]]]:
    """Carga bytes por fuente; deduplica por hash de imagen (misma foto en varias filas)."""
    reservables: List[Tuple[_FuenteComprobanteConciliar, bytes, str]] = []
    omitidos: List[Dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for fuente in fuentes:
        body, filename, err_bytes = cargar_bytes_comprobante(
            db,
            link_comprobante=fuente.link_comprobante,
            documento_ruta=fuente.documento_ruta,
        )
        base = {
            "fuente": fuente.fuente,
            "fuente_id": fuente.fuente_id,
            "referencia": fuente.referencia,
            "link_en_bd": "/comprobante-imagen/" in (fuente.link_comprobante or "").lower(),
        }
        if not body:
            omitidos.append({**base, "error": (err_bytes or "sin_bytes")[:500]})
            continue
        img_hash = hashlib.sha256(body).hexdigest()
        if img_hash in seen_hashes:
            continue
        seen_hashes.add(img_hash)
        fn = (filename or "comprobante.jpg").strip() or "comprobante.jpg"
        reservables.append((fuente, body, fn))

    return reservables, omitidos


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


def diagnostico_comprobantes_conciliar_prestamo(
    db: Session,
    prestamo_id: int,
) -> Dict[str, Any]:
    """
    Cuenta comprobantes reservables antes de Conciliar (pagos + con_errores + Gmail).
    No modifica BD.
    """
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Préstamo no encontrado"}

    pagos = (
        db.execute(
            select(Pago)
            .where(Pago.prestamo_id == prestamo_id)
            .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )
    fuentes = _iter_fuentes_comprobante_conciliar_revision(db, prestamo)
    reservables_raw, omitidos = _evaluar_fuentes_comprobante_reserva(db, fuentes)

    reservables = [
        {
            "fuente": f.fuente,
            "fuente_id": f.fuente_id,
            "pago_id": f.fuente_id if f.fuente == "pago" else None,
            "referencia": f.referencia,
            "link_en_bd": "/comprobante-imagen/" in (f.link_comprobante or "").lower(),
        }
        for f, _body, _fn in reservables_raw
    ]

    n_fuentes = len(fuentes)
    n_res = len(reservables)
    n_omit = len(omitidos)
    n_pagos_enlace = sum(1 for p in pagos if _tiene_comprobante(p))

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "total_pagos": len(pagos),
        "pagos_con_enlace": n_pagos_enlace,
        "fuentes_comprobante_total": n_fuentes,
        "fuentes_pago_cartera": sum(1 for f in fuentes if f.fuente == "pago"),
        "fuentes_pago_con_error": sum(1 for f in fuentes if f.fuente == "pago_con_error"),
        "fuentes_gmail_sync": sum(1 for f in fuentes if f.fuente == "gmail_sync"),
        "pagos_reservables": n_res,
        "pagos_omitidos_sin_bytes": n_omit,
        "reservables": reservables,
        "omitidos": omitidos,
        "requiere_confirmacion_comprobantes_omitidos": n_omit > 0,
        "sin_comprobantes_reservables": n_res == 0 and n_fuentes > 0,
    }


def _crear_pago_asiento_abonos_general(
    db: Session,
    prestamo: Prestamo,
    usuario_registro: str,
    *,
    abonos_total_usd: float,
    lote_aplicado: Optional[str] = None,
) -> Tuple[Optional[Pago], Optional[str]]:
    """Asiento 1: total ABONOS de Notificaciones → General, sin comprobante adjunto."""
    fecha_date = _placeholder_fecha_reserva().date()
    try:
        cedula_fk = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=(prestamo.cedula or "").strip() or None,
            prestamo_id=prestamo.id,
        )
    except CedulaPagoFkError as e:
        return None, str(e)

    monto_dec = Decimal(str(round(float(abonos_total_usd), 2)))
    ref = f"ABONOS-NOTIF-{prestamo.id}-{uuid.uuid4().hex[:8].upper()}"[:100]

    monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(
        db,
        cedula_normalizada=(cedula_fk or "").strip().upper(),
        fecha_pago=fecha_date,
        monto_pagado=monto_dec,
        moneda_registro="USD",
        tasa_cambio_manual=None,
    )

    msg_h = conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_date,
        monto_pagado=monto_usd,
        numero_documento=ref,
        referencia_pago=ref,
    )
    if msg_h:
        return None, msg_h

    ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
    nota = (
        "Conciliar cartera: asiento ABONOS (Notificaciones → General). "
        f"Monto hoja/caché: ${float(abonos_total_usd):.2f}."
    )
    lote_txt = (lote_aplicado or "").strip()
    if lote_txt:
        nota += f" Lote: {lote_txt}."

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=prestamo.id,
        fecha_pago=datetime.combine(fecha_date, dt_time.min),
        monto_pagado=monto_usd,
        numero_documento=ref,
        institucion_bancaria=None,
        estado="PAGADO",
        notas=nota,
        referencia_pago=ref,
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
    return pago, None


def _ref_sintetica_conciliar_ocr(
    prestamo_id: int,
    reserva_orden: int,
    *,
    n_hex: int = 6,
) -> str:
    return f"CONC-IMG-{prestamo_id}-{reserva_orden}-{uuid.uuid4().hex[:n_hex]}"[:100]


def _resolver_numero_documento_conciliar_ocr(
    db: Session,
    *,
    num_op: Optional[str],
    prestamo_id: int,
    reserva_orden: int,
    fecha_pago: date,
    monto_pagado: Decimal,
) -> Tuple[str, str]:
    """
    Elige par (numero_documento, referencia_pago) único en cartera.

    El OCR puede repetir un serial ya usado en otro préstamo (ux_pagos_numero_documento_btrim);
    en ese caso se desambigua con §CD: o referencia sintética CONC-IMG-…
    """

    def _valido(doc: str, ref: str) -> bool:
        if numero_documento_ya_registrado(db, doc):
            return False
        return (
            conflicto_huella_para_creacion(
                db,
                prestamo_id=prestamo_id,
                fecha_pago=fecha_pago,
                monto_pagado=monto_pagado,
                numero_documento=doc,
                referencia_pago=ref,
            )
            is None
        )

    candidatos: List[Tuple[str, str]] = []
    if num_op:
        base = compose_numero_documento_almacenado(num_op, None)
        if base:
            candidatos.append((base, base[:100]))
        for codigo in (f"P{prestamo_id}", f"CONC-{prestamo_id}-{reserva_orden}"):
            comp = compose_numero_documento_almacenado(num_op, codigo)
            if comp:
                candidatos.append((comp, (num_op or comp)[:100]))

    ref0 = _ref_sintetica_conciliar_ocr(prestamo_id, reserva_orden)
    candidatos.append((ref0, ref0))
    ref1 = _ref_sintetica_conciliar_ocr(prestamo_id, reserva_orden, n_hex=12)
    candidatos.append((ref1, ref1))

    seen: set[str] = set()
    for doc, ref in candidatos:
        doc_key = doc[:100]
        if doc_key in seen:
            continue
        seen.add(doc_key)
        ref_use = ref[:100]
        if _valido(doc_key, ref_use):
            return doc_key, ref_use

    ref_last = _ref_sintetica_conciliar_ocr(prestamo_id, reserva_orden, n_hex=16)
    return ref_last, ref_last


def _crear_pago_asiento_imagen_ocr(
    db: Session,
    reserva: RevisionManualConciliacionReserva,
    prestamo: Prestamo,
    usuario_registro: str,
    gem: Dict[str, Any],
) -> Tuple[Optional[Pago], Optional[str]]:
    """Asiento 2+: pago desde OCR del comprobante (monto de la imagen, no ABONOS)."""
    monto_raw = gem.get("monto")
    if monto_raw is None:
        return None, "OCR sin monto en el comprobante."
    try:
        monto_dec = Decimal(str(round(float(monto_raw), 2)))
    except (TypeError, ValueError):
        return None, "OCR devolvió un monto inválido."

    if monto_dec <= 0:
        return None, "OCR devolvió monto cero o negativo."

    fecha_date = gem.get("fecha_pago")
    if isinstance(fecha_date, datetime):
        fecha_date = fecha_date.date()
    if not isinstance(fecha_date, date):
        return None, "OCR sin fecha en el comprobante."

    num_op = sanitizar_numero_operacion_comprobante(gem.get("numero_operacion"))

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
        monto_pagado=monto_dec,
        moneda_registro=(str(gem.get("moneda") or "USD").strip().upper()[:10] or "USD"),
        tasa_cambio_manual=None,
    )

    num_stored, ref_tmp = _resolver_numero_documento_conciliar_ocr(
        db,
        num_op=num_op,
        prestamo_id=int(prestamo.id),
        reserva_orden=int(reserva.orden),
        fecha_pago=fecha_date,
        monto_pagado=monto_usd,
    )

    inst = (gem.get("institucion_financiera") or "").strip() or None
    ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=prestamo.id,
        fecha_pago=datetime.combine(fecha_date, dt_time.min),
        monto_pagado=monto_usd,
        numero_documento=num_stored[:100],
        institucion_bancaria=inst[:255] if inst else None,
        estado="PAGADO",
        notas="Conciliar cartera: asiento comprobante (monto y datos del reescaneo OCR).",
        referencia_pago=ref_tmp[:100],
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
) -> Dict[str, Any]:
    """Asiento comprobante: reescanea imagen reservada y crea pago con monto OCR (ej. $177)."""
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
            "tipo_asiento": "comprobante_ocr",
        }

    ctx_ced = normalizar_cedula_almacenamiento(
        (reserva.cedula_cliente or prestamo.cedula or "").strip()
    ) or ""
    gem = await extract_infopagos_campos_desde_comprobante_async(
        ctx_ced,
        body,
        filename,
        institucion_plantilla=None,
    )

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

    if not gem.get("ok"):
        db.flush()
        return {
            "reserva_id": reserva_id,
            "ok": False,
            "error": reserva.ocr_error,
            "pago_id": None,
            "tipo_asiento": "comprobante_ocr",
        }

    pago, err_crear = _crear_pago_asiento_imagen_ocr(
        db, reserva, prestamo, usuario_registro, gem
    )
    if err_crear:
        reserva.ocr_ok = False
        reserva.ocr_error = err_crear[:2000]
        db.flush()
        return {
            "reserva_id": reserva_id,
            "ok": False,
            "error": err_crear,
            "pago_id": None,
            "tipo_asiento": "comprobante_ocr",
        }

    if pago is not None:
        _vincular_comprobante_reserva_al_pago(db, reserva, pago)
        db.flush()
        db.delete(reserva)
        db.flush()

    monto_ocr: Optional[float] = None
    try:
        if pago is not None and pago.monto_pagado is not None:
            monto_ocr = float(pago.monto_pagado)
    except (TypeError, ValueError):
        monto_ocr = None

    return {
        "reserva_id": reserva_id,
        "ok": True,
        "error": None,
        "pago_id": pago.id if pago else None,
        "tipo_asiento": "comprobante_ocr",
        "monto_ocr_usd": monto_ocr,
    }


def _reservar_comprobantes_prestamo(
    db: Session,
    prestamo: Prestamo,
    *,
    permitir_sin_comprobantes: bool = False,
    confirmar_comprobantes_omitidos: bool = False,
) -> Dict[str, Any]:
    """Bytes de comprobante desde pagos, pagos_con_errores (cédula) e ítems Gmail."""
    pagos = (
        db.execute(
            select(Pago)
            .where(Pago.prestamo_id == prestamo.id)
            .order_by(Pago.fecha_pago.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )
    fuentes = _iter_fuentes_comprobante_conciliar_revision(db, prestamo)

    if not pagos and not fuentes:
        if permitir_sin_comprobantes:
            return {
                "ok": True,
                "reservas": 0,
                "reservas_sin_imagen": 0,
                "omitidos_sin_bytes": 0,
                "mensaje": "Sin pagos ni comprobantes en cartera; continuando solo con asiento ABONOS.",
            }
        return {
            "ok": False,
            "error": "No hay pagos ni comprobantes Gmail/errores para reservar.",
            "requiere_confirmacion_sin_comprobantes": True,
        }

    reservables, omitidos_detalle = _evaluar_fuentes_comprobante_reserva(db, fuentes)
    omitidos_sin_bytes = [str(o.get("referencia") or o.get("fuente_id") or "") for o in omitidos_detalle]
    orden = 0
    placeholder_fecha = _placeholder_fecha_reserva()

    for fuente, body, filename in reservables:
        orden += 1
        ct = mime_efectivo_comprobante_web(
            "",
            (filename or "comprobante.jpg").strip() or "comprobante.jpg",
        )
        pago_id_origen = fuente.fuente_id if fuente.fuente == "pago" else None
        db.add(
            RevisionManualConciliacionReserva(
                prestamo_id=int(prestamo.id),
                orden=orden,
                pago_id_origen=pago_id_origen,
                cedula_cliente=(prestamo.cedula or fuente.cedula_cliente or "").strip() or None,
                monto_pagado=Decimal("0"),
                fecha_pago=placeholder_fecha,
                numero_documento=None,
                referencia_pago=fuente.referencia[:100],
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
                notas=f"fuente={fuente.fuente}:{fuente.fuente_id}"[:500],
            )
        )

    n_fuentes = len(fuentes)

    if orden == 0:
        if permitir_sin_comprobantes:
            det = (
                f" ({len(omitidos_sin_bytes)} con enlace pero sin imagen descargable)"
                if omitidos_sin_bytes
                else ""
            )
            return {
                "ok": True,
                "reservas": 0,
                "reservas_sin_imagen": n_fuentes,
                "omitidos_sin_bytes": len(omitidos_sin_bytes),
                "omitidos_detalle": omitidos_sin_bytes,
                "fuentes_comprobante_total": n_fuentes,
                "mensaje": (
                    "Sin comprobantes con imagen reservables"
                    + det
                    + "; continuando solo con asiento ABONOS."
                ),
            }
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
            "requiere_confirmacion_sin_comprobantes": True,
            "omitidos_sin_bytes": len(omitidos_sin_bytes),
            "omitidos_detalle": omitidos_sin_bytes,
            "fuentes_comprobante_total": n_fuentes,
        }

    if omitidos_sin_bytes and not confirmar_comprobantes_omitidos:
        return {
            "ok": False,
            "error": (
                f"Solo se reservaron {orden} de {n_fuentes} comprobante(s) con imagen. "
                f"{len(omitidos_sin_bytes)} fuente(s) tienen enlace pero la imagen no está en el "
                "sistema. Si continúa, esos comprobantes no se recrearán."
            ),
            "requiere_confirmacion_comprobantes_omitidos": True,
            "reservas": orden,
            "omitidos_sin_bytes": len(omitidos_sin_bytes),
            "omitidos_detalle": omitidos_sin_bytes,
            "fuentes_comprobante_total": n_fuentes,
        }

    db.flush()
    msg = (
        f"Reservadas {orden} imagen(es) de comprobante en tabla temporal "
        f"(fuentes: {n_fuentes} pagos/Gmail/errores)."
    )
    if omitidos_sin_bytes:
        msg += f" Omitidos sin bytes: {len(omitidos_sin_bytes)}."
    return {
        "ok": True,
        "reservas": orden,
        "reservas_sin_imagen": 0,
        "omitidos_sin_bytes": len(omitidos_sin_bytes),
        "omitidos_detalle": omitidos_sin_bytes,
        "fuentes_comprobante_total": n_fuentes,
        "mensaje": msg,
    }


async def ejecutar_conciliar_cartera_revision_manual(
    db: Session,
    prestamo_id: int,
    usuario_registro: str,
    *,
    lote: Optional[str] = None,
    confirmacion_montos_altos: Optional[str] = None,
    confirmar_sin_comprobantes: bool = False,
    confirmar_comprobantes_omitidos: bool = False,
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

    est_bloqueado = (prestamo.estado or "").strip().upper()
    if est_bloqueado in {"DESISTIMIENTO", "RECHAZADO"}:
        return {
            "ok": False,
            "error": (
                f"No se puede conciliar cartera en préstamos {est_bloqueado} "
                f"(estado actual: {prestamo.estado or 'sin estado'})."
            ),
            "prestamo_id": prestamo_id,
            "estado_actual": prestamo.estado,
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

    reserva_out = _reservar_comprobantes_prestamo(
        db,
        prestamo,
        permitir_sin_comprobantes=confirmar_sin_comprobantes,
        confirmar_comprobantes_omitidos=confirmar_comprobantes_omitidos,
    )
    if not reserva_out.get("ok"):
        return {**reserva_out, "referencia_abonos": snap}

    # Persistir imágenes reservadas antes de borrar pagos (sobreviven rollback si falla OCR).
    if int(reserva_out.get("reservas") or 0) > 0:
        db.commit()

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

    abonos_total_objetivo = float(abonos_f or abonos_drive or 0)
    lote_snap = (snap.get("lote_aplicado") or lote or "").strip() or None

    pago_abonos, err_abonos = _crear_pago_asiento_abonos_general(
        db,
        prestamo,
        usuario_registro,
        abonos_total_usd=abonos_total_objetivo,
        lote_aplicado=lote_snap,
    )
    if err_abonos or pago_abonos is None:
        return {
            "ok": False,
            "error": err_abonos or "No se pudo crear el asiento ABONOS.",
            "prestamo_id": prestamo_id,
            "reservas": int(reserva_out.get("reservas") or 0),
            "pagos_eliminados": int(del_res.get("pagos_eliminados") or 0),
            "referencia_abonos": snap,
        }

    detalle: List[Dict[str, Any]] = [
        {
            "ok": True,
            "tipo_asiento": "abonos_general",
            "pago_id": pago_abonos.id,
            "monto_abonos_usd": abonos_total_objetivo,
        }
    ]

    filas = list(
        db.execute(
            select(RevisionManualConciliacionReserva)
            .where(RevisionManualConciliacionReserva.prestamo_id == prestamo_id)
            .order_by(RevisionManualConciliacionReserva.orden.asc())
        )
        .scalars()
        .all()
    )

    ocr_ok_n = 0
    for reserva in filas:
        item = await _ocr_fila_reserva_revision(db, reserva, prestamo, usuario_registro)
        detalle.append(item)
        if item.get("ok"):
            ocr_ok_n += 1

    ocr_fallidos = len(filas) - ocr_ok_n
    advertencia_parcial = ocr_fallidos > 0
    if len(filas) > 0 and ocr_ok_n == 0:
        advertencia_parcial = True

    total_pagos_usd = float(
        db.scalar(
            select(func.coalesce(func.sum(Pago.monto_pagado), 0)).where(
                Pago.prestamo_id == prestamo_id
            )
        )
        or 0
    )

    total_imagenes_ocr_usd = round(
        max(0.0, total_pagos_usd - abonos_total_objetivo),
        2,
    )
    pagos_recriados = 1 + ocr_ok_n

    # Cascada tras asiento ABONOS + asientos comprobante (OCR).
    cascada: Dict[str, Any] | None = None
    from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline

    logger.info(
        "revision conciliar cascada prestamo_id=%s abonos=%.2f imagenes_ocr=%.2f total=%.2f ocr_ok=%s/%s",
        prestamo_id,
        abonos_total_objetivo,
        total_imagenes_ocr_usd,
        total_pagos_usd,
        ocr_ok_n,
        len(filas),
    )
    cascada = aplicar_cascada_prestamo_pipeline(int(prestamo_id), db)

    drive_msg = (
        f" Asiento ABONOS: ${abonos_total_objetivo:.2f} (pago #{pago_abonos.id}); "
        f"asientos comprobante OCR: {ocr_ok_n}/{len(filas)} "
        f"(${total_imagenes_ocr_usd:.2f}); total cartera: ${total_pagos_usd:.2f}."
    )

    parcial_msg = ""
    if advertencia_parcial:
        parcial_msg = (
            f" Atención: {ocr_fallidos} comprobante(s) no generaron asiento OCR; "
            "solo quedó el asiento ABONOS si no hubo error previo."
        )

    ocr_msg = (
        f"Creados {pagos_recriados} asiento(s): 1 ABONOS (${abonos_total_objetivo:.2f}) + "
        f"{ocr_ok_n} comprobante(s) reescaneado(s)."
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
        "ocr_ok": ocr_ok_n,
        "ocr_total": len(filas),
        "ocr_fallidos": ocr_fallidos,
        "advertencia_parcial": advertencia_parcial,
        "pagos_recriados": pagos_recriados,
        "pago_id_abonos": pago_abonos.id,
        "total_pagos_recriados_usd": round(total_pagos_usd, 2),
        "total_imagenes_ocr_usd": total_imagenes_ocr_usd,
        "abonos_drive": abonos_drive,
        "abonos_total_aplicado_usd": round(abonos_total_objetivo, 2),
        "abonos_cuadra_total": False,
        "diferencia_drive_ocr_usd": round(total_imagenes_ocr_usd, 2),
        "diferencia_referencia_ocr_usd": round(total_imagenes_ocr_usd, 2),
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
    confirmar_sin_comprobantes: bool = False,
    confirmar_comprobantes_omitidos: bool = False,
) -> Dict[str, Any]:
    return asyncio.run(
        ejecutar_conciliar_cartera_revision_manual(
            db,
            prestamo_id,
            usuario_registro,
            lote=lote,
            confirmacion_montos_altos=confirmacion_montos_altos,
            confirmar_sin_comprobantes=confirmar_sin_comprobantes,
            confirmar_comprobantes_omitidos=confirmar_comprobantes_omitidos,
        )
    )
