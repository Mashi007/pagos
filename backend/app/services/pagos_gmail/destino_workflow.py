# -*- coding: utf-8 -*-
"""Destino del comprobante Gmail según workflows de traza A–F/NR (sin deps HTTP)."""

from __future__ import annotations

from typing import Optional


def destino_workflow_sync_item(
    *,
    etapa_final: Optional[str],
    traza_pago_id: Optional[int],
    duplicado_en_pagos: bool,
) -> str:
    """
    Destino del comprobante según workflows ya implementados (traza A–F/NR).

    - **nuevo**: `CUOTAS_OK` con `pago_id` (alta automática aplicada a cartera/cuotas).
    - **viejo**: `OMITIDO_DUPLICADO` o serial ya en `pagos` (no se duplica).
    - **revision_manual**: resto (PAGO_SIN_CUOTAS, OMITIDO_NEGOCIO, sin traza, etc.).
    """
    etapa = (etapa_final or "").strip().upper()
    if etapa == "CUOTAS_OK" and traza_pago_id is not None:
        return "nuevo"
    if etapa == "OMITIDO_DUPLICADO" or duplicado_en_pagos:
        return "viejo"
    return "revision_manual"
