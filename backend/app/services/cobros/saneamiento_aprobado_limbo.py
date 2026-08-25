"""
Saneamiento de limbos de cobros sin inventar campos OCR ni montos/fechas/cédulas.

1. `aprobado` sin cierre → `importado` (solo si el pago ya aplicó a cuotas) o `en_revision`.
2. `importado` fantasma (sin pago aplicado) → `en_revision` para cola manual.
3. `en_revision` recuperable por bug `current_user` → reintento de carga.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, load_only

from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.services.cobros.cobros_publico_reporte_service import (
    intentar_importar_reportado_automatico,
    reportado_datos_cargables_a_cartera,
)
from app.services.cobros.pago_reportado_documento import (
    cedula_clave_reportado,
    pago_reportado_colisiona_tabla_pagos,
    reportado_tiene_serial_banco,
    serial_comprobante_canonico_colision,
    serial_voucher_en_cartera,
)
from app.services.pagos_gmail.parse_campos_comprobante import (
    mensaje_excepcion_autoconciliacion,
    reportado_exento_autoconciliacion,
)

logger = logging.getLogger(__name__)

MOTIVO_SISTEMA = "sistema@saneamiento-limbo"
NOTA_PREFIX = "[SANEAMIENTO_LIMBO]"
# Ventana pedida: ningún reporte desde 2026-01-01 queda importado sin cartera aplicada.
LIMBO_IMPORTADO_DESDE = date(2026, 1, 1)


@dataclass
class SaneamientoLimboResultado:
    scanned: int = 0
    marcado_importado_colision: int = 0
    importado_auto: int = 0
    a_en_revision: int = 0
    sin_cambio: int = 0
    errores: int = 0
    dry_run: bool = True
    detalle: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scanned": self.scanned,
            "marcado_importado_colision": self.marcado_importado_colision,
            "importado_auto": self.importado_auto,
            "a_en_revision": self.a_en_revision,
            "sin_cambio": self.sin_cambio,
            "errores": self.errores,
            "dry_run": self.dry_run,
            "detalle": self.detalle[:200],
        }


def _anotar(pr: PagoReportado, nota: str) -> None:
    prev = (getattr(pr, "gemini_comentario", None) or "").strip()
    full = f"{NOTA_PREFIX} {nota}".strip()
    if full in prev:
        pass
    else:
        pr.gemini_comentario = (f"{prev} {full}".strip() if prev else full)[:500]
    # También en observación de cola: la UI muestra observacion, no gemini_comentario.
    _anotar_observacion_cola(pr, nota)


def _anotar_observacion_cola(pr: PagoReportado, nota: str) -> None:
    """Persiste motivo visible en la columna Observación de pagos-reportados."""
    n = (nota or "").strip()
    if not n:
        return
    prev = (getattr(pr, "observacion", None) or "").strip()
    if n[:80] in prev:
        return
    pr.observacion = (f"{prev} / {n}".strip(" /") if prev else n)[:2000]


def _historial(
    db: Session,
    pr: PagoReportado,
    estado_anterior: str,
    estado_nuevo: str,
    motivo: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    db.add(
        PagoReportadoHistorial(
            pago_reportado_id=int(pr.id),
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            usuario_email=MOTIVO_SISTEMA,
            motivo=(motivo or "")[:500] or None,
        )
    )


def _motivo_no_cargable(pr: PagoReportado) -> str:
    if not reportado_datos_cargables_a_cartera(pr):
        return (
            "Datos del recibo incompletos o marcadores OCR "
            "(institución/operación/monto/fecha); requiere revisión manual."
        )
    mon = (getattr(pr, "moneda", None) or "USD").strip().upper()
    if mon == "USDT":
        mon = "USD"
    try:
        monto = float(getattr(pr, "monto", None) or 0)
    except (TypeError, ValueError):
        monto = 0.0
    if reportado_exento_autoconciliacion(monto, moneda=mon):
        return mensaje_excepcion_autoconciliacion(monto, moneda=mon)
    return "No elegible para carga automática; revisión manual."


def _puede_intentar_carga_automatica(pr: PagoReportado) -> bool:
    if not reportado_datos_cargables_a_cartera(pr):
        return False
    mon = (getattr(pr, "moneda", None) or "USD").strip().upper()
    if mon == "USDT":
        mon = "USD"
    try:
        monto = float(getattr(pr, "monto", None) or 0)
    except (TypeError, ValueError):
        monto = 0.0
    if reportado_exento_autoconciliacion(monto, moneda=mon):
        return False
    return True


def asegurar_aprobado_no_queda_en_limbo(
    db: Session,
    pr: PagoReportado,
    referencia: str,
    log_tag: str,
) -> str:
    """
    Cierre duro post-digitalización: `aprobado` debe terminar en `importado`
    o `en_revision`. No inventa datos; solo demote si el auto-import no cerró.
    """
    if pr is None:
        return "skip"
    estado = (getattr(pr, "estado", None) or "").strip()
    if estado != "aprobado":
        return estado or "skip"
    try:
        if pago_reportado_colisiona_tabla_pagos(db, pr):
            pr.estado = "importado"
            pr.falla_validadores_manual = False
            db.add(pr)
            db.commit()
            logger.info(
                "[%s] Limbo cerrado por colisión cartera ref=%s → importado",
                log_tag,
                referencia,
            )
            return "importado"
    except Exception as e:
        logger.warning("[%s] Colisión limbo ref=%s: %s", log_tag, referencia, e)
        try:
            db.rollback()
        except Exception:
            pass

    if not _puede_intentar_carga_automatica(pr):
        motivo = _motivo_no_cargable(pr)
        pr.estado = "en_revision"
        pr.falla_validadores_manual = True
        _anotar(pr, motivo)
        db.add(pr)
        db.commit()
        logger.info(
            "[%s] Limbo aprobado → en_revision (no cargable) ref=%s",
            log_tag,
            referencia,
        )
        return "en_revision"

    res = intentar_importar_reportado_automatico(db, pr, referencia, log_tag)
    try:
        db.refresh(pr)
    except Exception:
        pass
    estado2 = (getattr(pr, "estado", None) or "").strip()
    if estado2 == "importado":
        return "importado"
    if estado2 == "aprobado":
        # Cierre duro: nunca dejar aprobado tras el intento.
        err = (getattr(res, "error", None) or "auto-import no cerró a cartera").strip()
        pr.estado = "en_revision"
        pr.falla_validadores_manual = True
        _anotar(pr, err[:220])
        db.add(pr)
        db.commit()
        logger.warning(
            "[%s] Limbo aprobado forzado a en_revision ref=%s: %s",
            log_tag,
            referencia,
            err[:180],
        )
        return "en_revision"
    return estado2 or "en_revision"


def sanear_aprobados_en_limbo(
    db: Session,
    *,
    max_ids: int = 80,
    dry_run: bool = False,
    oldest_first: bool = True,
    include_detalle: bool = True,
) -> SaneamientoLimboResultado:
    """
    Procesa hasta `max_ids` reportes en `aprobado`.
    Por defecto oldest-first para drenar el backlog histórico.
    """
    out = SaneamientoLimboResultado(dry_run=dry_run)
    max_ids = max(1, min(int(max_ids or 80), 500))
    order = PagoReportado.id.asc() if oldest_first else PagoReportado.id.desc()
    ids = list(
        db.execute(
            select(PagoReportado.id)
            .where(PagoReportado.estado == "aprobado")
            .order_by(order)
            .limit(max_ids)
        )
        .scalars()
        .all()
    )
    out.scanned = len(ids)

    for pid in ids:
        try:
            pr = db.get(PagoReportado, int(pid))
            if pr is None or (getattr(pr, "estado", None) or "").strip() != "aprobado":
                out.sin_cambio += 1
                continue
            estado_ant = "aprobado"
            ref = (pr.referencia_interna or "").strip() or str(pr.id)
            accion = "sin_cambio"
            motivo = ""

            if pago_reportado_colisiona_tabla_pagos(db, pr):
                accion = "importado_colision"
                motivo = "Comprobante ya existe en pagos; se cierra como importado."
                if not dry_run:
                    pr.estado = "importado"
                    pr.falla_validadores_manual = False
                    _anotar(pr, motivo)
                    db.add(pr)
                    _historial(db, pr, estado_ant, "importado", motivo, dry_run=False)
                    db.commit()
                out.marcado_importado_colision += 1

            elif not _puede_intentar_carga_automatica(pr):
                accion = "en_revision"
                motivo = _motivo_no_cargable(pr)
                if not dry_run:
                    pr.estado = "en_revision"
                    pr.falla_validadores_manual = True
                    _anotar(pr, motivo)
                    db.add(pr)
                    _historial(db, pr, estado_ant, "en_revision", motivo, dry_run=False)
                    db.commit()
                out.a_en_revision += 1

            else:
                if dry_run:
                    accion = "import_candidato"
                    motivo = "Candidato a carga automática (dry-run; no se persistió)."
                    out.sin_cambio += 1
                else:
                    intentar_importar_reportado_automatico(
                        db, pr, ref, "SANEAMIENTO_LIMBO"
                    )
                    try:
                        db.refresh(pr)
                    except Exception:
                        pass
                    estado_nuevo = (getattr(pr, "estado", None) or "").strip()
                    if estado_nuevo == "importado":
                        accion = "importado_auto"
                        motivo = "Cargado a pagos con datos del recibo (sin inventar campos)."
                        _historial(
                            db, pr, estado_ant, "importado", motivo, dry_run=False
                        )
                        db.commit()
                        out.importado_auto += 1
                    elif estado_nuevo == "aprobado":
                        accion = "en_revision"
                        motivo = (
                            "Auto-import no materializó el pago; pasa a revisión manual."
                        )
                        pr.estado = "en_revision"
                        pr.falla_validadores_manual = True
                        _anotar(pr, motivo)
                        db.add(pr)
                        _historial(
                            db, pr, estado_ant, "en_revision", motivo, dry_run=False
                        )
                        db.commit()
                        out.a_en_revision += 1
                    else:
                        accion = estado_nuevo or "en_revision"
                        motivo = f"Estado post-import={accion}"
                        if estado_nuevo == "en_revision":
                            _historial(
                                db,
                                pr,
                                estado_ant,
                                "en_revision",
                                motivo,
                                dry_run=False,
                            )
                            try:
                                db.commit()
                            except Exception:
                                db.rollback()
                            out.a_en_revision += 1
                        else:
                            out.sin_cambio += 1

            if include_detalle:
                out.detalle.append(
                    {
                        "id": int(pr.id),
                        "ref": ref,
                        "accion": accion,
                        "motivo": motivo[:240],
                    }
                )
        except Exception as e:
            out.errores += 1
            logger.warning(
                "[SANEAMIENTO_LIMBO] Error id=%s: %s", pid, e, exc_info=False
            )
            try:
                db.rollback()
            except Exception:
                pass
            if include_detalle:
                out.detalle.append(
                    {"id": int(pid), "ref": None, "accion": "error", "motivo": str(e)[:240]}
                )

    logger.info(
        "[SANEAMIENTO_LIMBO] scanned=%s colision=%s import_auto=%s revision=%s "
        "sin_cambio=%s errores=%s dry_run=%s",
        out.scanned,
        out.marcado_importado_colision,
        out.importado_auto,
        out.a_en_revision,
        out.sin_cambio,
        out.errores,
        dry_run,
    )
    return out


# --- Recuperables en_revision (bug histórico current_user / colisión cartera) ---

BUG_CURRENT_USER = "name 'current_user' is not defined"


@dataclass
class SaneamientoRevisionResultado:
    scanned: int = 0
    marcado_importado_colision: int = 0
    reintentado_import: int = 0
    importado_auto: int = 0
    sigue_en_revision: int = 0
    errores: int = 0
    dry_run: bool = True
    detalle: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scanned": self.scanned,
            "marcado_importado_colision": self.marcado_importado_colision,
            "reintentado_import": self.reintentado_import,
            "importado_auto": self.importado_auto,
            "sigue_en_revision": self.sigue_en_revision,
            "errores": self.errores,
            "dry_run": self.dry_run,
            "detalle": self.detalle[:200],
        }


def _es_recuperable_por_bug_current_user(pr: PagoReportado) -> bool:
    nota = getattr(pr, "gemini_comentario", None) or ""
    return BUG_CURRENT_USER in nota


def sanear_en_revision_recuperables(
    db: Session,
    *,
    max_ids: int = 80,
    dry_run: bool = False,
    include_detalle: bool = True,
    solo_bug_current_user: bool = True,
) -> SaneamientoRevisionResultado:
    """
    Recupera `en_revision` que pueden cerrarse sin inventar datos:
    - comprobante ya en `pagos` → `importado`
    - nota histórica del bug `current_user` + datos cargables → reintenta auto-import
      vía `aprobado` + `asegurar_aprobado_no_queda_en_limbo`
    """
    out = SaneamientoRevisionResultado(dry_run=dry_run)
    max_ids = max(1, min(int(max_ids or 80), 500))
    q = (
        select(PagoReportado.id)
        .where(PagoReportado.estado == "en_revision")
        .order_by(PagoReportado.id.asc())
        .limit(max_ids * 4)
    )
    if solo_bug_current_user:
        q = q.where(PagoReportado.gemini_comentario.ilike("%current_user%"))
    ids = list(db.execute(q).scalars().all())[:max_ids]
    out.scanned = len(ids)

    for pid in ids:
        try:
            pr = db.get(PagoReportado, int(pid))
            if pr is None or (getattr(pr, "estado", None) or "").strip() != "en_revision":
                continue
            ref = (pr.referencia_interna or "").strip() or str(pr.id)
            accion = "sin_cambio"
            motivo = ""

            if not reportado_tiene_serial_banco(pr):
                out.sigue_en_revision += 1
                accion = "queda_en_revision"
                motivo = (
                    "Serial de banco vacío o ambiguo (RPC/OCR); "
                    "revisión manual. No se cierra por clave interna."
                )
            elif pago_reportado_colisiona_tabla_pagos(db, pr):
                # No cerrar a importado desde este job: En revisión es cola del
                # operador. Cerrar aquí (y el reconciliador cada 20 min) hacía
                # saltar Por gestionar / En revisión.
                out.sigue_en_revision += 1
                accion = "queda_en_revision"
                motivo = (
                    "Comprobante ya en cartera; permanece en revisión manual. "
                    "Elimine el reporte de cobros si no lo necesita; el pago no se borra."
                )
            elif _es_recuperable_por_bug_current_user(pr) and _puede_intentar_carga_automatica(
                pr
            ):
                accion = "reintento_import"
                motivo = "Reintento tras bug current_user (sin inventar campos)."
                out.reintentado_import += 1
                if dry_run:
                    out.sigue_en_revision += 1
                else:
                    pr.estado = "aprobado"
                    pr.falla_validadores_manual = False
                    _anotar(pr, motivo)
                    db.add(pr)
                    db.commit()
                    db.refresh(pr)
                    final = asegurar_aprobado_no_queda_en_limbo(
                        db, pr, ref, "SANEAMIENTO_REVISION_CURRENT_USER"
                    )
                    if final == "importado":
                        out.importado_auto += 1
                        _historial(
                            db,
                            pr,
                            "en_revision",
                            "importado",
                            motivo,
                            dry_run=False,
                        )
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                        accion = "importado_auto"
                    else:
                        out.sigue_en_revision += 1
                        accion = final or "en_revision"
            else:
                out.sigue_en_revision += 1
                accion = "queda_en_revision"
                motivo = "No recuperable automático (negocio/OCR)."

            if include_detalle:
                out.detalle.append(
                    {
                        "id": int(pr.id),
                        "ref": ref,
                        "accion": accion,
                        "motivo": (motivo or "")[:240],
                    }
                )
        except Exception as e:
            out.errores += 1
            logger.warning(
                "[SANEAMIENTO_REVISION] Error id=%s: %s", pid, e, exc_info=False
            )
            try:
                db.rollback()
            except Exception:
                pass
            if include_detalle:
                out.detalle.append(
                    {
                        "id": int(pid),
                        "ref": None,
                        "accion": "error",
                        "motivo": str(e)[:240],
                    }
                )

    logger.info(
        "[SANEAMIENTO_REVISION] scanned=%s colision=%s reintento=%s import=%s "
        "sigue=%s errores=%s dry_run=%s",
        out.scanned,
        out.marcado_importado_colision,
        out.reintentado_import,
        out.importado_auto,
        out.sigue_en_revision,
        out.errores,
        dry_run,
    )
    return out


@dataclass
class SaneamientoImportadoFantasmaResultado:
    scanned: int = 0
    a_en_revision: int = 0
    sin_cambio: int = 0
    errores: int = 0
    dry_run: bool = True
    last_id: int = 0
    detalle: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scanned": self.scanned,
            "a_en_revision": self.a_en_revision,
            "sin_cambio": self.sin_cambio,
            "errores": self.errores,
            "dry_run": self.dry_run,
            "last_id": self.last_id,
            "detalle": self.detalle[:200],
        }


def _exists_pago_mismo_documento_reportado():
    """Mismo serial exacto o con sufijo admin; no Hamming de vecinos."""
    from app.models.pago import Pago

    op_len_ok = func.length(func.trim(func.coalesce(PagoReportado.numero_operacion, ""))) >= 8
    return exists(
        select(Pago.id).where(
            or_(
                Pago.numero_documento == PagoReportado.numero_operacion,
                Pago.doc_canon_numero == PagoReportado.numero_operacion,
                Pago.doc_canon_referencia == PagoReportado.numero_operacion,
                Pago.referencia_pago == PagoReportado.numero_operacion,
                Pago.numero_documento == PagoReportado.referencia_interna,
                Pago.referencia_pago == PagoReportado.referencia_interna,
                and_(
                    op_len_ok,
                    Pago.numero_documento.like(
                        func.concat(PagoReportado.numero_operacion, "%")
                    ),
                ),
                and_(
                    op_len_ok,
                    Pago.doc_canon_numero.like(
                        func.concat(PagoReportado.numero_operacion, "%")
                    ),
                ),
            )
        )
    )


def _exists_pago_mismo_doc_sin_cuota_pagos():
    from app.models.cuota_pago import CuotaPago
    from app.models.pago import Pago

    op_len_ok = func.length(func.trim(func.coalesce(PagoReportado.numero_operacion, ""))) >= 8
    match_doc = or_(
        Pago.numero_documento == PagoReportado.numero_operacion,
        Pago.doc_canon_numero == PagoReportado.numero_operacion,
        Pago.referencia_pago == PagoReportado.numero_operacion,
        Pago.numero_documento == PagoReportado.referencia_interna,
        Pago.referencia_pago == PagoReportado.referencia_interna,
        and_(
            op_len_ok,
            Pago.numero_documento.like(func.concat(PagoReportado.numero_operacion, "%")),
        ),
    )
    return exists(
        select(Pago.id).where(
            match_doc,
            ~exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id)),
        )
    )


def sanear_importados_sin_cartera_aplicada(
    db: Session,
    *,
    max_ids: int = 150,
    dry_run: bool = False,
    oldest_first: bool = True,
    include_detalle: bool = True,
    after_id: int = 0,
    created_desde: Optional[date] = LIMBO_IMPORTADO_DESDE,
) -> SaneamientoImportadoFantasmaResultado:
    """
    `importado` sin pago aplicado a cuotas → `en_revision`.

    No crea pagos ni inventa OCR/monto/fecha/cédula. No borra reportes ni `pagos`.
    Solo reabre la cola manual. ``after_id`` pagina por id.
    """
    out = SaneamientoImportadoFantasmaResultado(dry_run=dry_run)
    max_ids = max(1, min(int(max_ids or 150), 500))
    after_id = max(0, int(after_id or 0))
    order = PagoReportado.id.asc() if oldest_first else PagoReportado.id.desc()
    conds = [
        PagoReportado.estado == "importado",
    ]
    if created_desde is not None:
        conds.append(
            PagoReportado.created_at
            >= datetime.combine(created_desde, datetime.min.time())
        )
    if oldest_first and after_id > 0:
        conds.append(PagoReportado.id > after_id)
    elif (not oldest_first) and after_id > 0:
        conds.append(PagoReportado.id < after_id)
    ids = list(
        db.execute(
            select(PagoReportado.id).where(*conds).order_by(order).limit(max_ids)
        )
        .scalars()
        .all()
    )
    out.scanned = len(ids)
    if ids:
        out.last_id = int(max(ids) if oldest_first else min(ids))
    motivo = (
        "Importado sin el serial del comprobante aplicado a cuotas; "
        "pasa a revisión manual. No se inventaron datos."
    )
    if not ids:
        logger.info(
            "[SANEAMIENTO_IMPORTADO_FANTASMA] scanned=0 revision=0 sin_cambio=0 "
            "errores=0 dry_run=%s",
            dry_run,
        )
        return out

    from app.models.cuota_pago import CuotaPago
    from app.models.pago import Pago

    rows = list(
        db.execute(
            select(PagoReportado)
            .options(
                load_only(
                    PagoReportado.id,
                    PagoReportado.estado,
                    PagoReportado.numero_operacion,
                    PagoReportado.referencia_interna,
                    PagoReportado.tipo_cedula,
                    PagoReportado.numero_cedula,
                    PagoReportado.gemini_comentario,
                    PagoReportado.falla_validadores_manual,
                )
            )
            .where(PagoReportado.id.in_([int(x) for x in ids]))
        )
        .scalars()
        .all()
    )
    # Solo el serial canónico del banco cierra el limbo (exacto o §CD:/_P/_A).
    # La clave RPC no cuenta: el cliente busca el número del comprobante.
    claves_op: set[str] = set()
    canons_op: set[str] = set()
    for pr in rows:
        op = (getattr(pr, "numero_operacion", None) or "").strip()
        if op:
            claves_op.add(op)
            canon = serial_comprobante_canonico_colision(op)
            if len(canon) >= 8:
                canons_op.add(canon)
    aplicados: set[str] = set()
    aplicados_cedula: set[tuple[str, str]] = set()
    if claves_op or canons_op:
        from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

        claves_list = list(claves_op)
        canon_list = [c for c in canons_op if len(c) >= 8]
        match_parts = []
        if claves_list:
            match_parts.extend(
                [
                    Pago.numero_documento.in_(claves_list),
                    Pago.doc_canon_numero.in_(claves_list),
                ]
            )
        for i in range(0, len(canon_list), 40):
            for c in canon_list[i : i + 40]:
                match_parts.append(Pago.numero_documento.like(f"{c}%"))
                match_parts.append(Pago.doc_canon_numero.like(f"{c}%"))
        if match_parts:
            for row in db.execute(
                select(
                    Pago.numero_documento,
                    Pago.referencia_pago,
                    Pago.doc_canon_numero,
                    Pago.cedula_cliente,
                ).where(
                    or_(*match_parts),
                    or_(
                        exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id)),
                        func.upper(Pago.estado) == "PAGADO",
                    ),
                )
            ):
                nd, rp, cn = row[0], row[1], row[2]
                ced = row[3] if len(row) > 3 else None
                voucher = serial_voucher_en_cartera(nd, rp, cn)
                if not voucher:
                    continue
                nd_s = (str(nd) if nd is not None else "").strip()
                if nd_s in claves_op:
                    aplicados.add(nd_s)
                if voucher in canons_op:
                    aplicados.add(voucher)
                    ced_k = texto_cedula_comparable_bd(ced) if ced is not None else ""
                    if ced_k:
                        aplicados_cedula.add((voucher, ced_k))

    for pr in rows:
        try:
            pid = int(getattr(pr, "id", 0) or 0)
            if (getattr(pr, "estado", None) or "").strip() != "importado":
                out.sin_cambio += 1
                continue
            op = (getattr(pr, "numero_operacion", None) or "").strip()
            canon = serial_comprobante_canonico_colision(op) if op else ""
            want_ced = cedula_clave_reportado(pr)
            # Placeholder OCR / RPC / vacío: siempre revisión. Un pago con
            # numero_documento=REV-MANUAL-… no es el voucher del banco.
            if not reportado_tiene_serial_banco(pr):
                pass
            elif (
                want_ced
                and canon
                and aplicados_cedula
                and (canon, want_ced) in aplicados_cedula
            ):
                out.sin_cambio += 1
                continue
            elif (not aplicados_cedula) and op and (
                op in aplicados or (canon and canon in aplicados)
            ):
                out.sin_cambio += 1
                continue
            # Vacío, solo RPC, Hamming o PENDIENTE sin cuota → revisión. No inventar.
            ref = (pr.referencia_interna or "").strip() or str(pr.id)
            if not dry_run:
                pr.estado = "en_revision"
                pr.falla_validadores_manual = True
                _anotar(pr, motivo)
                db.add(pr)
                _historial(db, pr, "importado", "en_revision", motivo, dry_run=False)
            out.a_en_revision += 1
            if include_detalle:
                out.detalle.append(
                    {
                        "id": int(pr.id),
                        "ref": ref,
                        "accion": "en_revision",
                        "motivo": motivo[:240],
                    }
                )
        except Exception as e:
            out.errores += 1
            logger.warning(
                "[SANEAMIENTO_IMPORTADO_FANTASMA] Error id=%s: %s", pid, e, exc_info=False
            )
            try:
                db.rollback()
            except Exception:
                pass
            if include_detalle:
                out.detalle.append(
                    {
                        "id": int(pid),
                        "ref": None,
                        "accion": "error",
                        "motivo": str(e)[:240],
                    }
                )

    if not dry_run and out.a_en_revision:
        try:
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(
                "[SANEAMIENTO_IMPORTADO_FANTASMA] commit lote falló; revision=%s",
                out.a_en_revision,
            )

    logger.info(
        "[SANEAMIENTO_IMPORTADO_FANTASMA] scanned=%s revision=%s sin_cambio=%s "
        "errores=%s dry_run=%s",
        out.scanned,
        out.a_en_revision,
        out.sin_cambio,
        out.errores,
        dry_run,
    )
    return out
