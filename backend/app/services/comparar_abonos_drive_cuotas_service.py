"""
Compara ABONOS de la hoja CONCILIACIÓN (snapshot Drive) vs suma de total_pagado en cuotas por préstamo.
Usado desde notificaciones (misma cédula que el listado).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.reporte_clientes_hoja import _as_text, _pick_cedula_header
from app.services.reporte_prestamos_drive import _pick_abonos_header
from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

logger = logging.getLogger(__name__)

_TOL_MONTO = 0.02


def _parse_monto_celda_hoja(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        x = float(val)
        return x if x == x and abs(x) < 1e30 else None
    s = str(val).strip()
    if not s or s in ("-", "—", "NE", "N/A", "n/a"):
        return None
    s = re.sub(r"[\sBs$€]", "", s, flags=re.IGNORECASE)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) <= 2 and parts[-1].replace("0", "").isdigit():
            s = "".join(parts[:-1]).replace(",", "") + "." + parts[-1]
        else:
            s = s.replace(",", "")
    try:
        x = float(s)
        return x if x == x and abs(x) < 1e30 else None
    except ValueError:
        return None


def _to_float_cuota_total(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def comparar_abonos_drive_vs_cuotas(
    db: Session,
    *,
    cedula: str,
    prestamo_id: int,
) -> Dict[str, Any]:
    cedula_in = (cedula or "").strip()
    if not cedula_in:
        raise ValueError("Indique la cédula.")
    if prestamo_id <= 0:
        raise ValueError("Indique un préstamo válido.")

    prestamo = db.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise ValueError("Préstamo no encontrado.")

    clave_param = normalizar_cedula_clave_cupo(cedula_in)
    clave_prest = normalizar_cedula_clave_cupo(prestamo.cedula or "")
    if clave_param and clave_prest and clave_param != clave_prest:
        raise ValueError("La cédula no coincide con el préstamo indicado.")

    total_row = db.execute(
        select(func.coalesce(func.sum(Cuota.total_pagado), 0)).where(
            Cuota.prestamo_id == prestamo_id
        )
    ).scalar_one()
    total_pagado_cuotas = _to_float_cuota_total(total_row)

    meta = db.get(ConciliacionSheetMeta, 1)
    headers: List[str] = list(meta.headers) if meta and meta.headers else []
    synced_at: Optional[str] = None
    if meta and getattr(meta, "synced_at", None):
        sa = meta.synced_at
        if isinstance(sa, datetime):
            synced_at = sa.isoformat()

    advertencias: List[str] = []
    if not headers:
        advertencias.append("No hay cabeceras de hoja sincronizada (CONCILIACIÓN).")

    ced_key = _pick_cedula_header(headers) if headers else None
    abo_key = _pick_abonos_header(headers) if headers else None
    if not ced_key:
        advertencias.append("No se detectó columna de cédula en la hoja.")
    if not abo_key:
        advertencias.append("No se detectó columna ABONOS en la hoja.")

    filas_coincidentes = 0
    suma_abonos_drive = 0.0
    if ced_key and abo_key:
        clave = clave_param or normalizar_cedula_clave_cupo(cedula_in)
        sheet_rows = db.execute(
            select(ConciliacionSheetRow).order_by(ConciliacionSheetRow.row_index)
        ).scalars().all()
        for sr in sheet_rows:
            cells = sr.cells or {}
            if not isinstance(cells, dict):
                continue
            c_raw = _as_text(cells.get(ced_key))
            if normalizar_cedula_clave_cupo(c_raw) != clave:
                continue
            filas_coincidentes += 1
            m = _parse_monto_celda_hoja(cells.get(abo_key))
            if m is not None:
                suma_abonos_drive += m

    abonos_drive: Optional[float] = None
    if ced_key and abo_key and filas_coincidentes > 0:
        abonos_drive = suma_abonos_drive
    elif ced_key and abo_key and filas_coincidentes == 0:
        advertencias.append(
            "No hay filas en la hoja CONCILIACIÓN con esta cédula (tras sincronizar)."
        )

    diferencia: Optional[float] = None
    if abonos_drive is not None:
        diferencia = round(abonos_drive - total_pagado_cuotas, 2)

    coincide = (
        abonos_drive is not None
        and diferencia is not None
        and abs(diferencia) <= _TOL_MONTO
    )

    # Indicador operativo: "sí" solo si ABONOS (hoja) es claramente mayor que total en cuotas (regla de negocio notificaciones).
    puede_aplicar = bool(
        abonos_drive is not None
        and float(abonos_drive) > float(total_pagado_cuotas) + _TOL_MONTO
    )
    indicador: str = "si" if puede_aplicar else "no"

    logger.info(
        "[comparar_abonos] cedula=%s prestamo_id=%s filas_hoja=%s abonos_drive=%s total_cuotas=%s",
        cedula_in,
        prestamo_id,
        filas_coincidentes,
        abonos_drive,
        total_pagado_cuotas,
    )

    return {
        "cedula": cedula_in,
        "prestamo_id": prestamo_id,
        "filas_hoja_coincidentes": filas_coincidentes,
        "abonos_drive": abonos_drive,
        "total_pagado_cuotas": round(total_pagado_cuotas, 2),
        "diferencia": diferencia,
        "coincide_aproximado": coincide,
        "indicador": indicador,
        "puede_aplicar": puede_aplicar,
        "tolerancia": _TOL_MONTO,
        "hoja_synced_at": synced_at,
        "columna_cedula_detectada": ced_key,
        "columna_abonos_detectada": abo_key,
        "advertencias": advertencias,
    }
