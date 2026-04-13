"""
Compara ABONOS de la hoja CONCILIACIÓN (snapshot Drive) vs suma de total_pagado en cuotas por préstamo.

Solo se consideran filas de la hoja que corresponden al préstamo en análisis (cédula + huella de
monto/cuotas/modalidad). Si hay varias filas con la misma cédula y no se puede resolver, se pide
elegir LOTE (columna detectada, p. ej. LOTE en B) y se valida que esa fila corresponda al préstamo.
No se suman abonos de otros créditos de la misma cédula (opción A de negocio).
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.reporte_clientes_hoja import (
    _as_text,
    _norm_lote_celda,
    _pick_cedula_header,
    _pick_lote_header,
)
from app.services.reporte_prestamos_drive import (
    _pick_abonos_header,
    _pick_modalidad_pago_header,
    _pick_numero_cuotas_header,
    _pick_total_financiamiento_header,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

logger = logging.getLogger(__name__)

_TOL_MONTO = 0.02
_TOL_FIN_HOJA_USD = 1.0  # tolerancia hoja vs prestamo.total_financiamiento (redondeos / lectura)
_HORAS_SYNC_CONSIDERADA_ANTIGUA = 48
# Umbral compartido con aplicar_abonos_drive: montos mayores exigen escribir CONFIRMO en UI y backend.
UMBRAL_CONFIRMO_ABONOS_USD = 5000.0


def _persist_prestamo_abonos_drive_cuotas_cache(
    db: Session, prestamo_id: int, payload: Dict[str, Any]
) -> None:
    """Persiste el resultado de comparación en el préstamo (columna JSON + marca de tiempo)."""
    row = db.get(Prestamo, prestamo_id)
    if row is None:
        return
    try:
        row.abonos_drive_cuotas_cache = json.loads(json.dumps(payload, default=str))
    except (TypeError, ValueError):
        row.abonos_drive_cuotas_cache = None
    row.abonos_drive_cuotas_cache_at = datetime.utcnow()


def _prestamo_huella_dict(prestamo: Prestamo) -> Dict[str, Any]:
    """Huella de negocio en BD (financiamiento, cuotas, modalidad) para depuración y UI."""
    try:
        tf = float(prestamo.total_financiamiento or 0)
    except (TypeError, ValueError):
        tf = 0.0
    try:
        nc = int(prestamo.numero_cuotas or 0)
    except (TypeError, ValueError):
        nc = 0
    return {
        "total_financiamiento": round(tf, 2),
        "numero_cuotas": nc,
        "modalidad_pago": (prestamo.modalidad_pago or "").strip(),
    }


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


def _parse_int_celda(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int) and not isinstance(val, bool):
        return int(val)
    if isinstance(val, float):
        if val != val or abs(val) > 1e9:
            return None
        return int(round(val))
    s = _as_text(val)
    if not s:
        return None
    s = s.replace(" ", "").replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return None


def _norm_modalidad(s: str) -> str:
    return (s or "").strip().upper().replace(" ", "")


def _fila_hoja_coincide_prestamo(
    cells: Dict[str, Any],
    prestamo: Prestamo,
    tf_key: Optional[str],
    mod_key: Optional[str],
    ncu_key: Optional[str],
) -> bool:
    """True si la fila (monto total, cuotas, modalidad) alinea con el préstamo en BD."""
    if not tf_key or not ncu_key or not mod_key:
        return False
    m_tf = _parse_monto_celda_hoja(cells.get(tf_key))
    if m_tf is None:
        return False
    try:
        tf_bd = float(prestamo.total_financiamiento or 0)
    except (TypeError, ValueError):
        tf_bd = 0.0
    if abs(m_tf - tf_bd) > _TOL_FIN_HOJA_USD:
        return False
    n_h = _parse_int_celda(cells.get(ncu_key))
    if n_h is None or int(prestamo.numero_cuotas or 0) != int(n_h):
        return False
    mod_h = _norm_modalidad(_as_text(cells.get(mod_key)))
    mod_p = _norm_modalidad(prestamo.modalidad_pago or "")
    if not mod_h or not mod_p or mod_h != mod_p:
        return False
    return True


def _norm_lote_param(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return _norm_lote_celda(s)


def comparar_abonos_drive_vs_cuotas(
    db: Session,
    *,
    cedula: str,
    prestamo_id: int,
    lote: Optional[str] = None,
    persist_cache: bool = False,
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
    hoja_sync_antigua = False
    hoja_sync_antigua_horas: Optional[float] = None
    if meta and getattr(meta, "synced_at", None):
        sa = meta.synced_at
        if isinstance(sa, datetime):
            synced_at = sa.isoformat()
            now_utc = datetime.now(timezone.utc)
            sa_utc = sa if sa.tzinfo else sa.replace(tzinfo=timezone.utc)
            if sa_utc.tzinfo is not None and sa_utc.tzinfo != timezone.utc:
                sa_utc = sa_utc.astimezone(timezone.utc)
            delta_h = (now_utc - sa_utc).total_seconds() / 3600.0
            hoja_sync_antigua_horas = round(delta_h, 1)
            if delta_h > float(_HORAS_SYNC_CONSIDERADA_ANTIGUA):
                hoja_sync_antigua = True

    advertencias: List[str] = []
    if hoja_sync_antigua and hoja_sync_antigua_horas is not None:
        advertencias.append(
            f"La última sincronización de la hoja fue hace ~{hoja_sync_antigua_horas} h "
            f"(más de {_HORAS_SYNC_CONSIDERADA_ANTIGUA} h). Resincronice CONCILIACIÓN si necesita datos al día."
        )
    if not headers:
        advertencias.append("No hay cabeceras de hoja sincronizada (CONCILIACIÓN).")

    ced_key = _pick_cedula_header(headers) if headers else None
    abo_key = _pick_abonos_header(headers) if headers else None
    lote_key = _pick_lote_header(headers) if headers else None
    tf_key = _pick_total_financiamiento_header(headers) if headers else None
    mod_key = _pick_modalidad_pago_header(headers) if headers else None
    ncu_key = _pick_numero_cuotas_header(headers) if headers else None

    if not ced_key:
        advertencias.append("No se detectó columna de cédula en la hoja.")
    if not abo_key:
        advertencias.append("No se detectó columna ABONOS en la hoja.")
    if not lote_key:
        advertencias.append("No se detectó columna LOTE en la hoja (necesaria si hay varios créditos por cédula).")

    lote_filtro = _norm_lote_param(lote)

    filas_por_cedula: List[Tuple[Dict[str, Any], Optional[str]]] = []
    if ced_key:
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
            ln = _norm_lote_celda(cells.get(lote_key)) if lote_key else None
            filas_por_cedula.append((cells, ln))

    filas_prestamo: List[Dict[str, Any]] = []
    requiere_seleccion_lote = False
    opciones_lote: List[Dict[str, Any]] = []

    if ced_key and abo_key and filas_por_cedula:
        candidatas = filas_por_cedula
        if lote_filtro and lote_key:
            candidatas = [(c, ln) for c, ln in candidatas if ln is not None and ln == lote_filtro]

        for cells, _ln in candidatas:
            if _fila_hoja_coincide_prestamo(cells, prestamo, tf_key, mod_key, ncu_key):
                filas_prestamo.append(cells)

        if not filas_prestamo and filas_por_cedula:
            # Varias filas misma cédula: pedir LOTE si hay más de un lote distinto
            if len(filas_por_cedula) > 1 and lote_key and not lote_filtro:
                por_lote: Dict[str, float] = defaultdict(float)
                for cells, ln in filas_por_cedula:
                    if ln is None:
                        continue
                    m = _parse_monto_celda_hoja(cells.get(abo_key)) if abo_key else None
                    if m is not None:
                        por_lote[ln] += m
                if len(por_lote) > 1:
                    requiere_seleccion_lote = True

                    def _sort_lote_key(item: Tuple[str, float]) -> Tuple[int, str]:
                        k, _ = item
                        try:
                            return (0, f"{int(k):012d}")
                        except (TypeError, ValueError):
                            return (1, str(k))

                    opciones_lote = [
                        {"lote": k, "abonos": round(v, 2)}
                        for k, v in sorted(por_lote.items(), key=_sort_lote_key)
                    ]
                elif len(por_lote) == 1:
                    unico = next(iter(por_lote.keys()))
                    candidatas2 = [(c, ln) for c, ln in filas_por_cedula if ln == unico]
                    for cells, _ln in candidatas2:
                        if _fila_hoja_coincide_prestamo(cells, prestamo, tf_key, mod_key, ncu_key):
                            filas_prestamo.append(cells)
            # Una sola fila cédula: usar aunque falle huella estricta (compatibilidad), con aviso
            if not filas_prestamo and len(filas_por_cedula) == 1:
                cells0, _ = filas_por_cedula[0]
                filas_prestamo = [cells0]
                if not _fila_hoja_coincide_prestamo(cells0, prestamo, tf_key, mod_key, ncu_key):
                    advertencias.append(
                        "La fila de la hoja no coincide plenamente con monto/cuotas/modalidad del préstamo en BD; "
                        "revise la hoja o use el lote correcto."
                    )

        if lote_filtro and lote_key and not filas_prestamo and filas_por_cedula:
            raise ValueError(
                f"El lote {lote_filtro!s} no corresponde a este préstamo en la hoja "
                "(cédula + total financiamiento / número de cuotas / modalidad)."
            )

    filas_coincidentes = len(filas_prestamo)
    suma_abonos_drive = 0.0
    if abo_key:
        for cells in filas_prestamo:
            m = _parse_monto_celda_hoja(cells.get(abo_key))
            if m is not None:
                suma_abonos_drive += m

    abonos_drive: Optional[float] = None
    if ced_key and abo_key and filas_coincidentes > 0:
        abonos_drive = suma_abonos_drive
    elif ced_key and abo_key and not filas_por_cedula:
        advertencias.append(
            "No hay filas en la hoja CONCILIACIÓN con esta cédula (tras sincronizar)."
        )
    elif ced_key and abo_key and filas_por_cedula and filas_coincidentes == 0 and not requiere_seleccion_lote:
        advertencias.append(
            "No hay fila en la hoja que corresponda a este préstamo (misma cédula y datos de crédito). "
            "Si hay varios lotes, elija el lote correcto."
        )

    diferencia: Optional[float] = None
    if abonos_drive is not None:
        diferencia = round(abonos_drive - total_pagado_cuotas, 2)

    coincide = (
        abonos_drive is not None
        and diferencia is not None
        and abs(diferencia) <= _TOL_MONTO
    )

    puede_aplicar = bool(
        abonos_drive is not None
        and not requiere_seleccion_lote
        and float(abonos_drive) > float(total_pagado_cuotas) + _TOL_MONTO
    )
    indicador: str = "si" if puede_aplicar else "no"

    logger.info(
        "[comparar_abonos] cedula=%s prestamo_id=%s lote=%s filas_prestamo=%s abonos=%s total_cuotas=%s requiere_lote=%s",
        cedula_in,
        prestamo_id,
        lote_filtro,
        filas_coincidentes,
        abonos_drive,
        total_pagado_cuotas,
        requiere_seleccion_lote,
    )

    out: Dict[str, Any] = {
        "cedula": cedula_in,
        "prestamo_id": prestamo_id,
        "prestamo_huella": _prestamo_huella_dict(prestamo),
        "filas_hoja_coincidentes": filas_coincidentes,
        "filas_misma_cedula_hoja": len(filas_por_cedula),
        "abonos_drive": abonos_drive,
        "total_pagado_cuotas": round(total_pagado_cuotas, 2),
        "diferencia": diferencia,
        "coincide_aproximado": coincide,
        "indicador": indicador,
        "puede_aplicar": puede_aplicar,
        "tolerancia": _TOL_MONTO,
        "hoja_synced_at": synced_at,
        "hoja_sync_antigua": hoja_sync_antigua,
        "hoja_sync_antigua_horas": hoja_sync_antigua_horas,
        "columna_cedula_detectada": ced_key,
        "columna_abonos_detectada": abo_key,
        "columna_lote_detectada": lote_key,
        "lote_aplicado": lote_filtro,
        "requiere_seleccion_lote": requiere_seleccion_lote,
        "opciones_lote": opciones_lote,
        "advertencias": advertencias,
        "umbral_doble_confirmacion_abonos_usd": UMBRAL_CONFIRMO_ABONOS_USD,
    }
    if persist_cache:
        try:
            _persist_prestamo_abonos_drive_cuotas_cache(db, prestamo_id, out)
        except Exception:
            logger.warning(
                "[comparar_abonos] no se pudo persistir caché prestamo_id=%s",
                prestamo_id,
                exc_info=True,
            )
    return out
