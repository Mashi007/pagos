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
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Set

from sqlalchemy import or_, select

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Referencia interna automática (RPC-YYYYMMDD-NNNNN), con o sin prefijo COB-.
_REF_INTERNA_RPC_RECIBO = re.compile(r"^(COB-)?RPC-\d{8}-\d{5}$", re.IGNORECASE)
_SUFIJO_ADMIN_VISTO_DOC_RE = re.compile(r"_[AP]\d{4}$", re.IGNORECASE)


def numero_operacion_sin_sufijo_admin_visto(raw: Optional[str]) -> str:
    """Quita sufijo _A#### / _P#### (revision manual Cobros / carga masiva)."""
    s = (raw or "").strip()
    if not s:
        return ""
    return _SUFIJO_ADMIN_VISTO_DOC_RE.sub("", s).strip()


def _es_solo_referencia_interna_rpc_automatica(s: str) -> bool:
    return bool((s or "").strip() and _REF_INTERNA_RPC_RECIBO.match((s or "").strip()))


def reportado_tiene_serial_banco(pr: Any) -> bool:
    """
    True si hay número de operación del comprobante (no RPC, no marcador OCR).

    Sin serial de banco el estado de cuenta no puede mostrar el voucher:
    el caso es ambiguo y va a revisión manual. No se inventa el serial.
    """
    op = (getattr(pr, "numero_operacion", None) or "").strip()
    if not op:
        return False
    if op.upper().startswith("REV-MANUAL"):
        return False
    if _es_solo_referencia_interna_rpc_automatica(op):
        return False
    refi = (getattr(pr, "referencia_interna", None) or "").strip()
    if refi and op == refi and _es_solo_referencia_interna_rpc_automatica(refi):
        return False
    return True


def claves_serial_banco_cierre_importado(pr: Any) -> list[str]:
    """Claves de colisión para cerrar como importado: solo serial de banco, nunca RPC."""
    if not reportado_tiene_serial_banco(pr):
        return []
    op = (getattr(pr, "numero_operacion", None) or "").strip()[:100]
    if not op:
        return []
    out: list[str] = []
    for k in (op, normalize_documento(op) or ""):
        if k and k not in out:
            out.append(k)
    return out


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
    """
    Id de un `Pago` con el **serial de banco** del reporte (exacto o sufijo ``_P``/``_A``/``§CD:``).

    No usa la clave RPC ni Hamming de vecinos: eso cerraba el reporte como importado
    sin cargar el voucher del cliente al estado de cuenta.
    """
    claves = claves_serial_banco_cierre_importado(pr)
    if not claves:
        return None
    candidatos: Set[str] = set()
    for k in claves:
        if not k:
            continue
        c = normalize_documento(k) or k
        if c:
            candidatos.add(c)
    ids = _pago_ids_exactos_por_claves(db, claves, candidatos)
    op = (getattr(pr, "numero_operacion", None) or "").strip()
    ced_k = cedula_clave_reportado(pr)
    if op:
        for pid in _pago_ids_mismo_serial_sufijo_admin(
            db, op, cedula_clave=ced_k or None
        ):
            if pid not in ids:
                ids.append(pid)
    for pid in ids:
        if _pago_cierra_reportado_como_importado(db, pid, pr):
            return int(pid)
    return None


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

    PERF: SELECT solo (id, numero_operacion, referencia_interna) y una sola query con
    fetchmany() por bloques (sin OFFSET/LIMIT repetido). Antes hacia `select(PagoReportado)`
    -> hidratacion ORM completa incluyendo el blob ``recibo_pdf`` (~100 KB por fila), lo que
    convertia este barrido en 10+ segundos en PATCH de un solo reportado y bloqueaba el unico
    worker en Render. El cambio reduce de ~MB a ~KB por fila y reusa el cursor.
    """
    first: Dict[str, int] = {}
    if not norms:
        return first
    pending: Set[str] = set(norms)

    def _scan_phase(desde: Optional[datetime], cap: int) -> None:
        if not pending:
            return
        stmt = (
            select(
                PagoReportado.id,
                PagoReportado.numero_operacion,
                PagoReportado.referencia_interna,
            )
            .where(PagoReportado.estado.in_(_ESTADOS_REPORTADO_DUP_PEER))
            .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
        )
        if desde is not None:
            stmt = stmt.where(PagoReportado.created_at >= desde)
        seen = 0
        res = db.execute(stmt)
        block_size = 4000
        while pending and seen < cap:
            chunk = res.fetchmany(block_size)
            if not chunk:
                break
            for pid, op, ref in chunk:
                seen += 1
                if seen > cap:
                    return
                _, n_eff = documento_numero_desde_pago_reportado(
                    SimpleNamespace(numero_operacion=op, referencia_interna=ref)
                )
                if not n_eff or n_eff not in pending:
                    continue
                first[n_eff] = int(pid)
                pending.discard(n_eff)
                if not pending:
                    return

    _scan_phase(created_at_desde, max_rows_scan)
    if pending:
        _scan_phase(None, max(10_000, max_rows_scan // 2))
    return first


def pago_reportado_colisiona_tabla_pagos_documento_base(
    db: "Session",
    pr: PagoReportado,
) -> bool:
    """
    Colision con cartera usando el comprobante **sin** sufijo admin (_A#### / _P####).

    En bancos distintos a Mercantil no se permite reaplicar aunque el operador
    anada sufijo al numero de operacion.
    """
    op_raw = (getattr(pr, "numero_operacion", None) or "").strip()
    op_base = numero_operacion_sin_sufijo_admin_visto(op_raw)
    if op_base and op_base != op_raw:
        pr_base = SimpleNamespace(
            numero_operacion=op_base,
            referencia_interna=getattr(pr, "referencia_interna", None),
            tipo_cedula=getattr(pr, "tipo_cedula", None),
            numero_cedula=getattr(pr, "numero_cedula", None),
        )
        return pago_reportado_colisiona_tabla_pagos(db, pr_base)  # type: ignore[arg-type]
    return pago_reportado_colisiona_tabla_pagos(db, pr)


def serial_comprobante_canonico_colision(raw: Optional[str]) -> str:
    """
    Serial del comprobante para colisión anti-duplicado (sin Hamming).

    Quita ``§CD:`` y sufijo admin ``_A####`` / ``_P####``. No trata como igual
    seriales Mercantil vecinos (1 dígito de diferencia = otro voucher).
    """
    from app.core.documento import split_numero_documento_almacenado
    from app.services.pagos_gmail.parse_campos_comprobante import digitos_operacion_compacto

    s = (raw or "").strip()
    if not s:
        return ""
    base, _codigo = split_numero_documento_almacenado(s)
    base = numero_operacion_sin_sufijo_admin_visto(base or s)
    return digitos_operacion_compacto(base)


def serial_voucher_en_cartera(
    numero_documento: Optional[str],
    referencia_pago: Optional[str] = None,
    doc_canon_numero: Optional[str] = None,
) -> str:
    """
    Serial del voucher en estado de cuenta.

    Usa ``numero_documento`` (o ``doc_canon_numero``). ``referencia_pago`` solo
    cuenta si no hay serial en el documento: un vecino Hamming anotado en
    referencia (p. ej. ``7400… §CD:A2450``) no cierra otro comprobante.
    """
    nd = serial_comprobante_canonico_colision(numero_documento)
    if nd:
        return nd
    dc = serial_comprobante_canonico_colision(doc_canon_numero)
    if dc:
        return dc
    return serial_comprobante_canonico_colision(referencia_pago)


def cedula_clave_reportado(pr: Any) -> str:
    """Cédula comparable (V + dígitos) del reporte; vacía si falta."""
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

    t = (getattr(pr, "tipo_cedula", None) or "").strip()
    n = str(getattr(pr, "numero_cedula", None) or "").strip()
    if t and n:
        return texto_cedula_comparable_bd(f"{t}{n}")
    if n:
        return texto_cedula_comparable_bd(n)
    return ""


def _pago_cierra_reportado_como_importado(
    db: "Session",
    pago_id: int,
    pr: Any = None,
) -> bool:
    """
    Cerrar como ``importado`` si el pago está en estado de cuenta:

    - tiene ``cuota_pagos``, o
    - está ``PAGADO`` (p. ej. crédito LIQUIDADO sin cupo de cuotas).

    Un ``PENDIENTE`` sin ``cuota_pagos`` es limbo: no cierra el reporte.
    Si se pasa ``pr``, el voucher de ``numero_documento`` debe ser el serial
    del reporte y la cédula la misma (no Hamming en ``referencia_pago``).
    """
    from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

    aplicado = False
    try:
        if bool(pago_tiene_aplicaciones_cuotas(db, int(pago_id))):
            aplicado = True
    except Exception:
        pass
    pago = None
    try:
        pago = db.get(Pago, int(pago_id))
    except Exception:
        pago = None
    if not aplicado:
        try:
            est = (getattr(pago, "estado", None) or "").strip().upper()
            aplicado = bool(pago is not None and est == "PAGADO")
        except Exception:
            return False
    if not aplicado:
        return False
    if pr is None or pago is None:
        return True
    report_serial = serial_comprobante_canonico_colision(
        getattr(pr, "numero_operacion", None)
    )
    if not report_serial:
        return False
    voucher = serial_voucher_en_cartera(
        getattr(pago, "numero_documento", None),
        getattr(pago, "referencia_pago", None),
        getattr(pago, "doc_canon_numero", None),
    )
    if voucher != report_serial:
        return False
    want = cedula_clave_reportado(pr)
    if not want:
        return False
    have = texto_cedula_comparable_bd(getattr(pago, "cedula_cliente", None))
    return have == want


def _pago_ids_exactos_por_claves(db: "Session", claves_raw: list[str], candidatos: Set[str]) -> list[int]:
    ids: list[int] = []
    seen: Set[int] = set()

    def _add(row: Any) -> None:
        if not row:
            return
        pid = int(row[0])
        if pid not in seen:
            seen.add(pid)
            ids.append(pid)

    if candidatos:
        lst = list(candidatos)
        for i in range(0, len(lst), 450):
            part = lst[i : i + 450]
            if not part:
                continue
            for row in db.execute(select(Pago.id).where(Pago.doc_canon_numero.in_(part)).limit(20)):
                _add(row)
            for row in db.execute(select(Pago.id).where(Pago.doc_canon_referencia.in_(part)).limit(20)):
                _add(row)
    if claves_raw:
        for row in db.execute(select(Pago.id).where(Pago.numero_documento.in_(list(claves_raw))).limit(20)):
            _add(row)
        for row in db.execute(select(Pago.id).where(Pago.referencia_pago.in_(list(claves_raw))).limit(20)):
            _add(row)
    return ids


def _pago_ids_mismo_serial_sufijo_admin(
    db: "Session",
    numero_operacion: str,
    *,
    cedula_clave: Optional[str] = None,
) -> list[int]:
    """Mismo serial con ``_P####`` / ``_A####`` / ``§CD:`` en el voucher; no Hamming."""
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

    serial = serial_comprobante_canonico_colision(numero_operacion)
    if len(serial) < 8:
        return []
    rows = db.execute(
        select(
            Pago.id,
            Pago.numero_documento,
            Pago.referencia_pago,
            Pago.doc_canon_numero,
            Pago.cedula_cliente,
        )
        .where(
            or_(
                Pago.numero_documento.like(f"{serial}%"),
                Pago.doc_canon_numero.like(f"{serial}%"),
                Pago.referencia_pago.like(f"{serial}%"),
            )
        )
        .limit(80)
    ).all()
    out: list[int] = []
    seen: Set[int] = set()
    want_ced = (cedula_clave or "").strip()
    for row in rows:
        pid, nd, refp, canon = row[0], row[1], row[2], row[3]
        ced = row[4] if len(row) > 4 else None
        ipid = int(pid)
        if ipid in seen:
            continue
        if serial_voucher_en_cartera(nd, refp, canon) != serial:
            continue
        if want_ced and ced is not None:
            if texto_cedula_comparable_bd(ced) != want_ced:
                continue
        seen.add(ipid)
        out.append(ipid)
    return out


def pago_reportado_colisiona_tabla_pagos(db: "Session", pr: PagoReportado) -> bool:
    """
    True si el mismo comprobante ya está en cartera (cuotas o ``PAGADO``).

    Criterio (no inventa; no Hamming; no cierra por clave RPC):
    - serial de banco en el voucher (``numero_documento`` / ``doc_canon_numero``)
    - mismo serial con sufijo admin (``_P`` / ``_A`` / ``§CD:``) en ese voucher
    - misma cédula (otro cliente con el mismo serial no cierra este reporte)
    - el pago cierra el reporte (``cuota_pagos`` o estado ``PAGADO``)
    - sin serial de banco → False (revisión manual)
    """
    if not reportado_tiene_serial_banco(pr):
        return False
    claves_raw = claves_serial_banco_cierre_importado(pr)
    if not claves_raw:
        return False
    candidatos: Set[str] = set()
    for k in claves_raw:
        if not k:
            continue
        c = normalize_documento(k) or k
        if c:
            candidatos.add(c)
    ids = _pago_ids_exactos_por_claves(db, claves_raw, candidatos)
    op = (getattr(pr, "numero_operacion", None) or "").strip()
    ced_k = cedula_clave_reportado(pr)
    if op:
        for pid in _pago_ids_mismo_serial_sufijo_admin(
            db, op, cedula_clave=ced_k or None
        ):
            if pid not in ids:
                ids.append(pid)
    for pid in ids:
        if _pago_cierra_reportado_como_importado(db, pid, pr):
            return True
    return False


def numero_operacion_colisiona_reportado_activo(
    db: "Session",
    numero_operacion: Optional[str],
    *,
    excluir_id: Optional[int] = None,
) -> bool:
    """
    True si un ``pagos_reportados`` activo (pendiente/en_revision/aprobado) coincide
    por número de operación exacto o evasión (sufijo/prefijo).
    """
    from app.models.pago_reportado import PagoReportado
    from app.services.pago_numero_documento import _documento_colisiona_evasion_en_modelo

    op = (numero_operacion or "").strip()
    if not op:
        return False

    estados = ("pendiente", "en_revision", "aprobado")
    return _documento_colisiona_evasion_en_modelo(
        db,
        PagoReportado,
        op,
        exclude_id=excluir_id,
        value_column=PagoReportado.numero_operacion,
        extra_where=(PagoReportado.estado.in_(estados),),
    )


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
