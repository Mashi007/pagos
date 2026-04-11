"""
Excel "Clientes" desde el snapshot de la hoja CONCILIACIÓN (conciliacion_sheet_rows).
Columnas de salida: Cédula | Nombres | Teléfono | Email.
Filtro: la celda de la columna LOTE (p. ej. columna B en la hoja) debe coincidir con uno de
los enteros en `lotes` (ej. 70 → todas las filas con LOTE 70).
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

logger = logging.getLogger(__name__)

_MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _pick_cedula_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula identidad" in hl or hl == "cedula" or hl == "cédula":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula" in hl or "cédula" in hl:
            return h
    if len(headers) > 4:
        return headers[4]
    return headers[0] if headers else None


def _pick_mes_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if hl == "mes":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if hl.startswith("mes") and len(hl) <= 6:
            return h
    return None


def _pick_lote_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if hl == "lote":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if "lote" in hl:
            return h
    return None


def _pick_nombres_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cliente" in hl or "nombres" in hl or "nombre" in hl:
            return h
    return None


def _pick_telefono_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "movil" in hl or "móvil" in hl or "telefono" in hl or "teléfono" in hl or hl == "tel":
            return h
    return None


def _pick_email_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "correo" in hl or "email" in hl or "e-mail" in hl:
            return h
    return None


def _parse_mes_to_year_month(raw: str) -> Optional[Tuple[int, int]]:
    """
    Devuelve (año, mes 1-12) a partir del texto de la columna MES, o None si no se reconoce.
    Soporta YYYY-MM-DD, D/M/YYYY y D-mon-YY (misma heurística que Fecha Drive).
    """
    s = _as_text(raw)
    if not s:
        return None

    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[:10].replace("-", "").isdigit():
        y, m = int(s[:4]), int(s[5:7])
        if 1 <= m <= 12:
            return y, m
        return None

    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return y, mo
        return None

    m2 = re.match(
        r"^(\d{1,2})-([a-zA-Z]{3,})-(\d{2,4})$",
        s.replace(" ", ""),
    )
    if m2:
        d = int(m2.group(1))
        mon = m2.group(2).lower()[:3]
        yr = int(m2.group(3))
        if yr < 100:
            yr += 2000 if yr < 50 else 1900
        mo = _MESES.get(mon)
        if mo and 1 <= d <= 31:
            return yr, mo
        return None

    return None


def _norm_lote_celda(v: Any) -> Optional[str]:
    """Valor de celda LOTE comparable con los enteros del filtro (70, '70', '70.0' → '70')."""
    s = _as_text(v)
    if not s:
        return None
    t = s.replace(" ", "").replace(",", ".")
    try:
        if "." in t:
            return str(int(float(t)))
        return str(int(t))
    except ValueError:
        u = s.strip()
        return u if u else None


def build_clientes_hoja_excel(
    db: Session,
    lotes: List[int],
) -> Tuple[bytes, int]:
    import openpyxl

    if not lotes:
        raise ValueError("Indique al menos un número de lote para el filtro.")

    lotes_set: Set[str] = {str(int(x)) for x in lotes}

    logger.info(
        "[clientes_hoja] build_clientes_hoja_excel lotes=%s",
        sorted(int(x) for x in lotes_set),
    )

    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    if not headers:
        raise ValueError(
            "No hay cabeceras de la hoja sincronizada. Sincronice desde Drive "
            "(POST /api/v1/conciliacion-sheet/sync-now o sync con secreto)."
        )

    lote_key = _pick_lote_header(headers)
    ced_key = _pick_cedula_header(headers)
    nom_key = _pick_nombres_header(headers)
    tel_key = _pick_telefono_header(headers)
    mail_key = _pick_email_header(headers)

    missing = [
        name
        for name, key in [
            ("LOTE", lote_key),
            ("cédula", ced_key),
            ("nombres/cliente", nom_key),
            ("teléfono/móvil", tel_key),
            ("correo/email", mail_key),
        ]
        if not key
    ]
    if missing:
        raise ValueError(
            "No se pudieron detectar columnas en la hoja para: "
            + ", ".join(missing)
            + ". Revise cabeceras (LOTE, cédula, cliente, móvil, correo) y vuelva a sincronizar."
        )

    logger.info(
        "[clientes_hoja] columnas: lote=%r cedula=%r nombres=%r tel=%r email=%r",
        lote_key,
        ced_key,
        nom_key,
        tel_key,
        mail_key,
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
    ws.title = "Clientes"
    ws.append(["Cédula", "Nombres", "Teléfono", "Email"])

    out_count = 0
    for sr in sheet_rows:
        cells = sr.cells or {}
        if not isinstance(cells, dict):
            continue

        raw_lote_norm = _norm_lote_celda(cells.get(lote_key or ""))
        if raw_lote_norm is None or raw_lote_norm not in lotes_set:
            continue

        ced = _as_text(cells.get(ced_key or ""))
        nom = _as_text(cells.get(nom_key or ""))
        tel = _as_text(cells.get(tel_key or ""))
        em = _as_text(cells.get(mail_key or ""))

        ws.append([ced, nom, tel, em])
        out_count += 1

    buf = io.BytesIO()
    wb.save(buf)
    out_bytes = buf.getvalue()
    logger.info(
        "[clientes_hoja] OK filas_export=%s bytes=%s fecha=%s",
        out_count,
        len(out_bytes),
        date.today().isoformat(),
    )
    return out_bytes, out_count


def parse_anos_meses_query(anos: str, meses: str) -> Tuple[List[int], List[int]]:
    """Parsea query tipo anos=2024,2025 y meses=10,11."""
    ya: List[int] = []
    mo: List[int] = []
    for part in (anos or "").split(","):
        part = part.strip()
        if not part:
            continue
        ya.append(int(part))
    for part in (meses or "").split(","):
        part = part.strip()
        if not part:
            continue
        mo.append(int(part))
    return ya, mo


def parse_lotes_query(lotes: str) -> List[int]:
    """Parsea query tipo lotes=70 o lotes=70,71,72."""
    out: List[int] = []
    for part in (lotes or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out
