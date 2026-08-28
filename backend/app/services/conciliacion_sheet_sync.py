"""
Utilidades de lectura de Google Sheets (pestaña CONCILIACIÓN y otros documentos).

Helpers compartidos por aseguradora, cuotas hoja período, etc.
Credenciales: get_google_credentials (OAuth / cuenta de servicio) o pipeline Gmail.
"""
from __future__ import annotations

import logging
import time
from typing import Any, List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCOPES_SHEETS_FALLBACK = ["https://www.googleapis.com/auth/spreadsheets"]


def _build_sheets_service(creds: Any) -> Any:
    from googleapiclient.discovery import build

    timeout_sec = int(getattr(settings, "CONCILIACION_SHEET_GOOGLE_HTTP_TIMEOUT_SECONDS", 120) or 120)
    try:
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp

        http = AuthorizedHttp(creds, http=httplib2.Http(timeout=timeout_sec))
        return build("sheets", "v4", http=http, cache_discovery=False)
    except ImportError:
        logger.debug(
            "[conciliacion_sheet] Sheets client sin timeout HTTP configurado (%ss): faltan httplib2/google_auth_httplib2",
            timeout_sec,
        )
        return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _sheets_execute(request: Any) -> Any:
    from googleapiclient.errors import HttpError

    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            return request.execute()
        except HttpError as e:
            st = getattr(getattr(e, "resp", None), "status", None)
            if st in (429, 503) and attempt < max_attempts - 1:
                delay = (0.75 * (2**attempt)) + (0.03 * attempt)
                logger.warning(
                    "[conciliacion_sheet] Sheets HttpError status=%s reintento %s/%s tras_s=%.2f",
                    st,
                    attempt + 1,
                    max_attempts,
                    delay,
                )
                time.sleep(delay)
                continue
            raise


def _mask_spreadsheet_id(spreadsheet_id: str) -> str:
    s = (spreadsheet_id or "").strip()
    if not s:
        return "(vacío)"
    if len(s) <= 10:
        return f"{s[:3]}…(len={len(s)})"
    return f"{s[:4]}…{s[-4:]}(len={len(s)})"


def _col_letter_to_index1(col: str) -> int:
    n = 0
    for c in (col or "").strip().upper():
        if "A" <= c <= "Z":
            n = n * 26 + (ord(c) - ord("A") + 1)
    return max(n, 1)


def _parse_columns_range(spec: str) -> Tuple[str, str, int]:
    raw = (spec or "A:S").strip().upper().replace(" ", "")
    if ":" not in raw:
        return "A", "S", 19
    left, right = raw.split(":", 1)
    left = left.strip().upper() or "A"
    right = right.strip().upper() or "S"
    if not left.isalpha() or not right.isalpha():
        return "A", "S", 19
    i1, i2 = _col_letter_to_index1(left), _col_letter_to_index1(right)
    if i2 < i1:
        left, right, i1, i2 = right, left, i2, i1
    ncols = i2 - i1 + 1
    if ncols > 200:
        raise ValueError("CONCILIACION_SHEET_COLUMNS_RANGE excede el máximo permitido (200 columnas).")
    return left, right, ncols


def _titles_match(found: str, expected: str) -> bool:
    return (found or "").strip().casefold() == (expected or "").strip().casefold()


def _escape_sheet_title_for_range(title: str) -> str:
    return (title or "").replace("'", "''")


def _resolve_sheet_title(service: Any, spreadsheet_id: str, expected_tab: str) -> str:
    meta = _sheets_execute(
        service.spreadsheets().get(
            spreadsheetId=spreadsheet_id, fields="sheets(properties(title,sheetId))"
        )
    )
    sheets = meta.get("sheets") or []
    for s in sheets:
        title = (s.get("properties") or {}).get("title") or ""
        if _titles_match(title, expected_tab):
            return title
    titles = [(s.get("properties") or {}).get("title") for s in sheets]
    logger.warning(
        "[conciliacion_sheet] pestaña no encontrada: buscada=%r disponibles=%r spreadsheet=%s",
        expected_tab,
        titles,
        _mask_spreadsheet_id(spreadsheet_id),
    )
    raise ValueError(
        f"No se encontró la pestaña {expected_tab!r}. Pestañas disponibles: {titles!r}"
    )


def _get_sheets_credentials():
    from app.core.google_credentials import get_google_credentials

    creds = get_google_credentials(SCOPES_SHEETS_FALLBACK)
    if creds is not None:
        return creds
    creds = get_google_credentials(SCOPES_SHEETS)
    if creds is not None:
        return creds
    try:
        from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials

        creds = get_pagos_gmail_credentials()
        return creds
    except Exception as ex:
        logger.warning(
            "[conciliacion_sheet] credenciales Gmail no disponibles: %s",
            type(ex).__name__,
        )
        return None
