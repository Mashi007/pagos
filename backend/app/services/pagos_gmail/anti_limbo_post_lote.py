# -*- coding: utf-8 -*-
"""
Cierre anti-limbo tras un lote Pagos Gmail / Auditoría Email.

Objetivo: que lo re-escaneado no quede colgado en `gmail_temporal` ni como `pago`
sin `cuota_pagos`, y que lo elegible según validadores vigentes termine aplicado
al préstamo (cascada). Lo que exige revisión manual sigue yendo a `pagos_con_errores`.

Alcance: cuando hay ``sync_id``, migración y cascada se acotan a ese lote (no mezclan colas).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import and_, delete, exists, or_, select
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza
from app.models.pagos_gmail_sync import GmailTemporal, PagosGmailSyncItem

logger = logging.getLogger(__name__)

_BANCO_A_FMT = {
    "MERCANTIL": "A",
    "BNC": "B",
    "BINANCE": "C",
    "BNV": "D",
    "BDV": "D",
    "RECIBO": "NR",
}
# E/F se digitalizan pero NO tienen alta automática vigente → van a revisión.
_BANCO_SOLO_REVISION = frozenset({"BANCAMIGA", "TESORO", "BANCO DEL TESORO"})


def _fmt_desde_banco(banco: Optional[str]) -> Optional[str]:
    b = (banco or "").strip().upper()
    if not b:
        return None
    if b in _BANCO_SOLO_REVISION or "BANCAMIGA" in b or "TESORO" in b:
        return None  # no reintentar alta A–D; migración a errores
    if b in _BANCO_A_FMT:
        return _BANCO_A_FMT[b]
    if b in ("A", "B", "C", "D", "NR"):
        return b
    return None


def _message_ids_del_sync(db: Session, sync_id: int) -> List[str]:
    rows = (
        db.execute(
            select(PagosGmailSyncItem.gmail_message_id)
            .where(
                PagosGmailSyncItem.sync_id == sync_id,
                PagosGmailSyncItem.gmail_message_id.isnot(None),
            )
            .distinct()
        )
        .scalars()
        .all()
    )
    return [str(m).strip() for m in rows if m and str(m).strip()]


def _ids_temporal_ya_cuotas_ok(
    db: Session, *, limit: int = 5000, gmail_message_ids: Optional[List[str]] = None
) -> List[int]:
    """Temporales residuales con traza CUOTAS_OK + pago_id (ya en cartera)."""
    q = (
        select(GmailTemporal.id)
        .join(
            PagosGmailSyncItem,
            and_(
                PagosGmailSyncItem.gmail_message_id == GmailTemporal.gmail_message_id,
                PagosGmailSyncItem.numero_referencia == GmailTemporal.numero_referencia,
                PagosGmailSyncItem.cedula == GmailTemporal.cedula,
            ),
        )
        .join(
            PagosGmailAbcdCuotasTraza,
            PagosGmailAbcdCuotasTraza.sync_item_id == PagosGmailSyncItem.id,
        )
        .where(
            GmailTemporal.gmail_message_id.isnot(None),
            GmailTemporal.numero_referencia.isnot(None),
            GmailTemporal.cedula.isnot(None),
            PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
            PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
        )
        .limit(limit)
    )
    if gmail_message_ids:
        q = q.where(GmailTemporal.gmail_message_id.in_(list(gmail_message_ids)))
    rows = db.execute(q).scalars().all()
    return list(dict.fromkeys(int(x) for x in rows if x is not None))


def _limpiar_temporal_cuotas_ok(
    db: Session, *, gmail_message_ids: Optional[List[str]] = None
) -> int:
    ids = _ids_temporal_ya_cuotas_ok(db, gmail_message_ids=gmail_message_ids)
    if not ids:
        return 0
    db.execute(delete(GmailTemporal).where(GmailTemporal.id.in_(ids)))
    db.commit()
    logger.info("[PAGOS_GMAIL] [ANTI_LIMBO] temporales CUOTAS_OK eliminados=%d", len(ids))
    return len(ids)


def _reintentar_alta_auto_temporal(
    db: Session, *, sync_id: Optional[int] = None, limit: int = 500
) -> Dict[str, int]:
    """
    Reintenta alta automática A/B/C/D/NR para filas aún en gmail_temporal
    (mismas reglas/validadores que el pipeline; no fuerza revisión manual).
    """
    from app.services.pagos_gmail.pago_abcd_auto_service import (
        crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd,
        _fecha_pago_date_desde_gmail,
    )
    from app.services.pagos_gmail.pago_nr_auto_service import (
        crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr,
    )
    from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
        monto_gmail_sync_requiere_revision_manual_usd,
    )
    from app.services.pagos_gmail.parse_campos_comprobante import (
        fecha_pago_es_futura_revision_manual,
    )
    from app.services.pagos_gmail.helpers import normalizar_fecha_pago

    ERROR_CEDULA_EMAIL = "ERROR EMAIL"
    stmt = select(GmailTemporal).order_by(GmailTemporal.id.asc()).limit(limit)
    if sync_id is not None:
        msg_ids = _message_ids_del_sync(db, sync_id)
        if msg_ids:
            stmt = (
                select(GmailTemporal)
                .where(GmailTemporal.gmail_message_id.in_(msg_ids))
                .order_by(GmailTemporal.id.asc())
                .limit(limit)
            )
        else:
            return {
                "reintento_ok": 0,
                "reintento_skip": 0,
                "reintento_fail": 0,
                "prestamos_tocados": 0,
            }

    rows = list(db.execute(stmt).scalars().all())
    ok = 0
    skip = 0
    fail = 0
    prestamo_ids: Set[int] = set()

    for row in rows:
        fmt = _fmt_desde_banco(row.banco)
        if not fmt:
            skip += 1
            continue
        cedula = (row.cedula or "").strip()
        if not cedula or cedula.upper() == ERROR_CEDULA_EMAIL:
            skip += 1
            continue
        if monto_gmail_sync_requiere_revision_manual_usd(row.monto):
            skip += 1
            continue
        fp_raw = (row.fecha_pago or "").strip()
        fp_norm = normalizar_fecha_pago(fp_raw) if fp_raw else ""
        if not fp_norm and not fp_raw:
            skip += 1
            continue
        try:
            fp_date = _fecha_pago_date_desde_gmail(fp_raw or fp_norm)
            if fp_date is None:
                skip += 1
                continue
            if fecha_pago_es_futura_revision_manual(fp_date):
                skip += 1
                continue
        except Exception:
            skip += 1
            continue

        si = None
        if row.gmail_message_id and row.numero_referencia:
            si = (
                db.execute(
                    select(PagosGmailSyncItem)
                    .where(
                        PagosGmailSyncItem.gmail_message_id == row.gmail_message_id,
                        PagosGmailSyncItem.numero_referencia == row.numero_referencia,
                    )
                    .order_by(PagosGmailSyncItem.id.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )

        link = row.drive_link or None
        try:
            if fmt == "NR":
                res = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr(
                    db,
                    cedula_columna=cedula,
                    fecha_pago_str=fp_raw or fp_norm,
                    monto_operacion_str=row.monto or "",
                    numero_referencia=row.numero_referencia or "",
                    institucion_bancaria=row.banco,
                    link_comprobante=link,
                    filename=None,
                    sync_id=getattr(si, "sync_id", None) or sync_id,
                    sync_item_id=getattr(si, "id", None),
                    comprobante_imagen_id=None,
                )
            else:
                res = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
                    db,
                    cedula_columna=cedula,
                    fecha_pago_str=fp_raw or fp_norm,
                    monto_str=row.monto or "",
                    numero_referencia=row.numero_referencia or "",
                    institucion_bancaria=row.banco,
                    link_comprobante=link,
                    fmt=fmt,
                    filename=None,
                    sync_id=getattr(si, "sync_id", None) or sync_id,
                    sync_item_id=getattr(si, "id", None),
                    comprobante_imagen_id=None,
                )
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] [ANTI_LIMBO] reintento temporal id=%s: %s", row.id, e
            )
            fail += 1
            continue

        if res.get("ok") and str(res.get("etapa_final") or "") == "CUOTAS_OK":
            ok += 1
            pid = res.get("prestamo_id")
            if pid:
                prestamo_ids.add(int(pid))
            try:
                db.execute(delete(GmailTemporal).where(GmailTemporal.id == int(row.id)))
                db.commit()
            except Exception:
                db.rollback()
        else:
            fail += 1
            motivo = res.get("motivo") or "no_ok"
            if motivo in (
                "monto_umbral_revision_manual",
                "fecha_futura",
                "fecha_invalida",
                "cedula_vacia",
                "sin_prestamo_aprobado_unico",
                "usuario_operaciones",
            ):
                skip += 1
                fail -= 1

    return {
        "reintento_ok": ok,
        "reintento_skip": skip,
        "reintento_fail": fail,
        "prestamos_tocados": len(prestamo_ids),
    }


def _pago_ids_huerfanos_para_sync(db: Session, sync_id: int, *, limit: int = 300) -> List[int]:
    """
    Pagos sin cuota_pagos ligados al sync:
    - por traza.pago_id
    - por numero_documento / referencia = sync_item.numero_referencia
    """
    tiene_app = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))
    ids: Set[int] = set()

    for pid in (
        db.execute(
            select(PagosGmailAbcdCuotasTraza.pago_id).where(
                PagosGmailAbcdCuotasTraza.sync_id == sync_id,
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
            )
        )
        .scalars()
        .all()
    ):
        if pid:
            ids.add(int(pid))

    refs = [
        str(r).strip()
        for r in (
            db.execute(
                select(PagosGmailSyncItem.numero_referencia).where(
                    PagosGmailSyncItem.sync_id == sync_id,
                    PagosGmailSyncItem.numero_referencia.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        if r and str(r).strip()
    ]
    if refs:
        # Match documento o referencia_pago
        found = (
            db.execute(
                select(Pago.id).where(
                    ~tiene_app,
                    Pago.prestamo_id.isnot(None),
                    or_(
                        Pago.numero_documento.in_(refs),
                        Pago.referencia_pago.in_(refs),
                        Pago.doc_canon_numero.in_(refs),
                    ),
                ).limit(limit)
            )
            .scalars()
            .all()
        )
        for pid in found:
            ids.add(int(pid))

    if not ids:
        return []
    # Filtrar los que aún no tienen aplicación
    huerfanos = (
        db.execute(
            select(Pago.id).where(
                Pago.id.in_(list(ids)),
                ~tiene_app,
                Pago.prestamo_id.isnot(None),
            ).limit(limit)
        )
        .scalars()
        .all()
    )
    return [int(x) for x in huerfanos]


def _aplicar_cascada_pagos_sin_cuotas(
    db: Session, *, sync_id: Optional[int] = None, limit: int = 200
) -> Dict[str, int]:
    """Pagos ya creados sin filas en cuota_pagos → cascada vigente."""
    from app.api.v1.endpoints import pagos as pagos_ep
    from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas

    tiene_app = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))
    if sync_id is not None:
        pago_ids = _pago_ids_huerfanos_para_sync(db, sync_id, limit=limit)
        if not pago_ids:
            return {"cascada_ok": 0, "cascada_fail": 0, "cascada_skip": 0}
        stmt = select(Pago).where(Pago.id.in_(pago_ids)).order_by(Pago.id.asc())
    else:
        stmt = (
            select(Pago)
            .where(
                ~tiene_app,
                Pago.prestamo_id.isnot(None),
                Pago.usuario_registro.ilike("%gmail%"),
            )
            .order_by(Pago.id.asc())
            .limit(limit)
        )

    pagos = list(db.execute(stmt).scalars().all())
    ok = 0
    fail = 0
    skip = 0
    prestamos_done: Set[int] = set()

    for pago in pagos:
        if pago_tiene_aplicaciones_cuotas(db, int(pago.id)):
            skip += 1
            continue
        prestamo_id = int(pago.prestamo_id) if pago.prestamo_id else None
        if not prestamo_id:
            skip += 1
            continue
        if prestamo_id in prestamos_done:
            skip += 1
            continue
        try:
            from app.services.pagos_aplicacion_prestamo import (
                aplicar_cascada_prestamo_pipeline,
            )

            pipeline = aplicar_cascada_prestamo_pipeline(
                prestamo_id,
                db,
                reconstruir_completa=True,
                user=None,
            )
            if pipeline.get("ok"):
                db.commit()
                prestamos_done.add(prestamo_id)
                ok += 1
            else:
                db.rollback()
                cc, cp = pagos_ep._aplicar_pago_a_cuotas_interno(pago, db)
                pagos_ep._estado_conciliacion_post_cascada(pago, cc, cp)
                if cc > 0 or cp > 0:
                    db.commit()
                    ok += 1
                else:
                    db.rollback()
                    fail += 1
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] [ANTI_LIMBO] cascada pago_id=%s prestamo=%s: %s",
                pago.id,
                prestamo_id,
                e,
            )
            try:
                db.rollback()
            except Exception:
                pass
            fail += 1

    return {"cascada_ok": ok, "cascada_fail": fail, "cascada_skip": skip}


def message_ids_listos_para_analizados(
    db: Session,
    *,
    sync_id: Optional[int],
    candidate_message_ids: List[str],
) -> Dict[str, Any]:
    """
    No etiqueta ANALIZADOS si el mensaje sigue en gmail_temporal (limbo abierto).
    Así un fallo a medias no oculta el correo del re-escaneo.
    """
    cands = [str(x).strip() for x in candidate_message_ids if str(x).strip()]
    if not cands:
        return {"listos": [], "pendientes_temporal": [], "omitidos": []}

    still = set(
        str(x).strip()
        for x in (
            db.execute(
                select(GmailTemporal.gmail_message_id).where(
                    GmailTemporal.gmail_message_id.in_(cands)
                )
            )
            .scalars()
            .all()
        )
        if x
    )
    listos = [m for m in cands if m not in still]
    return {
        "listos": listos,
        "pendientes_temporal": sorted(still),
        "omitidos": sorted(still),
        "sync_id": sync_id,
    }


def cerrar_lote_anti_limbo(
    db: Session,
    *,
    sync_id: Optional[int] = None,
    migrar_restantes_a_errores: bool = True,
    candidate_message_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Secuencia post-lote:
    1) reconciliar trazas CUOTAS_OK sin pago_id
    2) borrar temporales ya aplicados a cuotas (acotado al sync si hay ids)
    3) reintentar alta auto elegible
    4) cascada a préstamos (traza + numero_documento)
    5) migrar resto de temporal del sync → pagos_con_errores
    6) devolver message_ids listos para ANALIZADOS
    """
    out: Dict[str, Any] = {"sync_id": sync_id}
    scope_ids: Optional[List[str]] = None
    if sync_id is not None:
        scope_ids = _message_ids_del_sync(db, sync_id)
        if candidate_message_ids:
            # Unión: items del sync + candidatos del lote (texto sin sync_item)
            scope_ids = list(
                dict.fromkeys(
                    list(scope_ids)
                    + [str(x).strip() for x in candidate_message_ids if str(x).strip()]
                )
            )
    elif candidate_message_ids:
        scope_ids = [str(x).strip() for x in candidate_message_ids if str(x).strip()]

    try:
        from app.services.pagos_gmail.gmail_abcd_cuotas_traza import (
            reconciliar_cuotas_ok_sin_pago_id,
        )

        out["reconciliar"] = reconciliar_cuotas_ok_sin_pago_id(db, max_ids=500)
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ANTI_LIMBO] reconciliar: %s", e)
        out["reconciliar"] = {"error": str(e)[:200]}

    try:
        out["temporales_cuotas_ok_eliminados"] = _limpiar_temporal_cuotas_ok(
            db, gmail_message_ids=scope_ids
        )
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ANTI_LIMBO] limpiar temporal: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        out["temporales_cuotas_ok_eliminados"] = 0
        out["limpiar_error"] = str(e)[:200]

    try:
        out["reintento_alta"] = _reintentar_alta_auto_temporal(
            db, sync_id=sync_id, limit=500
        )
        out["temporales_cuotas_ok_eliminados"] = int(
            out.get("temporales_cuotas_ok_eliminados") or 0
        ) + _limpiar_temporal_cuotas_ok(db, gmail_message_ids=scope_ids)
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ANTI_LIMBO] reintento alta: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        out["reintento_alta"] = {"error": str(e)[:200]}

    try:
        out["cascada"] = _aplicar_cascada_pagos_sin_cuotas(db, sync_id=sync_id, limit=200)
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ANTI_LIMBO] cascada: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        out["cascada"] = {"error": str(e)[:200]}

    if migrar_restantes_a_errores:
        try:
            from app.api.v1.endpoints.pagos_gmail.routes import (
                _migrar_pendientes_gmail_a_con_errores_core,
            )

            # Acotar al lote/sync para no mezclar colas de otra corrida.
            out["migracion_errores"] = _migrar_pendientes_gmail_a_con_errores_core(
                db, gmail_message_ids=scope_ids
            )
        except Exception as e:
            logger.warning("[PAGOS_GMAIL] [ANTI_LIMBO] migracion errores: %s", e)
            out["migracion_errores"] = {"error": str(e)[:200]}

    cands = candidate_message_ids or scope_ids or []
    out["analizados"] = message_ids_listos_para_analizados(
        db, sync_id=sync_id, candidate_message_ids=cands
    )

    logger.info("[PAGOS_GMAIL] [ANTI_LIMBO] cierre lote sync_id=%s → %s", sync_id, {
        "reintento_ok": (out.get("reintento_alta") or {}).get("reintento_ok"),
        "cascada_ok": (out.get("cascada") or {}).get("cascada_ok"),
        "migrados": (out.get("migracion_errores") or {}).get("migrados"),
        "analizados": len((out.get("analizados") or {}).get("listos") or []),
        "pendientes_temporal": len(
            (out.get("analizados") or {}).get("pendientes_temporal") or []
        ),
    })
    return out
