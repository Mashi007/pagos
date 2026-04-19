# -*- coding: utf-8 -*-
"""
Registro en BD de la trazabilidad Gmail (plantilla A–D) → `pagos` → cuotas.

Usado desde el pipeline y desde `pago_abcd_auto_service`. Los fallos al insertar la traza
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
    fmt = (plantilla_fmt or "?")[:1].upper()
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
