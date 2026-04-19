# -*- coding: utf-8 -*-
"""
Persistencia best-effort de eventos del pipeline Gmail antes de crear fila sync/temporal.
Misma política que `gmail_abcd_cuotas_traza.registrar_traza_*`: commit aislado; fallo → log, no aborta pipeline.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.pagos_gmail_pipeline_evento import PagosGmailPipelineEvento

logger = logging.getLogger(__name__)

# Motivos estables (filtros / informes)
EVT_OMISION_ETIQUETA_USUARIO = "OMISION_ETIQUETA_USUARIO"
EVT_REMITENTE_INVALIDO = "REMITENTE_INVALIDO"
EVT_REMITENTE_NO_CLIENTE_CON_MEDIA = "REMITENTE_NO_CLIENTE_CON_MEDIA"
EVT_SIN_ADJUNTOS_DIGITABLES = "SIN_ADJUNTOS_DIGITABLES"
EVT_SOLO_PDF_MULTIPAGINA = "SOLO_PDF_MULTIPAGINA"
EVT_DEDUPE_SHA_CORRIDA = "DEDUPE_SHA_CORRIDA"
EVT_NO_PLANTILLA_GEMINI = "NO_PLANTILLA_GEMINI"
EVT_CAMPOS_INCOMPLETOS_PLANTILLA = "CAMPOS_INCOMPLETOS_PLANTILLA"
EVT_ERROR_PROCESAR_ADJUNTO = "ERROR_PROCESAR_ADJUNTO"


def registrar_pagos_gmail_pipeline_evento(
    db: Session,
    *,
    sync_id: Optional[int],
    gmail_message_id: str,
    gmail_thread_id: Optional[str],
    motivo: str,
    sha256_hex: Optional[str] = None,
    filename: Optional[str] = None,
    detalle: Optional[str] = None,
) -> None:
    mid = (gmail_message_id or "").strip()[:100]
    if not mid:
        return
    tid = (gmail_thread_id or "").strip()[:100] or None
    sh = (sha256_hex or "").strip().lower()[:64] or None
    if sh and len(sh) != 64:
        sh = None
    fn = (filename or "").strip()[:500] or None
    mot = (motivo or "DESCONOCIDO").strip()[:64]
    det = (detalle or "").strip()[:8000] if detalle else None
    row = PagosGmailPipelineEvento(
        sync_id=sync_id,
        gmail_message_id=mid,
        gmail_thread_id=tid,
        sha256_hex=sh,
        filename=fn,
        motivo=mot,
        detalle=det,
    )
    try:
        db.add(row)
        db.commit()
    except Exception as e:
        logger.warning(
            "[PAGOS_GMAIL] [PIPELINE_EVT] No persistir evento motivo=%s msg=%s: %s",
            mot,
            mid[:24],
            e,
        )
        try:
            db.rollback()
        except Exception:
            pass
