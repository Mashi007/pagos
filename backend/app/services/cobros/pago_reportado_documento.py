"""
Documento unico en `pagos` para filas creadas desde `pagos_reportados`.

Criterio unificado (anti-duplicado / idempotencia):
- `documento_numero_desde_pago_reportado`: valor que se guarda en `pagos.numero_documento`.
- `claves_documento_pago_para_reportado`: posibles `pagos.numero_documento` que enlazan
  el mismo reporte (efectivo + COB-+RPC + RPC solo, por datos historicos).
- Import masivo, auto-import publico/Infopagos y Aprobar deben comprobar colision contra
  **todas** las claves, igual que este modulo expone.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional

from sqlalchemy import select

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def documento_numero_desde_pago_reportado(pr: PagoReportado) -> tuple[str, str]:
    """
    (raw, normalizado) para `pagos.numero_documento` y validacion de duplicados.

    Prioriza `numero_operacion` cuando no esta vacia; si no, `referencia_interna` (RPC-…).
    """
    op = (getattr(pr, "numero_operacion", None) or "").strip()[:100]
    rpc = (pr.referencia_interna or "").strip()[:100]
    raw = op if op else rpc
    norm = normalize_documento(raw) if raw else ""
    if raw and not norm:
        norm = raw[:100]
    return raw, norm


def claves_documento_pago_desde_campos(
    referencia_interna: Optional[str],
    numero_operacion: Optional[str],
) -> list[str]:
    """
    Misma lista que `claves_documento_pago_para_reportado` sin instancia ORM (para mapas en caliente).
    """
    ref = (referencia_interna or "").strip()
    op = (numero_operacion or "").strip()[:100]
    raw = op if op else ref
    norm = normalize_documento(raw) if raw else ""
    if raw and not norm:
        norm = raw[:100]
    doc_eff = norm or ""
    legacy_cob = ("COB-" + ref)[:100] if ref else ""
    ref_cut = ref[:100] if ref else ""
    out: list[str] = []
    for k in (doc_eff, legacy_cob, ref_cut):
        if k and k not in out:
            out.append(k)
    return out


def claves_documento_pago_para_reportado(pr: PagoReportado) -> list[str]:
    """
    Posibles valores de `pagos.numero_documento` que enlazan este reporte (idempotencia / estado de cuenta).

    Incluye documento efectivo actual y formatos legacy (COB-RPC, RPC solo) por datos historicos.
    """
    return claves_documento_pago_desde_campos(
        getattr(pr, "referencia_interna", None),
        getattr(pr, "numero_operacion", None),
    )


def claves_documento_para_lote_reportados(reportados: Iterable[PagoReportado]) -> set[str]:
    """Union de claves por fila (precarga IN contra `pagos.numero_documento` en import masivo)."""
    out: set[str] = set()
    for pr in reportados:
        for k in claves_documento_pago_para_reportado(pr):
            if k:
                out.add(k)
    return out


def primer_pago_id_si_existe_para_claves_reportado(db: "Session", pr: PagoReportado) -> Optional[int]:
    """Id de un `Pago` cuyo `numero_documento` coincide con alguna clave del reporte, o None."""
    claves = claves_documento_pago_para_reportado(pr)
    if not claves:
        return None
    return db.execute(select(Pago.id).where(Pago.numero_documento.in_(claves)).limit(1)).scalar()


def reportado_toca_claves_canonicas_en_pagos(
    pr: PagoReportado,
    claves_doc_en_pagos: frozenset,
) -> bool:
    """
    True si alguna clave del reporte, normalizada como en `_pagos_documentos_canonicos_*`,
    aparece ya en cartera (comparacion contra conjunto de canonicos de pagos).
    """
    if not claves_doc_en_pagos:
        return False
    for k in claves_documento_pago_para_reportado(pr):
        if not k:
            continue
        c = normalize_documento(k) or k
        if c in claves_doc_en_pagos:
            return True
    return False
