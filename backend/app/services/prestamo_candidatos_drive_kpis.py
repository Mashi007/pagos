"""
KPIs de candidatos Drive alineados al guardado masivo (`_motivos_no_100`).

Cuenta cuántas filas el botón «Guardar (100%)» intentaría crear (misma validación de servidor que al persistir),
no solo el color verde de la grilla (la grilla puede verse verde y aún faltar cliente, N, R, S, J, etc.).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.prestamo_candidatos_drive_guardar import (
    MAX_DIAS_APROBACION_DRIVE,
    _fechas_desde_col_q,
    _motivos_no_100,
)
from app.services.prestamo_candidatos_drive_validadores import (
    conteo_prestamos_aprobados_por_cedula_norm,
)


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _cedula_es_ve(payload: Dict[str, Any], cedula_cmp_fila: str) -> bool:
    if payload.get("cedula_es_tipo_ve") is True:
        return True
    u = _cell(payload.get("cedula_cmp") or cedula_cmp_fila).upper()
    if u and u[0] in ("V", "E"):
        return True
    return payload.get("cedula_es_tipo_v_venezolano") is True or payload.get("cedula_es_tipo_e") is True


def _cedula_es_j(payload: Dict[str, Any], cedula_cmp_fila: str) -> bool:
    if payload.get("cedula_es_tipo_j") is True:
        return True
    u = _cell(payload.get("cedula_cmp") or cedula_cmp_fila).upper()
    return bool(u and u[0] == "J")


def _formato_ok(payload: Dict[str, Any]) -> bool:
    a = payload.get("validador_formato_cedula_ok")
    if a is not None:
        return a is True
    return payload.get("cedula_valida") is True


def _hoja_ok(payload: Dict[str, Any]) -> bool:
    v = payload.get("validador_sin_duplicado_en_hoja_ok")
    if v is not None:
        return v is True
    return payload.get("duplicada_en_hoja") is not True


def _tabla_ve_ok(payload: Dict[str, Any], cedula_cmp_fila: str, n_prest: int, es_ve: bool, es_j: bool) -> bool:
    if es_j:
        return True
    for k in ("validador_ve_max_un_prestamo_ok", "validador_v_max_un_prestamo_ok"):
        t = payload.get(k)
        if t is True:
            return True
        if t is False:
            return False
    try:
        n_aprob = int(payload.get("prestamos_aprobados_misma_cedula_norm_count") or 0)
    except (TypeError, ValueError):
        n_aprob = n_prest
    return not (es_ve and n_aprob >= 1)


def fila_payload_grilla_verde(payload: Dict[str, Any], cedula_cmp_fila: str) -> bool:
    """True si la fila se mostraría en verde (listas para guardar según validadores de pantalla)."""
    formato_ok = _formato_ok(payload)
    hoja_ok = _hoja_ok(payload)
    try:
        n_prest = int(payload.get("prestamos_misma_cedula_norm_count") or 0)
    except (TypeError, ValueError):
        n_prest = 0
    es_ve = _cedula_es_ve(payload, cedula_cmp_fila)
    es_j = _cedula_es_j(payload, cedula_cmp_fila)
    tabla_ok = _tabla_ve_ok(payload, cedula_cmp_fila, n_prest, es_ve, es_j)

    q_raw = _cell(payload.get("col_q_fecha"))
    red_fecha = False
    fechas = _fechas_desde_col_q(q_raw)
    if fechas:
        _, ap_d = fechas
        red_fecha = (date.today() - ap_d).days > MAX_DIAS_APROBACION_DRIVE

    try:
        n_aprob = int(payload.get("prestamos_aprobados_misma_cedula_norm_count") or 0)
    except (TypeError, ValueError):
        n_aprob = n_prest
    red_ve = es_ve and n_aprob >= 1
    if not formato_ok or red_ve or red_fecha:
        return False
    dup = payload.get("duplicada_en_hoja") is True
    if formato_ok and dup:
        return False
    return bool(formato_ok and tabla_ok and hoja_ok)


def conteos_listo_guardar_y_map_por_id(
    db: Session,
    *,
    cedula_cmp_contains: str | None,
) -> Tuple[int, int, Dict[int, bool], Dict[int, List[str]]]:
    """
    Una sola pasada sobre el snapshot filtrado:
    - cuenta guardables / no guardables (`_motivos_no_100`, igual que «Guardar (100%)»);
    - devuelve mapa `id` → cumple validación previa al crear préstamo (para la UI por fila);
    - devuelve mapa `id` → motivos de no-guardable (lista vacía si guardable), para mostrar en UI.
    """
    prestamo_counts_aprob = conteo_prestamos_aprobados_por_cedula_norm(db)
    stmt = select(PrestamoCandidatoDrive.id, PrestamoCandidatoDrive.payload, PrestamoCandidatoDrive.cedula_cmp)
    q = (cedula_cmp_contains or "").strip()
    if q:
        stmt = stmt.where(PrestamoCandidatoDrive.cedula_cmp.contains(q))
    rows = list(db.execute(stmt).all() or [])
    listo_map: Dict[int, bool] = {}
    motivos_map: Dict[int, List[str]] = {}
    apr = 0
    for rid, payload, cmp in rows:
        pl = payload if isinstance(payload, dict) else {}
        ok, motivos, pc = _motivos_no_100(pl, db, prestamo_counts_aprob)
        v = bool(ok and pc is not None)
        listo_map[int(rid)] = v
        motivos_map[int(rid)] = [] if v else list(motivos)
        if v:
            apr += 1
    total = len(rows)
    return apr, total - apr, listo_map, motivos_map
