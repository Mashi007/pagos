"""
Refresco del snapshot `prestamo_candidatos_drive` desde la tabla `drive` (post sync CONCILIACIÓN).

Criterio (v1): la cédula en columna E de la hoja, normalizada igual que carga masiva / check-cédulas,
no aparece en ningún `prestamos.cedula` con la misma normalización. No infiere segundo crédito
misma cédula (fila adicional en Drive con titular ya en cartera).

Job: domingo y miércoles 04:05 America/Caracas (tras sync hoja 04:00).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.models.drive import DriveRow
from app.models.prestamo import Prestamo
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive

logger = logging.getLogger(__name__)

# Producto fijo acordado para propuesta desde Drive (submódulo préstamos / CONCILIACIÓN).
PRODUCTO_PROPUESTO_DRIVE = "FINCAMIRETO"


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def ejecutar_refresh_prestamo_candidatos_drive(db: Session) -> Dict[str, Any]:
    """
    Borra el snapshot anterior e inserta las filas candidatas actuales.
    Hace commit al finalizar (o rollback si falla).
    """
    # Import diferido: evita ciclo api.v1 -> este módulo -> clientes -> api.v1
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva
    from app.api.v1.endpoints.validadores import validate_cedula

    meta = db.get(ConciliacionSheetMeta, 1)
    drive_synced_at = meta.synced_at if meta else None

    en_prest: set[str] = set()
    for c in db.execute(select(Prestamo.cedula)).scalars().all() or []:
        n = _normalizar_cedula_carga_masiva(c or "")
        if n:
            en_prest.add(n)

    drive_rows: List[DriveRow] = list(
        db.execute(select(DriveRow).order_by(DriveRow.sheet_row_number.asc())).scalars().all()
        or []
    )

    conteos: Dict[str, int] = {}
    tmp: List[tuple[DriveRow, str]] = []
    for r in drive_rows:
        raw_e = _cell(getattr(r, "col_e", None))
        cmp_e = _normalizar_cedula_carga_masiva(raw_e)
        if not cmp_e:
            continue
        conteos[cmp_e] = conteos.get(cmp_e, 0) + 1
        tmp.append((r, cmp_e))

    now = datetime.now(timezone.utc)
    to_insert: List[PrestamoCandidatoDrive] = []

    for r, cmp_e in tmp:
        if cmp_e in en_prest:
            continue
        raw_e = _cell(getattr(r, "col_e", None))
        dup_sheet = conteos.get(cmp_e, 0) > 1
        vced = validate_cedula(raw_e)
        cedula_valida = bool(vced.get("valido"))
        cedula_error = None if cedula_valida else (vced.get("error") or "Cédula inválida")

        payload: Dict[str, Any] = {
            "col_e_cedula": raw_e or None,
            "col_i_modelo_vehiculo": _cell(getattr(r, "col_i", None)) or None,
            "col_j_analista": _cell(getattr(r, "col_j", None)) or None,
            "col_k_concesionario": _cell(getattr(r, "col_k", None)) or None,
            "col_n_total_financiamiento": _cell(getattr(r, "col_n", None)) or None,
            "col_q_fecha": _cell(getattr(r, "col_q", None)) or None,
            "col_r_numero_cuotas": _cell(getattr(r, "col_r", None)) or None,
            "col_s_modalidad_pago": _cell(getattr(r, "col_s", None)) or None,
            "producto": PRODUCTO_PROPUESTO_DRIVE,
            "cedula_cmp": cmp_e,
            "cedula_valida": cedula_valida,
            "cedula_error": cedula_error,
            "duplicada_en_hoja": dup_sheet,
            "drive_synced_at": drive_synced_at.isoformat() if drive_synced_at else None,
        }

        to_insert.append(
            PrestamoCandidatoDrive(
                sheet_row_number=int(r.sheet_row_number),
                cedula_cmp=cmp_e[:32],
                payload=payload,
                computed_at=now,
            )
        )

    try:
        db.execute(delete(PrestamoCandidatoDrive))
        for row in to_insert:
            db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "[prestamo_candidatos_drive] refresh filas_drive=%s candidatos=%s drive_synced_at=%s",
        len(drive_rows),
        len(to_insert),
        drive_synced_at,
    )
    return {
        "filas_en_drive": len(drive_rows),
        "candidatos_insertados": len(to_insert),
        "drive_synced_at": drive_synced_at.isoformat() if drive_synced_at else None,
        "computed_at": now.isoformat(),
    }


def listar_prestamo_candidatos_drive_snapshot(db: Session) -> Dict[str, Any]:
    """Último snapshot (tabla completa ordenada por fila de hoja)."""
    meta = db.get(ConciliacionSheetMeta, 1)
    drive_synced_at = meta.synced_at.isoformat() if meta and meta.synced_at else None

    rows = list(
        db.execute(
            select(PrestamoCandidatoDrive).order_by(
                PrestamoCandidatoDrive.sheet_row_number.asc()
            )
        )
        .scalars()
        .all()
        or []
    )
    computed_at = None
    if rows:
        computed_at = max(r.computed_at for r in rows if r.computed_at)
        computed_at = computed_at.isoformat() if computed_at else None

    return {
        "drive_synced_at": drive_synced_at,
        "computed_at": computed_at,
        "total": len(rows),
        "filas": [
            {
                "id": r.id,
                "sheet_row_number": r.sheet_row_number,
                "cedula_cmp": r.cedula_cmp,
                "payload": r.payload,
                "computed_at": r.computed_at.isoformat() if r.computed_at else None,
            }
            for r in rows
        ],
    }
