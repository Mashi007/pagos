"""Construye payload JSON al registrar MARCAR_OK (prestamo, cliente, control, KPIs de la corrida)."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.services.prestamo_cartera_auditoria import ejecutar_auditoria_cartera, leer_meta_ejecucion


def construir_payload_snapshot_marcar_ok(
    db: Session,
    *,
    prestamo_id: int,
    codigo_control: str,
) -> dict[str, Any]:
    """
    Evalua el motor para el par (prestamo, control) y guarda prestamo, cliente, detalle del control
    y KPIs de esa corrida (mas meta persistida del job si existe).
    """
    meta_persistida = leer_meta_ejecucion(db)
    rows, resumen = ejecutar_auditoria_cartera(
        db,
        solo_con_alerta=True,
        prestamo_id=prestamo_id,
        cedula_contiene=None,
        skip=0,
        limit=None,
        incluir_filas=True,
        excluir_marcar_ok=False,
        codigo_control=codigo_control,
    )
    fila: Optional[dict[str, Any]] = None
    for r in rows:
        if int(r.get("prestamo_id") or 0) == prestamo_id:
            fila = r
            break

    control_snap: Optional[dict[str, Any]] = None
    if fila:
        for c in fila.get("controles") or []:
            if str(c.get("codigo") or "").strip() == codigo_control:
                control_snap = {
                    "codigo": codigo_control,
                    "titulo": c.get("titulo"),
                    "alerta": c.get("alerta"),
                    "detalle": c.get("detalle"),
                }
                break

    prestamo_snap: dict[str, Any]
    cliente_snap: dict[str, Any]
    if fila:
        prestamo_snap = {
            "prestamo_id": int(fila["prestamo_id"]),
            "cliente_id": int(fila["cliente_id"]),
            "cedula": str(fila.get("cedula") or ""),
            "nombres": str(fila.get("nombres") or ""),
            "estado_prestamo": str(fila.get("estado_prestamo") or ""),
        }
        cliente_snap = {"email": str(fila.get("cliente_email") or "")}
    else:
        p = db.get(Prestamo, prestamo_id)
        if not p:
            prestamo_snap = {"prestamo_id": prestamo_id, "error": "prestamo_no_encontrado"}
            cliente_snap = {}
        else:
            cl = db.get(Cliente, int(p.cliente_id)) if p.cliente_id else None
            prestamo_snap = {
                "prestamo_id": int(p.id),
                "cliente_id": int(p.cliente_id),
                "cedula": str(p.cedula or ""),
                "nombres": str(p.nombres or ""),
                "estado_prestamo": str(p.estado or ""),
            }
            cliente_snap = {"email": str(cl.email or "") if cl else ""}
        if control_snap is None:
            control_snap = {
                "codigo": codigo_control,
                "titulo": None,
                "alerta": None,
                "detalle": "Sin fila de alerta en evaluacion puntual (motor NO o prestamo fuera de universo).",
            }

    kpis_corrida = {
        "prestamos_evaluados": resumen.get("prestamos_evaluados"),
        "prestamos_con_alerta": resumen.get("prestamos_con_alerta"),
        "prestamos_listados_total": resumen.get("prestamos_listados_total"),
        "conteos_por_control": resumen.get("conteos_por_control"),
        "reglas_version": resumen.get("reglas_version"),
        "fecha_referencia": resumen.get("fecha_referencia"),
        "excluye_marcar_ok": resumen.get("excluye_marcar_ok"),
        "filtrado_por_codigo_control": resumen.get("filtrado_por_codigo_control"),
        "meta_ultima_corrida_persistida": meta_persistida,
    }

    return {
        "prestamo": prestamo_snap,
        "cliente": cliente_snap,
        "control": control_snap,
        "kpis_corrida": kpis_corrida,
    }


def payload_minimo_revocar_ok(
    *,
    prestamo_id: int,
    codigo_control: str,
) -> dict[str, Any]:
    return {
        "evento": "REVOCAR_OK",
        "prestamo_id": prestamo_id,
        "codigo_control": codigo_control,
    }
