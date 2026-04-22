"""
Sincronización masiva ABONOS (hoja CONCILIACIÓN) -> cuotas/pagos en BD.

Objetivo:
- Detectar diferencias por préstamo usando la misma regla de comparar_abonos_drive_vs_cuotas.
- Si procede, aplicar automáticamente la corrección con aplicar_abonos_drive_a_cuotas_prestamo.
- Soportar dry-run para auditoría sin escrituras.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.services.aplicar_abonos_drive_cuotas_service import (
    aplicar_abonos_drive_a_cuotas_prestamo,
)
from app.services.comparar_abonos_drive_cuotas_service import (
    UMBRAL_CONFIRMO_ABONOS_USD,
    comparar_abonos_drive_vs_cuotas,
)

logger = logging.getLogger(__name__)

_EXCL_ESTADOS = ("LIQUIDADO", "DESISTIMIENTO")


def _safe_float(value: Any) -> Optional[float]:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:
        return None
    return n


def sincronizar_abonos_drive_a_cuotas_masivo(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int = 0,
    prestamo_id: Optional[int] = None,
    aplicar_montos_altos: bool = False,
    usuario_registro: str = "AUTO_ABONOS_DRIVE",
) -> Dict[str, Any]:
    """
    Recorre préstamos y aplica diferencias ABONOS > total_pagado_cuotas.

    Reglas:
    - Reusa comparación oficial (misma semántica del modal de Notificaciones).
    - Si requiere lote, no aplica automáticamente (marca omitido para revisión).
    - Montos altos (> UMBRAL_CONFIRMO_ABONOS_USD): por defecto se omiten salvo
      aplicar_montos_altos=True.
    """
    if limit < 0:
        limit = 0

    q = select(Prestamo).order_by(Prestamo.id.asc())
    if prestamo_id and int(prestamo_id) > 0:
        q = q.where(Prestamo.id == int(prestamo_id))
    else:
        q = q.where(~Prestamo.estado.in_(_EXCL_ESTADOS))
    rows = list(db.execute(q).scalars().all())
    if limit > 0:
        rows = rows[:limit]

    out_items: List[Dict[str, Any]] = []
    stats = {
        "total_evaluados": 0,
        "con_diferencia_aplicable": 0,
        "aplicados": 0,
        "omitidos_requiere_lote": 0,
        "omitidos_monto_alto": 0,
        "sin_diferencia_o_no_aplicable": 0,
        "errores": 0,
    }

    for p in rows:
        pid = int(getattr(p, "id", 0) or 0)
        ced = (getattr(p, "cedula", "") or "").strip()
        if pid <= 0 or not ced:
            continue
        stats["total_evaluados"] += 1
        entry: Dict[str, Any] = {
            "prestamo_id": pid,
            "cedula": ced,
            "estado_prestamo": (getattr(p, "estado", "") or "").strip(),
        }
        try:
            cmp = comparar_abonos_drive_vs_cuotas(
                db,
                cedula=ced,
                prestamo_id=pid,
                lote=None,
                persist_cache=False,
            )
            entry["comparacion"] = {
                "abonos_drive": cmp.get("abonos_drive"),
                "total_pagado_cuotas": cmp.get("total_pagado_cuotas"),
                "diferencia": cmp.get("diferencia"),
                "puede_aplicar": bool(cmp.get("puede_aplicar")),
                "requiere_seleccion_lote": bool(cmp.get("requiere_seleccion_lote")),
            }

            if bool(cmp.get("requiere_seleccion_lote")):
                stats["omitidos_requiere_lote"] += 1
                entry["resultado"] = "omitido_requiere_lote"
                out_items.append(entry)
                continue

            if not bool(cmp.get("puede_aplicar")):
                stats["sin_diferencia_o_no_aplicable"] += 1
                entry["resultado"] = "sin_diferencia_o_no_aplicable"
                out_items.append(entry)
                continue

            stats["con_diferencia_aplicable"] += 1
            ab = _safe_float(cmp.get("abonos_drive"))
            if (
                ab is not None
                and ab > float(UMBRAL_CONFIRMO_ABONOS_USD)
                and not aplicar_montos_altos
            ):
                stats["omitidos_monto_alto"] += 1
                entry["resultado"] = "omitido_monto_alto"
                entry["motivo"] = (
                    f"abonos_drive>{UMBRAL_CONFIRMO_ABONOS_USD}; "
                    "usar aplicar_montos_altos=true para incluirlos."
                )
                out_items.append(entry)
                continue

            if dry_run:
                entry["resultado"] = "simulado_aplicable"
                out_items.append(entry)
                continue

            apply_res = aplicar_abonos_drive_a_cuotas_prestamo(
                db,
                cedula=ced,
                prestamo_id=pid,
                usuario_registro=usuario_registro,
                lote=None,
                confirmacion_montos_altos="CONFIRMO" if ab is not None and ab > float(UMBRAL_CONFIRMO_ABONOS_USD) else None,
            )
            db.commit()
            stats["aplicados"] += 1
            entry["resultado"] = "aplicado"
            entry["aplicacion"] = {
                "pago_id": apply_res.get("pago_id"),
                "monto_pago_usd": apply_res.get("monto_pago_usd"),
                "cuotas_completadas": apply_res.get("cuotas_completadas"),
                "cuotas_parciales": apply_res.get("cuotas_parciales"),
                "pagos_eliminados": apply_res.get("pagos_eliminados"),
            }
            out_items.append(entry)
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            stats["errores"] += 1
            entry["resultado"] = "error"
            entry["error"] = str(e)[:400]
            out_items.append(entry)

    return {
        "ok": True,
        "dry_run": bool(dry_run),
        "aplicar_montos_altos": bool(aplicar_montos_altos),
        "umbral_monto_alto_usd": float(UMBRAL_CONFIRMO_ABONOS_USD),
        "limit": int(limit),
        "prestamo_id": int(prestamo_id) if prestamo_id else None,
        "resumen": stats,
        "items": out_items,
    }

