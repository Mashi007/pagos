# -*- coding: utf-8 -*-
"""
Registro en BD de la trazabilidad Gmail (plantillas A–D y **NR**) → `pagos` → cuotas.

Usado desde el pipeline y desde `pago_abcd_auto_service` / `pago_nr_auto_service`. Los fallos al insertar la traza
no deben interrumpir el pipeline (solo se registran en log).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza

logger = logging.getLogger(__name__)


def registrar_traza_gmail_abcd_cuotas_evento(
    db: Session,
    *,
    sync_id: Optional[int],
    sync_item_id: Optional[int],
    plantilla_fmt: str,
    cedula: Optional[str],
    numero_referencia: Optional[str],
    banco_excel: Optional[str],
    archivo_adjunto: Optional[str],
    comprobante_imagen_id: Optional[str],
    duplicado_documento: bool,
    etapa_final: str,
    motivo: Optional[str] = None,
    detalle: Optional[str] = None,
    pago_id: Optional[int] = None,
    prestamo_id: Optional[int] = None,
    cuotas_completadas: int = 0,
    cuotas_parciales: int = 0,
    conciliado_final: Optional[bool] = None,
    pago_estado_final: Optional[str] = None,
) -> None:
    """Inserta una fila de auditoría y hace commit (transacción independiente de otras operaciones)."""
    fmt = (plantilla_fmt or "?").strip().upper()[:4] or "?"
    row = PagosGmailAbcdCuotasTraza(
        sync_id=sync_id,
        sync_item_id=sync_item_id,
        plantilla_fmt=fmt,
        cedula=(cedula or "")[:50] or None,
        numero_referencia=(numero_referencia or "")[:200] or None,
        banco_excel=(banco_excel or "")[:50] or None,
        archivo_adjunto=(archivo_adjunto or "")[:500] or None,
        comprobante_imagen_id=(comprobante_imagen_id or "")[:32] or None,
        duplicado_documento=bool(duplicado_documento),
        etapa_final=(etapa_final or "DESCONOCIDO")[:40],
        motivo=(motivo or "")[:80] or None,
        detalle=(detalle or "")[:8000] if detalle else None,
        pago_id=pago_id,
        prestamo_id=prestamo_id,
        cuotas_completadas=int(cuotas_completadas or 0),
        cuotas_parciales=int(cuotas_parciales or 0),
        conciliado_final=conciliado_final,
        pago_estado_final=(pago_estado_final or "")[:30] or None,
    )
    try:
        db.add(row)
        db.commit()
    except Exception as e:
        logger.warning(
            "[PAGOS_GMAIL] [TRAZA_ABCD] No se pudo persistir traza (sync_item_id=%s etapa=%s): %s",
            sync_item_id,
            etapa_final,
            e,
        )
        try:
            db.rollback()
        except Exception:
            pass


def reconciliar_cuotas_ok_sin_pago_id(
    db: Session,
    *,
    max_ids: int = 200,
    dry_run: bool = False,
) -> dict:
    """
    Backfill de `pago_id`/`prestamo_id` en trazas `CUOTAS_OK` sin pago_id cuando
    ya existe el comprobante en `pagos` por `numero_documento` = `numero_referencia`.

    No crea pagos ni inventa datos; solo enlaza auditoría histórica.
    """
    from sqlalchemy import select as sa_select

    from app.models.pago import Pago

    cap = max(1, min(int(max_ids or 200), 1000))
    rows = list(
        db.execute(
            sa_select(PagosGmailAbcdCuotasTraza)
            .where(
                PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
                PagosGmailAbcdCuotasTraza.pago_id.is_(None),
                PagosGmailAbcdCuotasTraza.numero_referencia.isnot(None),
            )
            .order_by(PagosGmailAbcdCuotasTraza.id.asc())
            .limit(cap)
        )
        .scalars()
        .all()
    )
    linked = 0
    skipped = 0
    for row in rows:
        ref = (row.numero_referencia or "").strip()
        if not ref:
            skipped += 1
            continue
        pago = db.execute(
            sa_select(Pago)
            .where(Pago.numero_documento == ref)
            .order_by(Pago.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if pago is None:
            skipped += 1
            continue
        if dry_run:
            linked += 1
            continue
        row.pago_id = int(pago.id)
        if getattr(pago, "prestamo_id", None) is not None:
            row.prestamo_id = int(pago.prestamo_id)
        est = (getattr(pago, "estado", None) or "")[:30] or None
        row.pago_estado_final = est
        prev = (row.detalle or "").strip()
        nota = "[RECONCILIO] pago_id enlazado por numero_documento existente."
        if nota not in prev:
            row.detalle = (f"{prev} {nota}".strip() if prev else nota)[:8000]
        linked += 1
    if not dry_run and linked:
        try:
            db.commit()
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] [TRAZA_ABCD] reconciliar commit falló: %s", e
            )
            try:
                db.rollback()
            except Exception:
                pass
            return {
                "scanned": len(rows),
                "linked": 0,
                "skipped": skipped,
                "dry_run": dry_run,
            }
    logger.info(
        "[PAGOS_GMAIL] [TRAZA_ABCD] reconciliar CUOTAS_OK sin pago_id "
        "scanned=%s linked=%s skipped=%s dry_run=%s",
        len(rows),
        linked,
        skipped,
        dry_run,
    )
    return {
        "scanned": len(rows),
        "linked": linked,
        "skipped": skipped,
        "dry_run": dry_run,
    }
