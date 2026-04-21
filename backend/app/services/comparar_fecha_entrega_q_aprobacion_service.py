"""
Compara la columna Q de la hoja CONCILIACIÓN (snapshot en BD) con `prestamos.fecha_aprobacion`.

La celda Q se resuelve por posición dentro de `CONCILIACION_SHEET_COLUMNS_RANGE` (cabecera en
`conciliacion_sheet_meta.headers`, mismo criterio de letra Excel que la tabla `drive.col_q`).
La fila de la hoja se alinea al préstamo como en ABONOS: cédula + huella monto/cuotas/modalidad + lote.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.models.prestamo import Prestamo
from app.services.comparar_abonos_drive_cuotas_service import (
    _HORAS_SYNC_CONSIDERADA_ANTIGUA,
    _fila_hoja_coincide_prestamo,
    _norm_lote_param,
    _prestamo_huella_dict,
)
from app.services.conciliacion_sheet_sync import _col_letter_to_index1, _parse_columns_range
from app.services.reporte_clientes_hoja import (
    _as_text,
    _norm_lote_celda,
    _pick_cedula_header,
    _pick_lote_header,
)
from app.services.reporte_prestamos_drive import (
    _pick_modalidad_pago_header,
    _pick_numero_cuotas_header,
    _pick_total_financiamiento_header,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

logger = logging.getLogger(__name__)

_COL_Q_LETTER = "Q"


def _persist_prestamo_fecha_entrega_q_cache(
    db: Session, prestamo_id: int, payload: Dict[str, Any]
) -> None:
    row = db.get(Prestamo, prestamo_id)
    if row is None:
        return
    try:
        row.fecha_entrega_q_aprobacion_cache = json.loads(json.dumps(payload, default=str))
    except (TypeError, ValueError):
        row.fecha_entrega_q_aprobacion_cache = None
    row.fecha_entrega_q_aprobacion_cache_at = datetime.utcnow()


def _header_key_for_excel_column(
    headers: List[str], range_start_letter: str, abs_col_letter: str
) -> Optional[str]:
    i0 = _col_letter_to_index1(range_start_letter)
    ic = _col_letter_to_index1(abs_col_letter)
    idx = ic - i0
    if idx < 0 or idx >= len(headers):
        return None
    return headers[idx]


def _column_q_in_range(range_spec: str) -> Tuple[bool, str, str, str]:
    raw = (range_spec or "A:S").strip().upper()
    start_l, end_l, _ncols = _parse_columns_range(raw)
    iq = _col_letter_to_index1(_COL_Q_LETTER)
    i1 = _col_letter_to_index1(start_l)
    i2 = _col_letter_to_index1(end_l)
    ok = i1 <= iq <= i2
    return ok, start_l, end_l, raw


def _parse_fecha_celda_hoja(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        # Google Sheets puede serializar fechas como número de días desde 1899-12-30.
        try:
            x = float(val)
        except (TypeError, ValueError):
            return None
        if 20000 <= x <= 80000 and abs(x - round(x)) < 1e-9:
            base = date(1899, 12, 30)
            return base + timedelta(days=int(round(x)))
        return None
    s = _as_text(val)
    if not s:
        return None
    s2 = s.strip()
    if len(s2) >= 10 and s2[4:5] == "-" and s2[7:8] == "-":
        try:
            return date.fromisoformat(s2[:10])
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        for lim in (8, 9, 10):
            if len(s2) >= lim:
                try:
                    return datetime.strptime(s2[:lim], fmt).date()
                except ValueError:
                    continue
    m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b", s2)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def _fecha_aprobacion_sistema_date(prestamo: Prestamo) -> Optional[date]:
    fa = getattr(prestamo, "fecha_aprobacion", None)
    if fa is None:
        return None
    if isinstance(fa, datetime):
        return fa.date()
    if isinstance(fa, date):
        return fa
    return None


def _fecha_requerimiento_prestamo_date(prestamo: Prestamo) -> Optional[date]:
    fr = getattr(prestamo, "fecha_requerimiento", None)
    if fr is None:
        return None
    if isinstance(fr, datetime):
        return fr.date()
    if isinstance(fr, date):
        return fr
    return None


def comparar_fecha_entrega_column_q_vs_aprobacion(
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

    range_spec = (getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()
    q_ok, range_start, range_end, range_raw = _column_q_in_range(range_spec)

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
    if not q_ok:
        advertencias.append(
            f"La columna Q no está dentro del rango configurado ({range_raw!r}; leídas {range_start!s}:{range_end!s})."
        )

    ced_key = _pick_cedula_header(headers) if headers else None
    lote_key = _pick_lote_header(headers) if headers else None
    tf_key = _pick_total_financiamiento_header(headers) if headers else None
    mod_key = _pick_modalidad_pago_header(headers) if headers else None
    ncu_key = _pick_numero_cuotas_header(headers) if headers else None

    if not ced_key:
        advertencias.append("No se detectó columna de cédula en la hoja.")
    if not lote_key:
        advertencias.append("No se detectó columna LOTE en la hoja (necesaria si hay varios créditos por cédula).")

    q_header_key: Optional[str] = None
    if q_ok and headers:
        q_header_key = _header_key_for_excel_column(headers, range_start, _COL_Q_LETTER)

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

    if ced_key and filas_por_cedula:
        candidatas = filas_por_cedula
        if lote_filtro and lote_key:
            candidatas = [(c, ln) for c, ln in candidatas if ln is not None and ln == lote_filtro]

        for cells, _ln in candidatas:
            if _fila_hoja_coincide_prestamo(cells, prestamo, tf_key, mod_key, ncu_key):
                filas_prestamo.append(cells)

        if not filas_prestamo and filas_por_cedula:
            if len(filas_por_cedula) > 1 and lote_key and not lote_filtro:
                lotes_dist = {_norm_lote_celda(ln) for _c, ln in filas_por_cedula if ln is not None}
                lotes_dist.discard(None)
                if len(lotes_dist) > 1:
                    requiere_seleccion_lote = True
                    opciones_lote = [{"lote": str(x)} for x in sorted(lotes_dist, key=lambda z: str(z))]
                elif len(lotes_dist) == 1:
                    unico = next(iter(lotes_dist))
                    candidatas2 = [(c, ln) for c, ln in filas_por_cedula if ln == unico]
                    for cells, _ln in candidatas2:
                        if _fila_hoja_coincide_prestamo(cells, prestamo, tf_key, mod_key, ncu_key):
                            filas_prestamo.append(cells)

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

    fecha_q: Optional[date] = None
    raw_q: Any = None
    if q_ok and q_header_key and filas_coincidentes > 0:
        c0 = filas_prestamo[0]
        raw_q = c0.get(q_header_key)
        fecha_q = _parse_fecha_celda_hoja(raw_q)
        if raw_q is not None and str(_as_text(raw_q)).strip() and fecha_q is None:
            advertencias.append(
                "La columna Q tiene valor pero no se pudo interpretar como fecha (revise formato en la hoja)."
            )
    elif ced_key and not filas_por_cedula:
        advertencias.append("No hay filas en la hoja CONCILIACIÓN con esta cédula (tras sincronizar).")
    elif ced_key and filas_por_cedula and filas_coincidentes == 0 and not requiere_seleccion_lote:
        advertencias.append(
            "No hay fila en la hoja que corresponda a este préstamo (misma cédula y datos de crédito). "
            "Si hay varios lotes, elija el lote correcto."
        )

    fecha_ap = _fecha_aprobacion_sistema_date(prestamo)
    if fecha_ap is None:
        advertencias.append("El préstamo no tiene fecha_aprobacion en el sistema.")

    fecha_req = _fecha_requerimiento_prestamo_date(prestamo)

    diferencia_dias: Optional[int] = None
    if fecha_q is not None and fecha_ap is not None:
        diferencia_dias = int((fecha_q - fecha_ap).days)

    coincide_calendario = (
        fecha_q is not None and fecha_ap is not None and fecha_q == fecha_ap
    )

    # «Sí» en UI / POST aplicar (misma validación que POST: Q >= fecha_requerimiento si existe):
    # - Q posterior a la aprobación en BD, o
    # - Q anterior a la aprobación en BD pero >= requerimiento: corrige aprobación errónea vs hoja
    #   (p. ej. serial Excel / carga masiva → fecha de aprobación incorrecta en BD).
    puede_aplicar = False
    if fecha_q is not None and fecha_ap is not None and fecha_q != fecha_ap:
        bloqueado_por_requerimiento = fecha_req is not None and fecha_q < fecha_req
        if bloqueado_por_requerimiento:
            advertencias.append(
                "La fecha Q es anterior a la fecha de requerimiento del préstamo; no se puede usar "
                "como fecha de aprobación desde aquí (use revisión manual)."
            )
        else:
            puede_aplicar = True
    indicador = "si" if puede_aplicar else "no"
    tolerancia_dias = 0

    logger.info(
        "[comparar_fecha_q] cedula=%s prestamo_id=%s lote=%s filas=%s fecha_q=%s fecha_ap=%s "
        "diff_dias=%s puede_aplicar=%s correccion_q_anterior_bd=%s",
        cedula_in,
        prestamo_id,
        lote_filtro,
        filas_coincidentes,
        fecha_q,
        fecha_ap,
        diferencia_dias,
        puede_aplicar,
        bool(
            puede_aplicar
            and fecha_q is not None
            and fecha_ap is not None
            and fecha_q < fecha_ap
        ),
    )

    out: Dict[str, Any] = {
        "cedula": cedula_in,
        "prestamo_id": prestamo_id,
        "prestamo_huella": _prestamo_huella_dict(prestamo),
        "filas_hoja_coincidentes": filas_coincidentes,
        "filas_misma_cedula_hoja": len(filas_por_cedula),
        "columna_q_letra": _COL_Q_LETTER,
        "columna_q_header_detectado": q_header_key,
        "rango_columnas_hoja": range_raw,
        "columna_q_dentro_rango": q_ok,
        "fecha_entrega_column_q": fecha_q.isoformat() if fecha_q else None,
        "fecha_entrega_column_q_raw": raw_q,
        "fecha_aprobacion_sistema": fecha_ap.isoformat() if fecha_ap else None,
        "diferencia_dias": diferencia_dias,
        "coincide_calendario": coincide_calendario,
        "coincide_aproximado": coincide_calendario,
        "puede_aplicar": puede_aplicar,
        "indicador": indicador,
        "correccion_desde_q_anterior_bd": bool(
            puede_aplicar
            and fecha_q is not None
            and fecha_ap is not None
            and fecha_q < fecha_ap
        ),
        "tolerancia_dias": tolerancia_dias,
        "hoja_synced_at": synced_at,
        "hoja_sync_antigua": hoja_sync_antigua,
        "hoja_sync_antigua_horas": hoja_sync_antigua_horas,
        "columna_cedula_detectada": ced_key,
        "columna_lote_detectada": lote_key,
        "lote_aplicado": lote_filtro,
        "requiere_seleccion_lote": requiere_seleccion_lote,
        "opciones_lote": opciones_lote,
        "advertencias": advertencias,
    }
    if persist_cache:
        try:
            _persist_prestamo_fecha_entrega_q_cache(db, prestamo_id, out)
        except Exception:
            logger.warning(
                "[comparar_fecha_q] no se pudo persistir caché prestamo_id=%s",
                prestamo_id,
                exc_info=True,
            )
    return out
