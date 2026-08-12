"""
Saneamiento de `pagos_reportados` en estado `aprobado` sin cierre (limbo).

Reglas (no inventa campos OCR ni montos/fechas/cédulas):
1. Si el comprobante ya existe en `pagos` → `importado`.
2. Si faltan datos cargables, monto >= umbral, o el auto-import falla → `en_revision`.
3. Si los datos del recibo son reales y el import existente puede materializar →
   reutiliza `intentar_importar_reportado_automatico` (misma naturaleza del recibo).

Uso: job scheduler, endpoint admin o script CLI.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.services.cobros.cobros_publico_reporte_service import (
    intentar_importar_reportado_automatico,
    reportado_datos_cargables_a_cartera,
)
from app.services.cobros.pago_reportado_documento import pago_reportado_colisiona_tabla_pagos
from app.services.pagos_gmail.parse_campos_comprobante import (
    mensaje_excepcion_autoconciliacion,
    reportado_exento_autoconciliacion,
)

logger = logging.getLogger(__name__)

MOTIVO_SISTEMA = "sistema@saneamiento-limbo"
NOTA_PREFIX = "[SANEAMIENTO_LIMBO]"


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
        return
    pr.gemini_comentario = (f"{prev} {full}".strip() if prev else full)[:500]


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

            if pago_reportado_colisiona_tabla_pagos(db, pr):
                accion = "importado_colision"
                motivo = "Comprobante ya en cartera; cierra en_revision → importado."
                if not dry_run:
                    pr.estado = "importado"
                    pr.falla_validadores_manual = False
                    _anotar(pr, motivo)
                    db.add(pr)
                    _historial(db, pr, "en_revision", "importado", motivo, dry_run=False)
                    db.commit()
                out.marcado_importado_colision += 1
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
