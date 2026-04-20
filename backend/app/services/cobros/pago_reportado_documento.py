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

import re
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Set

from sqlalchemy import select

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Referencia interna automática (RPC-YYYYMMDD-NNNNN), con o sin prefijo COB-.
_REF_INTERNA_RPC_RECIBO = re.compile(r"^(COB-)?RPC-\d{8}-\d{5}$", re.IGNORECASE)


def _es_solo_referencia_interna_rpc_automatica(s: str) -> bool:
    return bool((s or "").strip() and _REF_INTERNA_RPC_RECIBO.match((s or "").strip()))


def texto_numero_documento_recibo_desde_reportado(pr: PagoReportado) -> str:
    """
    Valor del recibo PDF (voucher / Nº de documento del banco): ``numero_operacion`` del reporte,
    excepto cuando es la misma cadena que ``referencia_interna`` o solo la clave RPC automática.
    """
    op = (getattr(pr, "numero_operacion", None) or "").strip()
    refi = (getattr(pr, "referencia_interna", None) or "").strip()
    if not op:
        return ""
    if refi and op == refi:
        return ""
    if _es_solo_referencia_interna_rpc_automatica(op):
        return ""
    return op[:100]


def texto_numero_documento_recibo_desde_pago_cartera(
    numero_documento: Optional[str],
    referencia_pago: Optional[str],
) -> str:
    """Recibo cartera: preferir texto que no sea solo clave interna tipo RPC/COB-RPC."""
    nd = (numero_documento or "").strip()
    refp = (referencia_pago or "").strip()
    for cand in (nd, refp):
        if cand and not _es_solo_referencia_interna_rpc_automatica(cand):
            return cand[:100]
    return (refp or nd)[:100]


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


_ESTADOS_REPORTADO_DUP_PEER = ("pendiente", "en_revision", "aprobado")


def primer_reportado_id_por_norm_peer_first_map(
    db: "Session",
    norms: Set[str],
) -> Dict[str, int]:
    """
    Para cada documento normalizado en ``norms``, id del ``PagoReportado`` más antiguo
    (created_at asc, id asc) entre estados pendiente / en_revision / aprobado.

    Misma semántica que ``primer_reportado_id_por_norm_batch(..., created_at_desde=None)``
    cuando ese barrido cubriría toda la cola, pero:

    - Solo lee ``id``, ``numero_operacion``, ``referencia_interna`` (sin hidratar ORM completo).
    - Sale en cuanto tiene primer id para cada norm en ``norms`` (evita leer el resto de la tabla).
    """
    first: Dict[str, int] = {}
    if not norms:
        return first
    pending_left = len(norms)
    stmt = (
        select(PagoReportado.id, PagoReportado.numero_operacion, PagoReportado.referencia_interna)
        .where(PagoReportado.estado.in_(_ESTADOS_REPORTADO_DUP_PEER))
        .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
    )
    res = db.execute(stmt)
    while pending_left > 0:
        block = res.fetchmany(4000)
        if not block:
            break
        for pid, op, ref in block:
            _, n_eff = documento_numero_desde_pago_reportado(
                SimpleNamespace(numero_operacion=op, referencia_interna=ref)
            )
            if not n_eff or n_eff not in norms or n_eff in first:
                continue
            first[n_eff] = int(pid)
            pending_left -= 1
            if pending_left <= 0:
                break
    return first


def primer_reportado_id_por_norm_batch(
    db: "Session",
    norms: Set[str],
    *,
    created_at_desde: Optional[datetime] = None,
    max_rows_scan: int = 60_000,
) -> Dict[str, int]:
    """
    Para cada documento normalizado en `norms`, devuelve el id del `PagoReportado` mas antiguo
    (created_at asc, id asc) entre estados pendiente / en_revision / aprobado con ese documento.

    Sirve para marcar DUPLICADO solo a reenvios del mismo comprobante: el primero en tiempo no
    se considera duplicado frente a otros reportados; los posteriores si.

    Escaneo acotado por `created_at_desde` (p. ej. min(created_at del lote) - 30 dias) y por
    `max_rows_scan` filas leidas en total por fase.
    """
    first: Dict[str, int] = {}
    if not norms:
        return first
    pending: Set[str] = set(norms)

    def _scan_phase(desde: Optional[datetime], cap: int) -> None:
        if not pending:
            return
        stmt = (
            select(PagoReportado)
            .where(PagoReportado.estado.in_(_ESTADOS_REPORTADO_DUP_PEER))
            .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
        )
        if desde is not None:
            stmt = stmt.where(PagoReportado.created_at >= desde)
        seen = 0
        offset = 0
        batch = 800
        while pending and seen < cap:
            chunk = db.execute(stmt.offset(offset).limit(batch)).scalars().all()
            if not chunk:
                break
            for pr in chunk:
                seen += 1
                if seen > cap:
                    return
                _, n_eff = documento_numero_desde_pago_reportado(pr)
                if not n_eff or n_eff not in pending:
                    continue
                first[n_eff] = pr.id
                pending.discard(n_eff)
                if not pending:
                    return
            offset += len(chunk)
            if len(chunk) < batch:
                break

    _scan_phase(created_at_desde, max_rows_scan)
    if pending:
        _scan_phase(None, max(10_000, max_rows_scan // 2))
    return first


def pago_reportado_colisiona_tabla_pagos(db: "Session", pr: PagoReportado) -> bool:
    """
    True si el comprobante del reporte ya existe en cartera (`pagos`).

    Usa ``doc_canon_numero`` / ``doc_canon_referencia`` cuando existan (migración 041)
    y, en respaldo, coincidencia literal en ``numero_documento`` / ``referencia_pago``.
    """
    claves_raw = claves_documento_pago_para_reportado(pr)
    if not claves_raw:
        return False
    candidatos: Set[str] = set()
    for k in claves_raw:
        if not k:
            continue
        c = normalize_documento(k) or k
        if c:
            candidatos.add(c)
    if candidatos:
        lst = list(candidatos)
        for i in range(0, len(lst), 450):
            part = lst[i : i + 450]
            if not part:
                continue
            if db.execute(select(Pago.id).where(Pago.doc_canon_numero.in_(part)).limit(1)).first():
                return True
            if db.execute(select(Pago.id).where(Pago.doc_canon_referencia.in_(part)).limit(1)).first():
                return True
    if db.execute(select(Pago.id).where(Pago.numero_documento.in_(list(claves_raw))).limit(1)).first():
        return True
    if db.execute(select(Pago.id).where(Pago.referencia_pago.in_(list(claves_raw))).limit(1)).first():
        return True
    return False


def reportado_toca_claves_canonicas_en_pagos(
    pr: PagoReportado,
    claves_doc_en_pagos: frozenset,
) -> bool:
    """
    True si alguna clave del reporte, normalizada como `normalize_documento`,
    aparece en el conjunto ``claves_doc_en_pagos`` (típicamente canónicos presentes en
    ``pagos.doc_canon_*`` cruzados por lote contra las claves del reporte).
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
