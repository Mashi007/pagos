"""
Refresco del snapshot `prestamo_candidatos_drive` desde la tabla `drive` (post sync CONCILIACIÓN).

Criterio de filas en snapshot (columna E, misma normalización que carga masiva / check-cédulas):
- **V** o **E**: no debe haber ya un préstamo con esa cédula (máximo un préstamo en cartera).
- **J** (jurídico): puede haber ya uno o más préstamos; el candidato puede seguir figurando (dos o más créditos permitidos).
- Otras letras: sin préstamo previo con esa cédula normalizada (mismo criterio que antes para no J).

Validadores en cada payload:
1) formato (`validate_cedula` / `cedula_valida`);
2) cédula tipo **V** o **E**: a lo sumo un préstamo en tabla `prestamos` con esa cédula normalizada;
   dos o más no cumplen (`validador_ve_max_un_prestamo_ok`; en candidatos V/E sin préstamo previo queda en true);
3) no duplicada en hoja (`duplicada_en_hoja` / `validador_sin_duplicado_en_hoja_ok`).

Job: domingo y miércoles 04:05 America/Caracas (tras sync hoja 04:00).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.models.drive import DriveRow
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.prestamo_candidatos_drive_kpis import conteos_aprueban_no_aprueban_snapshot
from app.services.prestamo_candidatos_drive_validadores import (
    cedula_cmp_es_tipo_j,
    cedula_cmp_es_tipo_v_o_e,
    cedula_cmp_es_tipo_venezolano_v,
    conteo_prestamos_por_cedula_norm,
)

logger = logging.getLogger(__name__)

# Producto fijo acordado para propuesta desde Drive (submódulo préstamos / CONCILIACIÓN).
PRODUCTO_PROPUESTO_DRIVE = "FINANCIAMIENTO"


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def ejecutar_refresh_prestamo_candidatos_drive(
    db: Session,
    *,
    forzar: bool = False,
) -> Dict[str, Any]:
    """
    Borra el snapshot anterior e inserta las filas candidatas actuales.
    Hace commit al finalizar (o rollback si falla).

    Si la tabla `drive` está vacía: por defecto no modifica el snapshot (omitido=True).
    Con forzar=True (solo uso manual vía API): vacía el snapshot y deja 0 filas.
    """
    # Import diferido: evita ciclo api.v1 -> este módulo -> clientes -> api.v1
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva
    from app.api.v1.endpoints.validadores import validate_cedula

    meta = db.get(ConciliacionSheetMeta, 1)
    drive_synced_at = meta.synced_at if meta else None

    prestamo_counts = conteo_prestamos_por_cedula_norm(db)

    drive_rows: List[DriveRow] = list(
        db.execute(select(DriveRow).order_by(DriveRow.sheet_row_number.asc())).scalars().all()
        or []
    )

    if not drive_rows:
        if not forzar:
            logger.warning(
                "[prestamo_candidatos_drive] refresh omitido: tabla drive sin filas "
                "(se conserva el snapshot anterior si existía)."
            )
            return {
                "filas_en_drive": 0,
                "candidatos_insertados": 0,
                "drive_synced_at": drive_synced_at.isoformat() if drive_synced_at else None,
                "computed_at": None,
                "omitido": True,
                "motivo": "tabla_drive_sin_filas",
            }
        now_clear = datetime.now(timezone.utc)
        try:
            db.execute(delete(PrestamoCandidatoDrive))
            db.commit()
        except Exception:
            db.rollback()
            raise
        logger.warning(
            "[prestamo_candidatos_drive] refresh forzado: drive vacío; snapshot limpiado."
        )
        return {
            "filas_en_drive": 0,
            "candidatos_insertados": 0,
            "drive_synced_at": drive_synced_at.isoformat() if drive_synced_at else None,
            "computed_at": now_clear.isoformat(),
            "omitido": False,
            "motivo": "forzar_con_drive_vacio",
        }

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
        n_prest = int(prestamo_counts.get(cmp_e, 0) or 0)
        es_v = cedula_cmp_es_tipo_venezolano_v(cmp_e)
        es_ve = cedula_cmp_es_tipo_v_o_e(cmp_e)
        es_e = bool(es_ve and not es_v)
        es_j = cedula_cmp_es_tipo_j(cmp_e)
        if es_ve and n_prest >= 1:
            continue
        if not es_ve and not es_j and n_prest >= 1:
            continue
        raw_e = _cell(getattr(r, "col_e", None))
        dup_sheet = conteos.get(cmp_e, 0) > 1
        vced = validate_cedula(raw_e)
        cedula_valida = bool(vced.get("valido"))
        cedula_error = None if cedula_valida else (vced.get("error") or "Cédula inválida")
        # V y E: máximo un préstamo; dos o más con la misma cédula normalizada no cumplen.
        validador_ve_max_un_prestamo_ok = not (es_ve and n_prest >= 2)
        validador_v_max_un_prestamo_ok = validador_ve_max_un_prestamo_ok

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
            "prestamos_misma_cedula_norm_count": n_prest,
            "cedula_es_tipo_v_venezolano": es_v,
            "cedula_es_tipo_e": es_e,
            "cedula_es_tipo_ve": es_ve,
            "cedula_es_tipo_j": es_j,
            "validador_formato_cedula_ok": cedula_valida,
            "validador_ve_max_un_prestamo_ok": validador_ve_max_un_prestamo_ok,
            "validador_v_max_un_prestamo_ok": validador_v_max_un_prestamo_ok,
            "validador_sin_duplicado_en_hoja_ok": not dup_sheet,
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
        if to_insert:
            db.add_all(to_insert)
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
        "omitido": False,
        "motivo": None,
    }


def listar_prestamo_candidatos_drive_snapshot(
    db: Session,
    *,
    limit: int = 500,
    offset: int = 0,
    cedula_q: str | None = None,
) -> Dict[str, Any]:
    """Último snapshot ordenado por fila de hoja; paginado y filtro opcional por cédula (normalizada)."""
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva

    meta = db.get(ConciliacionSheetMeta, 1)
    drive_synced_at = meta.synced_at.isoformat() if meta and meta.synced_at else None

    filt_norm = ""
    if cedula_q is not None and str(cedula_q).strip():
        filt_norm = _normalizar_cedula_carga_masiva(str(cedula_q).strip())

    base_filter = []
    if filt_norm:
        base_filter.append(PrestamoCandidatoDrive.cedula_cmp.contains(filt_norm))

    cnt_stmt = select(func.count(PrestamoCandidatoDrive.id))
    if base_filter:
        cnt_stmt = cnt_stmt.where(*base_filter)
    total = int(db.scalar(cnt_stmt) or 0)

    lim = max(1, min(int(limit), 2000))
    off = max(0, int(offset))

    stmt = select(PrestamoCandidatoDrive).order_by(PrestamoCandidatoDrive.sheet_row_number.asc())
    if base_filter:
        stmt = stmt.where(*base_filter)
    stmt = stmt.offset(off).limit(lim)

    rows = list(db.execute(stmt).scalars().all() or [])
    aprueban, no_aprueban = conteos_aprueban_no_aprueban_snapshot(
        db, cedula_cmp_contains=filt_norm or None
    )
    computed_at = None
    if total > 0:
        max_stmt = select(func.max(PrestamoCandidatoDrive.computed_at))
        if base_filter:
            max_stmt = max_stmt.where(*base_filter)
        last_ts = db.scalar(max_stmt)
        computed_at = last_ts.isoformat() if last_ts else None

    return {
        "drive_synced_at": drive_synced_at,
        "computed_at": computed_at,
        "kpis_aprueban": aprueban,
        "kpis_no_aprueban": no_aprueban,
        "total": total,
        "total_sin_filtro": (
            int(db.scalar(select(func.count(PrestamoCandidatoDrive.id))) or 0)
            if filt_norm
            else total
        ),
        "filtro_cedula": filt_norm or None,
        "limit": lim,
        "offset": off,
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
