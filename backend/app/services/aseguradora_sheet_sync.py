"""Sync cedulas Aseguradora desde Google Sheet (solo columna Cedula)."""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.aseguradora_universo import AseguradoraUniversoCedula
from app.utils.cedula_almacenamiento import (
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_DEFAULT_SHEET_ID = "1FEh7gMhCh4UD6_W5e5VnsWNsrOfGuILpxJ0CpWwDKVM"


def _sheet_id() -> str:
    return (
        getattr(settings, "ASEGURADORA_SHEET_SPREADSHEET_ID", None) or _DEFAULT_SHEET_ID
    ).strip()


def _norm_header(h: str) -> str:
    s = unicodedata.normalize("NFKD", (h or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


def _pick_cedula_col(headers: List[str]) -> Optional[int]:
    for i, h in enumerate(headers):
        hl = _norm_header(str(h))
        if hl in ("cedula", "cedula identidad", "nro cedula", "numero cedula"):
            return i
    for i, h in enumerate(headers):
        hl = _norm_header(str(h))
        if "cedula" in hl:
            return i
    return None


def _resolve_tab_title(service: Any, spreadsheet_id: str, tab_name: str) -> str:
    from app.services.conciliacion_sheet_sync import _resolve_sheet_title

    wanted = (tab_name or "").strip()
    if wanted:
        return _resolve_sheet_title(service, spreadsheet_id, wanted)
    meta = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )
    sheets = meta.get("sheets") or []
    if not sheets:
        raise RuntimeError("El spreadsheet Aseguradora no tiene pestanas.")
    return sheets[0]["properties"]["title"]


def fetch_cedulas_desde_sheet() -> List[str]:
    from app.services.conciliacion_sheet_sync import (
        _build_sheets_service,
        _escape_sheet_title_for_range,
        _get_sheets_credentials,
        _sheets_execute,
    )

    sid = _sheet_id()
    if not sid:
        raise RuntimeError("ASEGURADORA_SHEET_SPREADSHEET_ID no configurado.")
    creds = _get_sheets_credentials()
    if creds is None:
        raise RuntimeError(
            "Sin credenciales Google (Sheets) para sync Aseguradora. "
            "Configure Informe de pagos / cuenta de servicio o tokens Gmail."
        )
    service = _build_sheets_service(creds)
    tab_cfg = (getattr(settings, "ASEGURADORA_SHEET_TAB_NAME", None) or "").strip()
    title = _resolve_tab_title(service, sid, tab_cfg)
    cols = (getattr(settings, "ASEGURADORA_SHEET_COLUMNS_RANGE", None) or "A:B").strip()
    rng = f"'{_escape_sheet_title_for_range(title)}'!{cols}"
    logger.info("[aseguradora] leyendo spreadsheet tab=%r rango=%r", title, cols)
    resp = _sheets_execute(
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sid,
            range=rng,
            majorDimension="ROWS",
            valueRenderOption="UNFORMATTED_VALUE",
        )
    )
    values: List[List[Any]] = resp.get("values") or []
    if not values:
        raise RuntimeError("La hoja Aseguradora no devolvio filas.")

    header_idx = 0
    ced_col = None
    for i, row in enumerate(values[:30]):
        headers = [str(c or "").strip() for c in row]
        col = _pick_cedula_col(headers)
        if col is not None:
            header_idx = i
            ced_col = col
            break
    if ced_col is None:
        ced_col = 0
        header_idx = -1
        logger.warning("[aseguradora] no se encontro cabecera Cedula; se usa columna A")

    out: List[str] = []
    seen: Set[str] = set()
    start = header_idx + 1
    for row in values[start:]:
        if ced_col >= len(row):
            continue
        raw = row[ced_col]
        if raw is None:
            continue
        stored = normalizar_cedula_almacenamiento(str(raw))
        if not stored:
            continue
        key = texto_cedula_comparable_bd(stored)
        if not key or key in seen:
            continue
        if _norm_header(stored) in ("cedula", "cedula identidad"):
            continue
        seen.add(key)
        out.append(stored)
    return out


def claves_universo_aseguradora(db: Session) -> Set[str]:
    rows = db.execute(select(AseguradoraUniversoCedula.cedula)).scalars().all()
    return {texto_cedula_comparable_bd(c) for c in rows if c}


def meta_universo_aseguradora(db: Session) -> Dict[str, Any]:
    n = db.scalar(select(func.count()).select_from(AseguradoraUniversoCedula)) or 0
    return {"cantidad": int(n), "spreadsheet_id": _sheet_id()}


def sync_aseguradora_cedulas_desde_sheet(
    db: Session, *, usuario_id: Optional[int] = None
) -> Dict[str, Any]:
    cedulas = fetch_cedulas_desde_sheet()
    db.execute(delete(AseguradoraUniversoCedula))
    for c in cedulas:
        db.add(AseguradoraUniversoCedula(cedula=c[:20], usuario_id=usuario_id))
    db.commit()
    logger.info("[aseguradora] sync ok: %s cedulas", len(cedulas))
    return {"ok": True, "cantidad": len(cedulas), "spreadsheet_id": _sheet_id()}
