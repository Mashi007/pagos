"""
Excel "Prestamos Drive" desde el snapshot de la hoja CONCILIACIÓN (conciliacion_sheet_rows).
Misma regla de filtro que Clientes (hoja): columna LOTE (p. ej. columna B) ∈ lista `lotes`.
Cabeceras de salida (fila 1): snake_case como en la hoja de referencia operativa.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date
from typing import Any, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.services.reporte_clientes_hoja import (
    _as_text,
    _norm_lote_celda,
    _pick_cedula_header,
    _pick_lote_header,
)

logger = logging.getLogger(__name__)


def _norm_header_cell(h: str) -> str:
    """Normaliza encabezado: minúsculas, sin acentos, espacios simples."""
    if not h:
        return ""
    normalized = (h or "").strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    return normalized


def _pick_total_financiamiento_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "total" in hl and "financiam" in hl:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if "financiamiento" in hl or hl in ("monto", "monto total"):
            return h
    return None


def _pick_modalidad_pago_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "modalidad" in hl and "pago" in hl:
            return h
        if "modalidad" in hl and "financiam" in hl:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if hl == "modalidad" or "forma de pago" in hl or "forma pago" in hl:
            return h
    return None


def _pick_fecha_requerimiento_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "requerimiento" in hl:
            return h
        if "fecha" in hl and "req" in hl and "aprob" not in hl:
            return h
        if "entrega" in hl and "aprob" not in hl:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if "solicitud" in hl and "fecha" in hl:
            return h
    return None


def _pick_fecha_aprobacion_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "aprob" not in hl:
            continue
        if "requer" in hl:
            continue
        if (
            "fecha" in hl
            or hl.startswith("fec ")
            or hl.startswith("fec.")
            or " fec." in hl
            or " fec " in hl
        ):
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if "entrega" in hl and "aprob" not in hl and "requerimiento" not in hl:
            return h
    return None


def _pick_producto_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if hl == "producto" or "tipo producto" in hl:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if "financiam" in hl and ("para" in hl or "todas" in hl):
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if hl.startswith("financiam") and len(hl) > 10:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if "auto" in hl or "vehiculo" in hl or "vehículo" in hl:
            return h
    return None


def _pick_concesionario_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "concesion" in hl:
            return h
    return None


def _pick_analista_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "analista" in hl:
            return h
    return None


def _pick_modelo_vehiculo_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "modelo" in hl and "veh" in hl:
            return h
    for h in headers:
        hl = _norm_header_cell(h)
        if hl == "modelo" or "vehiculo" in hl or "vehículo" in hl:
            return h
    return None


def _pick_numero_cuotas_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = _norm_header_cell(h)
        if "cuota" in hl and (
            "num" in hl
            or "nro" in hl
            or "núm" in hl
            or "#" in (h or "")
            or "cantidad" in hl
        ):
            return h
        if hl in ("cuotas", ".", "numero cuotas", "número cuotas", "nro cuotas", "# cuotas"):
            return h
    return None


def build_prestamos_drive_excel(
    db: Session,
    lotes: List[int],
) -> Tuple[bytes, int]:
    import openpyxl

    if not lotes:
        raise ValueError("Indique al menos un número de lote para el filtro.")

    lotes_set: Set[str] = {str(int(x)) for x in lotes}

    logger.info(
        "[prestamos_drive] build_prestamos_drive_excel lotes=%s",
        sorted(int(x) for x in lotes_set),
    )

    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    if not headers:
        raise ValueError(
            "No hay cabeceras de la hoja sincronizada. Sincronice desde Drive "
            "(POST /api/v1/conciliacion-sheet/sync-now o sync con secreto)."
        )

    logger.info(
        "[prestamos_drive] HEADERS DETECTADAS (totales=%d): %s",
        len(headers),
        headers,
    )

    lote_key = _pick_lote_header(headers)

    # Columnas obligatorias (error si no se detectan)
    required_keys: dict[str, Optional[str]] = {
        "LOTE": lote_key,
        "cédula": _pick_cedula_header(headers),
        "total financiamiento": _pick_total_financiamiento_header(headers),
        "modalidad pago": _pick_modalidad_pago_header(headers),
        "fecha requerimiento": _pick_fecha_requerimiento_header(headers),
        "concesionario": _pick_concesionario_header(headers),
        "analista": _pick_analista_header(headers),
        "modelo vehículo": _pick_modelo_vehiculo_header(headers),
        "número cuotas": _pick_numero_cuotas_header(headers),
    }

    # Columnas opcionales (si no existen en la hoja se deja vacío en el Excel)
    optional_keys: dict[str, Optional[str]] = {
        "fecha aprobación (hoja)": _pick_fecha_aprobacion_header(headers),
        "producto": _pick_producto_header(headers),
    }

    all_keys = {**required_keys, **optional_keys}

    logger.info(
        "[prestamos_drive] KEYS MAPEADAS: %s",
        {k: v for k, v in all_keys.items()},
    )

    missing = [label for label, key in required_keys.items() if not key]
    if missing:
        import json
        headers_list_str = json.dumps(headers, ensure_ascii=False)
        logger.error(
            "[prestamos_drive] COLUMNAS FALTANTES: %s. Headers disponibles: %s",
            missing,
            headers_list_str,
        )
        raise ValueError(
            "No se pudieron detectar columnas en la hoja para: "
            + ", ".join(missing)
            + ". COLUMNAS DISPONIBLES EN LA HOJA: "
            + headers_list_str
            + " Revise que los nombres coincidan exactamente y vuelva a sincronizar desde Drive."
        )

    ced_key = required_keys["cédula"]
    tf_key = required_keys["total financiamiento"]
    mod_key = required_keys["modalidad pago"]
    frq_key = required_keys["fecha requerimiento"]
    fap_key = optional_keys["fecha aprobación (hoja)"]   # puede ser None
    prod_key = optional_keys["producto"]                  # puede ser None
    conc_key = required_keys["concesionario"]
    ana_key = required_keys["analista"]
    mv_key = required_keys["modelo vehículo"]
    ncu_key = required_keys["número cuotas"]

    logger.info(
        "[prestamos_drive] columnas: lote=%r ced=%r tf=%r mod=%r frq=%r fap=%r "
        "prod=%r conc=%r ana=%r mv=%r ncu=%r",
        lote_key,
        ced_key,
        tf_key,
        mod_key,
        frq_key,
        fap_key,
        prod_key,
        conc_key,
        ana_key,
        mv_key,
        ncu_key,
    )

    sheet_rows = db.execute(
        select(ConciliacionSheetRow).order_by(ConciliacionSheetRow.row_index)
    ).scalars().all()
    if not sheet_rows:
        raise ValueError(
            "No hay filas en conciliacion_sheet_rows. Ejecute sincronización desde Drive."
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prestamos Drive"
    ws.append(
        [
            "cedula",
            "total_financiamiento",
            "modalidad_pago",
            "fecha_requerimiento",
            "fecha_aprobacion",
            "producto",
            "concesionario",
            "analista",
            "modelo_vehiculo",
            "numero_cuotas",
        ]
    )

    out_count = 0
    for sr in sheet_rows:
        cells = sr.cells or {}
        if not isinstance(cells, dict):
            continue

        raw_lote_norm = _norm_lote_celda(cells.get(lote_key or ""))
        if raw_lote_norm is None or raw_lote_norm not in lotes_set:
            continue

        row_out = [
            _as_text(cells.get(ced_key or "")),
            _as_text(cells.get(tf_key or "")),
            _as_text(cells.get(mod_key or "")),
            _as_text(cells.get(frq_key or "")),
            _as_text(cells.get(fap_key or "")),
            _as_text(cells.get(prod_key or "")),
            _as_text(cells.get(conc_key or "")),
            _as_text(cells.get(ana_key or "")),
            _as_text(cells.get(mv_key or "")),
            _as_text(cells.get(ncu_key or "")),
        ]
        ws.append(row_out)
        out_count += 1

    buf = io.BytesIO()
    wb.save(buf)
    out_bytes = buf.getvalue()
    logger.info(
        "[prestamos_drive] OK filas_export=%s bytes=%s fecha=%s",
        out_count,
        len(out_bytes),
        date.today().isoformat(),
    )
    return out_bytes, out_count
