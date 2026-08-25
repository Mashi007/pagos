"""
Actualización puntual de campos del snapshot `prestamo_candidatos_drive` desde la UI.

Persiste también en la tabla `drive` para que un refresh posterior conserve el cambio.
"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.drive import DriveRow
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.prestamo_candidatos_drive_normalizacion import (
    cell_str,
    normalizar_cedula_cmp_drive,
    normalizar_modalidad_drive,
    parse_decimal_monto_drive,
    parse_fecha_q_iso_y_ambigua,
    parse_numero_cuotas_drive,
)
from app.services.prestamo_candidatos_drive_validadores import (
    cedula_bloqueada_por_desistimiento_drive,
    cedula_cmp_es_tipo_j,
    cedula_cmp_es_tipo_v_o_e,
    cedula_cmp_es_tipo_venezolano_v,
    conteos_cupo_para_una_cedula,
    cupo_ve_permite_nuevo_prestamo,
    enriquecer_payload_conteos_cupo_bd,
)

# Campos editables en UI ↔ columna en tabla `drive`.
_CAMPOS_EDITABLES_A_DRIVE = {
    "col_e_cedula": "col_e",
    "col_i_modelo_vehiculo": "col_i",
    "col_j_analista": "col_j",
    "col_k_concesionario": "col_k",
    "col_n_total_financiamiento": "col_n",
    "col_q_fecha": "col_q",
    "col_r_numero_cuotas": "col_r",
    "col_s_modalidad_pago": "col_s",
}


def _huella_no_comparable_desde_payload(payload: Dict[str, Any], q_date: date | None) -> bool:
    monto_norm = parse_decimal_monto_drive(cell_str(payload.get("col_n_total_financiamiento")))
    cuotas_norm = parse_numero_cuotas_drive(cell_str(payload.get("col_r_numero_cuotas")))
    modalidad_norm = normalizar_modalidad_drive(cell_str(payload.get("col_s_modalidad_pago")))
    return (
        monto_norm is None
        or cuotas_norm is None
        or modalidad_norm is None
        or q_date is None
    )


def _recomputar_derivados_payload(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recalcula validadores/normas del payload tras editar campos de negocio."""
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva
    from app.api.v1.endpoints.validadores import validate_cedula

    pl = dict(payload or {})
    raw_e = cell_str(pl.get("col_e_cedula"))
    cmp_e = normalizar_cedula_cmp_drive(raw_e) or _normalizar_cedula_carga_masiva(raw_e)
    if not cmp_e:
        # Edición parcial (p. ej. solo Q) sin col_e en payload: conservar clave previa.
        cmp_e = cell_str(pl.get("cedula_cmp"))
    if not raw_e and cmp_e:
        raw_e = cmp_e
    vced = validate_cedula(raw_e) if raw_e else {"valido": False, "error": "Cédula vacía"}
    cedula_valida = bool(vced.get("valido"))
    cedula_error = None if cedula_valida else (vced.get("error") or "Cédula inválida")

    q_raw = cell_str(pl.get("col_q_fecha"))
    q_date, q_ambigua = parse_fecha_q_iso_y_ambigua(q_raw)
    monto_norm = parse_decimal_monto_drive(cell_str(pl.get("col_n_total_financiamiento")))
    cuotas_norm = parse_numero_cuotas_drive(cell_str(pl.get("col_r_numero_cuotas")))
    modalidad_norm = normalizar_modalidad_drive(cell_str(pl.get("col_s_modalidad_pago")))

    es_v = cedula_cmp_es_tipo_venezolano_v(cmp_e)
    es_ve = cedula_cmp_es_tipo_v_o_e(cmp_e)
    es_e = bool(es_ve and not es_v)
    es_j = cedula_cmp_es_tipo_j(cmp_e)

    dup_count = 0
    if cmp_e:
        dup_count = int(
            db.scalar(
                select(func.count(PrestamoCandidatoDrive.id)).where(
                    PrestamoCandidatoDrive.cedula_cmp == cmp_e[:32]
                )
            )
            or 0
        )
    dup_sheet = dup_count > 1

    pl["col_e_cedula"] = raw_e or None
    pl["cedula_cmp"] = cmp_e
    pl["cedula_valida"] = cedula_valida
    pl["cedula_error"] = cedula_error
    pl["validador_formato_cedula_ok"] = cedula_valida
    pl["cedula_es_tipo_v_venezolano"] = es_v
    pl["cedula_es_tipo_e"] = es_e
    pl["cedula_es_tipo_ve"] = es_ve
    pl["cedula_es_tipo_j"] = es_j
    pl["duplicada_en_hoja"] = dup_sheet
    pl["validador_sin_duplicado_en_hoja_ok"] = not dup_sheet
    pl["col_n_total_financiamiento_norm"] = (
        str(monto_norm) if monto_norm is not None else None
    )
    pl["col_r_numero_cuotas_norm"] = cuotas_norm
    pl["col_s_modalidad_pago_norm"] = modalidad_norm
    if q_date is not None:
        pl["col_q_fecha"] = q_date.isoformat()
        pl["col_q_fecha_iso"] = q_date.isoformat()
        pl["col_q_fecha_ambigua"] = False
    else:
        pl["col_q_fecha_iso"] = None
        pl["col_q_fecha_ambigua"] = bool(q_ambigua)
    pl["huella_no_comparable"] = _huella_no_comparable_desde_payload(pl, q_date)

    # Solo esta cédula (no escanear toda la tabla prestamos: provocaba timeout 30s en UI).
    cupo = conteos_cupo_para_una_cedula(db, cmp_e)
    pl = enriquecer_payload_conteos_cupo_bd(
        pl,
        cmp_e,
        prestamo_counts_total={cmp_e: cupo["total"]},
        prestamo_counts_aprob={cmp_e: cupo["aprob"]},
        prestamo_counts_liq={cmp_e: cupo["liq"]},
        prestamo_counts_desist={cmp_e: int(cupo.get("desist") or 0)},
    )
    n_aprob = int(pl.get("prestamos_aprobados_misma_cedula_norm_count") or 0)
    n_desist = int(pl.get("prestamos_desistimiento_misma_cedula_norm_count") or 0)
    sin_desist = not cedula_bloqueada_por_desistimiento_drive(n_desist)
    pl["validador_sin_desistimiento_ok"] = sin_desist
    pl["validador_ve_max_un_prestamo_ok"] = (
        cupo_ve_permite_nuevo_prestamo(es_ve=es_ve, es_j=es_j, n_aprob=n_aprob) and sin_desist
    )
    pl["validador_v_max_un_prestamo_ok"] = pl["validador_ve_max_un_prestamo_ok"]
    return pl


def actualizar_fecha_q_candidato_drive(
    db: Session,
    *,
    fila_id: int,
    fecha_q: str,
) -> Dict[str, Any]:
    """
    Actualiza columna Q (fecha de aprobación) en snapshot y tabla `drive`.

    `fecha_q` debe ser YYYY-MM-DD (formato del input type=date en la UI).
    """
    res = actualizar_campos_candidato_drive(
        db,
        fila_id=fila_id,
        campos={"col_q_fecha": fecha_q},
    )
    pl = res.get("payload") or {}
    return {
        "ok": bool(res.get("ok")),
        "id": res.get("id"),
        "sheet_row_number": res.get("sheet_row_number"),
        "col_q_fecha": pl.get("col_q_fecha"),
        "col_q_fecha_iso": pl.get("col_q_fecha_iso"),
        "huella_no_comparable": bool(pl.get("huella_no_comparable")),
        "cedula_cmp": res.get("cedula_cmp"),
        "payload": pl,
        "mensaje": res.get("mensaje") or "",
    }


def actualizar_campos_candidato_drive(
    db: Session,
    *,
    fila_id: int,
    campos: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Actualiza uno o más campos de negocio del candidato (E, I, J, K, N, Q, R, S)
    en snapshot y tabla `drive`, y recalcula validadores derivados.
    """
    row = db.get(PrestamoCandidatoDrive, fila_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado en el snapshot.")

    if not isinstance(campos, dict) or not campos:
        raise HTTPException(status_code=400, detail="Indique al menos un campo a actualizar.")

    desconocidos = [k for k in campos.keys() if k not in _CAMPOS_EDITABLES_A_DRIVE]
    if desconocidos:
        raise HTTPException(
            status_code=400,
            detail=f"Campos no editables: {', '.join(sorted(desconocidos))}.",
        )

    payload = deepcopy(row.payload or {})
    # Conservar cédula de la fila si el payload no trae E (edición de otros campos).
    if not cell_str(payload.get("col_e_cedula")) and not cell_str(payload.get("cedula_cmp")):
        if row.cedula_cmp:
            payload["cedula_cmp"] = str(row.cedula_cmp).strip()
            payload["col_e_cedula"] = payload["cedula_cmp"]
    for key, raw in campos.items():
        val = cell_str(raw)
        payload[key] = val if val else None

    if "col_q_fecha" in campos:
        q_raw = cell_str(payload.get("col_q_fecha"))
        if q_raw and not re.match(r"^\d{4}-\d{2}-\d{2}$", q_raw):
            q_date, q_ambigua = parse_fecha_q_iso_y_ambigua(q_raw)
            if q_ambigua:
                raise HTTPException(
                    status_code=400,
                    detail="Fecha (Q) ambigua; use formato YYYY-MM-DD.",
                )
            if q_date is None:
                raise HTTPException(status_code=400, detail="Fecha (Q) inválida.")
            payload["col_q_fecha"] = q_date.isoformat()

    payload = _recomputar_derivados_payload(db, payload)
    cmp_e = cell_str(payload.get("cedula_cmp"))
    if not cmp_e:
        raise HTTPException(
            status_code=400,
            detail="Cédula (E) no normalizable; revise el valor.",
        )

    row.payload = payload
    row.cedula_cmp = cmp_e[:32]

    drive_row = db.get(DriveRow, int(row.sheet_row_number))
    if drive_row is not None:
        for payload_key, drive_col in _CAMPOS_EDITABLES_A_DRIVE.items():
            if payload_key not in campos:
                continue
            setattr(drive_row, drive_col, cell_str(payload.get(payload_key)) or None)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "id": fila_id,
        "sheet_row_number": int(row.sheet_row_number),
        "cedula_cmp": cmp_e,
        "payload": payload,
        "mensaje": f"Fila {row.sheet_row_number} actualizada en snapshot y drive.",
    }
