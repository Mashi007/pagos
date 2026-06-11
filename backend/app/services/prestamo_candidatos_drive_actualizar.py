"""
Actualización puntual de campos del snapshot `prestamo_candidatos_drive` desde la UI.

Persiste también en `drive.col_q` para que un refresh posterior conserve el cambio.
"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.drive import DriveRow
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.prestamo_candidatos_drive_normalizacion import (
    cell_str,
    parse_decimal_monto_drive,
    parse_fecha_q_iso_y_ambigua,
    parse_numero_cuotas_drive,
    normalizar_modalidad_drive,
)


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
    row = db.get(PrestamoCandidatoDrive, fila_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado en el snapshot.")

    raw = cell_str(fecha_q)
    if not raw:
        raise HTTPException(status_code=400, detail="Indique una fecha válida (YYYY-MM-DD).")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        raise HTTPException(
            status_code=400,
            detail="Use formato YYYY-MM-DD (sin ambigüedad día/mes).",
        )

    try:
        q_date = date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida.") from exc

    _, q_ambigua = parse_fecha_q_iso_y_ambigua(raw)
    if q_ambigua:
        raise HTTPException(
            status_code=400,
            detail="Fecha ambigua; use formato YYYY-MM-DD.",
        )

    payload = deepcopy(row.payload or {})
    iso = q_date.isoformat()
    payload["col_q_fecha"] = iso
    payload["col_q_fecha_iso"] = iso
    payload["col_q_fecha_ambigua"] = False
    payload["huella_no_comparable"] = _huella_no_comparable_desde_payload(payload, q_date)

    row.payload = payload

    drive_row = db.get(DriveRow, int(row.sheet_row_number))
    if drive_row is not None:
        drive_row.col_q = iso

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "id": fila_id,
        "sheet_row_number": int(row.sheet_row_number),
        "col_q_fecha": iso,
        "col_q_fecha_iso": iso,
        "huella_no_comparable": payload["huella_no_comparable"],
        "mensaje": f"Fecha (Q) actualizada a {iso} en fila {row.sheet_row_number}.",
    }
